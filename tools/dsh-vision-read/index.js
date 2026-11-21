/**
 * dsh-plugin-vision-read
 *
 * Registers `vision_read`: read the text inside image files (screenshots, slide
 * renders, extracted video frames, exported charts) through an
 * OpenAI-compatible vision route, and hand the calling model distilled text
 * instead of pixels.
 *
 * Why this exists: whether an agent may receive image content is decided by the
 * model route's declared input modalities. When the selected model declares
 * text-only input, `read_image` and every image-bearing tool result are
 * refused before the model ever sees them. This tool keeps image *reading*
 * available in that situation, because it never asks the calling model to look
 * at an image — it asks a vision route for text and returns text.
 *
 * Only Node builtins are imported: the package is authoritative-free, so it
 * runs whether it is linked from a directory or installed from a registry.
 */
import { readFile, stat } from 'node:fs/promises'
import { isAbsolute, resolve as resolvePath } from 'node:path'

/** Loader diagnostics name. */
export const name = 'dsh-plugin-vision-read'

/** Services required before the plugin starts. `credentials` is optional. */
export const inject = ['tools', 'systemPrompt']

/** Default route settings; every field is overridable through the patch config. */
const DEFAULTS = {
  baseURL: 'https://token.b1x.work/v1',
  model: 'deepseek-v4.1-flash-1017',
  apiKeyEnv: 'B1X_API_KEY',
  maxTokens: 4000,
  timeoutMs: 180000,
  maxImages: 8,
  maxImageBytes: 8388608,
  prompt: '',
}

/** The instruction used when the caller supplies no prompt of its own. */
const DEFAULT_PROMPT = [
  '逐字转写图中所有可见文字，保留原有的行列与层级（表格请用制表符分列）。',
  '然后用几句话描述无法转写的视觉要素：图表、图形、颜色、界面控件及其位置关系。',
  '看不清的地方直接说明看不清，不要臆测或补全。',
].join('\n')

/** Model-facing guidance registered with the system prompt. */
const GUIDANCE = [
  'vision_read reads the text inside image files (screenshots, slide renders, extracted frames) through a vision route and returns distilled text.',
  'Use it when you need exact wording, tables, or UI labels from an image path, when you want several images distilled instead of pasting pixels into this conversation, or when the current model refuses image input.',
  'When the current model does accept image input, read_image shows you the image itself; prefer it when appearance matters more than text.',
].join(' ')

/**
 * Resolve the plugin config over its defaults, rejecting unusable values early
 * so a broken route fails at activation instead of on the first call.
 * @param config - the patch row's raw config object.
 * @returns the resolved settings.
 */
function resolveConfig(config) {
  const raw = config !== null && typeof config === 'object' ? config : {}
  const text = (value, fallback) => (typeof value === 'string' && value.trim().length > 0 ? value.trim() : fallback)
  const count = (value, fallback) => (Number.isFinite(value) && value > 0 ? Math.floor(value) : fallback)
  const settings = {
    baseURL: text(raw.baseURL, DEFAULTS.baseURL).replace(/\/+$/, ''),
    model: text(raw.model, DEFAULTS.model),
    apiKeyEnv: text(raw.apiKeyEnv, DEFAULTS.apiKeyEnv),
    maxTokens: count(raw.maxTokens, DEFAULTS.maxTokens),
    timeoutMs: count(raw.timeoutMs, DEFAULTS.timeoutMs),
    maxImages: count(raw.maxImages, DEFAULTS.maxImages),
    maxImageBytes: count(raw.maxImageBytes, DEFAULTS.maxImageBytes),
    prompt: typeof raw.prompt === 'string' && raw.prompt.trim().length > 0 ? raw.prompt : DEFAULT_PROMPT,
  }
  try {
    const parsed = new URL(settings.baseURL)
    if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') throw new Error('scheme must be http or https')
  } catch (cause) {
    throw new Error('dsh-plugin-vision-read: baseURL must be a valid http(s) URL: ' + String(cause))
  }
  return settings
}

/**
 * Identify a supported raster image from its magic bytes.
 * @param data - the file bytes.
 * @returns the media type, or undefined when the bytes are not a supported image.
 */
