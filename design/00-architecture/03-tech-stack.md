# 03 - 技术栈表

**状态**：accepted
**定稿日期**：2026-04-20

---

## Q1：照搬 Prism 还是简化？

**决策**：**其他 9 项照搬 Prism，ORM 简化为单 ORM（选 B）**

**理由**：
1. 其他 9 项（Next.js/React/shadcn/Tailwind/FastAPI/PostgreSQL/Auth.js/AI Provider/Docker）都是 Prism 的稳定选择，没有强烈理由要换——聚焦设计训练，不分心做技术选型
2. ORM 从双 ORM 改为单 ORM：Prism 的双 ORM 架构（Drizzle + SQLAlchemy 镜像）是历史包袱，schema 同步成本高，不是本期要训练的核心能力
3. 训练精力聚焦在"数据模型设计 + 前后端契约设计"——这是现代全栈工程的核心能力

---

## Q2：技术栈表

| 层 | 技术选型 | 理由 |
|----|---------|------|
| 前端框架 | Next.js 16 (App Router) + React 19 + TypeScript | 照搬 Prism，生态成熟 |
| 状态管理 | Server Actions + React Context | 照搬 Prism，Next.js 原生 |
| UI 库 | shadcn/ui v4 | 照搬 Prism，可定制性强 |
| CSS | Tailwind CSS 4 | 照搬 Prism |
| 后端框架 | FastAPI + Pydantic 2 | 照搬 Prism，原生支持 OpenAPI |
| **ORM** | **SQLAlchemy 2.0（单 ORM，唯一 schema 真相源）** | **简化**：避免双 ORM 同步漂移，单一真相源 |
| **迁移工具** | **Alembic** | **新增**：替代 drizzle-kit，SQLAlchemy 官方推荐 |
| **前后端契约** | **OpenAPI → openapi-typescript 生成 TS 类型** | **新增**：后端 Pydantic 自动生成 OpenAPI → 前端 codegen TS 类型 |
| 数据库 | PostgreSQL 16 + pgvector | 照搬 Prism，pgvector 支持语义搜索 |
| 认证 | Auth.js v5 + JWT + RBAC | 照搬 Prism |
| **Auth.js session 存储** | **Redis**（Auth.js v5 Redis adapter） | 已选 Redis 作基础设施，复用能力不增加新依赖 |
| AI 集成 | AI Provider 抽象层（Claude / DeepSeek / Kimi / OpenAI / Mock） | 照搬 Prism，多 Provider 可切换 |
| 嵌入服务 | OpenAI text-embedding-3-small / Mock | 照搬 Prism |
| 部署 | Docker Compose | 照搬 Prism，多服务编排简单 |

---

## Q3：关键决策的后果澄清（选 B 的隐含影响）

### 1. 架构级变化：前后端彻底分离

- 前端 Next.js **不能直接访问数据库**
- 所有 CRUD **必须走 FastAPI API**
- Server Actions 只能作为"调 FastAPI 的壳"（参数收集 + 认证检查 + 调用 API）

### 2. 新增工具链

- **Alembic**：替代 drizzle-kit 做数据库迁移
- **openapi-typescript**：FastAPI 的 `/openapi.json` → 前端 TS 类型定义

### 3. 前后端类型流转链路

```
SQLAlchemy models（DB schema 真相源）
    ↓
Pydantic schemas（请求/响应契约）
    ↓ FastAPI 启动时自动生成
OpenAPI 规范（/openapi.json）
    ↓ openapi-typescript 运行生成
TypeScript 类型定义（前端 .d.ts）
    ↓
前端代码调 fetch 时类型检查
```

**类型安全保证**：
- 编译期：tsc 检查类型匹配
- 运行时：后端 Pydantic 校验 + 前端可选 Zod 校验

### 4. 单点依赖风险

- FastAPI 成为**唯一后端**——FastAPI 挂 → 前端全挂
- 个人项目可接受短时停机，运维复杂度可控

### 5. 未来架构选择权

- 锁定 FastAPI 架构
- 未来想转向"纯 Next.js + Drizzle"全栈架构，迁移成本高
- 本期接受这个 trade-off

---

## Q4：新增学习任务（已记入知识库 TODO）

- Alembic 迁移工具学习（替代 drizzle-kit）—— 30 分钟官方教程
- openapi-typescript 配置实践—— 一次性 30 分钟
- 前后端类型流转心智模型—— 训练过程中内化

TODO 位置：`/root/cy/ai-quality-engineering/00-GTD/待办/TODO-index.md` → 线B Prism项目 → Prism-0420 Shadow 设计训练

---

## 完成度判定

- [x] 每行的"理由"都不为空
- [x] 双 ORM vs 单 ORM 决策有明确理由和后果澄清
- [x] 新增工具链（Alembic + openapi-typescript）已加入学习清单
- [x] Auth.js session 存储位置明确（Redis）
- [x] AI 完整性质疑通过
