"""独立的识别、分析、版权初审与复习算法。"""
import json
import os
import re
from datetime import datetime, timedelta, timezone
from io import BytesIO
from urllib.request import Request, urlopen


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


def analyze(text):
    """可选 OpenAI 兼容接口；未配置时明确返回模拟结果。"""
    key, url, model = (os.getenv(k, "") for k in ("AI_API_KEY", "AI_BASE_URL", "AI_MODEL"))
    if key and url and model:
        # 限制输入、输出长度；不记录密钥和题目全文。
        prompt = "请分析这道错题。只返回JSON对象，字段tag,cause,explanation,variant,answer；每字段不超过90字。题目：" + text[:1200]
        payload = {"model": model, "temperature": 0.2, "max_tokens": 300,
                   "messages": [{"role": "user", "content": prompt}]}
        endpoint = url.rstrip("/") + ("/chat/completions" if url.rstrip("/").endswith("/v1") else "/v1/chat/completions")
        request = Request(endpoint, data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
        with urlopen(request, timeout=25) as resp:
            content = json.load(resp)["choices"][0]["message"]["content"]
        content = re.sub(r"^```(?:json)?|```$", "", content.strip(), flags=re.I).strip()
        result = json.loads(content)
        if not isinstance(result, dict) or not all(k in result and isinstance(result[k], str) for k in ("tag", "cause", "explanation", "variant", "answer")):
            raise ValueError("模型返回格式不符合要求")
        return {k: result[k][:300] for k in ("tag", "cause", "explanation", "variant", "answer")} | {"mode": "真实模型"}
    return {"tag": "待归类", "cause": "需自行核对错因", "explanation": "演示模式未接入大模型，请根据教材或课堂笔记手动完善解析。",
            "variant": "请尝试替换原题中的数字或条件，并重新求解。", "answer": "请自行核对答案。", "mode": "本地模拟（非AI分析）"}
