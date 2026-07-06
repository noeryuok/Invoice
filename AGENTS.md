# Invoice — AGENTS.md

财务数据报表。

## 仓库状态

- **Greenfield 项目**。只有一个初始提交，尚未创建任何处理/分析代码。
- 没有构建系统、测试框架、lint/格式化配置或 CI/CD。
- 需要在 `data/raw/` 中处理输入数据，并生成输出。

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

由于项目处于初期阶段，工作通常涉及：

1. **读取 CSV 输入：** `data/raw/*.csv`，需处理中文列名和 UTF-8 编码
2. **处理/分析：** 尚无现有代码
3. **写入输出：** 尚无既定输出目录

如需新增数据文件（如处理后的输出），建议使用 `data/` 下按用途命名的子目录。

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
│   └── processed/              # 中间结果
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
- 输出：分析结果必须先转为 `list[list]`（二维数组），再传给 uploader
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


"""
数据分析工作流主入口
执行流程：读取数据 → 分析计算 → 上传企微智能表格
"""

