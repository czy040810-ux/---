"""Streamlit 界面：PC/手机浏览器均可访问。"""
import os
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import qrcode
import requests
import streamlit as st

API = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
st.set_page_config(page_title="拾题 · 校园复习", page_icon="📚", layout="centered")
st.markdown("""<style>
.block-container{max-width:800px;padding-top:1.5rem;padding-bottom:2rem}
h1{color:#176b8c;font-size:2rem} div[data-testid='stButton'] button{min-height:2.7rem}
@media(max-width:600px){.block-container{padding:1rem .8rem 4rem}h1{font-size:1.65rem}
div[data-testid='stHorizontalBlock']{gap:.5rem}input,textarea{font-size:16px!important}}
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


st.title("📚 拾题 · 校园复习")
st.caption("拍照记录 · 知识点复习 · 校园共建题库")


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
    page = st.radio("功能导航", ["拍照录题", "我的错题", "今日复习", "公开题库"] + (["管理员审核"] if st.session_state.get("role") == "admin" else []) + ["扫码访问"])
    if st.button("退出登录"):
        call("POST", "/logout")
        st.session_state.clear()
        st.rerun()

if page == "拍照录题":
    st.subheader("录入错题")
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
    with st.form("create"):
        question = st.text_area("题目文字（可修正OCR结果）", value=st.session_state.get("ocr_text", ""), height=160)
        tag = st.text_input("知识点标签", value="待归类")
        source = st.text_input("来源声明", value="本人手写整理")
        if st.form_submit_button("保存到我的错题并分析", use_container_width=True):
            result = call("POST", "/questions", json={"text": question, "tag": tag, "source": source, "image": st.session_state.get("image", "")})
            if result:
                st.success("保存成功")
                st.info("分析方式：" + result["mode"])
                st.write("知识点：", result["tag"], "\n\n错因：", result["cause"])
                st.write("解析：", result["explanation"])
                st.write("变式题：", result["variant"], "\n\n参考答案：", result["answer"])
                st.session_state.pop("ocr_text", None)
                st.session_state.pop("image", None)

elif page in ("我的错题", "今日复习"):
    items = call("GET", "/questions") or []
    tags = sorted({x["tag"] for x in items})
    picked = st.selectbox("按知识点筛选", ["全部"] + tags)
    items = [x for x in items if picked == "全部" or x["tag"] == picked]
    if page == "今日复习":
        items = [x for x in items if datetime.fromisoformat(x["due"]) <= datetime.now(timezone.utc)]
    st.write(f"共 {len(items)} 道")
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
    st.subheader("审核通过的共建内容")
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
    st.write("电脑和手机需连接同一个 Wi-Fi；电脑防火墙需允许 TCP 8501 端口。")
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
