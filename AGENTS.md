# Invoice — AGENTS.md

财务数据报表。

## 数据文件

所有文件均为 **UTF-8 编码的 CSV**，包含中文字段名。

| 文件 | 路径 | 内容 |
|---|---|---|
| `客户付款.csv` | `data/raw/` | 客户付款记录：账单编号、客户名称、日期、收款账户名、金额、支付方式、参考编号 |
| `付款通知单.csv` | `data/raw/` | 发票/账单明细：账单编号、状态、日期、客户、分类、费用项目、金额、总计、余额 |

### 核心列

**客户付款.csv：** 账单编号、客户名称、日期、CF.收款账户名、金额(FCY)、支付方式、未使用金额(FCY)、支付编号、参考编号

**付款通知单.csv：** 账单编号、Invoice状态、账单日期、到期日期、客户名称、分类、描述、款项名称、款项金额、开始日期、结束日期、所属类别、总计、应收款余额、调整

## 数据领域

车队管理 / 运输财务数据。常见字段：
- 客户为车牌号（如 `鄂AJU231`）
- 费用类别包括：车管费、GPS服务费、营运证年审费、保险（鼎和/长江/太平洋）、承运人险、安责险、市内通行证等
- 多数记录的未使用余额为 `0.000`，但个别记录存在未使用余额

## 标准工作流程

项目工作流：

1. **读取 CSV 输入：** `data/raw/*.csv`，需处理中文列名和 UTF-8 编码
2. **数据清洗：** 写入 `data/processed/`，日期统一 `YYYY-MM-DD`，金融列转 `float`
3. **分析计算：** `src/pipelines/` 下纯函数，返回 `pd.DataFrame`
4. **保存结果：** `data/summary/` 目录（`utf-8-sig` 编码），日期列先 `dt.strftime("%Y-%m-%d")`
5. **上传企微：** `src/outputs/wecom_uploader.py` 负责 wecom-cli 交互，数据以 `list[list]` 传入

如需新增数据文件，建议使用 `data/` 下按用途命名的子目录。


7. 命名规范
●文件: 全小写，下划线分隔，如 invoice_loader.py
●类: 大驼峰，如 PaymentNoticeItem
●函数: 动词开头，如 load_payment_notices()
●常量: 全大写，如 RAWDATA_DIR = Path("/rawdata")
8. 日志规范
●全局禁止 print()，统一使用 loguru
●文件日志：logs/zifa_{YYYYMMDD}.log
●控制台日志：INFO 级别；文件日志：DEBUG 级别
●敏感信息（完整金额、车牌）禁止在 INFO 及以上级别输出


---


## 项目定位
危运车队数据分析工作流，处理结果通过 wecom-cli 写入企微智能表格。

## 技术栈
- Python 3.12 + uv 包管理
- pandas / polars 数据处理jianc
- wecom-cli（Node.js 外部工具）企微交互

## 目录规范
- `src/pipelines/`：所有数据分析逻辑，纯函数，返回 DataFrame
- `src/outputs/`：所有外部系统交互（wecom-cli、API、文件导出）
- `src/utils/`：通用工具（Excel 读取、日期处理、配置加载）
- 禁止在 pipelines 中直接调用 wecom-cli

## 项目结构
```
INVOICE/
├── pyproject.toml              # uv 依赖配置
├── .python-version             # Python 版本锁定
├── .env                        # 环境变量（不提交 Git）
├── .env.example                # 环境变量模板
├── AGENTS.md                   # opencode 项目规则
├── README.md
├── data/
│   ├── raw/                    # 原始数据（序时账、行车日志）
│   ├── processed/              # 中间结果
│   └── summary/                # 最终摘要 CSV
├── src/
│   ├── __init__.py
│   ├── pipelines/              # 数据分析管道
│   │   ├── __init__.py
│   │   ├── ledger_analyzer.py      # 财务序时账分析
│   │   ├── attendance_calculator.py # 单车出勤率统计
│   │   └── invoice_mapper.py       # Invoice 状态映射
│   ├── outputs/                # 结果输出封装
│   │   ├── __init__.py
│   │   └── wecom_uploader.py     # wecom-cli 调用封装
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── excel_reader.py
│   │   └── config.py
│   └── main.py                 # 工作流入口
├── scripts/
│   └── run_monthly.sh          # 定时任务脚本
└── tests/

```



## 数据约定
- 输入：`.xlsx` 或 `.csv`，放在 `data/raw/`
- 中间结果：`data/processed/`（清洗后 CSV）
- 分析结果：`data/summary/`（最终摘要 CSV），输出前日期列用 `dt.strftime("%Y-%m-%d")` 格式化为字符串
- 分析结果必须先转为 `list[list]`（二维数组），再传给 uploader
- 日期列统一用 `pd.to_datetime()` 处理，格式 `YYYY-MM-DD`

