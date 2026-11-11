"""FastAPI 后端：最小化账号、私有错题和人工审核公共库。"""
import hashlib
import os
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

from .services import analyze, copyright_check, next_review, now, ocr_image

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.getenv("DATA_DIR", str(ROOT / "data"))).resolve()
DATA.mkdir(exist_ok=True)
DB = DATA / "wrongbook.db"
UPLOADS = DATA / "uploads"
UPLOADS.mkdir(exist_ok=True)
app = FastAPI(title="校园错题复习本")


@app.get("/health")
def health():
    """容器和反向代理健康检查：不暴露数据库内容。"""
    return {"status": "ok"}


@contextmanager
def db():
    """每个请求独立连接；事务结束后关闭。"""
    conn = sqlite3.connect(DB, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=10000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()
    return f"{salt}${digest}"


def init():
    with db() as c:
        # 演示环境多名同学并发读写时，WAL 可减少读写互相阻塞。
        c.execute("PRAGMA journal_mode=WAL")
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user');
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, expires TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS questions(id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL, text TEXT NOT NULL, image TEXT, tag TEXT NOT NULL DEFAULT '待归类', cause TEXT DEFAULT '', explanation TEXT DEFAULT '', variant TEXT DEFAULT '', answer TEXT DEFAULT '', mode TEXT DEFAULT '', level INTEGER DEFAULT 0, due TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'private', source TEXT DEFAULT '', review_note TEXT DEFAULT '', created TEXT NOT NULL);
        """)
        # 管理员由环境变量首次创建；无默认公开弱密码。
        username, password = os.getenv("ADMIN_USER"), os.getenv("ADMIN_PASSWORD")
        if username and password and len(password) >= 8:
            c.execute("INSERT OR IGNORE INTO users(username,password,role) VALUES(?,?,'admin')", (username, password_hash(password)))


init()


class Auth(BaseModel):
    username: str = Field(min_length=2, max_length=30, pattern=r"^[\w\u4e00-\u9fff]+$")
    password: str = Field(min_length=8, max_length=100)


class Question(BaseModel):
    text: str = Field(min_length=2, max_length=5000)
    tag: str = Field(default="待归类", max_length=50)
    source: str = Field(default="本人手写整理", max_length=150)
    image: str = Field(default="", max_length=150)


class Update(BaseModel):
    tag: str = Field(min_length=1, max_length=50)


class Review(BaseModel):
    approved: bool
    note: str = Field(default="", max_length=200)


def current(authorization: str = Header(default="")):
    token = authorization.removeprefix("Bearer ").strip()
    with db() as c:
        row = c.execute("SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>?", (token, now().isoformat())).fetchone()
    if not row:
        raise HTTPException(401, "请先登录")
    return dict(row)


def owned(c, qid, uid):
    row = c.execute("SELECT * FROM questions WHERE id=? AND owner_id=?", (qid, uid)).fetchone()
    if not row:
        raise HTTPException(404, "错题不存在或无权访问")
    return row


@app.post("/register")
def register(body: Auth):
    try:
        with db() as c:
            c.execute("INSERT INTO users(username,password) VALUES(?,?)", (body.username, password_hash(body.password)))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "用户名已存在")
    return {"message": "注册成功"}


@app.post("/login")
def login(body: Auth):
    with db() as c:
        user = c.execute("SELECT * FROM users WHERE username=?", (body.username,)).fetchone()
        if not user or not secrets.compare_digest(password_hash(body.password, user["password"].split("$")[0]), user["password"]):
            raise HTTPException(401, "用户名或密码错误")
        token = secrets.token_urlsafe(32)
        from datetime import timedelta
        c.execute("INSERT INTO sessions VALUES(?,?,?)", (token, user["id"], (now() + timedelta(hours=8)).isoformat()))
    return {"token": token, "role": user["role"]}


@app.post("/logout")
def logout(user=Depends(current), authorization: str = Header(default="")):
    with db() as c:
        c.execute("DELETE FROM sessions WHERE token=? AND user_id=?", (authorization.removeprefix("Bearer ").strip(), user["id"]))
    return {"message": "已退出"}


@app.post("/ocr")
async def ocr(file: UploadFile = File(...), user=Depends(current)):
    data = await file.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(413, "图片不得超过5MB")
    from PIL import Image, UnidentifiedImageError
    from io import BytesIO
    try:
        pic = Image.open(BytesIO(data))
        pic.verify()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(400, "请上传有效图片")
    name = secrets.token_hex(16) + ".png"
    # 重新编码而非保存原始上传文件；去除原始元数据。
    pic = Image.open(BytesIO(data)).convert("RGB")
    if pic.width * pic.height > 16_000_000:
        raise HTTPException(413, "图片尺寸过大")
    pic.save(UPLOADS / name, "PNG")
    try:
        extracted = ocr_image(data)
        return {"text": extracted, "image": name, "ocr_ok": True}
    except Exception:
        return {"text": "", "image": name, "ocr_ok": False, "hint": "本机OCR不可用，请手动填写识别文本"}


@app.post("/questions")
def create(body: Question, user=Depends(current)):
    # 图片名受控且只允许本站生成的随机文件名。
    import re
    if body.image and (not re.fullmatch(r"[0-9a-f]{32}\.png", body.image) or not (UPLOADS / body.image).exists()):
        raise HTTPException(400, "图片标识无效")
    try:
        result = analyze(body.text)
    except Exception as e:
        raise HTTPException(502, f"模型调用失败，请检查配置：{type(e).__name__}")
    with db() as c:
        cursor = c.execute("INSERT INTO questions(owner_id,text,image,tag,cause,explanation,variant,answer,mode,due,source,created) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                           (user["id"], body.text, body.image, body.tag if body.tag != "待归类" else result["tag"], result["cause"], result["explanation"], result["variant"], result["answer"], result["mode"], now().isoformat(), body.source, now().isoformat()))
        return {"id": cursor.lastrowid, **result}


@app.get("/questions")
def mine(tag: str = "", user=Depends(current)):
    with db() as c:
        return [dict(x) for x in c.execute("SELECT * FROM questions WHERE owner_id=? AND (?='' OR tag=?) ORDER BY due ASC", (user["id"], tag, tag)).fetchall()]


@app.patch("/questions/{qid}/tag")
def update_tag(qid: int, body: Update, user=Depends(current)):
    with db() as c:
        owned(c, qid, user["id"])
        c.execute("UPDATE questions SET tag=? WHERE id=?", (body.tag, qid))
    return {"message": "已更新"}


@app.post("/questions/{qid}/review")
def practice(qid: int, remembered: bool, user=Depends(current)):
    with db() as c:
        row = owned(c, qid, user["id"])
        level, due = next_review(row["level"], remembered)
        c.execute("UPDATE questions SET level=?, due=? WHERE id=?", (level, due, qid))
    return {"level": level, "due": due}


@app.post("/questions/{qid}/submit")
def submit(qid: int, user=Depends(current)):
    with db() as c:
        row = owned(c, qid, user["id"])
        status, note = copyright_check(row["text"], row["source"])
        c.execute("UPDATE questions SET status=?,review_note=? WHERE id=?", (status, note, qid))
    return {"status": status, "note": note}


@app.get("/public")
def public(tag: str = ""):
    with db() as c:
        # 公开接口不泄漏 owner_id、图片路径、私人来源等信息。
        return [dict(x) for x in c.execute("SELECT id,text,tag,explanation,variant,answer FROM questions WHERE status='approved' AND (?='' OR tag=?) ORDER BY id DESC", (tag, tag)).fetchall()]


@app.get("/admin/pending")
def pending(user=Depends(current)):
    if user["role"] != "admin":
        raise HTTPException(403, "仅管理员可审核")
    with db() as c:
        return [dict(x) for x in c.execute("SELECT id,text,tag,source,review_note FROM questions WHERE status='pending' ORDER BY id DESC")]


@app.post("/admin/{qid}")
def approve(qid: int, body: Review, user=Depends(current)):
    if user["role"] != "admin":
        raise HTTPException(403, "仅管理员可审核")
    with db() as c:
        row = c.execute("SELECT * FROM questions WHERE id=? AND status='pending'", (qid,)).fetchone()
        if not row:
            raise HTTPException(404, "没有待审内容")
        status, reason = copyright_check(row["text"], row["source"])
        if status == "rejected":
            raise HTTPException(400, reason)
        c.execute("UPDATE questions SET status=?,review_note=? WHERE id=?", ("approved" if body.approved else "rejected", body.note or ("人工审核通过" if body.approved else "人工审核驳回"), qid))
    return {"message": "审核完成"}
