# 拾题：Docker、Render 和课堂扫码使用

## 0. 先明确一个限制

**Render Free Web Service 不支持持久磁盘。** 免费容器在休眠、重启和重新部署后，本地 SQLite 及上传图片可能全部丢失。项目保留 SQLite，但在 Render 免费档只能作为**临时课堂演示数据**，不能称为免费持久化。若要求账号、错题长期保存：

- 继续使用 SQLite：选择 Render 付费实例并挂载持久磁盘 `/app/data`；或者部署在其他提供真正免费持久卷的主机上（需自行核实条款）。
- 坚持 Render 免费档：只能接受数据随时丢失，课堂上使用测试账号和非敏感示例。
- 若可更换数据库：可改用外部托管数据库，但会偏离“SQLite 本地持久化”的需求。

参考：[Render Free 服务说明](https://render.com/docs/free)、[Render 磁盘说明](https://render.com/docs/disks)。

## 1. 项目结构

```text
ai_wrongbook/
├── Dockerfile            # Python + Tesseract 中文OCR + Streamlit + FastAPI
├── docker-compose.yml    # 本地容器编排，具名卷持久化
├── render.yaml           # Render 免费 Web Service Blueprint
├── .dockerignore         # 排除敏感文件和数据库
├── .env.example          # 环境变量模板（无真实密钥）
├── start.sh              # 在一个容器中启动前后端
├── frontend.py           # 自适应手机与微信内浏览器
├── backend/              # 用户、错题、审核、OCR、复习算法
├── miniprogram/          # 原生微信小程序版本（独立于H5）
└── requirements.txt
```

访问路线：手机/微信内置浏览器 → `https://你的服务.onrender.com` → Streamlit（公网 $PORT） → 本机 FastAPI（仅 127.0.0.1:8000） → SQLite（`DATA_DIR`）。

## 2. Docker 本地验证（开发者操作，普通同学不需要）

在项目目录复制 `.env.example` 为 `.env` 并更改随机管理员密码。不得上传 `.env` 到 GitHub。

```bash
docker compose up --build -d
docker compose ps
```

浏览器访问 `http://localhost:8501`。后台管理员账号由 `ADMIN_USER` 和 `ADMIN_PASSWORD` 首次建库时创建。本地 `shiti_data` Docker 卷可在重启后保留 SQLite 与图片。停止：`docker compose down`（**不要**加 `-v`，否则会删除卷）。

## 3. Render 免费部署步骤

1. 在 GitHub 建立**私有仓库**，将 `ai_wrongbook` 目录中的源码提交为仓库根目录（必须让根目录直接包含 `Dockerfile`、`render.yaml`、`backend/` 和 `frontend.py`）。不要上传 `.env`、`data/`、`*.db` 或私人图片。
2. 打开 [Render Dashboard](https://dashboard.render.com/)，登录后选择 **New → Blueprint**，连接这个 GitHub 仓库，选择 `render.yaml`。也可使用 **New → Web Service**，选择 Docker、Free 实例，Dockerfile Path 为 `./Dockerfile`。
3. 创建时在 Render 环境变量中填写：

   | 变量 | 要填的值 |
   |---|---|
   | `ADMIN_USER` | 自定义管理员用户名，例如 `teacher` |
   | `ADMIN_PASSWORD` | 独立、随机且至少 8 位的密码 |
   | `AI_API_KEY` | 可留空；接真实模型时才填写 |
   | `AI_BASE_URL` | 与模型供应商兼容的接口基址，可留空 |
   | `AI_MODEL` | 模型名称，可留空 |

   `PORT` 由 Render 提供，`BACKEND_URL` 已在 Dockerfile 设置。**不要把密钥写进代码、Dockerfile、GitHub 或公开演示截图。**
4. 点击部署，等待状态为 **Live**。打开 Render 提供的 `https://<服务名>.onrender.com` 地址检查登录页。如果页面显示无法连接后端，检查 Logs 内 FastAPI 是否启动并监听 127.0.0.1:8000。
5. 先注册学生 A/B 账号，测试错题隔离；再使用管理员账号审核公开题库。建议同学正式扫码前，在课堂里测试至少 5～10 台不同手机。

**免费实例注意事项：** 闲置后可能休眠，下一次唤醒需要约一分钟；不要在上课前最后一分钟才第一次打开。SQLite 和上传图片随实例生命周期丢失，务必用测试数据。单实例资源可能难以承受同时几十人 OCR 和模型请求；先做并发测试。

## 4. 微信内置浏览器兼容性

- Streamlit 页面使用窄屏布局和较大的触控按钮，无需安装 App。
- 在 HTTPS 公网链接下，部分微信版本允许网页相机授权，`拍照录题` 页同时保留图片上传；若微信 WebView 禁止直接调相机，则使用“从相册选择”或“拍照后上传”。
- 账号和上传内容留在后端，微信内打开不代表微信授权登录；不要把微信账号资料当作小程序账号同步。
- 真机兼容性未在此执行环境完成验证，尤其需检查 iOS 微信、Android 微信、图片权限与上传限制。

## 5. 生成二维码及课堂展示

**最简单方式（无需额外网站）：** Render 部署成功后，打开登录页顶部的“📱 课堂扫码进入（老师投屏）”，展开即可显示以 `RENDER_EXTERNAL_URL` 生成的二维码；投屏让学生扫。

也可以自行生成图片：

```bash
python -c "import qrcode; qrcode.make('https://替换为实际地址.onrender.com').save('shiti-qr.png')"
```

此命令仅由老师/开发者执行，学生无需安装 Python 或 Docker。二维码图片不要使用示例地址，需替换成 Render 实际 URL。

## 6. 一节课的推荐验收流程

1. 上课前打开 Render 链接，等待服务唤醒并确认登录正常。
2. 教师投屏二维码，学生在不同移动网络和 Wi-Fi 环境扫码。
3. 学生独立注册、上传手写错题、查看识别结果并修正文字。
4. 查看知识点标签、错因解析、变式题及下一次复习日期。
5. 用教师账号完成公共题库审核；不同学生只看自己私有错题。
6. 记录同时在线人数、上传失败率、响应时间；出错时保存非敏感日志。

## 7. 不属于免费部署交付的能力

- 免费 Render + **真实持久 SQLite**：Render 当前平台能力不支持。
- 长期可用的真实 AI 分析：需要单独的模型调用额度；未设置 API 时软件明确标注“本地模拟”。
- 无限量并发：Render Free 的资源与休眠策略不提供此保证。
- 正式微信小程序发布：这里提供的是**微信内浏览器 H5 扫码版**，不是微信官方小程序码；原生小程序项目仍位于 `miniprogram/`，两者独立。
