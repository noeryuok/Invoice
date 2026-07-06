from pathlib import Path

import pandas as pd
from loguru import logger

DATE_COLS = ["日期"]
FINANCE_COLS = ["金额(FCY)", "未使用金额 (FCY)"]


def clean_customer_payment(df: pd.DataFrame) -> pd.DataFrame:
    """清理客户付款数据。

    1. 日期列统一为 YYYY-MM-DD 格式。
    2. 金融列转为 float 类型。
    """
    result = df.copy()

    for col in DATE_COLS:
        if col not in result.columns:
            logger.warning(f"列 '{col}' 不存在，跳过")
            continue
        parsed = pd.to_datetime(result[col], errors="coerce", format="mixed")
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
