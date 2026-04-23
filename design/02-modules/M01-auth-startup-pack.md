---
title: M01 用户账号 - 启动包（auth pilot 模式，供新 session 使用）
status: draft
owner: CY
created: 2026-04-24
module_id: M01
prism_ref: F1
pilot: true
pilot_type: auth (同步 + 特殊横切)
---

# M01 启动包

> 本文件是 **M01 用户账号（auth pilot）** 的 brainstorming 启动包。由基线补丁 session（2026-04-24）扫完 Prism auth 现状后写就，供新 session 读完直接启动 M01 设计。
>
> **新 session 读完顺序**：本文件 → `02-modules/README.md`（16 字段模板 + R 规则）→ `M04-feature-archive/00-design.md`（同步 pilot 范本）→ `M17-ai-import/00-design.md`（pilot 流程范本）→ 回答 §5 brainstorming Q → 主对话出 16 节初稿。

---

## 1. 定位

- **模块号**：M01（C 档第三批 A2）
- **Prism 对应**：F1 用户账号
- **pilot 类型**：**auth pilot**——第三种 pilot 形态（M04 同步 / M17 异步 Queue / M01 认证横切）
- **范围**（CY 2026-04-24 ack）：**注册 / 登录 / session / profile**——不含 M20 团队空间 / 项目成员（那是 M02 自己的 `project_members` 表管理）

## 2. 与其他模块的横切关系

M01 是**最特殊的横切模块**——所有其他模块都依赖它（user_id 是所有业务表的 FK 源）。

| 模块 | 依赖 M01 的方式 |
|------|----------------|
| 所有模块 | `user_id UUID REFERENCES users(id)` 是 audit/ownership 的 FK 起点 |
| M02 项目 | `project_members.user_id` + `projects.created_by` |
| M15 数据流转 | `activity_log.user_id`（谁做的操作） |
| M09 搜索 | `accessible_project_ids` 依赖 user_id 查成员身份 |
| 所有路由 | `Depends(require_user)` / `Depends(check_project_access)`（ADR-001 权限三层） |

**核心挑战**：M01 自己不在乎其他模块，但其他模块全部依赖它 → §2 依赖图是单向的"所有 → M01"。

## 3. Prism auth 现状扫描（/root/prism）

### 3.1 User 数据模型（`api/models/tables.py:29-43`）

```python
class User(Base):
    __tablename__ = "users"
    id = Column(UUID, primary_key=True)
    email = Column(Text, unique=True, nullable=False)
    name = Column(Text, nullable=False)
    password_hash = Column(Text, nullable=False)         # bcrypt 12 rounds
    role = Column(Text, default="user")                   # platform_admin / user
    status = Column(Text, default="active")               # active / disabled
    token_invalidated_at = Column(DateTime)               # 全局撤销所有 JWT 的锚点
    failed_login_count = Column(Integer, default=0)
    locked_until = Column(DateTime)                       # 5 次失败 → 锁 15 min
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())
```

### 3.2 RefreshToken 表

```python
class RefreshToken(Base):
    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, FK users.id)
    token_hash = Column(Text)                 # sha256(raw_token)，raw 不落库
    expires_at = Column(DateTime)             # now + 7 days
```

### 3.3 已实现的端点（`api/routers/auth.py`）

| 方法 | 路径 | 功能 | 认证 |
|------|------|------|------|
| POST | `/login` | email+password → access+refresh token | 公开 |
| POST | `/refresh` | refresh token → 新 access token | 公开 |
| POST | `/logout` | 撤销 refresh token | 公开（凭 refresh token） |
| GET | `/me` | 当前用户 profile | require_user |
| GET | `/users` | 列所有用户 | require_admin |
| POST | `/users` | **admin** 创建用户（**用户无法自助注册**） | require_admin |
| PATCH | `/users/{id}` | 改 role / status | require_admin |

### 3.4 常量

- Access token: 15 min
- Refresh token: 7 days
- 失败锁: 5 次 → 15 min
- bcrypt: 12 rounds

### 3.5 Prism 的"内部服务"机制（重要）