function sniffMediaType(data) {
  if (data.length >= 8 && data[0] === 0x89 && data[1] === 0x50 && data[2] === 0x4e && data[3] === 0x47) return 'image/png'
  if (data.length >= 3 && data[0] === 0xff && data[1] === 0xd8 && data[2] === 0xff) return 'image/jpeg'
  if (data.length >= 6 && data[0] === 0x47 && data[1] === 0x49 && data[2] === 0x46) return 'image/gif'
  if (data.length >= 12 && data[0] === 0x52 && data[1] === 0x49 && data[2] === 0x46 && data[3] === 0x46
    && data[8] === 0x57 && data[9] === 0x45 && data[10] === 0x42 && data[11] === 0x50) return 'image/webp'
  return undefined
}

/**
 * Expand one caller-supplied path into the absolute candidates worth trying.
 * Relative paths are tried against the process directory and the session's
 * default working directory, because those differ between deployments.
 * @param path - the path as the model wrote it.
 * @param base - the session's default working directory, when known.
 * @returns ordered absolute candidates.
 */
function pathCandidates(path, base) {
  if (isAbsolute(path)) return [path]
  const candidates = [resolvePath(process.cwd(), path)]
  if (typeof base === 'string' && base.length > 0) {
    const fromBase = resolvePath(base, path)
    if (!candidates.includes(fromBase)) candidates.push(fromBase)
  }
  return candidates
}

/**
 * Read one image file, honouring the byte cap and sniffing its real type.
 * @param path - the path as the model wrote it.
 * @param base - the session's default working directory, when known.
 * @param maxBytes - the accepted byte ceiling.
 * @returns the loaded image.
 */
async function loadImage(path, base, maxBytes) {
  const candidates = pathCandidates(path, base)
  let lastError
  for (const candidate of candidates) {
    try {
      const info = await stat(candidate)
      if (!info.isFile()) {
        lastError = new Error('not a regular file')
        continue
      }
      if (info.size > maxBytes) throw new Error('file is ' + String(info.size) + ' bytes, above the ' + String(maxBytes) + ' byte cap')
      const data = new Uint8Array(await readFile(candidate))
      const mediaType = sniffMediaType(data)
      if (mediaType === undefined) throw new Error('not a PNG, JPEG, GIF, or WebP image')
      return { path: candidate, data, mediaType, bytes: data.length }
    } catch (error) {
      lastError = error
    }
  }
  throw new Error('cannot read "' + path + '": ' + (lastError === undefined ? 'not found' : String(lastError && lastError.message ? lastError.message : lastError)))
}

/**
 * Resolve the API key from the credential store, falling back to the process
 * environment. Resolution happens per call so a rotated key is picked up
 * without a restart.
 * @param ctx - the plugin context, whose `credentials` service may be mounted.
 * @param apiKeyEnv - the credential / environment-variable name to resolve.
 * @returns the key, or undefined while unconfigured.
 */
async function resolveApiKey(ctx, apiKeyEnv) {
  const credentials = ctx.get('credentials')
  if (credentials !== undefined) {
    try {
      const resolved = await credentials.resolve(apiKeyEnv)
      if (resolved !== undefined && typeof resolved.value === 'string' && resolved.value.length > 0) return resolved.value
    } catch {
      // A store failure degrades to the environment; the caller reports a
      // missing key with the same message either way.
    }
  }
  const fromEnv = process.env[apiKeyEnv]
  return typeof fromEnv === 'string' && fromEnv.length > 0 ? fromEnv : undefined
}

/**
 * Flatten an OpenAI-compatible message body into plain text.
 * @param message - the assistant message from the response.
 * @returns the visible text, falling back to reasoning text when a reasoning
 *   model spent its whole budget before emitting content.
 */
