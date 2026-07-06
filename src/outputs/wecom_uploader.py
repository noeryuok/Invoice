from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any

from loguru import logger


@dataclass
class FieldDef:
    title: str
    field_type: str


FIELD_DEFS = [
    FieldDef("账单编号", "FIELD_TYPE_TEXT"),
    FieldDef("Invoice状态", "FIELD_TYPE_TEXT"),
    FieldDef("账单日期", "FIELD_TYPE_DATE_TIME"),
    FieldDef("客户名称", "FIELD_TYPE_TEXT"),
    FieldDef("总计", "FIELD_TYPE_NUMBER"),
    FieldDef("应收款 余额", "FIELD_TYPE_NUMBER"),
    FieldDef("调整", "FIELD_TYPE_NUMBER"),
]

RECORDS_BATCH_SIZE = 500
DOC_ID = "s3_AEgATgYRAGMCNEL1NP6WGT3mlm7fN"
SHEET_NAME = "应收款摘要"


def _run(method: str, args: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps(args, ensure_ascii=False)
    cmd = ["wecom-cli", "doc", method, payload]
    logger.debug(f"wecom-cli {method} ...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(
            f"wecom-cli {method} 失败: {result.stderr or result.stdout}"
        )
    output = json.loads(result.stdout)
    lines = json.loads(output["content"][0]["text"])
    if lines.get("errcode", 0) != 0:
        raise RuntimeError(
            f"wecom-cli {method} 返回错误: {lines.get('errmsg', lines)}"
        )
    return lines


def _sheet_exists() -> str | None:
    sheets = _run("smartsheet_get_sheet", {"docid": DOC_ID})
    for s in sheets.get("sheet_list", []):
        if s["title"] == SHEET_NAME:
            return s["sheet_id"]
    return None


def _get_field_map(sheet_id: str) -> dict[str, str]:
    resp = _run("smartsheet_get_fields", {
        "docid": DOC_ID,
        "sheet_id": sheet_id,
    })
    return {f["field_title"]: f["field_id"] for f in resp.get("fields", [])}


def _ensure_sheet_and_fields() -> str:
    sheet_id = _sheet_exists()
    if sheet_id:
        logger.info(f"子表已存在 (sheet_id={sheet_id})")
    else:
        resp = _run("smartsheet_add_sheet", {"docid": DOC_ID})
        sheet_id = resp["properties"]["sheet_id"]
        _run("smartsheet_update_sheet", {
            "docid": DOC_ID,
            "properties": {
                "sheet_id": sheet_id,
                "title": SHEET_NAME,
            },
        })
        logger.info(f"创建子表 '{SHEET_NAME}' (sheet_id={sheet_id})")

    field_map = _get_field_map(sheet_id)
    existing_titles = set(field_map.keys())
    needed_titles = {f.title for f in FIELD_DEFS}

    if needed_titles.issubset(existing_titles):
        logger.info("所有字段已存在")
        return sheet_id

    if not existing_titles:
        _run("smartsheet_add_fields", {
            "docid": DOC_ID,
            "sheet_id": sheet_id,
            "fields": [
                {"field_title": f.title, "field_type": f.field_type}
                for f in FIELD_DEFS
            ],
        })
        logger.info(f"新增 {len(FIELD_DEFS)} 个字段")
    else:
        default_field_id = field_map.get("智能表列")
        if default_field_id:
            _run("smartsheet_update_fields", {
                "docid": DOC_ID,
                "sheet_id": sheet_id,
                "fields": [{
                    "field_id": default_field_id,
                    "field_title": FIELD_DEFS[0].title,
                    "field_type": FIELD_DEFS[0].field_type,
                }],
            })
            del field_map["智能表列"]
            field_map[FIELD_DEFS[0].title] = default_field_id

        remaining = [
            {"field_title": f.title, "field_type": f.field_type}
            for f in FIELD_DEFS
            if f.title not in field_map
        ]
        if remaining:
            _run("smartsheet_add_fields", {
                "docid": DOC_ID,
                "sheet_id": sheet_id,
                "fields": remaining,
            })
            logger.info(f"新增 {len(remaining)} 个字段")

    return sheet_id


def upload_receivables(records: list[list]) -> None:
    sheet_id = _ensure_sheet_and_fields()

    total = len(records)
    logger.info(f"上传 {total} 条记录")

    for start in range(0, total, RECORDS_BATCH_SIZE):
        batch = records[start: start + RECORDS_BATCH_SIZE]
        rows = []
        for row in batch:
            values = {}
            for i, val in enumerate(row):
                if val is None:
                    continue
                if isinstance(val, float) and str(val) == "nan":
                    continue
                ftype = FIELD_DEFS[i].field_type
                title = FIELD_DEFS[i].title
                if ftype == "FIELD_TYPE_NUMBER":
                    values[title] = float(val)
                elif ftype == "FIELD_TYPE_TEXT":
                    values[title] = [{"type": "text", "text": str(val)}]
                else:
                    values[title] = str(val)
            rows.append({"values": values})

        _run("smartsheet_add_records", {
            "docid": DOC_ID,
            "sheet_id": sheet_id,
            "records": rows,
        })
        logger.info(f"  已上传 {start + len(batch)}/{total}")