Prism 是 Next.js + FastAPI 双栈架构，Next.js 走 Server Actions 调 FastAPI 时用 `X-Internal-Token`（HMAC 共享密钥） + `X-User-Id` 双 header 绕过 JWT（`api/routers/auth.py:47-54`）。

**prism-0420 决策建议**：保留 internal token 机制（Next.js → FastAPI 服务间），但 M01 §8 权限三层要把"internal token 路径"显式列出（ADR-002 类似，但新增 ADR 讨论）。

---

## 4. Prism vs CY 扩展范围的缺口

CY 本轮要做"注册 / 登录 / session / profile"4 项。对比 Prism：

| 能力 | Prism 现状 | M01 是否新增 | 决策点 |
|------|-----------|-------------|--------|
| **登录** | ✅ email+pw + JWT + refresh | 基本照搬 | 是否引入 OAuth/SSO？（Q4） |
| **注册** | ❌ 只有 admin 创建 | **新增用户自助注册** | 开放注册 vs 邀请码 vs 邮箱白名单？（Q1） |
| **忘记密码** | ❌ 无 | **可选新增**（注册需要）| 邮件重置 vs 管理员重置 vs 不做？（Q2） |
| **Profile** | 只有 GET /me | **新增 PATCH /me** | 改哪些字段（name / avatar / email / password）？（Q3） |
| **Session 管理** | 只有单 refresh token | **可选新增**（看/撤销设备）| 做 vs 不做？（Q5） |

---

## 5. Brainstorming 问题清单（CY 一次答完）

### Q1：注册策略——哪种？

**业务场景**：一个新用户打开 prism-0420 首页，想开始用。现在有 3 种路径。

- **A 完全开放**：填 email+密码直接注册，登录后自己建第一个项目。优点：零门槛。缺点：SPAM 注册、公网暴露要加验证码
- **B 邀请码注册**：必须有已注册用户的邀请链接才能注册。优点：熟人网络，质量高。缺点：冷启动慢，第一个用户怎么来？（admin 手动）
- **C 邮箱白名单**：只允许特定域名注册（如 `@yourcompany.com`）。优点：私有化场景强。缺点：个人用户用不了
- **D 管理员创建**（沿用 Prism）：没有自助注册，全部 admin 建账号。优点：最可控。缺点：单人用 prism-0420 场景下"admin 建自己"很奇怪

你选哪个？**单人/小团队场景**建议 A 或 D（D 需额外的"首个用户自动 admin"逻辑）。

### Q2：忘记密码流程——做吗？

- **A 做**：需要邮件服务（SMTP 或第三方）、token 链接、过期时间、防滥用节流。工作量大（约 1 额外子模块）
- **B 不做**：用户忘密码找 admin 手动重置（admin 改 password_hash 后推新密码给用户）。单人场景足够
- **C 延后**：本期不做，M01 frontmatter 标 `features_deferred: [forgot_password]`

倾向 B 或 C（单人场景用 B，团队场景 C 延后到 phase 2）。

### Q3：Profile 编辑——改哪些字段？

Prism 的 `/me` 只返回 `{id, email, name, role, status}`。PATCH /me 能改哪些？

- **name** ✅ 肯定可以
- **email**：改邮箱是大动作（唯一约束 + 可能破坏 session + 要验证新邮箱）。**做 / 延后 / 不做**？
- **password**：改密码需要旧密码验证 + 重新登录所有 session？**做 / 延后**？
- **avatar**（头像）：Prism 没这字段。**新增 / 不做**？单人项目不值得开文件上传这个坑
- **role/status**：禁止自改（admin 专有）——这是固定决策，不讨论

建议默认集：name + password（需旧密码验证），email + avatar 延后。

### Q4：第三方登录（OAuth / SSO）——做吗？

- **A 做（只 Google）**：Google OAuth 一条线。工作量 1-2 天。优点：用户零密码负担
- **B 做（GitHub）**：开发者友好。同工作量
- **C 都做**：工作量 x2，抽象 provider 层
- **D 不做**：只保留 email+password。最小化

prism-0420 是"shadow 对照项目"——Prism 都没做 OAuth，建议 **D 不做**保持对照洁净，但设计文档里要给"未来怎么加"的扩展口（ADR 级别）。

