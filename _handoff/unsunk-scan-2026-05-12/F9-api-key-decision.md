---
title: F9 — M18 OpenAI api_key vs M13 ProjectSettings AES 对齐决策
status: accepted
decision: 方案 A (env-only)
decided_at: 2026-05-12
decided_by: CY (显式拍 / 反向 audit 后明确授权)
created: 2026-05-12
related:
  - F-6.14 cross-sprint punt ✅ DONE
  - ADR-006 §Consequences 横切影响段（已修订）
  - M18 design §6 env 配置清单（已加 OPENAI_API_KEY）
  - api/services/embedding_provider.py:286-322（已删 R1 fix #13 TODO + DeprecationWarning）
  - chunk_6 F-6.5 / F-6.14
related_modules: [M02, M13, M18]
---

## 决议（2026-05-12 / CY 显式拍方案 A）

**采纳方案 A (env-only)**。落地变更：
1. `embedding_provider.py:286-322` 删 R1 fix #13 TODO + 删 DeprecationWarning + 改 docstring "接受 env-only 范式"
2. `M18 design §6 env 配置清单` 加 `OPENAI_API_KEY` 一行（含范式差异业务理由）
3. `ADR-006 §Consequences 横切影响段` 改"违反 ADR 隐含范式 punt 处理" → "范式差异是显式决策 / F-6.14 ✅ DONE"
4. `ADR-006 关联段` F-6.14 标 ✅ DONE
5. ADR-006 §正面段 typo 修：M13 字段 `embedding_api_key_enc` → `ai_api_key_enc` (M02 真实字段)

**业务理由**：embedding 是基础设施级（搜索 / RAG），与 M13 LLM analysis (业务级) 语义不同；ADR-001 §4 已声明 embedding provider 部署期固定；单租户场景 OpenAI 账号通常公司级一个 key。**可逆性**：未来多租户 SaaS 升级方案 B 无沉没（升级成本 ≈ B 工作量 1.5-2d / 无遗留）。

**预期影响**：spec→impl drift bug 修复（R1 fix #13 注释引用的 `ProjectSettings.embedding_api_key_enc` 字段从未实施，现删 TODO 字面化 env-only 为正式范式）。

---

# F9 — M18 OpenAI api_key 范式对齐决策建议

## 现状 fact-finding（2026-05-12 fact-finding subagent 跑）

### M13（已实施 / accepted）

**范式**：项目级 AES。
- `M02.projects.ai_api_key_enc`（VARCHAR，AES 加密存）+ `ai_provider` + `ai_model` 三字段
- `api/services/project_service.py:197-202`：`encrypt(fields["ai_api_key"])` 写入；`ai_api_key=None` 清密钥
- `api/services/analyze_service.py:299-309` + `ai_snapshot_service.py:323-333` + `ai_orchestration_service.py:243-252`：`decrypt(enc) → get_provider(provider_name, api_key=...)` 全链路
- AES 实现 `api/auth/crypto.py`（owner=M02 / 多模块复用 helper）
- 每 project 独立 key、admin UI 可改、活动日志可审计

### M18（部分实施 / Phase 2.1 accepted / R1 fix #13 留下 TODO）

**当前实情**：env-only fallback + TODO 走 AES。
- `api/services/embedding_provider.py:279-327`：`get_embedding_provider(api_key=...)` 接受 caller 传入，未传 fallback `os.getenv("OPENAI_API_KEY", "")` + `DeprecationWarning`
- 注释里写："R1 fix #13：caller 从 `ProjectSettings.embedding_api_key_enc` + AES decrypt 传入；未传时 fallback 到 os.getenv OPENAI_API_KEY"
- **但 `ProjectSettings.embedding_api_key_enc` 字段不存在**（`api/models/project.py` 只有 `ai_api_key_enc` / `rrf_k` / `similarity_threshold`，无 `embedding_api_key_enc`）
- M18 design §6 env 配置清单无 `OPENAI_API_KEY`（API key 来源未登记），只列 `EMBEDDING_PROVIDER` / `EMBEDDING_MODEL_NAME` / `EMBEDDING_MODEL_VERSION`
- M18 design §10 / §12 也无 key 来源段

### ADR-006 已声明 F-6.14（2026-05-12 立）

