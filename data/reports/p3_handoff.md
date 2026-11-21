# P3 喂料包：匹配引擎接口 + 真实返回样例

> 给 P3（全栈 & Demo）。你不用懂算法，按这份接就行。
> 生成方式：`python p2/scripts/make_p3_samples.py` → `data/reports/p3_samples.jsonl`（5 条查询的真实返回，每行一条）
> 状态：**已跑通**，纯规则、毫秒级、不联网、不依赖 LLM。

---

## 1. 怎么调（两种，任选）

**起一个本地 HTTP 服务（前端直接 fetch，最省事）**

```powershell
cd Y:\hks\p2
python scripts/api_server.py --port 8787
# GET http://127.0.0.1:8787/match?q=汉德%2035%20吨桥，前面那副
# GET http://127.0.0.1:8787/health   → {"ok":true,"skus":217,"axles":7}
```

只用标准库（不用装 FastAPI），已开 CORS，单次 3–6 ms。

**命令行（调试用）**

```powershell
cd Y:\hks\p2
python -m engine.match --query "147×100×14.5" --json
```

**Python 模块（做成 API 服务）**

```python
import sys
sys.path.insert(0, r"Y:\hks\p2")
from engine.match import match_query

r = match_query("汉德 35 吨桥，前面那副")
```

---

## 2. 返回结构（以真实输出为准，别改字段名）

```jsonc
{
  "query": "147×100×14.5",
  "parsed": {                    // 引擎从这句话里解析出的信号，可用于"显示我理解到的是什么"
    "dims": {"arc_mm": 147.0, "width_mm": 100.0, "thickness_mm": 14.5,
             "thickness_alt_mm": null, "outer_dia_mm": null, "raw_text": "147×100×14.5"},
    "has_dims": true,
    "codes": [],                 // 识别到的编码
    "norm_codes": [],
    "axles": [],                 // 识别到的车桥 [{axle_id, brand, model}]
    "car_models": []             // 识别到的车型
  },
  "mode": "rule",                // rule=有把握 / ask=信息不足要追问 / export=海外对码命中（见下）
  "export_matches": [            // ★ 外商场景：FMSI / OE / WVA / 英制尺寸 对回出口册
    { "score": 0.98, "kind": "american", "fmsi": "4524", "oe_ref": "A3222E1383",
      "shoe_code": "4524Q", "size": "5", "wva": null, "hardware": null,
      "page": 32, "verified": false, "why": "FMSI 4524 命中",
      "source": "kooying catalog p32（出口册图页，OCR）" }
  ],
  "candidates": [                // Top3 候选，按 score 降序
    {
      "sku_id": "FIT-解放虎威前AABS",
      "score": 1.0,
      "dims_err": 0.0,           // 尺寸偏差，0 = 硬匹配
      "verified": true,          // ★ 这一条是否人工核对过产品册原文（true 才敢在台上说"可溯源"）
      "ocr": false,              // ★ 是否来自扫描图页（OCR 识别）——建议 UI 上加个小灰标
      "extractor": "rule_coord", // rule_coord=PDF 文字层 / rule_ocr=扫描图页
      "src_rank": 1,             // 同分排序用，前端不用管
      "confidence": "高",         // 高 / 中 / 低 —— 直接拿去做 UI 徽章
      "reason": "尺寸硬匹配。解放虎威前A(ABS) 前 ABS 147×100×14.5/16.5",
      "dims": {"arc_mm": 147.0, "width_mm": 100.0, "thickness_mm": 14.5,
               "thickness_alt_mm": 16.5, "raw_text": "147×100×14.5/16.5"},
      "material": "未知",
      "category": "鼓式",
      "axle_fit": [],
      "evidence": [{"report_id": "kooying_catalog", "page": 28,
                    "snippet": "解放虎威前A(ABS) 147×100×14.5/16.5", "kind": "产品册"}],
      "price": null,             // 恒为 null：资料包没有价格（口径：一律答"询价确认"）
      "stock": "未知",
      "placeholder": false
    }
  ],
  "followups": ["车桥铭牌上的品牌与型号是什么？…"],   // mode=ask 时的追问话术
  "elapsed_ms": 7
}
```

## 3. UI 字段怎么摆（照这个用，别自己拼字符串）

