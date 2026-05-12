---
title: ADR-006 LLM provider 不引 SDK 依赖（httpx 直解析 SSE）
status: accepted
owner: CY
created: 2026-05-12
accepted: 2026-05-12
supersedes: []
superseded_by: null
last_reviewed_at: 2026-05-12
related_modules: [M13]
---

# ADR-006：LLM provider 不引 SDK 依赖

## Context（背景）

M13（需求分析）是 prism-0420 首个集成 LLM 调用的模块（sprint 完成于 2026-05-08）。需求路径：用户提交需求文本 → Claude 流式分析 → 返回结构化结果。

集成层面临选型问题：

| 方式 | 实现 |
|------|------|
| A. 引 `anthropic` SDK | `from anthropic import AsyncAnthropic; await client.messages.stream(...)` |
| B. 引 `openai` SDK（含 anthropic 兼容层）| 同上跨 provider |
| C. 直 `httpx.stream` 解析 anthropic SSE protocol | 自行处理 `data: {...}` 行 + `content_block_delta` 等事件 |

M13 sprint 期间 CY 拍定走 C，但**未走 ADR 流程**。本 ADR 补落该决策。

## Decision（决策）

**LLM provider 实现层不引 SDK 依赖，用 `httpx.stream` 直接解析 anthropic SSE wire protocol。**

具体：
- `ClaudeProvider`（`api/services/ai/claude_provider.py`）用 `httpx.AsyncClient.stream("POST", url, ...)` 调 anthropic `/v1/messages` 端点
- 自行解析 `data: {...}\n\n` SSE 帧
- 自行处理 `message_start` / `content_block_start` / `content_block_delta` / `content_block_stop` / `message_delta` / `message_stop` 事件类型
- 对未识别的 `delta.type` 显式 raise（M13 R1-A P1-3 抓出的契约校验）

未来添加 OpenAI / Gemini provider 遵守同样模式（各自 wire protocol + httpx）。

## Consequences（后果）

### 正面

- **依赖最小化**：与 prism-0420 单 ORM（SQLAlchemy）+ 最小依赖哲学一致（参见 ADR-001 §架构差异）
- **MockProvider 实现可控**：M13 设计了 `aclose_called: bool` 区分自然完成 vs caller 显式 `.aclose()`（PEP 533 GeneratorExit 才设 True）—— SDK 抽象下这个契约难以精确实现
- **API key 管理范式独立**：M13 走 `ProjectSettings.embedding_api_key_enc` + AES decrypt 全链路；SDK 默认 env 读，自管 wire protocol 才能控制 key 来源
- **协议演进可见**：anthropic SSE 协议升级时，自有解析代码会显式失败（content_block_delta 不识别即 raise）；SDK 抽象下静默兼容反而失去契约校验机会
- **测试边界清晰**：跳过 SDK 中间层意味着集成测试可用真 httpx mock（responses 库等），降低测试复杂度

### 负面

- **协议跟进负担**：anthropic SSE protocol 升级（如新增 delta type、引入 tool_use 流式格式）需要手工同步代码
- **工具调用扩展成本**：未来需要 function calling / tool use 时，要自行实现 SDK 已封装好的协议细节
- **错误码翻译**：HTTP 4xx/5xx 状态码 + anthropic 自定义错误结构需要自己映射到业务异常（M13 已实现 ConflictError / NodeNotFoundError 等映射）

### 横切影响

- **M18（embedding）现状不一致**：OpenAIEmbeddingProvider 当前从 `os.environ` 取 api_key，违反本 ADR 隐含的"key 走 ProjectSettings AES decrypt"范式 —— 由 F-6.14 跨 sprint punt 处理（待 sprint 末是否对齐自验）
- **新增 LLM provider 模板**：M13 ClaudeProvider 是参考样板，新 provider 实现时引本 ADR 声明"我用 httpx 直解析 X provider 的 wire protocol"

## Alternatives（备选方案）

### A. 引 anthropic SDK

- **优势**：协议变化自动适配；工具调用 / 流式 / batch API 等接口完整
- **劣势**：
  - 依赖膨胀（anthropic + 传递依赖 ~5MB）
  - 与 prism-0420 最小依赖哲学冲突
  - MockProvider 难精确控制 PEP 533 GeneratorExit 等行为
  - API key 默认 env 取，跟 ProjectSettings AES 范式冲突
- **拒绝**

### B. 抽象层 + 可选 SDK adapter

- **优势**：未来可以切 SDK 或自管
- **劣势**：YAGNI（当前只需 Claude）；过度抽象徒增维护负担
- **拒绝**

### C. httpx 直解析 SSE（采纳）

- **优势**：见 §Consequences 正面段
- **劣势**：见 §Consequences 负面段
- **采纳**：M13 sprint 已实施 + 跑通 + R1-A 抓出契约校验缺口已修

## 引用方

- `design/02-modules/M13-requirement-analysis/00-design.md` §6（provider 实现）、§12（MockProvider）、§14.5（spec 对齐验证）
- 未来添加 M-X（其他 LLM 集成模块）时引本 ADR
- `design/00-architecture/06-design-principles.md` §最小依赖原则（待补 — 见后续 lessons-learned）

## 关联

- [ADR-001](./ADR-001-shadow-prism.md)（§架构差异 - 最小依赖哲学起源）
- M13 design §6 / §12 / §14.5（具体实现 + MockProvider 契约 + spec 对齐）
- F-6.14（M18 OpenAI api_key 未对齐 ProjectSettings 范式 —— 跨 sprint punt）
- `_handoff/unsunk-scan-2026-05-12/chunk_6.md F-6.5`（本 ADR 起源 — 扫描提炼）