- ADR-006 §Consequences 横切影响段已显式承认："**M18（embedding）现状不一致**：OpenAIEmbeddingProvider 当前从 `os.environ` 取 api_key，违反本 ADR 隐含的'key 走 ProjectSettings AES decrypt'范式 —— 由 F-6.14 跨 sprint punt 处理（待 sprint 末是否对齐自验）"
- 所以本决策**不是新立 ADR-007**，而是对 ADR-006 横切影响段 + F-6.14 punt 的落地路径选型

---

## 决策候选（≥2 个 + 业务理由 + 优缺点 + 工作量）

### 方案 A：env-only（M18 不与 M13 对齐 / 全局 OPENAI_API_KEY）

**实现**：
- M18 design §6 env 配置清单加 `OPENAI_API_KEY` 一行（部署期注入 / secrets manager）
- `embedding_provider.py:316-327` 删 R1 fix #13 注释、删 DeprecationWarning，正式接受 env-only
- ADR-006 §Consequences 横切影响段改为"M18 与 M13 范式差异是显式决策（embedding 是基础设施 / LLM analysis 是业务功能）"

**业务理由 / 场景**：
- Embedding 是**基础设施级**功能（搜索 / RAG），不是按项目定制的 AI 行为
- 单租户部署下，OpenAI 账号通常是公司级一个 key，不是按项目分
- 维度 / model_name / model_version 切换是**运维操作**（ADR-001 §4 已声明），key 来源遵循同样的运维范式更自洽

**优点**：
- 实施工作量 ≈ **0.5 天**（删 TODO 注释 + 改 design §6 + 跑 R1-fix 改写 e2e）
- 与 ADR-001 §4 "embedding provider 部署期固定" 自洽
- 单租户 / 自部署场景天然适配
- 不引入新 ProjectSettings 字段、不动 alembic 迁移、不动 admin UI

**缺点**：
- **业务断面**：未来若引入"按项目跑 OpenAI / 按项目跑 bge / 按项目跑自有 embedding endpoint"则需重做范式
- **多租户 SaaS 演进路径堵死**：客户用自己的 OpenAI 账号、按 project 分隔 key 用量这个能力没了
- **审计弱**：env 注入的 key 没有 admin UI 改动轨迹（M13 改 ai_api_key 经 activity_log 记录，M18 没有）
- 与 M13 范式不一致 = 后续模块新增 LLM/embedding 时纠结"我学 M13 还是学 M18"

**3-5 月后果**：
- 若 dogfooding sprint + 0-1 商业化期间一直单租户 / 单 OpenAI 账号 → 无痛
- 若开启多租户或 customer-managed key 商业模式 → 需要回头加 ProjectSettings AES + 重写 caller 接通，约 2-3 天工作量
- 与"AI 质量工程师跳槽"叙事相关性低（不是面试加分项）

### 方案 B：ProjectSettings AES（M18 完全对齐 M13 范式 / 每 project 不同 key）

**实现**：
- M02 加字段 `projects.embedding_api_key_enc`（AES 加密存）+ alembic 迁移
- M02 ProjectService.update_project 扩 `embedding_api_key` 字段处理（同 `ai_api_key` 模式）
- M02 Server Action 表单加 OpenAI key 输入框（admin UI）
- `EmbeddingService._get_provider(db, project_id)` 从 ProjectSettings 读 enc → AES decrypt → 传给 `get_embedding_provider(api_key=...)`
- `embedding_provider.py:316-327` 删 env fallback、删 DeprecationWarning，正式只接受 caller 传入
- M18 design §6 / §10 加 "API key 来源" 段，cross-ref ADR-004 + M13
- ADR-006 §Consequences 横切影响段改为 "M18 已对齐 ProjectSettings AES 范式（commit XYZ）"

**业务理由 / 场景**：
- 多租户 SaaS 演进打基础：每客户用自己的 OpenAI key、用量隔离、可独立轮换
- 与 M13 范式完全一致 = 心智成本归零（新人加新 LLM/embedding 模块时直接抄）
- AI 质量审计叙事（用户 key 永不出客户租户 / 加密入库 / 改动有 activity_log 留痕）

**优点**：
- 与 M13 范式 1:1 对齐（一致性最优）
- 多租户 / SaaS 演进零阻力
- 审计 / activity_log / admin UI 改动留痕完整
- 跳槽叙事直接受益（"我做了 prism-0420 AI 凭据管理范式统一"）

