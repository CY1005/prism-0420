---
title: 安全基线（最小集占位决策）
status: accepted-minimal
owner: CY
created: 2026-04-20
accepted: 2026-04-26
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
