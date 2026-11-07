# 提示词交付、生图能力与自定义配置

适用于总入口和单独使用 `light-diagram-prompt`。提示词始终是交付物；是否实际生图取决于用户要求、宿主可用工具和可选配置。配置和网络都不是提示词制作的依赖。

## 执行顺序

1. 完成科学 brief、结构蓝图、标签白名单和完整提示词。准备生图时保存为案例目录中的 `prompt-v1.txt`；修改用新的版本文件。
2. **调用前**在用户可见回复中贴完整提示词，或给出实际文件的可点击链接。可写“生图提示词已保存：”并用 `[查看提示词](绝对文件路径)` 链接实际文件。不等待例行确认；后续版本、编辑提示词也同样先交付。仅写磁盘、打印工具日志或调用结束后再补链接都不满足这项要求。
3. 明确“只要提示词”时结束，不读取 Key、不调用任何生图服务。
4. 否则发现宿主实际暴露的生图工具或连接器。宿主模型会描述图片不等于已提供可调用的生图工具；不能从模型名称推断可用能力。
5. 默认 `auto`：宿主工具可用 → 直接用宿主工具；宿主没有 → 按现有宿主 fallback 或用户配置路由；没有可用路线 → 交付提示词并结束。用户明确要求自定义服务则使用 `custom`，不会因宿主可用而覆盖用户选择。
6. 得到真实图片后检查科学关系、标签与版式，再交给后端或交付图片。总入口与子 skill 共用本次结果，不能各生成一次。

宿主路线必须遵守该环境的生图工具与 skill 要求，包括生成/编辑语义、透明背景和引用图处理。自定义配置不会绕过宿主约束。当前助手可以发现并使用内置生图工具，但本地 Python 无法代调它；`plan` 返回 `builtin` 后，由助手执行工具调用。

## 已有宿主 fallback

若宿主有 imagegen 与 imagegen-fallback，读取并遵循其现有路由：内置优先；不可用或技术失败时，可在已有授权内使用其配置与适配器，不要求另一套 Key，不另造 SDK runner。安全拒绝不得换供应商绕过。记录实际尝试、失败与采用结果；技术超时可能已执行，先检查已有任务/产物，不无界重复调用。已有用户授权持续有效，无需按阶段重复确认；无此路线或授权时才按真实条件说明可用选择。

下方 Python helper 是独立环境的可移植同步 text-to-image 适配器，不实现宿主 fallback、不读取其他工具的配置，也不能用其 plan 结果否定宿主已经提供的能力。测试它不需要真实服务或任何用户密钥。

## 可选配置

示例文件：[imagegen.example.json](../assets/imagegen.example.json)。复制到本 skill 目录下的 `imagegen.local.json` 后填写真实服务；该文件已列入本目录 `.gitignore`。也可把配置放在其他位置，通过 `--config` 或 `LIGHT_DIAGRAM_IMAGE_CONFIG` 指定。

查找顺序：显式 `--config` → `LIGHT_DIAGRAM_IMAGE_CONFIG` → 本 skill 下的 `imagegen.local.json`。示例文件不会自动启用。不要搜索其他项目的密钥或修改宿主全局设置。

```json
{
  "provider": "auto",
  "api_style": "openai_images",
  "url": "https://your-image-service.example/v1/images/generations",
  "api_key_env": "LIGHT_DIAGRAM_IMAGE_API_KEY",
  "model": "YOUR_IMAGE_MODEL",
  "timeout_seconds": 180,
  "params": {}
}
```

- `provider`：`auto` 默认优先宿主；`custom` 明确使用此服务；`builtin` 只用宿主；`prompt_only` 只交付提示词。用户当前明确指令优先于文件偏好。
- `url`：完整生图接口地址；也接受服务根地址或 `/v1` 前缀，分别补齐为 `/v1/images/generations` 或追加 `/images/generations`。其他明确接口路径原样保留。也可改用 `base_url`，如 `https://your-image-service.example/v1`；两者同时填写以 `url` 为准。实际使用地址会记录在 generation.json。
- `api_key_env`：Key 所在的环境变量名；也支持 `api_key` 直接填写 Key，环境变量有值时优先。Key 不传命令行，不进入提示词、报告或输出日志。
- `model`：用户服务实际支持的生图模型名，不绑定某个厂商或版本。
- `params`：服务支持的可选请求字段，如 `size`、`quality`、`output_format`；默认只发送 `model`、`prompt`、`n: 1`。不强制发送 `response_format`，因为不同模型不一定支持。`params` 不能覆盖实际提示词、模型、认证或开启流式响应。
- `timeout_seconds`：单次请求/下载超时。默认不自动重试；超时可能已产生服务端任务，不能推断为没有计费。
- 无需认证的本地兼容服务可指定 `auth: "none"`；默认是 Bearer Key。外部接口使用 HTTPS，本机服务可用 localhost HTTP。

