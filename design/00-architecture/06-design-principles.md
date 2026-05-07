# 06 - 设计原则

**状态**：accepted
**定稿日期**：2026-04-20
**v2 修订**：2026-05-07（M02 sprint 启动 reconcile pass 暴露原则体系缺"横切 vs 业务关注"元维度，新增原则 6；详见 [`../audit/time-dimension-blindspot-2026-05-07.md`](../audit/time-dimension-blindspot-2026-05-07.md)）

---

## 6 条核心原则

> 原则数量精简——每条必须是**不可由其他原则推导的元维度**。新增原则前必证明独立性（如原则 6 横切 vs 业务边界与原则 2 纵向分层正交，不可互推）。
> 每条原则包含"是什么"+"违反时怎么办"。

### 原则 1：SQLAlchemy 是 schema 唯一真相源

**含义**：
- 所有 DB 字段定义在 SQLAlchemy models
- 前端通过 OpenAPI codegen 消费类型，不自己定义 schema
- 迁移通过 Alembic（替代 drizzle-kit）

**违反时怎么办**：
- 前端出现手写的 DB 字段类型 → code review 打回
- 前端绕过 OpenAPI codegen 直接 fetch 返回 `any` → CI 检查失败
- 任何双定义 schema 的 PR 阻塞合并

### 原则 2：分层严格，禁止跨层调用

**含义**：
- Page / Component → Server Action → Router → Service → DAO
- 每层只能调下一层，不能跨层
- Router 不能直查 DB，Server Action 不能直查 DB，Component 不能直接 fetch API

**违反时怎么办**：
- lint 规则禁止跨层 import（import 路径校验）
- code review 强制拦截
- 出现跨层调用的 PR 阻塞合并

### 原则 3：接口 Contract First

**含义**：
- 新 API 必须先定义 Pydantic schema（请求 + 响应）
- 再写实现逻辑
- OpenAPI 是前后端契约的真相源

**违反时怎么办**：
- CI 检查"所有 API route 必须有 Pydantic request / response schema"
- 无 schema 的 API 阻塞合并
- 前端生成的 TS 类型必须来自 OpenAPI（不允许手写对应）

### 原则 4：状态机必须显式定义

**含义**：
- 任何有 `status` 字段或有状态变化的实体，设计文档必须有状态机图
- 图必须包含：所有状态 + 允许转换 + 非法转换 + 触发事件 + 副作用

**违反时怎么办**：
- 设计 review 阶段强制检查状态机图
- PR 描述必须附状态机图链接（Mermaid 在设计文档中）
- 无状态机图的"有状态实体"阻塞合并

### 原则 5：多人架构 4 维必答（强约束）

**含义**：
- 每个模块设计必须显式回答：Tenant / 事务 / 异步 / 并发 4 个维度
- 每个维度答案必须对照下方"多人架构约束清单"逐项检查
- 即使答案是"不涉及"也必须显式写明（不能省略）

**违反时怎么办**：
- 模块设计 checklist 强制覆盖 4 维
- 未对照清单检查 → review 拦截
- 任一清单项违反 = 违反本原则 = 阻塞合并

---

### 原则 6：横切关注 vs 业务关注必须显式判定（2026-05-07 时间维度盲区沉淀）

**含义**：

- 任何 helper / service / 配置 / 基础设施在 design 时必须**显式声明类型**：
  - **horizontal**（横切关注）：多模块复用 / 横切 ADR 范畴 / 工程基础设施（加密 / 限流 / 链路追踪 / metrics / 鉴权 / activity_log / tenant_filter / queue scaffold 等）
  - **module-specific**（业务关注）：仅当前模块业务规则封装 / 不属于 horizontal ADR 范畴 / 不被其他模块复用
- **横切关注必须建在横切层**（`api/auth/` / `api/errors/` / `api/services/<horizontal>.py` / `.github/workflows/` / 等），**禁止挂在某业务模块名下**
- **不确定时默认横切**（YAGNI 反向）：项目早期 helper 抽象的边际成本低，但**横切关注被错放进模块 own** 的修复成本高（需迁移代码 + 改所有调用方 import + 测试回归）；降级"horizontal → 模块 own"成本远低于升级"模块 own → horizontal"
- 与原则 2（分层严格）的关系：原则 2 是**纵向**分层（Page/Server Action/Router/Service/DAO/Model），原则 6 是**横向**归属（horizontal vs business），两者正交

**典型反模式**（违反原则 6）：

| 反模式 | 错例 | 正确 |
|----|----|----|
| 横切 helper 挂在业务模块名下 | `api/services/m02/crypto.py` | `api/auth/crypto.py`（horizontal owner = 05-security-baseline）|
| frontmatter `helpers:` 引用业务模块路径 | `helpers: { crypto: { ref: M02.crypto } }` | `helpers: { crypto: { ref: api/auth/crypto.py } }` |
| accepted-minimal 早期触发条款选 "B 模块 own helper" 处理横切关注 | M02 own AES helper（违反 §7 修订版） | §7.1 横切关注三选一（A 完整 / B' 部分 / C 推迟），helper 都建在横切层 |