| 界面元素 | 取哪个字段 | 注意 |
|---|---|---|
| 型号标题 | `sku_id` | 就可以直接显示（已带 `FIT-` 前缀） |
| 置信度徽章 | `confidence` | 高=绿 / 中=黄 / 低=灰 |
| 一句话差异说明 | `reason` | 已经是人话，可直接显示 |
| 尺寸 | `dims.raw_text` | **不要**用 arc/width/thickness 自己拼，原文里有备选厚度 `14.5/16.5` |
| 出处（可溯源） | `evidence[0].report_id` + `.page` | 显示成「kooying 产品册 p28」，点击可跳 PDF 页 |
| 原文片段 | `evidence[0].snippet` | 展开"为什么是这个"时用 |
| 报价 | `price` | 为 `null` → 显示「询价确认」，**不要显示 0 或编价** |
| 库存 | `stock` | 恒为「未知」→ 弱化显示，别当卖点 |
| 追问 | `followups` | `mode == "ask"` 时把 1–3 条渲染成追问卡片，**不要给候选** |
| **可溯源徽章** | `verified` | true 才显示「已核对产品册原文」；false 显示「未核对」。**别对 false 的说"可溯源"** |
| **OCR 来源标** | `ocr` | true 时在出处旁加个小灰标「扫描图页识别」 |
| **海外对码卡片** | `export_matches` | 外商场景才渲染：一行一个「外商报的码 → 我方型号 → 册子页码」。`mode=="export"` 时**不要**渲染成空结果 |

> 红线：`candidates` 为空时必须走追问界面，不能前端"猜一个"填上。

## 4. 五条演示查询（缓存就预热这五条）

| 场景 | query | 期望 | 实测 |
|---|---|---|---|
| 尺寸直查 | `147×100×14.5` | rule，3 候选，Top1 `FIT-解放虎威前AABS` | 7 ms |
| 车桥口语 | `汉德 35 吨桥，前面那副` | rule，2 候选（前/后），Top1 `FIT-汉德桥35T前` | 5 ms |
| 适配名直查 | `解放虎威前` | rule，3 候选，Top1 `FIT-解放虎威前B` | 5 ms |
| 车型+型号数字 | `客户说这车是欧曼 400` | rule，Top1 `FIT-新欧曼400A`（A/B 并列） | 5 ms |
| **真正的追问场景** | `BPW 空压桥的片子` | **ask**，0 候选（资料包无 BPW） | 5 ms |
| 内部型号 | `GY1054` | rule，1 候选 `FIT-GY1054` | 5 ms |
| **海外对码（外商场景）** | `客户要 FMSI 4524` | **export**，0 候选 + 1 条对码 → `4524Q`（p32） | 7 ms |
| 海外对码·欧系 | `BPW 420X180 的后蹄` | **export** → `BPW180`（p33） | 7 ms |

「只有车型」这条是**加分项不是缺陷**：演示时就按它讲"不瞎猜，主动追问"。

**海外对码（`mode=export`）是老板点名的重点**：外商报的不是中文车型，是 FMSI 号 / OE 号 / WVA 衬片号。这时界面要切到"对码卡片"：左边外商报的码，右边我方型号 + 册子页码，**不要**显示成"没找到"。数据来自出口册 p32–34 图页 OCR，共 34 条；**10 条已人工核对**（`verified: true`，可显示绿标），其余 24 条只能说「册子上写着」。

## 5. 你要动的工程（按优先级）

1. **不要每条请求都起子进程**：`match_query` 是纯本地计算，直接在 API 进程里 import 调用；`python -m engine.match` 只用于调试。
2. **缓存**：五条演示查询的结果落盘（`data/reports/p3_samples.jsonl` 已经有真实结果，可直接当缓存种子），命中即秒回。
3. **超时/重试**：调 LLM 的地方（`engine/llm.py`，只有 `mode=llm` 兜底时才用）必须 3 次指数退避 + 30s 超时；网络挂了要有降级（本次网关实测约 1/3 概率需重试）。
4. **录屏兜底**：命令行跑这五条，拍下来，比任何界面都稳。

## 6. 联调 checklist（19:30 前）

- [ ] 界面能显示 Top3（型号 + 置信度 + reason + 尺寸 + 页码）
- [ ] `mode=ask` 时显示追问，不显示候选
- [ ] `price=null` 显示「询价确认」
- [ ] 五条演示查询都能在界面上跑出来
- [ ] 断网状态下五条走缓存仍然能跑

## 7. 有疑问找 P2 要什么

- 数据口径（**v1.2：外弧 × 宽度 × 厚度**，不是"宽×长×厚"）看 `p2/schema/sku.schema.json`
- 引擎内部不要改；要新字段先看看板第 3 节契约冻结区