最简配置也可以只填 `url`、`api_key`、`model`，其余使用默认值。不要将带 Key 的配置提交或复制到交付案例中。

当前适配器支持**同步、非流式、OpenAI 兼容 Image API**：发送 JSON，读取 `data[].b64_json` 或 `data[].url`，保存 PNG/JPEG/WebP。服务返回 URL 时下载图片，不向图片地址转发 API Key。不支持所有模型供应商的专用协议、异步任务轮询、聊天接口生图、上传参考图或图像编辑；这些需要使用宿主已有适配工具或另行实现适配器，不能只改模型名就声称兼容。

协议依据：[OpenAI Image API 官方参考](https://developers.openai.com/api/reference/resources/images/methods/generate)。第三方的兼容程度取决于其实际接口；代码通过本地协议测试不代表已验证某个第三方服务。

客户端请求携带 `light-diagram/1.0` 应用标识，避免部分网关拒绝默认 Python 请求标识。已验证的一个用户服务案例与适用边界见 [真实接入测试](../../evaluations/2026-11-02-custom-service-test/REPORT.md)；不保证其他服务采用相同协议或可用模型。

## 调用助手

以下是可移植的 PowerShell 示例，`$skill` 是 prompt 子 skill 的绝对目录，`$case` 是本次案例目录。助手先发现宿主能力，再填 `yes` 或 `no`，不能让用户重复判断。`unknown` 会要求先发现，不会偷选自定义服务。

```powershell
python -X utf8 "$skill/scripts/image_service.py" plan --prompt "$case/prompt-v1.txt" --host-available yes
```

`plan` 只做离线决策，既不调用 API，也不创建图片。即使自定义服务未配置，宿主可用时仍应直接调用宿主；无须为了它先准备 Key。

无宿主工具且配置完成时，**先在回复中交付提示词/文件链接**，再运行：

```powershell
python -X utf8 "$skill/scripts/image_service.py" generate --prompt "$case/prompt-v1.txt" --host-available no --config "$skill/imagegen.local.json" --output-dir "$case/image-v1" --prompt-published
```

`--prompt-published` 是调用方对已交付提示词的声明，脚本不能验证用户实际看到了消息。输出目录必须不存在，以保护已有版本。新目录包含实际执行提示词、生成图片和 `generation.json`；记录输出哈希、调用次数与未做图像检查的状态，保留原始提示词文件。

`generate` 在选到宿主或提示词路线时只报告该路线，不会伪造图片。路由配置不完整、宿主能力未知或接口失败返回非零状态；提示词路径仍会输出。Key/接口错误的原始响应不写入日志。若有服务端修订提示词，当前记录不声称掌握该内部改写，执行记录指本地发送版本。

## 降级与交接

没有服务或配置不完整：交付完整提示词/链接，简述未生图原因；不强迫用户补配置，不自动启动后端复现。在共同交接中用 `generation.status: not_run`、`calls_this_run: 0`、`executed_prompt: null`。

已经调用但失败：用 `generation.status: failed`，记录实际调用数、发送提示词与脱敏失败记录；不得写成 `not_run` 或 `generated`，不自动反复重试或静默换服务。宿主已授权的技术 fallback 按上节执行并保留失败链，不能用 fallback 绕过安全拒绝。提示词仍可交付。

若本次最终只交付提示词，`output_mode: prompt_only`；原始图像/编辑文件目标存入 `requested_output_mode`，解释可以在用户之后提供图像或配置时继续。提示词质量核查通过不等于生图已通过。

新生图的 handoff 增加 `generation.selection`（`builtin|custom|prompt_only`）及 `prompt_delivery: {artifact: "prompt", channel: "inline|file_link", before_call: true}`。后者是交付声明与文件绑定，不是 UI 阅读证明；验证器只能核对一致性。实际生图后 `generation.executed_prompt` 指向所交付版本；旧案例没有这些新增字段时保持可追溯兼容。
