# P2 工作区（AI & 数据工程）

> 现状：**128 条真实 SKU**（适配名 + 外弧×宽度×厚度 + 产品册页码）｜引擎纯规则毫秒级｜回归 20/20、口语 6/6｜全量一致性审计 128/128。
> 缺：材质 / 型号级摩擦系数 / 价格 / 编码 —— 资料包里没有，**别编**。

## 目录

    data/
      structured/skus.json          主数据（128 条，schema v1.2）
      structured/axles.json         车桥词典（7 个，由适配名反推，未核实）
      structured/benchmark.json     企业级 14 项台架对比（企业介绍 p25）
      structured/catalog_rows.json  原始行（134 行）
      eval/cases.jsonl              回归集（20 条，由主数据派生）
      eval/cases_spoken.jsonl       「客户真话」口语集（6 条）
      reports/field_inventory.md    **资料包勘察结论（先读这份）**
      reports/test_report_gap.md    **「测试报告」到底指什么、缺哪一页**
      reports/demo_transcript.md    Demo 文字稿（可做录屏字幕）
      reports/{eval_report,eval_spoken,keyword_census,image_pages}.md
    p2/
      schema/sku.schema.json        数据契约 v1.2（已冻结）
      engine/{llm,store,match}.py
      scripts/                      见下
    资料包/                         三份原始 PDF

## 命令（除标注外都在仓库根目录跑）

    # 0) 一键演示（最能说明问题）
    python p2/scripts/demo.py

    # 1) 抽文本：普通模式看内容 / 版式模式保列位置
    python p2/scripts/extract_text.py --inbox 资料包
    python p2/scripts/extract_text.py --inbox 资料包 --out data/text_layout --layout

    # 2) 结构化
    python p2/scripts/parse_layout.py --merge     # 产品册表格 → skus.json（主力）
    python p2/scripts/build_axles.py              # 适配名 → 车桥词典
    python p2/scripts/parse_benchmark.py          # 企业介绍 p25 对比表 → benchmark.json

    # 3) 体检 / 评估
    python p2/scripts/inspect_images.py           # 哪些页是纯图片、值不值得 OCR
    python p2/scripts/validate_skus.py            # 交付自检（0 占位才合格）
    python p2/scripts/make_eval.py && python p2/scripts/run_eval.py
    python p2/scripts/run_eval.py --cases data/eval/cases_spoken.jsonl --out data/reports/eval_spoken.md

## 匹配引擎

    cd p2
    python -m engine.match --query "汉德 35 吨桥，前面那副"   # 口语 → 车桥 → 型号
    python -m engine.match --query "147×100×14.5"            # 尺寸硬匹配
    python -m engine.match --query "客户说这车是欧曼 400"      # 会追问，不瞎配
    python -m engine.match --query "..." --json

模块调用（给 P3）：

    from engine.match import match_query
    r = match_query("汉德 35 吨桥，前面那副")
    # r["candidates"] -> [{sku_id, confidence, reason, dims, evidence, price, stock}, ...]
    # r["followups"]  -> 追问列表
    # r["mode"]       -> rule / llm / ask
    # r["elapsed_ms"] -> 毫秒

## 数据口径（v1.2）

- 尺寸 = **外弧×宽度×厚度(/备选厚)** mm，来自产品册原文（表头：外弧*宽度*厚度 孔数 / outer arch·width·thickness）
- `fit_name` = 适配名（解放虎威前A / 汉德桥35T前 / GY1054）——客户嘴里的说法
- `evidence` = 文件 + 页码 + 原文片段
- 没有的字段一律 null / 「未知」，不填占位值

## 已知限制

1. 资料包 33 页是 Illustrator 转曲页（0 字符、上千条矢量路径），要 OCR 才能取；收益低，暂不做。
2. 盘式产品只有 GYS-xxx 型号清单，没有尺寸。
3. 车桥词典由适配名反推（7 个），未核实。
4. 0 条人工核对（`provenance.verified` 全 false）——抽检后改。

## 红线

1. 候选只来自 `skus.json`，表外型号不返回
2. 无尺寸/编码/车桥信号时返回追问
3. 每条结论带 `report_id + page`
4. 没核对过的记录 `provenance.verified = false`，答辩不许说「已核实」