function messageText(message) {
  const content = message === null || message === undefined ? undefined : message.content
  if (typeof content === 'string' && content.trim().length > 0) return { text: content.trim(), reasoning: false }
  if (Array.isArray(content)) {
    const joined = content
      .map((part) => (part !== null && typeof part === 'object' && typeof part.text === 'string' ? part.text : ''))
      .join('')
      .trim()
    if (joined.length > 0) return { text: joined, reasoning: false }
  }
  const reasoning = typeof message?.reasoning_content === 'string' ? message.reasoning_content.trim() : ''
  if (reasoning.length > 0) return { text: reasoning, reasoning: true }
  return { text: '', reasoning: false }
}

/**
 * Ask the vision route about one image.
 * @param settings - resolved plugin settings.
 * @param key - the resolved API key.
 * @param image - the loaded image.
 * @param prompt - the instruction for this image.
 * @param signal - cooperative cancellation.
 * @returns the answer text plus the finish reason.
 */
async function describeImage(settings, key, image, prompt, signal) {
  const base64 = Buffer.from(image.data).toString('base64')
  const body = {
    model: settings.model,
    max_tokens: settings.maxTokens,
    stream: false,
    messages: [
      {
        role: 'user',
        content: [
          { type: 'text', text: prompt },
          { type: 'image_url', image_url: { url: 'data:' + image.mediaType + ';base64,' + base64 } },
        ],
      },
    ],
  }
  const response = await fetch(settings.baseURL + '/chat/completions', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      authorization: 'Bearer ' + key,
    },
    body: JSON.stringify(body),
    signal,
  })
  if (!response.ok) {
    const detail = (await response.text().catch(() => '')).slice(0, 500)
    throw new Error('HTTP ' + String(response.status) + ' from ' + settings.baseURL + ': ' + detail)
  }
  const payload = await response.json()
  const choice = Array.isArray(payload?.choices) ? payload.choices[0] : undefined
  if (choice === undefined) throw new Error('response carried no choices')
  const { text, reasoning } = messageText(choice.message)
  if (text.length === 0) throw new Error('response carried no text')
  return { text, reasoning, finish: typeof choice.finish_reason === 'string' ? choice.finish_reason : 'unknown' }
}

/**
 * A deadline that still observes the caller's cancellation.
 * @param signal - the caller's signal.
 * @param timeoutMs - the per-image deadline.
 * @returns the derived signal and its disposer.
 */
function deadline(signal, timeoutMs) {
  const controller = new AbortController()
  const onAbort = () => controller.abort(signal.reason)
  if (signal.aborted) controller.abort(signal.reason)
  else signal.addEventListener('abort', onAbort, { once: true })
  const timer = setTimeout(() => controller.abort(new Error('vision_read: request timed out after ' + String(timeoutMs) + ' ms')), timeoutMs)
  return {
    signal: controller.signal,
    dispose() {
      clearTimeout(timer)
      signal.removeEventListener('abort', onAbort)
    },
  }
}

/**
 * Render the canonical value as the text the model reads.
 * @param value - the validated tool value.
 * @returns the content blocks.
 */
function renderResults(value) {
  const lines = ['vision_read › ' + value.model + ' · ' + String(value.images.length) + ' image(s)']
  for (const image of value.images) {
    lines.push('')
    lines.push('## ' + image.path + '  (' + image.mediaType + ', ' + String(image.bytes) + ' bytes)')
    if (image.ok) {
      lines.push(image.text)
      if (image.finish === 'length') lines.push('')
      if (image.finish === 'length') lines.push('_[回答被 maxTokens 截断]_')
    } else {
      lines.push('读取失败: ' + image.text)
    }
  }
  return [{ type: 'text', text: lines.join('\n') }]
}

/**
 * Build the `vision_read` definition bound to one resolved configuration.
 * @param ctx - the plugin context.
 * @param settings - resolved plugin settings.
 * @returns the tool definition.
 */
