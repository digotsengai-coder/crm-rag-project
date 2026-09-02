"""文字切分（Chunking）：對應提案流程中「文件 → 切分」的步驟。"""
import re


def split_into_chunks(text: str, max_len: int = 200, overlap: int = 40):
    """先依中文條列符號（一、二、三...）切段，過長的段落再依字數切分。"""
    parts = re.split(r"(?=[一二三四五六七八九十]{1,3}、)", text)
    chunks = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(part) <= max_len:
            chunks.append(part)
        else:
            start = 0
            while start < len(part):
                end = start + max_len
                chunks.append(part[start:end])
                start = end - overlap
    return chunks
