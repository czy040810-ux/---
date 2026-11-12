"""独立的识别、分析、版权初审与复习算法。"""
import json
import os
import re
from datetime import datetime, timedelta, timezone
from io import BytesIO
from urllib.request import Request, urlopen
from urllib.error import HTTPError


def now():
    """统一使用 UTC 时间存储，便于跨设备。"""
    return datetime.now(timezone.utc)


def next_review(level, remembered):
    """简化版艾宾浩斯阶梯：1/2/4/7/15/30 天；忘记则回到第一级。"""
    intervals = [1, 2, 4, 7, 15, 30]
    new_level = min(level + 1, len(intervals)) if remembered else 0
    days = intervals[new_level - 1] if remembered else 1
    return new_level, (now() + timedelta(days=days)).isoformat()


def copyright_check(text, source):
    """仅规则初审：识别明显违规声明，无法证明一题的真实版权归属。"""
    value = f"{text} {source}".lower()
    banned = ["整本教材", "整章原文", "付费教辅原题", "付费题库原题", "盗版", "扫描整本", "paid question bank"]
    if any(word in value for word in banned):
        return "rejected", "疑似整本教材或付费教辅搬运：仅允许提交自己整理的手写错题和笔记。"
    if len(text) > 3000 or len(re.findall(r"第\s*\d+\s*[章节]", text)) >= 3:
        return "rejected", "内容疑似大段教材摘录：请只提交自己整理的单题或笔记。"
    return "pending", "自动初审未发现明显风险；仍需管理员核实来源后公开。"


def ocr_image(data):
    """本地 Tesseract OCR；安装程序和中文训练数据后才能识别中文。"""
    from PIL import Image
    import pytesseract
    image = Image.open(BytesIO(data)).convert("RGB")
    return pytesseract.image_to_string(image, lang=os.getenv("OCR_LANG", "chi_sim+eng")).strip()


class ModelAPIError(Exception):
    """对用户提供不含密钥、连接地址和题目内容的模型错误说明。"""


def explain_model_http_error(exc):
    status = exc.code
    code = ""
    try:
        payload = json.loads(exc.read(2048).decode("utf-8", errors="replace"))
        code = str(payload.get("error", {}).get("code", ""))[:100]
    except (ValueError, AttributeError, TypeError):
        pass
    if status == 401:
        return "豆包接口认证失败（401）：请检查 AI_API_KEY 是否为火山方舟 API Key。"
    if status == 403:
        return "豆包接口拒绝访问（403）：请检查 API Key 权限、账号余额与模型开通状态。"
    if status == 404:
        return "豆包模型不可访问（404）：请在火山方舟开通 AI_MODEL 对应模型，或核对模型 ID。"
    if status == 429:
        return "豆包调用次数或额度受限（429）：请稍后再试并检查配额。"
    if status == 400:
        return "豆包请求参数错误（400）：请核对模型与接口配置。"
    return f"豆包接口返回 HTTP {status}"


def analyze(text):
    """可选 OpenAI 兼容接口；未配置时明确返回模拟结果。"""
    key, url, model = (os.getenv(k, "") for k in ("AI_API_KEY", "AI_BASE_URL", "AI_MODEL"))
    if key and url and model:
        # 限制输入、输出长度；不记录密钥和题目全文。
        prompt = (
            "你是大学课程错题辅导老师。请严谨解题、检查计算和最终答案。"
            "仅输出一个合法JSON对象，恰好包含五个字符串字段："
            "tag(知识点，10字内)、cause(可能错因，无法判断时写'需学生自述错因')、"
            "explanation(分步骤解析，120字内)、variant(同知识点新题，70字内)、"
            "answer(新题正确答案和简要过程，70字内)。不要Markdown。"
            "题目：" + text[:1200]
        )
        # 不启用深度思考，控制输入和输出量；密钥只在服务端使用。
        payload = {"model": model, "max_tokens": 550,
                   "thinking": {"type": "disabled"},
                   "messages": [{"role": "user", "content": prompt}]}
        # 火山方舟正式数据面基址为 .../api/v3；同时兼容完整URL和旧版/v1。
        base = url.rstrip("/")
        endpoint = base if base.endswith("/chat/completions") else base + "/chat/completions"
        request = Request(endpoint, data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
        try:
            with urlopen(request, timeout=25) as resp:
                content = json.load(resp)["choices"][0]["message"]["content"]
        except HTTPError as exc:
            raise ModelAPIError(explain_model_http_error(exc)) from None
        content = re.sub(r"^```(?:json)?|```$", "", content.strip(), flags=re.I).strip()
        result = json.loads(content)
        if not isinstance(result, dict) or not all(k in result and isinstance(result[k], str) for k in ("tag", "cause", "explanation", "variant", "answer")):
            raise ValueError("模型返回格式不符合要求")
        return {k: result[k][:300] for k in ("tag", "cause", "explanation", "variant", "answer")} | {"mode": "豆包真实模型分析"}
    return {"tag": "待归类", "cause": "需自行核对错因", "explanation": "演示模式未接入大模型，请根据教材或课堂笔记手动完善解析。",
            "variant": "请尝试替换原题中的数字或条件，并重新求解。", "answer": "请自行核对答案。", "mode": "本地模拟（非AI分析）"}
