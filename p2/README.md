# P2 工作区（AI & 数据工程）

> 现状：**120 条真实 SKU 已入库**（适配名 + 宽×长×厚 + 产品册页码），引擎纯规则毫秒级，回归集 20/20。
> 缺：材质 / 摩擦系数 / 价格 / 编码 —— 资料包里没有，别编。

## 目录

    data/
      structured/skus.json          主数据（120 条，schema v1.1）
      structured/catalog_rows.json  原始行（134 行，含未配对的）
      eval/cases.jsonl              回归评估集
      reports/field_inventory.md    **资料包勘察结论（先读这份）**
      reports/keyword_census.md     关键词普查
      reports/eval_report.md        评估结果
    p2/
      schema/sku.schema.json        数据契约 v1.1（已冻结）
      engine/{llm,store,match}.py
      scripts/{extract_text,parse_layout,parse_catalog_words,scan_keywords,
               make_eval,run_eval,validate_skus,extract_skus}.py
    资料包/                         三份原始 PDF

## 命令

    # 1) 抽文本（普通模式看内容）
    python p2/scripts/extract_text.py --inbox 资料包
    # 2) 抽版式（保留列位置，解析表格必备）
    python p2/scripts/extract_text.py --inbox 资料包 --out data/text_layout --layout
    # 3) 版式解析 → SKU（主力命令，--merge 直接更新 skus.json）
    python p2/scripts/parse_layout.py --merge
    # 4) 自检 / 评估
    python p2/scripts/validate_skus.py
    python p2/scripts/make_eval.py
    python p2/scripts/run_eval.py

## 匹配引擎

    cd p2
    python -m engine.match --query "汉德桥35T前"
    python -m engine.match --query "240×220×18.5"
    python -m engine.match --query "客户要 150×100×14/15.5 的片"
    python -m engine.match --query "2019 款丰田 Hilux 后桥换过"    # 会追问，不瞎配
    python -m engine.match --query "..." --json

模块调用（给 P3）：

    from engine.match import match_query
    r = match_query("汉德桥35T前")
    # r["candidates"] -> [{sku_id, confidence, reason, dims, evidence, price}, ...]
    # r["followups"]  -> 追问列表（信息不足时）
    # r["mode"]       -> rule / llm / ask

## 数据口径（v1.1）

- 尺寸 = **宽×长×厚(/备选厚)**，单位 mm，来自产品册原文
- `fit_name` = 产品册上的适配名（解放虎威前A / 汉德桥35T前 / GY1054）——客户嘴里的说法
- `evidence` = 哪份文件第几页 + 原文片段
- 没有的字段一律 null / 「未知」，**不填占位值**

## 红线

1. 候选只来自 `skus.json`，表外型号不返回
2. 无尺寸/编码/车桥信号时返回追问
3. 每条结论带 `report_id + page`
4. 没核对过的记录 `provenance.verified = false`，答辩不许说「已核实」
