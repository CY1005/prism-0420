---
title: 安全基线（最小集占位决策）
status: accepted-minimal
owner: CY
created: 2026-04-20
accepted: 2026-04-26
v2_revision: 2026-05-07  # §7 加 early adopter 触发条款 + 后续 D4 推演修订（含横切 vs 模块特定判断前置 + §7.1 横切三选一 / §7.2 模块特定三选一），详见 ../audit/time-dimension-blindspot-2026-05-07.md
phase: Phase 2.0 启动决策（A4.3）+ Phase 2.3 上线前补完
parent: ../00-roadmap.md
---

# 05 - 安全基线

> 认证方案 / 授权模型已在 [`../adr/ADR-004-auth-cross-cutting.md`](../adr/ADR-004-auth-cross-cutting.md) 决策完成，本文不重复。本期决密钥管理 + 加密 + 漏洞扫描最小集。详细 Phase 2.3 上线前补。

---

## 1. 认证方案（已决，引用）

✅ **决定**：见 [`ADR-004 Auth 横切`](../adr/ADR-004-auth-cross-cutting.md)
- P1 Bearer JWT（用户态，所有业务 endpoint）
- P2 internal token（Server Action → FastAPI 转发）
- P3 refresh token（M01 既有刷流程）
- P4 一次性确认 token（暂不引入，UI 二次确认替代 / M20 §8.5 Q11=A）

---

## 2. 授权模型（已决，引用）

✅ **决定**：见 [`ADR-001 Shadow 项目`](../adr/ADR-001-shadow-prism.md) + 各模块 §8 三层防御
- L1 Server Action / Router 粗粒度（require_user + require_*_access）
- L2 Service 细粒度（assert_*_role）
- L3 SQL 兜底（user_accessible_project_ids_subquery，M20 引入）

---

## 3. 密钥管理

| 候选 | 优 | 缺 |
|------|----|----|
| **A `.env` 本地 + `.env.example` 占位 + `.gitignore` 强制**| 0 依赖 / 单人项目足够 | 多人 / prod 时不可扩展 |
| B Doppler / 1Password / Vault 托管 | 多人友好 / prod-grade | Phase 2.0/2.1 过度 |

**决定**：✅ **A `.env`**

**理由**：单人项目，Phase 2.3 上线前可加托管，本期不引入

**.gitignore 强制项**：
```
.env
.env.local
.env.*.local
!.env.example
```

**.env.example 字段清单**（Phase 2.0 B1 仓库脚手架时建）：
```
# Database
PG_DSN=postgresql://prism:prism@localhost:5432/prism_dev
TEST_PG_DSN=postgresql://prism:prism@localhost:5432/prism_test

# Redis
REDIS_URL=redis://localhost:6379/0

# Auth
JWT_SECRET=__change_me__
INTERNAL_TOKEN_SECRET=__change_me__

# AI Provider
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
KIMI_API_KEY=

# Embedding
EMBEDDING_PROVIDER=mock-text-embedding-3-small
EMBEDDING_DIM=1536

# Observability
LOG_LEVEL=DEBUG
```

**替代触发**：多人协作 / prod 部署 → 切 B Doppler

---

## 4. 数据加密

| 项 | 决定 |
|----|------|
| **传输层** | HTTPS（Phase 2.3 上线时配 nginx + Let's Encrypt）|
| **DB 连接** | TLS（生产环境强制 sslmode=require）|
| **AI API Key 存储** | AES-256-GCM 加密（M02 ai_api_key_enc 字段已 design）|

### 4.1 AES-256-GCM helper 实装（M02 sprint 子片 3 落地，2026-05-07）

按本文 §7.1 B' 部分提前 + design/02-modules/M02-project/00-design.md §3.Z early adopter 触发：