**违反时怎么办**：
- design accepted 前 reviewer 强制扫描所有 helper 引用归属
- 横切层文件清单见 [`04-layer-architecture.md`](./04-layer-architecture.md) §横切层定义
- 违反 → 阻塞 accept，修复后再审
- 已 accepted 模块若发现违反（如 prism-0420 2026-05-07 §7 修订暴露），立刻回扫修复

**关联**：
- R-X6（02-modules/README.md）：横切 helper 必建在横切层 + 注释含 4 字段强制模板（归纳 scaffold S2/S5 先例）
- frontmatter `helpers:` 字段约束（02-modules/README.md）：仅允许引用横切层路径
- accepted-minimal §7 触发条款（05-security-baseline.md）：判断前置（horizontal vs module-specific）

---

## 多人架构约束清单（原则 5 的强制实施细则）

> **必须参考**——每个模块设计和实现都必须对照此清单逐项检查。违反任一项 = 违反原则 5 = 阻塞合并。

### 清单 1：所有变更操作必须写 activity_log

- **目的**：审计可追溯（谁在什么时候改了什么）
- **执行**：Service 层 create / update / delete 方法必须调 `activity_dao.log(user_id, action, entity_id)`
- **检查**：CI 扫描 Service 层的变更方法，必须包含 activity_log 调用
- **豁免条件**：无（所有变更操作都要记录，包括系统任务）

### 清单 2：可能并发编辑的实体必须有 version 字段（乐观锁）

- **目的**：防止多人同时编辑导致静默数据丢失
- **执行**：SQLAlchemy model 定义 `version: int`，update 时 `WHERE id=? AND version=expected`，影响行数 0 则抛 ConflictError
- **检查**：
  - 数据模型设计阶段标注哪些实体"可能并发编辑"
  - 这些实体必须有 version 字段
- **豁免条件**：只有单用户能编辑的实体（如 user profile）

### 清单 3：异步任务 payload 必须带 user_id + project_id

- **目的**：tenant 隔离强制，防止 Queue 消费者绕过权限
- **执行**：
  - 所有 `queue.enqueue()` 的 payload 必须包含 user_id 和 project_id
  - 定义统一的 Task 基类强制这两个字段（类似 Pydantic 校验）
  - Queue 消费者入口校验 payload 字段
- **检查**：静态分析扫描 `queue.enqueue()` 调用点
- **豁免条件**：系统级任务（如数据清理 / 定时统计）—— 但必须显式记录豁免理由

### 清单 4：敏感操作必须有 idempotency_key

- **目的**：防止重复提交（用户重复点击 / 网络重试导致重复执行）
- **执行**：
  - 客户端生成 idempotency_key（UUID）
  - 服务端收到后查 Redis 判断是否已处理过
  - 已处理返回原结果，未处理执行并缓存结果
- **适用操作**：删除 / 审批 / 发布 / 支付类
- **检查**：敏感操作的 API schema 必须接受 idempotency_key 参数
- **豁免条件**：只读操作（GET）不需要

### 清单 5：DAO 层查询必须显式带 tenant 过滤（读路径 tenant 隔离）

- **目的**：防止读路径越权——多租户系统最常见的安全漏洞
- **执行**：
  - 所有 DAO 层的 `SELECT` / `UPDATE` / `DELETE` 必须包含 tenant 过滤条件
  - 常见条件：`WHERE project_id = ?` 或 `WHERE user_id = ?` 或 `WHERE project_id IN (<user 有权限的 project ids>)`
- **检查**：CI 扫描 DAO 层，发现无 tenant 过滤的查询 → 告警阻塞合并
- **豁免条件**（必须显式声明）：
  - 全局数据：用户系统登录查询 / 全局行业动态 / 系统配置表
  - 管理员操作（平台管理员可跨 tenant）——接口层需显式标注 `@admin_only`
- **配合原则**：本清单覆盖"读路径"；原则 5 的其他清单覆盖"写路径"（activity_log / 乐观锁 / Queue tenant / 幂等）

---

## 原则间的优先级

如果原则冲突，按序决策：

1. **原则 5（多人架构）** ≥ 其他——安全性优先
2. **原则 2（分层）** ≥ 原则 4（状态机）——架构正确性优先于文档完整性
3. **原则 1 / 3（schema / contract）**：并列，都是前后端对齐的基石

---

## 完成度判定

- [x] 5 条原则都有"违反时怎么办"
- [x] 多人架构约束清单 4 项都明确
- [x] 原则 5 明确引用清单（强约束关系）
- [x] 清单标注"必须参考"、每项有检查方式和豁免条件
- [x] 原则间优先级明确
- [x] AI 完整性质疑通过

## 关联参考

- 多人架构 4 维的原理和例子：`/root/cy/ai-quality-engineering/02-技术/架构设计/工程师必懂架构决策-分层权限事务隔离.md`
- 分层实施细节：`/root/cy/prism-0420/design/00-architecture/04-layer-architecture.md`
