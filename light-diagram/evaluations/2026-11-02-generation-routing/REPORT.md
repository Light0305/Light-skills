# 提示词优先与可选生图服务：2026-11-02

总入口与 prompt 子 skill 已统一采用：先交付完整提示词或实际文件链接；明确只要提示词时结束；否则优先宿主生图，宿主没有时使用用户配置，均不可用则交付提示词。用户明确指定自定义服务时优先遵从；配置不是必填步骤。

新增 [配置说明](../../light-diagram-prompt/references/image-generation.md)、[无密钥示例](../../light-diagram-prompt/assets/imagegen.example.json) 和 [调用助手](../../light-diagram-prompt/scripts/image_service.py)。自定义适配器支持同步 OpenAI 兼容 Image API 的 URL、Key/环境变量、模型及可选请求参数，不声称兼容任意厂商专用协议。实际生图前必须由助手发出提示词/链接；命令行中的交付标志不能证明 UI 消息已经发出。

## 本轮实际检查

- **41 项文档、检索与服务助手测试通过**：原 16 项，加 25 项路由/客户端检查。客户端对 localhost 模拟接口发送了真实 HTTP 请求；响应使用合成单像素 PNG。覆盖宿主优先、自定义覆盖、缺配置和未知能力、完整 Unicode 提示词传输、base64/URL 保存、下载不携带 Key、失败/队列/非图片响应、重定向不跟随、无自动重试、版本哈希、已有文件保护和调用前交付声明。
- **原 13 项交接回归检查通过**：复用旧三个后端案例的文件与审计；没有重新生图或打开绘图软件。
- **新 11 项交接声明检查通过**：[机器记录](handoff-verification.json)。覆盖提示词降级保留原目标、未执行不能登记已执行、新调用须有先行交付声明、执行版本一致、失败调用须有次数和证据、失败不能交付图片。这些是内存中的合成声明测试，引用旧文件不代表发生了新生图。
- 总入口与 prompt 子 skill 的宿主格式校验通过。新增/修改文档的本地链接与代码结构另行检查。

检查时发现并修正：损坏的可选配置不应阻止可用的宿主工具；“未调用”与“调用失败”不能使用同一状态；执行版本必须绑定已交付提示词。原生图形后端没有改动。

## 范围

本轮没有调用真实外部生图模型、使用真实 API Key、测定供应商兼容性或重新评价科学图片效果。以前的真实生图实测保留各自日期与报告；这次通过的是路由、HTTP 协议处理和交接一致性，不是新一轮生图质量验证。没有启用本地配置或安装到宿主全局 skills 目录。

重跑命令（从包目录执行）：

```powershell
python -X utf8 -m unittest discover -s light-diagram-prompt/tests -v
python -X utf8 evaluations/2026-10-31-integration/verify_integration.py
python -X utf8 evaluations/2026-11-02-generation-routing/verify_generation_handoff.py
```
