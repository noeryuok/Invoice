from pathlib import Path

import pandas as pd
from loguru import logger

from src.outputs.wecom_uploader import upload_receivables
from src.pipelines.customer_payment_cleaner import clean_customer_payment
from src.pipelines.invoice_cleaner import clean_invoice_notice
from src.pipelines.invoice_mapper import build_receivables_summary

DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SUMMARY_DIR = DATA_DIR / "summary"


def _process_file(
    filename: str,
    clean_fn: callable,
) -> None:
    input_path = RAW_DIR / filename
    output_path = PROCESSED_DIR / filename

    logger.info(f"读取原始数据: {input_path}")
    df = pd.read_csv(input_path, dtype_backend="numpy_nullable", encoding="utf-8")
    logger.info(f"原始记录数: {len(df)}")

    df_clean = clean_fn(df)

    logger.info(f"写入清理后数据: {output_path}")
    df_clean.to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.success(f"完成，共 {len(df_clean)} 条记录")


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    _process_file("付款通知单.csv", clean_invoice_notice)
    _process_file("客户付款.csv", clean_customer_payment)

    logger.info("生成应收款摘要")
    invoice_df = pd.read_csv(
        PROCESSED_DIR / "付款通知单.csv", encoding="utf-8-sig"
    )
    receivables = build_receivables_summary(invoice_df)
    logger.info(f"应收款摘要: {len(receivables)} 条记录")

    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = SUMMARY_DIR / "应收款摘要.csv"
    receivables["账单日期"] = receivables["账单日期"].dt.strftime("%Y-%m-%d")
    receivables.to_csv(summary_path, index=False, encoding="utf-8-sig")
    logger.success(f"应收款摘要已保存: {summary_path}")

    records = receivables.values.tolist()
    if records:
        upload_receivables(records)
        logger.success("应收款摘要上传完成")
    else:
        logger.warning("应收款摘要为空，跳过上传")


if __name__ == "__main__":
    main()