**缺点**：
- 实施工作量 ≈ **1.5-2 天**（alembic 迁移 + ProjectService 改 + Server Action 表单 + EmbeddingService._get_provider 接通 + 6-8 e2e 测试）
- 引入一个不会马上用到的字段（dogfooding 单 OpenAI key 下，每 project 都填同一个 key 是冗余的）
- M18 worker 内的 `_get_provider` 需要从 payload 拿 project_id → 拉 ProjectSettings → decrypt，比 env 多 1 次 DB hit + 1 次解密 / task
- 不同 project key 不同时，缓存 provider 失效 / `EmbeddingService._provider_cache` 需要按 project key

**3-5 月后果**：
- dogfooding sprint 期间填重复 key 略冗余但无害
- 商业化 0-1 期若拓多租户 / SaaS = 直接复用范式 / 无返工
- 与 M02 admin UI 改动一并落地 = 一次性把 AI 凭据管理面板补齐

### 方案 C：混合（env fallback + project override）

**实现**：
- 加 `projects.embedding_api_key_enc` 字段（同 B）但**可空**
- `EmbeddingService._get_provider(db, project_id)`：先查 ProjectSettings.embedding_api_key_enc → 有则 decrypt 用 → 没有 fallback 到 `os.getenv("OPENAI_API_KEY")`
- M18 design §6 加 env 配置 `OPENAI_API_KEY`（fallback 用）
- M02 admin UI 加可选字段（空 = 用平台默认）
- 保留 R1 fix #13 注释精神但**显式化**为"fallback 是设计意图，不是 deprecated"

**业务理由 / 场景**：
- "平台默认 + 按需 override"模式（GitHub Actions / Vercel / 多数 SaaS 都用这种模式）
- 普通项目跑平台 key，重度用户自带 key 做用量隔离 / 控制成本

**优点**：
- dogfooding 期间不强制每 project 填 key（用平台默认 = 与方案 A 体验等同）
- 多租户演进时按需启用 project override（与方案 B 终态等同）
- 与 GitHub Actions secrets / Vercel env override 等行业范式契合

**缺点**：
- 实施工作量 ≈ **2-2.5 天**（同 B 的 alembic / ProjectService / Server Action + 多 1 个 fallback 分支 + fallback 命中场景 e2e）
- **审计复杂度变高**：一个 embedding 请求用了平台 key 还是 project key？需要 activity_log / observability 显式区分（M13 没这个二义性）
- **测试矩阵翻倍**：B 只测 project key 路径，C 要测 project key + fallback + project key 误删 fallback 兜底 等 3-4 个矩阵
- 与 M13 范式仍不完全一致（M13 没 fallback）

**3-5 月后果**：
- 演进最灵活，但工程复杂度最高
- 若 dogfooding 期间没人真用 project override = 等同方案 A 但多了未启用的代码 / 字段

---

## 推荐方向 + why

### 推荐 **方案 A（env-only）** 作为本期落地 / 但**显式声明 B 作为多租户启动时升级**

**核心理由**：

1. **YAGNI**：dogfooding sprint + 0-1 商业化期间，prism-0420 是单租户 / 单 OpenAI 账号场景；方案 B 引入的字段 + admin UI + alembic 迁移当前**零业务价值**
2. **一致性差异是可接受的**：M13 vs M18 范式差异有**业务语义**——M13 LLM analysis 是"按项目跑业务功能"（项目可选不同模型 / 不同 prompt 风格 → 自然按项目 key），M18 embedding 是"全局搜索基础设施"（部署期固定 provider / 维度切换是运维事件 → 全局 key 自洽）
3. **ADR-001 §4 已为这种差异打下地基**：embedding provider 部署期固定 / 不承诺运行时切换；env-only key 与"部署期固定"心智完全自洽
4. **可逆性**：A 升级到 B 的成本 ≈ 2 天（B 方案的工作量），后续多租户启动时一次性升级；不会有"现在做 A 浪费工作量"的沉没成本
5. **跳槽叙事不依赖此项**：质量工程师跳槽叙事核心是 PRISM 代表作 / Eval 工具链，"AI 凭据管理范式统一" 是次级叙事，不值得现在花 1.5-2 天

