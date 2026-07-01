#!/usr/bin/env python3
"""知识库文件导入 — 支持 md / yaml / json / pdf / docx / txt

导入规则:
    .md → 直接复制到 knowledge/imported/
    .yml/.yaml/.json → 直接复制（不合并到结构化文件）
    .pdf → pdfplumber 提取文本 → 存为 .md
    .docx → python-docx 提取文本 → 存为 .md
    .txt → 直接复制为 .md

全部进 imported/ 子目录，与手写作的 laws/rules/templates 分开。
"""

import os
import shutil
import re

KB = os.path.join(os.path.expanduser("~"), ".bid_tool", "knowledge")
IMPORTED = os.path.join(KB, "imported")


def import_file(filepath: str) -> str | None:
    """
    导入一个文件到 knowledge/imported/。
    返回导入后的相对路径（如 "imported/法规摘要.md"），或 None 表示失败。
    """
    os.makedirs(IMPORTED, exist_ok=True)

    fname = os.path.basename(filepath)
    base, ext = os.path.splitext(fname)
    ext_lower = ext.lower()

    if ext_lower == ".md":
        return _copy_as_is(filepath, fname)

    elif ext_lower in (".yml", ".yaml", ".json"):
        return _copy_as_is(filepath, fname)

    elif ext_lower == ".pdf":
        text = _extract_pdf(filepath)
        if text:
            return _save_text(text, base + ".md")

    elif ext_lower == ".docx":
        text = _extract_docx(filepath)
        if text:
            return _save_text(text, base + ".md")

    elif ext_lower == ".txt":
        text = _read_text_file(filepath)
        if text:
            return _save_text(text, base + ".md")

    return None


# ── 内部 ──

def _copy_as_is(src: str, fname: str) -> str:
    dst = os.path.join(IMPORTED, fname)
    shutil.copy2(src, dst)
    return os.path.join("imported", fname)


def _save_text(text: str, fname: str) -> str:
    dst = os.path.join(IMPORTED, fname)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(text)
    return os.path.join("imported", fname)


def _read_text_file(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(path, "r", encoding="gbk") as f:
                return f.read()
        except Exception:
            return None
    except Exception:
        return None


def _extract_pdf(path: str) -> str | None:
    try:
        import pdfplumber
    except ImportError:
        return None

    try:
        lines = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    # 合并孤行：中文段落通常不以换行分隔完整句子
                    lines.append(text.strip())
        result = "\n\n".join(lines)
        return result if len(result.strip()) > 50 else None
    except Exception:
        return None


def _extract_docx(path: str) -> str | None:
    try:
        from docx import Document
    except ImportError:
        return None

    try:
        doc = Document(path)
        lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        result = "\n\n".join(lines)
        return result if len(result.strip()) > 50 else None
    except Exception:
        return None
