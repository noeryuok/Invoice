import pandas as pd
from loguru import logger

STATUS_MAP = {
    "Closed": "已结清",
    "Open": "待处理",
    "Overdue": "已逾期",
    "PartiallyPaid": "部分付款",
}

RECEIVABLES_COLS = [
    "账单编号",
    "Invoice状态",
    "账单日期",
    "客户名称",
    "总计",
    "应收款 余额",
    "调整",
]


def build_receivables_summary(df: pd.DataFrame) -> pd.DataFrame:
    """从付款通知单生成应收款摘要。

    按账单编号去重，筛选客户含"鄂A"/"鄂W"且应收款余额 > 0 的记录，
    按客户名称排序，仅保留指定列。
    """
    grp = df.groupby("账单编号", as_index=False, sort=False).agg(
        {
            "Invoice状态": "first",
            "账单日期": "first",
            "客户名称": "first",
            "总计": "first",
            "应收款 余额": "first",
            "调整": "first",
        }
    )
    logger.info(f"去重后发票数: {len(grp)}")

    mask = grp["客户名称"].str.contains("鄂A|鄂W", na=False) & (
        grp["应收款 余额"] > 0
    )
    result = grp[mask].copy()
    logger.info(
        f"客户含鄂A/鄂W 且 应收款余额>0: {len(result)} 条"
    )

    result["Invoice状态"] = result["Invoice状态"].map(STATUS_MAP).fillna(result["Invoice状态"])

    result["账单日期"] = pd.to_datetime(result["账单日期"])
    today = pd.Timestamp.now().normalize()
    before = result["账单日期"] < today
    dropped = (~before).sum()
    if dropped:
        logger.info(f"过滤掉 {dropped} 条账单日期 >= 今天的记录")
    result = result[before]

    result = result.sort_values("客户名称")
    result = result[RECEIVABLES_COLS].reset_index(drop=True)
    return result