function visionReadTool(ctx, settings) {
  return {
    name: 'vision_read',
    description: [
      'Read the text inside image files and return it as text, by calling a vision route on your behalf.',
      'Works even when the current model declares text-only input, because the calling model never receives the image.',
      'Give one to ' + String(settings.maxImages) + ' image paths (PNG/JPEG/GIF/WebP); paths may be absolute or relative to the working directory.',
      'Pass prompt to aim the extraction (for example "把这张表格转成 TSV" or "这个界面有哪些控件").',
    ].join(' '),
    parameters: {
      paths: {
        type: 'array',
        items: { type: 'string' },
        required: true,
        description: 'Image files to read, in order. Absolute paths, or paths relative to the working directory.',
      },
      prompt: {
        type: 'string',
        description: 'What to extract or answer about each image. Defaults to a full verbatim transcription plus a layout description.',
      },
    },
    output: {
      // `output.schema` is validated as the enforced raw JSON Schema subset, so
      // required members are listed once per node, not marked per property.
      schema: {
        type: 'object',
        additionalProperties: false,
        required: ['model', 'images'],
        properties: {
          model: { type: 'string' },
          images: {
            type: 'array',
            items: {
              type: 'object',
              additionalProperties: false,
              required: ['path', 'mediaType', 'bytes', 'ok', 'finish', 'text'],
              properties: {
                path: { type: 'string' },
                mediaType: { type: 'string' },
                bytes: { type: 'integer' },
                ok: { type: 'boolean' },
                finish: { type: 'string' },
                text: { type: 'string' },
              },
            },
          },
        },
      },
      render: (_args, value) => renderResults(value),
    },
    isConcurrencySafe: () => true,
    timeoutMs: settings.timeoutMs * Math.min(settings.maxImages, 2),
    async execute(args, exec) {
      const rawPaths = args !== null && typeof args === 'object' ? args.paths : undefined
      const paths = Array.isArray(rawPaths) ? rawPaths.filter((entry) => typeof entry === 'string' && entry.trim().length > 0) : []
      if (paths.length === 0) throw new Error('paths must hold at least one image path')
      if (paths.length > settings.maxImages) {
        throw new Error('at most ' + String(settings.maxImages) + ' images per call; split the request')
      }
      const prompt = typeof args.prompt === 'string' && args.prompt.trim().length > 0 ? args.prompt.trim() : settings.prompt
      const key = await resolveApiKey(ctx, settings.apiKeyEnv)
      if (key === undefined) {
        throw new Error('no API key: store a credential named ' + settings.apiKeyEnv + ' (or set that environment variable) for ' + settings.baseURL)
      }
      const base = ctx.get('workingDirectory')?.defaultDirectory
      const images = []
      for (const path of paths) {
        let loaded
        try {
          loaded = await loadImage(path, base, settings.maxImageBytes)
        } catch (error) {
          images.push({
            path,
            mediaType: 'unknown',
            bytes: 0,
            ok: false,
            finish: 'error',
            text: String(error && error.message ? error.message : error),
          })
          continue
        }
        const gate = deadline(exec.signal, settings.timeoutMs)
        try {
          const answer = await describeImage(settings, key, loaded, prompt, gate.signal)
          images.push({
            path: loaded.path,
            mediaType: loaded.mediaType,
            bytes: loaded.bytes,
            ok: true,
            finish: answer.finish,
            text: answer.reasoning ? '[该路由只产出了推理文本]\n' + answer.text : answer.text,
          })
        } catch (error) {
          images.push({
            path: loaded.path,
            mediaType: loaded.mediaType,
            bytes: loaded.bytes,
            ok: false,
            finish: 'error',
            text: String(error && error.message ? error.message : error),
          })
        } finally {
          gate.dispose()
        }
      }
      if (images.every((image) => !image.ok)) {
        throw new Error(images.map((image) => image.path + ': ' + image.text).join('\n'))
      }
      return { model: settings.model, images }
    },
    presentCall(args) {
      const count = Array.isArray(args?.paths) ? args.paths.length : 0
      return { card: 'generic', title: 'vision_read · ' + String(count) + ' image(s)', kind: 'read' }
    },
  }
}

/**
 * Register the tool and its model-facing guidance.
 * @param ctx - context whose tools and systemPrompt registries receive the
 *   registrations.
 * @param config - the patch row's config.
 */
export function apply(ctx, config) {
  const settings = resolveConfig(config)
  ctx.systemPrompt.section({ name: 'tool:vision-read', order: 112, text: GUIDANCE })
  ctx.tools.register(visionReadTool(ctx, settings))
}