## 运行命令
```bash
uv sync                    # 安装依赖
uv run python src/main.py  # 执行工作流
uv run pytest              # 运行测试
```

## 代码风格
- 使用 pathlib.Path 处理路径
- 使用 python-dotenv 加载环境变量
- 函数必须有类型注解
- 异常必须捕获并打印中文错误信息

- 日志: loguru（严禁使用 print）

"""
数据分析工作流主入口
执行流程：读取数据 → 分析计算 → 上传企微智能表格
"""

---

## 付款通知单数据清理规则

操作目标：读取 `data/raw/付款通知单.csv`，清理后写入 `data/processed/付款通知单.csv`。

### 日期列（账单日期、到期日期、开始日期、结束日期）
- 统一输出格式：`YYYY-MM-DD`
- 账单日期、到期日期：直接 `pd.to_datetime()` 转换
- 开始日期、结束日期：处理不完整日期格式 ——
  - 纯年份 `2023` → `2023-01-01`
  - YYYYMM `202310` → `2023-10-01`
  - M/D/YY `1/1/23` → `2023-01-01`
  - YYYY-M `2023-1` → `2023-01-01`
  - `0` 或空值 → `NaN`

### 金融列（款项金额、总计、应收款 余额、调整）
- `pd.to_numeric()` 转为 `float` 类型（单位：元）

### 输出规范
- 编码：`utf-8-sig`
- 不修改 `data/raw/` 下任何文件

## 客户付款数据清理规则

操作目标：读取 `data/raw/客户付款.csv`，清理后写入 `data/processed/客户付款.csv`。
### 日期列（日期）
- 统一输出格式：`YYYY-MM-DD`

### 金融列（金额(FCY)、未使用金额 (FCY)）
- `pd.to_numeric()` 转为 `float` 类型（单位：元）

### 输出规范
- 编码：`utf-8-sig`
- 不修改 `data/raw/` 下任何文件

---

## InvoiceStatus 状态映射
| 原文 | 中文 | 含义 |
|---|---|---|
| Closed | 已结清 | 全额付款 |
| Open | 待处理 | 未处理 |
| Overdue | 已逾期 | 逾期未付 |
| PartiallyPaid | 部分付款 | 部分付款 |

解析/processed 文件夹下的付款通知单（多行明细账单）与客户付款记录，建立账单-付款关联。（依据“账单编号”建立关联）

## 应收款摘要

`src/pipelines/invoice_mapper.py::build_receivables_summary()`

处理流程：
1. 按 `账单编号` 去重（groupby first）
2. Invoice状态 映射为中文（STATUS_MAP：Closed→已结清, Open→待处理, Overdue→已逾期, PartiallyPaid→部分付款）
3. 筛选：`客户名称` 含 `鄂A`/`鄂W` 且 `应收款余额 > 0`
4. 筛选：`账单日期 < 今天`（过滤未来/今天的发票）
5. 按 `客户名称` 排序

保留列：
| 账单编号 | Invoice状态 | 账单日期 | 客户名称 | 总计 | 应收款 余额 | 调整 |
|---|---|---|---|---|---|---|


## 企业微信智能表格写入

文档: "财务数据分析" [https://doc.weixin.qq.com/smartsheet/s3_AEgATgYRAGMCNEL1NP6WGT3mlm7fN]
docid: `s3_AEgATgYRAGMCNEL1NP6WGT3mlm7fN`

### `src/outputs/wecom_uploader.py` 约定
- 字段定义用 `FIELD_DEFS` 列表（`title`, `field_type`）
- 字段名（key）必须是 `field_title`（不是 field_id）
- 批量写入上限 500 条/次

### Wecom API 值类型要求（关键）
| 字段类型 | Python 值格式 | 说明 |
|---|---|---|
| `FIELD_TYPE_TEXT` | `[{"type": "text", "text": str(val)}]` | 必须用数组+对象格式，不可传纯字符串 |
| `FIELD_TYPE_NUMBER` | `float(val)` | 必须传数值，不可传字符串 |
| `FIELD_TYPE_DATE_TIME` | `str(val)` | 传 `YYYY-MM-DD` 格式字符串 |

### 子表创建流程
1. `smartsheet_add_sheet` 创建子表（默认带一个"智能表列"字段）
2. `smartsheet_get_fields` 获取默认字段 ID
3. `smartsheet_update_fields` 将默认字段重命名为第一个目标字段
4. `smartsheet_add_fields` 添加剩余字段