### Q5：Session 管理页——做吗？

"我的账号"页面能看到"当前已登录设备：iPhone / Mac Chrome / iPad"，点"撤销"让某设备下线。

- **A 做**：RefreshToken 表加 `device_info JSONB` + `last_used_at` + UI 页。工作量 1 子模块
- **B 不做**：单用户用多设备也无所谓，想强制下线就 admin 改 `token_invalidated_at`（全部下线）
- **C 延后**：frontmatter 标 deferred

建议 B（单人项目），除非你想对标 GitHub 式的设备管理体验。

### Q6：角色体系——保留 Prism 2 角色还是扩展？

Prism：`platform_admin` / `user` 两种。项目内角色（owner/editor/viewer）在 M02 `project_members` 单独管。

- **A 完全照搬**（2 全局角色 + 3 项目角色）
- **B 简化**：全局角色去掉 platform_admin，admin 能力下放到"第一个注册用户自动成为 platform_admin"
- **C 扩展**：加"billing_admin" 之类的分角色（prism-0420 非 SaaS 场景不需要）

建议 A 照搬——与 Prism 对照价值最大。

### Q7：首个用户 bootstrap 问题

无论 Q1 选哪个，都会遇到"系统启动时没有任何 admin，第一个账号怎么来"。

- **A 环境变量种子**：启动时读 `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` 自动创建
- **B 首次访问向导**：第一次打开系统显示"创建初始管理员"表单
- **C 命令行工具**：`python scripts/create_admin.py` 手动跑
- **D Alembic 迁移种子**：migration 里 INSERT 默认 admin

Prism 现状用哪个不明（要我再查一下 Prism 的 seed 逻辑就告诉我）。

---

## 6. 预期产出（pilot 特殊清单）

常规 pilot 输出：16 节 `00-design.md` + `tests.md`（按 02-modules/README.md 模板）。

**auth pilot 特殊产出**（沉淀为未来模块范本）：
- **ADR-004（建议）** 认证横切范式：用户自助注册策略 + JWT/Refresh 规范 + internal service token 机制 + 首用户 bootstrap 模式
- **R 规则新增候选**：
  - R-A1：所有模块 §8 权限三层必引 M01 的 `require_user` / `require_admin` / `check_project_access` 三个依赖之一（不得自造）
  - R-A2：所有业务表 `user_id` FK 必须 `ON DELETE RESTRICT`（防止删用户导致 audit 链断）——需 CY 决策
- **README R10-2 同类扩增**：M01 accepted 后回写 M15 ActionType（register / login / logout / password_change / profile_update 等）

## 7. 启动流程建议（M17 模式）

新 session 开启后：
1. 读本文件（启动包）→ 理解 Prism 现状 + CY 范围
2. 读 `02-modules/README.md` § 16 字段模板 + R 规则
3. 读 M17 §0-§5 看 pilot brainstorming 流程范例
4. 把 §5 的 7 个 Q 发给 CY → CY 一次答完
5. 主对话出 16 节初稿（含 ADR-004 草案）
6. 独立 reviewer Agent 三轮 audit（重点：§8 权限、§11 idempotency 注册场景、§12 session 持久化）
7. 主对话精修 blocker
8. CY ack → status=accepted

## 8. 关联文档

- `02-modules/README.md` 16 字段模板 + R0-R15 + R-X1-X4 + 新规则（R10-1 等）
- `M04-feature-archive/00-design.md` 同步 pilot 范本
- `M17-ai-import/00-design.md` 异步 pilot 范本（brainstorming 流程）
- `adr/ADR-001-shadow-prism.md` 权限三层基础（Server Action / Router / Service）
- `adr/ADR-002-queue-consumer-tenant-permission.md` 权限横切范式（auth pilot 会扩展）
- `baseline-patch-batch3.md` 最新合规要求
- Prism 源码：
  - `/root/prism/api/services/auth.py`
  - `/root/prism/api/routers/auth.py`
  - `/root/prism/api/schemas/auth.py`
  - `/root/prism/api/models/tables.py:29-43`（User model）
