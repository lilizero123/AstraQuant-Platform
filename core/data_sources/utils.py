import re
from datetime import datetime
from typing import List


SINA_STOCK_RE = re.compile(r'var hq_str_(?P<code>s[hz]\d+)="(?P<data>[^"]*)"')
SINA_US_RE = re.compile(r'var hq_str_gb_(?P<code>[a-z.]+)="(?P<data>[^"]*)"')
TENCENT_RE = re.compile(r'v_(?P<code>s[hz]\d+)="(?P<data>[^"]*)"')


def ensure_sina_codes(codes: List[str]) -> List[str]:
    sina_codes = []
    for code in codes:
        code = code.lower()
        if code.startswith(("sh", "sz")):
            sina_codes.append(code)
        elif code.startswith("6"):
            sina_codes.append(f"sh{code}")
        else:
            sina_codes.append(f"sz{code}")
    return sina_codes


def parse_sina_datetime(date_str: str, time_str: str) -> datetime:
    try:
        return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.now()
