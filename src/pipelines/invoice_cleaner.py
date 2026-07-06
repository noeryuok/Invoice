import re
from pathlib import Path

import pandas as pd
from loguru import logger

DATE_COLS = ["账单日期", "到期日期", "开始日期", "结束日期"]
FINANCE_COLS = ["款项金额", "总计", "应收款 余额", "调整"]


def _clean_date_str(s: str) -> str:
    """清洗单个日期字符串，补齐不完整日期为 YYYY-MM-DD。"""
    s = s.strip()
    if not s or s in ("0", "1"):
        return ""
    s = re.sub(r"^[^0-9]+", "", s)
    if not s:
        return ""
    # 修复 5 位纯数字 (如 "20240" -> "2024")
    if re.match(r"^\d{5}$", s) and s[:4].isdigit() and 2000 <= int(s[:4]) <= 2100:
        s = s[:4]
    # 修复 5 位年份 (如 "22023-3-10")
    m = re.match(r"^(\d{5})(\D.*)$", s)
    if m:
        prefix, rest = m.group(1), m.group(2)
        if prefix[:4].isdigit() and 2000 <= int(prefix[:4]) <= 2100:
            s = prefix[:4] + rest
        elif prefix[1:].isdigit() and 2000 <= int(prefix[1:]) <= 2100:
            s = prefix[1:] + rest
    # 修复拼接重复 (如 "2025-1-312025-1-31")
    s = re.sub(r"(\d{4}-\d{1,2}-\d{1,2}).*", r"\1", s)
    # 先尝试标准解析
    try:
        pd.to_datetime(s)
        return s
    except (ValueError, TypeError):
        pass
    # 补全缺失的前导 '2' (如 "023-07", "206-6-13")
    if re.match(r"^0\d{2}\D", s) or re.match(r"^[01]\d{2}-\d", s):
        s = "2" + s
        try:
            pd.to_datetime(s)
            return s
        except (ValueError, TypeError):
            pass
    # YYYYMM -> YYYY-MM-01
    if re.match(r"^\d{6}$", s):
        return f"{s[:4]}-{s[4:6]}-01"
    # YYYY -> YYYY-01-01
    if re.match(r"^\d{4}$", s):
        return f"{s}-01-01"
    # YYYY-MM 或 YYYY-M -> YYYY-MM-01
    m = re.match(r"^(\d{4})-(\d{1,2})$", s)
    if m:
        return f"{m.group(1)}-{m.group(2).zfill(2)}-01"
    # M/D/YY -> YYYY-MM-DD
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2})$", s)
    if m:
        return f"20{m.group(3)}-{m.group(1).zfill(2)}-{m.group(2).zfill(2)}"
    return s


def clean_invoice_notice(df: pd.DataFrame) -> pd.DataFrame:
    """清理付款通知单数据。

    1. 日期列统一为 YYYY-MM-DD 格式；开始/结束日期缺失的月/日用 01-01 补齐。
    2. 金融列转为 float 类型。
    """
    result = df.copy()

    for col in DATE_COLS:
        if col not in result.columns:
            logger.warning(f"列 '{col}' 不存在，跳过")
            continue

        raw = result[col].astype(str)
        cleaned = raw.apply(_clean_date_str)
        parsed = pd.to_datetime(cleaned, errors="coerce", format="mixed")
        result[col] = parsed.dt.strftime("%Y-%m-%d")
        invalid_count = parsed.isna().sum()
        if invalid_count > 0:
            logger.warning(f"列 '{col}' 有 {invalid_count} 个无法解析的日期值")

    for col in FINANCE_COLS:
        if col not in result.columns:
            logger.warning(f"列 '{col}' 不存在，跳过")
            continue
        result[col] = pd.to_numeric(result[col], errors="coerce")
        invalid_count = result[col].isna().sum()
        if invalid_count > 0:
            logger.warning(f"列 '{col}' 有 {invalid_count} 个无法解析的数值")

    return result