- **位置**：`api/auth/crypto.py`（横切层；horizontal=是 / owner=M02 early adopter / 多模块复用候选 M13/M16/M17）
- **接口**：`encrypt(plaintext: str) -> str` / `decrypt(ciphertext_b64: str) -> str` / `generate_key_b64() -> str`
- **格式**：`base64(nonce[12B] || ciphertext+tag[≥16B])`
- **密钥**：`settings.encryption_key`（env `ENCRYPTION_KEY`，base64 of 32 bytes；dev default 已配，**生产部署必须覆盖**）
- **异常**：`CryptoKeyError`（密钥缺失/格式错/长度错）/ `CryptoDecryptError`（密文损坏/错密钥/InvalidTag）
- **测试**：`tests/test_m02_crypto.py` 14 PASS（encrypt/decrypt 往返 + 错密钥 + 错密文 + 短密文 + base64 + Unicode + 4KB 长文 + nonce 随机性）
- **本期不实装**（保留到 §8.0 上线前必补清单）：密钥轮转 / HSM/KMS 接入 / 多密钥 fallback / per-tenant key

| **JWT 签名** | HS256 + 长 secret（≥32 字符随机）|
| **password 存储** | bcrypt（M01 own）|

---

## 5. 漏洞扫描

| 候选 | 工具 | Phase 2.0 决定 |
|------|------|--------------|
| Python 依赖扫描 | pip-audit / safety | ✅ pip-audit（CI weekly） |
| Node 依赖扫描 | `npm audit` | ✅ CI weekly |
| Docker image 扫描 | Trivy | ⏳ Phase 2.3 上线前 |
| 代码层 SAST | bandit / semgrep | ⏳ Phase 2.3 上线前 |

---

## 6. 完成度判定（Phase 2.0 范围）

- [x] 认证方案（ADR-004 引用）
- [x] 授权模型（ADR-001 + 模块 §8 引用）
- [x] 密钥管理（.env + .env.example + .gitignore）
- [x] 数据加密最小集（HTTPS / TLS / AES-256-GCM / HS256 / bcrypt）
- [x] 漏洞扫描最小集（pip-audit + npm audit weekly）
- [ ] **Phase 2.3 上线前补**：Trivy / SAST / WAF / DDoS / Rate limiting

---

## 7. accepted-minimal 状态的 early adopter 触发条款（2026-05-07 时间维度盲区沉淀；2026-05-07 后续 D4 推演修订）

> **背景**：本文档与 03-cicd-plan / 04-observability-plan 同为 accepted-minimal——做了"够 Phase 2.0/2.1/2.2 业务开发的最小决策"，详细补完推到 Phase 2.3 §8.0。
>
> **盲点**：没规定"若 M02-M19 任一模块在 §8.0 补完之前就需要 minimal 之外的能力（如 AES helper 在 §8.0 之前用），如何处理"。M02 sprint 启动时首次撞到——`ai_api_key_enc` AES-256-GCM helper 在 §4 数据加密表已决（用 AES-256-GCM），但具体 helper 实装、密钥读 env 流程、加解密 service 边界都未在本文件落地。
>
> **修订盲点**（2026-05-07 后续）：D4 推演时发现原三选一里"B 模块 own helper"对**横切关注**是反模式——AES helper 是多模块复用（M02 写 / M13 读 / 未来 M16/M17 cron secret 加密），应建在横切层（`api/auth/crypto.py`），不是 M02 own。规则缺一道判断前置。

### 触发条款（修订版）

模块 M_X 的 sprint 启动 reconcile pass 期间，若发现本模块需要使用 03/04/05-spec accepted-minimal 范围**之外**的能力，sprint 启动前必须先做 **判断前置**，再按对应分支三选一。

#### 判断前置 — Helper 类型？

| 类型 | 判定标准 | 对应分支 |
|----|------|------|
| **横切关注**（horizontal） | 多模块复用 / 横切 ADR 范畴 / 工程基础设施（加密 / 限流 / 链路追踪 / metrics 等） | 走 §7.1 横切关注三选一 |
| **模块特定**（module-specific） | 仅当前模块业务逻辑用 / 不属于 horizontal ADR 范畴 / 业务规则封装 | 走 §7.2 模块特定三选一 |
| **不确定** | 信息不足判断 | **默认横切**（YAGNI 反向：先按横切建，未来发现真的只有一处用再降级——降级成本远低于"模块 own → 后期搬家成 horizontal"成本）|

**为什么"默认横切"**：项目早期 helper 抽象的边际成本低，但**横切关注被错放进模块 own** 的修复成本高（需迁移代码 + 改所有调用方 import + 测试回归）。M02 ai_api_key_enc helper 若误 own M02，M13/M16/M17 复用时要么重复造轮子，要么从 M02 模块 import horizontal helper（违反分层依赖方向）。

