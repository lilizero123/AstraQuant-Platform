from __future__ import annotations


def normalize_stock_code(code: str) -> str:
    """
    将输入的股票代码标准化为 6 位数字:
    - 忽略前缀 sh/sz（不区分大小写）
    - 移除空格、点、短横等符号
    """
    if not code:
        return ""
    value = (
        code.strip()
        .replace(".", "")
        .replace("-", "")
        .replace(" ", "")
        .lower()
    )
    if len(value) >= 8 and value[:2] in {"sh", "sz"}:
        value = value[2:]
    digits = "".join(ch for ch in value if ch.isdigit())
    return digits[:6] if len(digits) >= 6 else digits


def add_market_prefix(code: str) -> str:
    """
    根据代码首位自动推断市场前缀:
    - 6/9 开头默认为上交所 -> sh
    - 其余默认深交所 -> sz
    """
    normalized = normalize_stock_code(code)
    if not normalized:
        return ""
    prefix = "sh" if normalized.startswith(("5", "6", "9")) else "sz"
    return prefix + normalized
