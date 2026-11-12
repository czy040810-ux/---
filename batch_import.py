"""PDF、Word、图片批量录题：只负责文字提取和候选题拆分，不调用模型。"""
from __future__ import annotations

import re
from io import BytesIO

import pytesseract
from PIL import Image, UnidentifiedImageError
from docx import Document
from pypdf import PdfReader

MAX_FILES = 10
MAX_FILE_BYTES = 12 * 1024 * 1024
MAX_PAGES = 15
MAX_QUESTIONS = 30
MAX_QUESTION_CHARS = 5000
QUESTION_START = re.compile(
    r"(?m)^\s*(?:第\s*\d{1,3}\s*题[：:、.．]?\s*|"
    r"\d{1,3}\s*[.、．]\s*|[（(]\s*\d{1,3}\s*[）)]\s*)"
)


def _ocr(image: Image.Image) -> str:
    if image.width * image.height > 20_000_000:
        raise ValueError("图片像素过大，请缩小后重新上传（不超过 2000 万像素）")
    return pytesseract.image_to_string(image.convert("RGB"), lang="chi_sim+eng").strip()


def _split_questions(text: str) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []
    starts = [m.start() for m in QUESTION_START.finditer(text)]
    if len(starts) >= 2:
        chunks = [text[starts[i]:starts[i + 1]] for i in range(len(starts) - 1)]
        chunks.append(text[starts[-1]:])
        if text[:starts[0]].strip():
            chunks[0] = text[:starts[0]].strip() + "\n" + chunks[0]
    else:
        chunks = [text]
    return [piece.strip()[:MAX_QUESTION_CHARS] for piece in chunks if len(piece.strip()) >= 5]


def _pdf_pages(payload: bytes):
    reader = PdfReader(BytesIO(payload))
    if len(reader.pages) > MAX_PAGES:
        raise ValueError(f"PDF 超过 {MAX_PAGES} 页，请拆分文件")
    for index, page in enumerate(reader.pages, start=1):
        page_text = (page.extract_text() or "").strip()
        if len(page_text) < 15:
            # 仅在扫描件缺乏可提取文字时渲染页面后 OCR，避免普通 PDF 的额外开销。
            import pypdfium2 as pdfium

            document = pdfium.PdfDocument(payload)
            rendered = document[index - 1].render(scale=1.6).to_pil()
            page_text = _ocr(rendered)
            rendered.close()
            document.close()
        yield f"第 {index} 页", page_text


def _docx_text(payload: bytes) -> str:
    doc = Document(BytesIO(payload))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                paragraphs.append(" | ".join(cells))
    return "\n".join(paragraphs)


def extract_candidates(files: list[tuple[str, bytes]]) -> tuple[list[dict], list[str]]:
    """返回 [{"text": ..., "source": ...}] 和用户可读警告，候选结果仍需人工确认。"""
    candidates: list[dict] = []
    warnings: list[str] = []
    if len(files) > MAX_FILES:
        return [], [f"单次最多上传 {MAX_FILES} 个文件，请分批操作。"]
    for name, payload in files:
        if len(payload) > MAX_FILE_BYTES:
            warnings.append(f"{name}：文件超过 12MB，已跳过。")
            continue
        suffix = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        try:
            if suffix == "pdf":
                sources = [(f"{name} · {page}", content) for page, content in _pdf_pages(payload)]
            elif suffix == "docx":
                sources = [(name, _docx_text(payload))]
            elif suffix in ("jpg", "jpeg", "png"):
                with Image.open(BytesIO(payload)) as image:
                    sources = [(name, _ocr(image))]
            else:
                warnings.append(f"{name}：不支持此格式，Word 请另存为 .docx。")
                continue
            before = len(candidates)
            for source, content in sources:
                for question in _split_questions(content):
                    candidates.append({"text": question, "source": source})
                    if len(candidates) >= MAX_QUESTIONS:
                        warnings.append(f"本次最多预览 {MAX_QUESTIONS} 道候选题，请分批导入。")
                        return candidates, warnings
            if len(candidates) == before:
                warnings.append(f"{name}：没有识别到文字，可改用单题手动录入。")
        except Exception as exc:
            warnings.append(f"{name}：提取失败（{type(exc).__name__}），请检查文件格式或内容。")
    return candidates, warnings
