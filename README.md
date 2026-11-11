# 拾题：大学生 AI 复习错题本（课程演示版）

> **新增微信小程序原生前端**：位于 `miniprogram/`，导入、AppID 设置、HTTPS 后端域名、审核发布以及课堂多人验收步骤详见 [`miniprogram/README.md`](miniprogram/README.md)。原有 Streamlit 网页演示入口保留，互不影响。

> **新增 Docker + Render 扫码网页演示版**：见 [`RENDER_DEPLOY.md`](RENDER_DEPLOY.md)。Docker Compose 本地具名卷可持久保存 SQLite；**Render 免费 Web Service 不支持持久磁盘**，其 SQLite 数据随休眠、重启或重新部署可能丢失。网页二维码不是微信官方小程序码。

## 一、项目简介

拾题以“拍照录入—分析整理—间隔复习—审核共建”为主线，帮助大学生整理个人错题，并在经过审核后共享原创学习资料。后端 FastAPI、SQLite；前端 Streamlit，支持手机浏览器。用户账号、个人错题、复习计划均保存在演示电脑的 SQLite 数据库里。

## 二、目录

```text
ai_wrongbook/
├── backend/
│   ├── __init__.py       # 后端包
│   ├── main.py           # API、登录、数据隔离、审核
│   └── services.py       # OCR、模型接入、版权初审、复习算法
├── data/                 # 运行时自动创建；数据库及上传图片
├── frontend.py           # 手机/电脑界面
├── miniprogram/          # 原生微信小程序：7个页面 + 接口封装
├── launch.py             # 本地或公网扫码一键启动
├── requirements.txt      # Python依赖
├── tests/test_app.py     # 核心接口验证
└── README.md             # 本文件
```

## 三、安装与启动

推荐 Python 3.11 或 3.12。进入 `ai_wrongbook` 目录后：

```bash
python -m venv .venv
# Windows PowerShell：
.venv\Scripts\Activate.ps1
# macOS/Linux 改用：source .venv/bin/activate
python -m pip install -r requirements.txt
```

首次运行前设置管理员账号（密码至少8位，后续启动保持一致；只有第一次创建时读取）：

```powershell
# Windows PowerShell
$env:ADMIN_USER="teacher"
$env:ADMIN_PASSWORD="请替换为至少8位的专用密码"
python launch.py
```

```bash
# macOS/Linux
export ADMIN_USER=teacher
export ADMIN_PASSWORD='请替换为至少8位的专用密码'
python launch.py
```

电脑访问 `http://127.0.0.1:8501`。本地模式下，手机与电脑连同一 Wi-Fi，扫描终端二维码；如果电脑有多个网卡，可设置 `DEMO_LAN_IP` 为实际局域网 IPv4 地址，防火墙允许 8501 端口。**后端 8000 端口仅绑定 127.0.0.1。**

### 不同网络的手机扫码（推荐答辩展示）

1. 从 [Cloudflare 官方下载页](https://developers.cloudflare.com/tunnel/downloads/) 安装 `cloudflared`，确保 `cloudflared --version` 可执行。
2. 使用上面的管理员环境变量，然后执行：

   ```bash
   python launch.py --public
   ```

3. 等待控制台输出 `https://...trycloudflare.com` 地址及二维码。手机使用流量或其他 Wi-Fi 扫码即可。应用内“扫码访问”也会展示该二维码。

临时公网入口不要求购买域名或注册 Cloudflare 账号。**电脑需一直开机联网、终端不能关闭，重启后链接会变化；链接知道的人都能访问，请仅录入演示数据，演示结束按 Ctrl+C 关闭。** 建议使用专用测试密码，不要用真实账户密码或上传敏感试卷。

如运行环境阻断 Cloudflare 连接，请先检查网络策略；本项目不保证在所有校园网可建立隧道。需要固定地址和长期运行时应独立部署，并补充安全控制。

## 四、OCR 和大模型设置

- OCR：Python 包 `pytesseract` 只是调用器，需另装免费的 **Tesseract OCR** 程序及 `chi_sim` 中文语言数据；否则界面自动提示改用手工输入。照片始终可作为录入依据。
- 大模型：默认**本地模拟模式**（不是真实 AI 识别或推理，界面会显示）。如已有兼容 OpenAI Chat Completions 的接口，设置 `AI_API_KEY`、`AI_BASE_URL` 和 `AI_MODEL` 三个环境变量即可尝试调用。接口可能计费，费用由用户的服务商承担；单题限制 1200 字输入、300 `max_tokens` 输出。
- 真实模型的错误、幻觉或 JSON 格式问题需要人工核查；本项目不保证解析正确。

## 五、功能与复习规则

| 功能 | 演示操作 |
|---|---|
| 账号 | 注册两个普通账号，分别登录 |
| 私有错题 | A 创建后 B 无法查看或修改 |
| OCR | 上传图片识别，或手工修订 |
| 智能分析 | 生成知识点、错因、解析、变式题及答案；无 API 时明确模拟 |
| 标签筛选 | 在“我的错题”修改标签并筛选 |
| 间隔复习 | “记住了”按 1、2、4、7、15、30 天递进；“没记住”重置并安排次日 |
| 内容共建 | 用户申请公开 → 规则初审 → 管理员审核 → 公共库显示 |
| 版权风控 | 检测明显的大段摘录/付费原题声明立即驳回；其余必须人工核实 |
| 移动端 | 手机浏览器打开二维码链接，可拍照录题 |

复习模型是“艾宾浩斯思想的简化间隔阶梯”，不是严格还原心理学实验的个性化记忆模型。

## 六、建议答辩演示（约 5 分钟）

1. 电脑运行 `python launch.py --public`，用另一网络的手机扫码打开。
2. 注册学生 A，拍照或输入一道自己整理的错题，保存并展示解析与变式题。
3. 给错题打“函数”标签，展示筛选；点击“记住了”，展示下次复习日期。
4. 申请公开，显示“等待管理员审核”；改用管理员账户审核通过，公共题库出现这道题。
5. 提交含“付费教辅原题”的测试题，显示自动驳回与合规提示。
6. 用学生 B 账号确认无法看见学生 A 私有错题，但可查看审核通过的公共内容。

## 七、局限与后续优化

1. 版权判断仅是启发式关键词和篇幅规则，**无法确认某题真实来源和授权状态**；公开发布前需人工核查，不能依赖规则作为法律结论。
2. 当前数据库和上传图片都存于演示电脑，尚无加密备份、找回密码、审计日志与完整账号安全体系；不适合生产公网长期服务。
3. 尚无 OCR 版面还原、公式识别及题图在前端回显；低质量图片可能识别失败。
4. 模型回答需要事实核查；未来可加入教师知识库、公式 OCR、错因人工编辑和结果缓存降成本。
5. 未来可扩展真正的动态记忆参数、错题统计图、教研组权限、稳定域名、文件访问鉴权、限流、审核留痕与合规评估。

## 八、运行测试

安装测试工具：`python -m pip install pytest httpx`，然后在项目目录执行：

```bash
python -m pytest -q
```

本项目只用于课堂演示；不要上传未经授权的教材整本、付费教辅原题或含个人隐私的图片。
