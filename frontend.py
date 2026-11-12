"""Streamlit 界面：PC/手机浏览器均可访问。"""
import os
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import qrcode
import requests
import streamlit as st

API = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
st.set_page_config(page_title="拾题 · 校园复习", page_icon="📚", layout="wide")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&display=swap');
:root{--sea:#126a8d;--sea2:#0e88aa;--ink:#18334a;--muted:#68849a;--line:#dbeaf3}
html,body,[data-testid="stApp"]{font-family:'Noto Sans SC',sans-serif;color:var(--ink)}
[data-testid="stAppViewContainer"]{background:linear-gradient(145deg,#f3faff 0%,#f8fbff 45%,#f2f8fc 100%)}
[data-testid="stHeader"]{background:transparent}
.block-container{max-width:1080px;padding-top:2.1rem;padding-bottom:4rem}
[data-testid="stSidebar"]{background:linear-gradient(175deg,#e6f5fb,#f4faff 70%);border-right:1px solid var(--line)}
[data-testid="stSidebar"] .stRadio label{border-radius:12px;padding:.28rem .5rem;transition:.15s}
[data-testid="stSidebar"] .stRadio label:hover{background:#d8eff8}
h1,h2,h3{color:var(--ink)!important;letter-spacing:-.025em}
h1{font-weight:750!important;font-size:2rem!important}
h2{font-size:1.47rem!important}
p,li{line-height:1.8}
[data-testid="stForm"],[data-testid="stExpander"],[data-testid="stFileUploader"],[data-testid="stCameraInput"],[data-testid="stVerticalBlockBorderWrapper"]{border-color:var(--line)!important;border-radius:16px!important}
[data-testid="stForm"]{background:#fff;border:1px solid var(--line)!important;padding:1.2rem!important;box-shadow:0 8px 28px rgba(27,88,125,.045)}
div[data-testid="stButton"] button,div[data-testid="stFormSubmitButton"] button{border-radius:12px;min-height:2.85rem;border:1px solid #c9dfeb;font-weight:650;transition:.16s}
div[data-testid="stButton"] button:hover,div[data-testid="stFormSubmitButton"] button:hover{color:#087a9e;border-color:#0a92b2;box-shadow:0 5px 14px rgba(10,128,170,.12)}
div[data-testid="stFormSubmitButton"] button[kind="primary"],div[data-testid="stButton"] button[kind="primary"]{background:linear-gradient(110deg,#126e97,#1597bb);border:none;color:white}
input,textarea{border-radius:10px!important}
[data-testid="stTabs"] button{font-weight:650}
[data-testid="stAlert"]{border-radius:12px}
.sea-hero{background:linear-gradient(125deg,#126c94,#178dac 62%,#58b8c5);color:white;padding:28px 32px;border-radius:22px;box-shadow:0 14px 36px rgba(23,111,151,.16);margin:.4rem 0 1.4rem;position:relative;overflow:hidden}
.sea-hero:after{content:"";position:absolute;width:220px;height:220px;border:1px solid rgba(255,255,255,.16);border-radius:50%;right:-55px;top:-105px;box-shadow:0 0 0 40px rgba(255,255,255,.06),0 0 0 85px rgba(255,255,255,.035)}
.sea-hero .eyebrow{font-size:.8rem;font-weight:700;letter-spacing:.15em;color:#cef3ff}
.sea-hero h2{font-size:1.85rem!important;color:white!important;margin:.45rem 0 .4rem;line-height:1.4}
.sea-hero p{color:#e7f9ff;font-size:.96rem;margin:0;max-width:620px}
.section-kicker{color:#177d9e;font-size:.81rem;font-weight:800;letter-spacing:.14em;margin:.75rem 0 .3rem}
.metric-tile{background:white;border:1px solid #dcebf3;border-radius:16px;padding:18px 20px;box-shadow:0 5px 20px rgba(33,102,137,.035);min-height:120px}
.metric-tile .num{font-size:1.9rem;font-weight:800;color:#176f95;line-height:1.3}
.metric-tile .label{font-size:.9rem;color:#71889b;margin-top:.4rem}
.feature-tile{border:1px solid #dcebf3;border-radius:18px;background:#fff;padding:21px 22px 16px;min-height:148px}
.feature-tile .symbol{font-size:1.45rem}
.feature-tile .heading{font-weight:800;color:#183f58;font-size:1.02rem;margin:.4rem 0}
.feature-tile .desc{font-size:.86rem;color:#6b8293;line-height:1.7}
.soft-heading{background:#e6f5fb;border-left:4px solid #198fb2;color:#1a5d7b;border-radius:0 10px 10px 0;padding:12px 16px;margin:1rem 0}
[data-testid="stMetric"]{background:#fff;border:1px solid var(--line);border-radius:14px;padding:16px}
@media(max-width:700px){.block-container{padding:1.15rem .85rem 3.5rem}.sea-hero{padding:22px 20px;border-radius:16px}.sea-hero h2{font-size:1.4rem!important}.metric-tile{min-height:100px;padding:13px}.metric-tile .num{font-size:1.4rem}h1{font-size:1.65rem!important}input,textarea{font-size:16px!important}.feature-tile{min-height:auto}}
</style>""", unsafe_allow_html=True)


def call(method, route, **kwargs):
    """统一请求：服务端请求本机 FastAPI，不要求手机能访问8000端口。"""
    headers = {"Authorization": "Bearer " + st.session_state.get("token", "")}
    try:
        response = requests.request(method, API + route, headers=headers, timeout=35, **kwargs)
        if response.status_code >= 400:
            st.error(response.json().get("detail", "请求失败"))
            return None
        return response.json()
    except requests.RequestException:
        st.error("无法连接后端，请先启动 FastAPI（8000端口）。")
        return None


st.markdown('<div class="section-kicker">SHITI · SMART REVIEW</div>', unsafe_allow_html=True)
st.title("拾题 · 校园复习")
st.caption("让每一道错题，都成为下一次进步的起点")


def show_qr():
    """直接使用 Render 提供的 HTTPS 链接，不需要用户安装扫码工具。"""
    address = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("DEMO_URL", "")
    if not address:
        st.info("公网部署后将自动显示二维码；目前请使用电脑终端显示的网址。")
        return
    img = qrcode.make(address)
    buf = BytesIO()
    img.save(buf, format="PNG")
    st.image(buf.getvalue(), width=240)
    st.code(address)
    st.caption("老师可投屏此二维码；同学用微信扫一扫或手机相机打开。")

if "token" not in st.session_state:
    with st.expander("📱 课堂扫码进入（老师投屏）"):
        show_qr()
    login_tab, register_tab = st.tabs(["登录", "注册"])
    with login_tab:
        with st.form("login"):
            name = st.text_input("用户名")
            password = st.text_input("密码", type="password")
            if st.form_submit_button("登录", use_container_width=True):
                result = call("POST", "/login", json={"username": name, "password": password})
                if result:
                    st.session_state.token, st.session_state.role = result["token"], result["role"]
                    st.rerun()
    with register_tab:
        with st.form("register"):
            name = st.text_input("新用户名")
            password = st.text_input("新密码（至少8位）", type="password")
            if st.form_submit_button("创建账号", use_container_width=True):
                if call("POST", "/register", json={"username": name, "password": password}):
                    st.success("注册成功，请切换到登录页。")
    st.stop()

with st.sidebar:
    st.markdown("### 📘 拾题空间")
    st.caption("错题积累 · 智能解析 · 复习巩固")
    page = st.radio("学习导航", ["学习概览", "拍照录题", "我的错题", "今日复习", "公开题库"] + (["管理员审核"] if st.session_state.get("role") == "admin" else []) + ["扫码访问"], key="nav_page")
    if st.button("退出登录"):
        call("POST", "/logout")
        st.session_state.clear()
        st.rerun()

if page == "学习概览":
    st.markdown("""<div class="sea-hero"><div class="eyebrow">YOUR LEARNING SPACE</div>
    <h2>今天，也向掌握知识更进一步。</h2>
    <p>把不会的题留下来，把会做的题带走。录题、解析、变式训练和间隔复习，在这里顺畅衔接。</p></div>""", unsafe_allow_html=True)
    overview = call("GET", "/questions")
    if overview is not None:
        today = datetime.now(timezone.utc)
        due_count = sum(datetime.fromisoformat(x["due"]) <= today for x in overview)
        tags_count = len({x["tag"] for x in overview if x["tag"] != "待归类"})
        cols = st.columns(3)
        for col, number, label in zip(cols, (len(overview), due_count, tags_count),
                                      ("已收录错题", "今日待复习", "知识点分类")):
            with col:
                st.markdown(f'<div class="metric-tile"><div class="num">{number}</div><div class="label">{label}</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-kicker">QUICK START</div>', unsafe_allow_html=True)
    st.subheader("开启学习")
    c1, c2, c3 = st.columns(3)
    tiles = [
        (c1, "📷", "拍照录题", "上传题目或直接拍照，整理错题并获得解析。", "去录题"),
        (c2, "🗂️", "我的错题", "按知识点管理积累，集中查看解析与变式题。", "看错题"),
        (c3, "📅", "今日复习", "依据复习安排，逐步巩固已学知识。", "开始复习"),
    ]
    def jump_to(section):
        st.session_state["nav_page"] = section

    for col, symbol, heading, desc, action in tiles:
        with col:
            st.markdown(f'<div class="feature-tile"><div class="symbol">{symbol}</div><div class="heading">{heading}</div><div class="desc">{desc}</div></div>', unsafe_allow_html=True)
            st.button(action, key=f"go_{heading}", use_container_width=True,
                      on_click=jump_to, args=(heading,))
    st.markdown('<div class="soft-heading">💡 学习建议：先记录卡住的步骤，再对照解析完成一题变式练习。</div>', unsafe_allow_html=True)

elif page == "拍照录题":
    st.markdown("""<div class="sea-hero"><div class="eyebrow">QUESTION CAPTURE</div>
    <h2>记录这道题，找到突破口</h2><p>拍照识别或手动输入，豆包辅助梳理知识点、解题步骤和同类练习。</p></div>""", unsafe_allow_html=True)
    st.subheader("① 添加题目")
    photo = st.file_uploader("上传照片（手机可直接选择拍照）", type=["png", "jpg", "jpeg"])
    # 手机 camera_input 支持直接调用相机（部分浏览器需要 HTTPS 权限）。
    camera = st.camera_input("或直接拍照")
    chosen = camera or photo
    if chosen and st.button("OCR 识别图片", use_container_width=True):
        result = call("POST", "/ocr", files={"file": (chosen.name, chosen.getvalue(), "image/jpeg")})
        if result:
            st.session_state.ocr_text = result["text"]
            st.session_state.image = result["image"]
            if not result["ocr_ok"]:
                st.warning(result["hint"])
    st.subheader("② 补充信息并分析")
    with st.form("create"):
        question = st.text_area("题目文字（可修正OCR结果）", value=st.session_state.get("ocr_text", ""), height=160)
        tag = st.text_input("知识点标签", value="待归类")
        source = st.text_input("来源声明", value="本人手写整理")
        if st.form_submit_button("保存到我的错题并分析", use_container_width=True):
            result = call("POST", "/questions", json={"text": question, "tag": tag, "source": source, "image": st.session_state.get("image", "")})
            if result:
                st.success("已保存至我的错题")
                st.markdown("### ✨ 本题学习报告")
                st.info("分析方式：" + result["mode"])
                st.write("知识点：", tag if tag.strip() and tag != "待归类" else result["tag"], "\n\n错因：", result["cause"])
                st.write("解析：", result["explanation"])
                st.write("变式题：", result["variant"], "\n\n参考答案：", result["answer"])
                st.session_state.pop("ocr_text", None)
                st.session_state.pop("image", None)

elif page in ("我的错题", "今日复习"):
    items = call("GET", "/questions") or []
    st.markdown('<div class="section-kicker">MY LEARNING COLLECTION</div>', unsafe_allow_html=True)
    st.subheader("今日复习计划" if page == "今日复习" else "我的错题库")
    tags = sorted({x["tag"] for x in items})
    picked = st.selectbox("按知识点筛选", ["全部"] + tags)
    items = [x for x in items if picked == "全部" or x["tag"] == picked]
    if page == "今日复习":
        items = [x for x in items if datetime.fromisoformat(x["due"]) <= datetime.now(timezone.utc)]
    st.caption(f"当前显示 {len(items)} 道题目 · 点击卡片展开完整解析与练习")
    for item in items:
        with st.expander(f"#{item['id']} · {item['tag']} · {item['text'][:35]}"):
            st.write(item["text"])
            st.caption(f"状态：{item['status']} | 分析：{item['mode']} | 下次复习：{item['due'][:10]}")
            st.write("错因：", item["cause"])
            st.write("解析：", item["explanation"])
            st.write("变式题：", item["variant"])
            with st.popover("查看变式答案"):
                st.write(item["answer"])
            edited = st.text_input("修改标签", value=item["tag"], key=f"tag{item['id']}")
            if st.button("保存标签", key=f"save{item['id']}"):
                if call("PATCH", f"/questions/{item['id']}/tag", json={"tag": edited}):
                    st.rerun()
            col1, col2 = st.columns(2)
            with col1:
                if st.button("记住了", key=f"yes{item['id']}", use_container_width=True):
                    if call("POST", f"/questions/{item['id']}/review", params={"remembered": True}):
                        st.rerun()
            with col2:
                if st.button("还没记住", key=f"no{item['id']}", use_container_width=True):
                    if call("POST", f"/questions/{item['id']}/review", params={"remembered": False}):
                        st.rerun()
            if item["status"] in ("private", "rejected"):
                if st.button("提交公开审核", key=f"submit{item['id']}"):
                    res = call("POST", f"/questions/{item['id']}/submit")
                    if res:
                        st.warning(res["note"]) if res["status"] == "rejected" else st.success("已提交，等待管理员审核")
                        st.rerun()

elif page == "公开题库":
    st.subheader("🌐 校园共建题库")
    st.caption("仅展示审核通过的题目，尊重学习资料来源与原创权益。")
    items = call("GET", "/public") or []
    for item in items:
        with st.expander(f"{item['tag']} · {item['text'][:42]}"):
            st.write(item["text"])
            st.write("解析：", item["explanation"])
            st.write("变式题：", item["variant"])

elif page == "管理员审核":
    st.subheader("公开投稿人工审核")
    st.warning("请核实原创性和授权；规则初审通过不代表版权安全。")
    for item in call("GET", "/admin/pending") or []:
        with st.expander(f"待审 #{item['id']} · {item['tag']}"):
            st.write(item["text"])
            st.caption("来源：" + item["source"])
            note = st.text_input("审核备注", key=f"note{item['id']}")
            a, b = st.columns(2)
            for col, approved, title in [(a, True, "通过"), (b, False, "驳回")]:
                with col:
                    if st.button(title, key=f"audit{approved}{item['id']}", use_container_width=True):
                        if call("POST", f"/admin/{item['id']}", json={"approved": approved, "note": note}):
                            st.rerun()

elif page == "扫码访问":
    st.subheader("用手机扫码体验")
    st.write("公网部署后，手机使用微信或其他浏览器扫码即可访问，无需连接同一 Wi-Fi。")
    public_file = Path(__file__).resolve().parent / "data" / "public_url.txt"
    address = public_file.read_text(encoding="utf-8").strip() if public_file.exists() else (os.getenv("RENDER_EXTERNAL_URL") or os.getenv("DEMO_URL", ""))
    if public_file.exists():
        st.success("公网演示模式：其他 Wi-Fi 或手机流量均可访问。")
    if address:
        img = qrcode.make(address)
        buf = BytesIO()
        img.save(buf, format="PNG")
        st.image(buf.getvalue(), width=240)
        st.code(address)
    else:
        st.info("请使用 python launch.py 启动，程序会显示二维码及手机地址。")