### §7.1 横切关注（horizontal）三选一

横切 helper 必须建在横切层（`api/auth/` / `api/services/` / `api/services/<helper>.py` / 等），**禁止挂在某业务模块名下**。三选一的差异在 spec 文档完整化程度，不在 helper 位置：

- **A 完整提前 §8.0**：本 sprint 内将 §8.0 必补清单中对应项**完整化**——spec 文档落地 helper 边界 + 密钥/配置来源 + 操作流程（如密钥轮转 / fallback / HSM）+ 测试策略；Phase 2.3 §8.0 必补清单划掉对应项；helper 建在横切层；优：spec 与实装同步演进 / 不留 disambiguation；缺：单 sprint 工作量 +30-60 min
- **B' 部分提前（spec 最小段）**：spec 文档**仅加最小回写**（helper 位置 + 配置来源 + 必要的引用注释，~5-10 行）；helper 建在横切层；密钥轮转 / HSM / 多密钥 fallback / 监控等推 §8.0；优：sprint 工作量最小化 + helper 位置正确（避免后期搬家）/ 缺：spec 不完整需在 §8.0 补完
- **C 推迟字段（明文 + TODO）**：本 sprint 不实装 helper，字段用明文 + TODO 注释；§8.0 必补清单加一项"X 字段加密"；优：单 sprint 0 helper 工作量；缺：开发期数据库可能含敏感明文（需 git fixture 隔离）；**不推荐用于安全敏感字段**

### §7.2 模块特定（module-specific）三选一

仅当 helper 真的只有当前模块业务用且不属于横切 ADR 范畴时适用：

- **A 提前 §8.0 部分项**：本 sprint 落到 spec 文档（仅当业务规则有跨模块共识价值）
- **B 模块 own helper（注明边界）**：M_X 自己建 helper，spec 文档标"M_X own，§8.0 上线时回收为横切 helper / 保持 own 待评估"；M_X sprint 边界清晰
- **C 推迟字段（明文 / 占位）**：当前 sprint 用占位实现 + TODO

### 决策登记格式（M_X sprint reconcile pass 文档）

```markdown
### early adopter 触发（accepted-minimal 之外能力）
- **能力**：xxx（如 AES-256-GCM 加解密 service）
- **来源 spec**：05-security-baseline §4
- **判断前置 — Helper 类型**：横切 / 模块特定 / 不确定→默认横切（理由：xxx）
- **退化路径**：§7.1 A / §7.1 B' / §7.1 C （或 §7.2 A / B / C）
- **本 sprint 实装边界**：xxx
- **回写动作**：（A 选项）spec §X 已更新 commit hash / （B' 选项）spec 加最小段 commit hash / （B 选项）spec 加 own helper 段 / （C 选项）§8.0 必补清单加项
```

### 决策登记格式（M_X sprint reconcile pass 文档）

```markdown
### early adopter 触发（accepted-minimal 之外能力）
- **能力**：xxx（如 AES-256-GCM 加解密 service）
- **来源 spec**：05-security-baseline §4
- **退化路径**：A / B / C
- **本 sprint 实装边界**：xxx
- **回写动作**：（A 选项）spec §X 已更新 commit hash / （B 选项）spec 加 own helper 段 / （C 选项）§8.0 必补清单加项
```

### 已知 early adopter 触发清单（持续维护）

| 模块 | 能力 | 来源 § | Helper 类型 | 退化路径 | 触发日期 | 落地状态 |
|----|----|------|--------|------|------|------|
| M02 | AES-256-GCM AI Key 加解密 helper | §4 数据加密 | **横切** (M02 写 / M13 读 / 未来 M16/M17 cron secret) | _M02 sprint 启动时按 §7.1 拍 A / B' / C_ | 2026-05-07 | _待 sprint 启动_ |
| M13 | 同上（M13 读 ai_api_key_enc 解密走 prompt context） | §4 数据加密 | **横切**（同 M02） | 复用 M02 决策 | 2026-05-07 | _待 M13 sprint_ |

### 适用文档

本条款同时适用于 03-cicd-plan / 04-observability-plan（均 accepted-minimal）。任一文档下的能力被提前需要时，按本条款三选一。
