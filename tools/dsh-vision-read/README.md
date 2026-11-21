# dsh-plugin-vision-read

给 DSH 用的「读图」工具插件：把图片文件交给一个 OpenAI 兼容的视觉路由，拿回提炼后的文本。

## 它解决什么

模型能不能收到图片，由模型路由声明的输入模态决定。当前模型只声明 `text` 时，
`read_image` 和一切带图片的工具结果都会在模型看到之前被拒绝：

```
Error: cannot read "x.png" as an image: model "…" does not declare image input
```

`vision_read` 绕开这个限制：调用它的模型本人不看图，工具把图发给视觉路由，把文字拿回来。

## 安装

```powershell
# 在 DSH 会话里
plugin_manager install_bundle  → target: Y:\hks\tools\dsh-vision-read
```

装完即热生效，工具名 `vision_read`。

## 用法

```
vision_read({ paths: ["Y:\\hks\\资料包\\截图.png"] })
vision_read({ paths: ["a.png","b.png"], prompt: "把每张表格转成 TSV，不要解释" })
```

## 配置（profile 的 cordis.patch.yml，`id: vision-read`）

| 字段 | 默认 | 说明 |
|---|---|---|
| `baseURL` | `https://token.b1x.work/v1` | OpenAI 兼容端点，代码会拼 `/chat/completions` |
| `model` | `deepseek-v4.1-flash-1017` | 视觉路由上的模型 id |
| `apiKeyEnv` | `B1X_API_KEY` | 先查凭据存储（同名 credential），再查同名环境变量 |
| `maxTokens` | `4000` | 推理型模型会先烧推理 token，别设太小 |
| `timeoutMs` | `180000` | 单图请求超时 |
| `maxImages` | `8` | 单次调用图片数上限 |
| `maxImageBytes` | `8388608` | 单图字节上限 |
| `prompt` | 逐字转写 + 版式描述 | 默认指令，可整体替换 |

例：

```yaml
- id: vision-read
  name: dsh-plugin-vision-read
  config:
    model: deepseek-v4.1-flash-1017
    apiKeyEnv: B1X_API_KEY
```

## 注意

- 只支持 PNG / JPEG / GIF / WebP（按魔数判断，不信扩展名）。
- 不支持 PDF 或 BMP；PDF 请先渲染成 PNG。
- 返回值是文本，不占图片 token，也不消耗当前模型的视觉能力。
- 插件不 import 任何 `@deepseek-ai/*` 包，只依赖 Node 内置模块，因此从目录链接安装也能解析。