**反方思考（为什么不直接选 B）**：
- 唯一打动我的是"一致性 + 心智成本归零"；但 M13/M18 业务语义差异显式（功能 vs 基础设施）= 范式差异不是 bug 是 feature
- 若 CY 跳槽简历需要写"AI 凭据管理范式" → 改选 B（但建议放后置 sprint）

### 实施清单（若 CY 拍 A）

1. M18 design §6 env 配置清单加 `OPENAI_API_KEY` 一行（部署期注入 / secrets manager 推荐）
2. `embedding_provider.py:316-327` 把 DeprecationWarning 段改写为"env-only 是显式设计 / 不 deprecated"
3. ADR-006 §Consequences 横切影响段改写：把"违反 ADR 隐含范式"改为"M18 范式独立 / embedding 是基础设施 / 见 M18 design §6"
4. cross-sprint pool F-6.14 punt 标 ✅ DONE（决策落地 = punt 关闭）
5. 加 1 行 design 决策记录段："为什么 M13 走 ProjectSettings AES 而 M18 走 env-only" 解释业务语义差异

工作量 ≈ 0.5 天 / 不需要新 sprint。

### 实施清单（若 CY 拍 B）

1. 加 `projects.embedding_api_key_enc` 字段 + alembic 迁移
2. `ProjectService.update_project` 扩字段处理（同 ai_api_key 模式）
3. Server Action `actions/project-settings.ts` 表单加 OpenAI key 输入框
4. `EmbeddingService._get_provider(db, project_id)` 接通 ProjectSettings → AES decrypt → caller 传入 api_key
5. `embedding_provider.py:316-327` 删 env fallback、删 DeprecationWarning
6. M18 design §6 删 `OPENAI_API_KEY` env（或标 deprecated）+ §10 加"API key 来源"段（cross-ref M13 §6 + ADR-004 §3.7 secrets manager 候选）
7. 6-8 e2e（per-project key set / unset / cross-tenant 不读到对方 key / decrypt 失败 graceful 等）
8. cross-sprint pool F-6.14 punt 标 ✅ DONE
9. 新建 sprint 或并入下一 cleanup sprint（独立 sprint 更稳）

工作量 ≈ 1.5-2 天 / 建议独立小 sprint。

---

## 是否入 ADR？

**建议 = 仅 cross-ref + 改 ADR-006 横切影响段**（不新立 ADR-007）

理由：
- ADR-006 §Consequences 横切影响段已经显式声明 F-6.14；本决策落地后**就地修订** ADR-006 横切影响段比新立 ADR-007 更自洽
- 若 CY 拍 A：ADR-006 横切影响段改为"M18 范式独立（embedding 基础设施 vs M13 业务功能）"+ M18 design §6 加 env 配置说明
- 若 CY 拍 B：ADR-006 横切影响段改为"M18 已对齐 ProjectSettings AES 范式（commit XYZ）"
- 若 CY 拍 C：可考虑新立 ADR-007（混合范式涉及 fallback 优先级 / 审计区分 / 测试矩阵 = 决策复杂度足以单立 ADR）

### 与 Subagent 1（ADR-006 起草）协调点

> Subagent 1 已在 5/12 写了 ADR-006（status: accepted），本 subagent 不应再 own 起草

- 本决策建议主 agent 在 CY 拍方向后**就地修订 ADR-006 §Consequences 横切影响段**那一句话（不新立 ADR）
- 若 CY 拍 C → 升级为独立 ADR-007 + supersedes ADR-006 §Consequences 该段
- F-6.14 punt 在 cross-sprint pool 标 ✅ DONE 时同步引用本文件路径

---

## 关联

- ADR-006 §Consequences 横切影响段 + §关联 F-6.14
- chunk_6.md F-6.5（ADR-006 起源）+ F-6.14（M18 OpenAI 凭据 punt 起源）
- M13 design §3 上游依赖表（`projects.ai_api_key_enc` 读路径）
- M18 design §6 env 配置清单（待新增 `OPENAI_API_KEY` 行 / 若拍 A）
- `api/services/embedding_provider.py:279-327`（R1 fix #13 现状 / 待清理）
- `api/services/project_service.py:191-202`（M13/AES 范式参考）
