# 01 - 工程规约（engineering-spec）

**状态**：draft（A 档已填，B/C 档待填）
**定稿日期**：—
**档位**：B
**关联**：`design/00-architecture/04-layer-architecture.md`、`design/00-architecture/06-design-principles.md`、`design/adr/ADR-001-shadow-prism.md`
**宏观讲解**（为什么这么定）：知识库 `/root/cy/ai-quality-engineering/02-技术/架构设计/工程规约7条详解-AI时代工程素养基石.md`

---

## 引言

### 这文档是什么

prism-0420 所有代码必须遵守的工程规约。覆盖目录、命名、风格、分层、commit、错误、PR、分支、依赖、文档、类型、review、版本、注释 共 15 条规约（不含 i18n）。

### 为什么要

- AI 实现 20 个模块时风格不一致 → PR review 浪费在格式而非业务逻辑
- 多人架构约束（详见 06-design-principles.md 原则 5）必须有可执行的规约支撑
- "设计前置 vs 边做边想"对照需要可量化的工程指标（commit 一致性 / lint 通过率 / PR 流程完整度）

### 强制级别

| 级别 | 含义 | 失败后果 |
|------|------|----------|
| **A 档**（强制） | CI lint 必须通过 / 静态扫描必须通过 | PR 不能合并 |
| **B 档**（强制） | PR review checklist 必须勾过 | PR 不能合并（review 拦截） |
| **C 档**（参考） | 写到文档但不机械强制 | 鼓励遵守，违反需说明理由 |

### 如何使用

- **AI 实现前**：读相关条目（≤5 条），不需要全文
- **PR 提交时**：核对 PR 模板里的 checklist（B-08）
- **对抗式 Reviewer**：以本文档为依据判断 AI 输出是否合规

---

# A 档 强制（CI lint / 静态扫描必须通过）

## 1. 目录结构（A）

**适用范围**：全部

**规则**：

```
prism-0420/
├── api/                           # FastAPI 后端
│   ├── main.py                    # 应用入口 + 路由注册（不放业务逻辑）
│   ├── config.py                  # 配置加载（pydantic-settings，唯一读 env 的地方）
│   ├── deps.py                    # FastAPI 依赖注入（db session / current_user）
│   ├── routers/                   # 路由层
│   │   ├── module_router.py       # 命名：{资源}_router.py
│   │   └── ...
│   ├── services/                  # 业务逻辑层
│   │   ├── module_service.py      # 命名：{资源}_service.py
│   │   └── ...
│   ├── dao/                       # 数据访问层（必须含 tenant 过滤）
│   │   ├── module_dao.py
│   │   └── ...
│   ├── models/                    # SQLAlchemy 模型（schema 唯一真相源）
│   │   ├── module.py              # 一个表一个文件
│   │   └── base.py                # Base + 通用字段（id/created_at/updated_at/version）
│   ├── schemas/                   # Pydantic 请求/响应模型
│   │   ├── module_schema.py
│   │   └── ...
│   ├── queue/                     # arq 任务定义
│   │   ├── tasks.py               # @task 装饰的函数
│   │   └── base.py                # TaskPayload 基类（强制 user_id + project_id）
│   ├── errors/                    # AppError + ErrorCode 枚举（前后端一致）
│   │   ├── codes.py               # ErrorCode 枚举（唯一真相源）
│   │   └── exceptions.py          # AppError 类层级
│   ├── utils/                     # 通用工具（无业务）
│   ├── alembic/                   # 数据库迁移
│   └── tests/                     # pytest 套件
│
├── web/                           # Next.js 前端
│   ├── src/app/                   # App Router 页面
│   │   └── (routes)/page.tsx      # 页面文件
│   ├── src/actions/               # Server Actions（薄壳，仅参数+权限+调 services/）
│   │   └── module.ts
│   ├── src/services/              # API 客户端（调 FastAPI）
│   │   └── module-service.ts
│   ├── src/components/
│   │   ├── ui/                    # shadcn/ui 原子组件
│   │   └── business/              # 业务组件
│   ├── src/lib/                   # 工具函数 + 类型
│   ├── src/contexts/              # React Context
│   ├── src/errors/                # 错误码（从后端 OpenAPI 同步生成）
│   └── src/types/api.ts           # OpenAPI codegen 输出（不手写）
│
├── docs/                          # 项目文档
│   ├── adr/                       # 架构决策（ADR-NNN-题目.md）
│   ├── architecture/              # 技术架构（arc42 格式）
│   ├── product/                   # PRD
│   └── skills/                    # 开发触发型 skills
│
├── design/                        # 设计前置文档（本目录）
│   ├── 00-architecture/           # 档位 A：架构骨架
│   ├── 01-engineering/            # 档位 B：工程规约
│   ├── 02-modules/                # 档位 C：模块详细设计（M01-M20）
│   ├── 99-comparison/             # 与 Prism 对照报告
│   └── adr/                       # 设计阶段 ADR
│
├── scripts/                       # 工具脚本（部署 / 数据迁移 / 验证）
└── tests/                         # 跨服务集成测试（前后端联调）
```

**每目录的"禁止做什么"**：

| 目录 | 禁止 |
|------|------|
| `api/main.py` | 写业务逻辑、写 DB 查询 |
| `api/routers/` | 直查 DB、写文件、跨 router 调用 |
| `api/services/` | 直接 SQL、直接 HTTP（必须经 dao 或 queue）、直接读 env |
| `api/dao/` | 业务判断（"if 状态 == X then..."）、跨表 JOIN（除非显式标注理由） |
| `api/models/` | 业务方法（如 `def can_edit()`）—— 业务逻辑放 service |
| `api/schemas/` | 业务方法、SQLAlchemy import |
| `web/src/app/` | 直接调 dao / 直接 SQL |
| `web/src/actions/` | 业务逻辑（必须调 services 或 fetch FastAPI） |
| `web/src/components/` | 直接调 dao 或写 SQL |

**space_id 预留口**（呼应 ADR-001"不引入空间但预留扩展"）：

- `api/models/base.py` 的 Base 类**预留** `space_id: int | None` 字段（默认 NULL，未来引入空间时启用）
- 当前阶段 DAO 层 tenant 过滤**只用** `user_id + project_id`，不引用 space_id
- 引入空间的触发条件：单 user 跨多 project 时需要"工作组"概念

**示例（AI 实现新模块时的标准目录创建顺序）**：

1. `api/models/{module}.py` ← schema 真相源先建
2. `api/schemas/{module}_schema.py`
3. `api/dao/{module}_dao.py`
4. `api/services/{module}_service.py`
5. `api/routers/{module}_router.py`
6. `api/main.py` 注册路由
7. `web/src/types/api.ts` 重新 codegen
8. `web/src/services/{module}-service.ts`
9. `web/src/actions/{module}.ts`
10. `web/src/app/{module}/page.tsx`

**强制方式**：

- CI 检查目录结构（脚本扫 `api/` `web/src/` 是否符合上述布局）
- 新增不在白名单的根目录 → CI 失败
- import 路径校验（见规约 5 分层架构边界）

---

## 2. 命名规范（A）

**适用范围**：全部

### 2.1 通用文件名

| 类型 | 规则 | 示例 |
|------|------|------|
| Python 文件 | snake_case | `module_service.py` |
| Python 模块目录 | snake_case | `api/services/` |
| TS 文件（组件） | PascalCase | `ModuleCard.tsx` |
| TS 文件（非组件） | kebab-case | `module-service.ts` |
| 文档 | kebab-case | `01-engineering-spec.md` |
| ADR | `ADR-NNN-题目.md` | `ADR-001-shadow-prism.md` |
| 设计文档 | `NN-题目.md` | `04-layer-architecture.md` |

### 2.2 Python 标识符

| 类型 | 规则 | 示例 |
|------|------|------|
| 变量 / 函数 | snake_case | `user_id`、`get_module()` |
| 私有变量 / 函数 | `_` 前缀 | `_internal_helper()` |
| 类 | PascalCase | `ModuleService`、`AppError` |
| 常量 | SCREAMING_SNAKE | `MAX_RETRY_COUNT` |
| 类型别名 | PascalCase | `UserId = int` |
| 枚举值 | SCREAMING_SNAKE | `ErrorCode.MODULE_NOT_FOUND` |

### 2.3 TypeScript 标识符

| 类型 | 规则 | 示例 |
|------|------|------|
| 变量 / 函数 | camelCase | `userId`、`getModule()` |
| 私有 | `_` 前缀 | `_internalHelper()` |
| 组件 / 类 / 类型 | PascalCase | `ModuleCard`、`ModuleDto` |
| 常量 | SCREAMING_SNAKE | `MAX_RETRY_COUNT` |
| 自定义 hook | `use` 前缀 + camelCase | `useModuleList()` |
| 自定义事件 handler | `handle` / `on` 前缀 | `handleSubmit()`、`onSelect()` |

### 2.4 数据库

| 对象 | 规则 | 示例 |
|------|------|------|
| 表名 | snake_case 复数 | `modules`、`activity_logs` |
| 字段名 | snake_case | `created_at`、`user_id` |
| 主键 | `id`（统一） | `id: int` |
| 外键 | `{表单数}_id` | `module_id`、`user_id` |
| 时间字段 | `_at` 后缀 | `created_at`、`updated_at`、`deleted_at` |
| 布尔字段 | `is_` / `has_` 前缀 | `is_archived`、`has_attachment` |
| JSON 字段 | `_json` 后缀（可选，明确类型时） | `metadata_json` |

### 2.5 API 路径

| 元素 | 规则 | 示例 |
|------|------|------|
| 路径 | kebab-case 复数资源 | `/api/v1/modules`、`/api/v1/activity-logs` |
| 资源详情 | `/{资源}/{id}` | `/api/v1/modules/123` |
| 子资源 | `/{资源}/{id}/{子资源}` | `/api/v1/modules/123/dimensions` |
| 动作（非 RESTful） | 动词 + kebab-case | `/api/v1/modules/123/archive` |
| 版本 | `/api/v{N}/` | `/api/v1/`（首版） |

### 2.6 模块编号

- 模块统一用 `M01`-`M20`（呼应 `design/00-architecture/05-module-catalog.md`）
- 设计文档：`02-modules/M{NN}-{slug}/`
- commit scope：`m01`-`m20`（小写）
- 测试文件：`tests/m{NN}_{module_name}_test.py`

**反例**：

```python
# ❌ 命名违反
class moduleService: ...        # 应 PascalCase
def GetModule(): ...            # 应 snake_case
USER_id = 1                     # 应统一 SCREAMING 或 snake，不混用
```

```typescript
// ❌ 命名违反
const user_id = 1;              // 应 camelCase
function get_module() {}        // 应 camelCase
```

```sql
-- ❌ 命名违反
CREATE TABLE Module (id INT, CreatedAt TIMESTAMP);   -- 应 snake_case 复数
```

**强制方式**：

- Python：ruff 启用 `N` 系列规则（pep8-naming）
- TypeScript：eslint 启用 `@typescript-eslint/naming-convention`
- DB：alembic migration review 时人工核
- API：路由定义 review 时核（无自动 lint）

---

## 3. Python 代码风格（A）

**适用范围**：后端

**工具**：**仅用 ruff**（formatter + linter 一体，不引入 black / flake8 / isort）

理由：ruff 包含 ruff format（black 兼容）+ 所有主流 lint 规则，速度快 10-100 倍，配置一份。

### 3.1 ruff 配置（`pyproject.toml`）

```toml
[tool.ruff]
line-length = 100
target-version = "py312"
exclude = ["alembic/versions"]

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort（import 顺序）
    "N",    # pep8-naming（命名）
    "B",    # flake8-bugbear（潜在 bug）
    "UP",   # pyupgrade（用新语法）
    "S",    # flake8-bandit（安全）
    "ASYNC",# flake8-async（async 误用）
    "RUF",  # ruff 专属规则
]
ignore = [
    "S101", # 允许 assert（测试用）
    "E501", # line-length 由 formatter 处理
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S", "N802"]   # 测试可用 assert / 测试函数命名宽松

[tool.ruff.format]
quote-style = "double"            # 强制双引号
indent-style = "space"            # 强制空格缩进
docstring-code-format = true      # docstring 内代码也格式化

[tool.ruff.lint.isort]
known-first-party = ["api"]
section-order = ["future", "standard-library", "third-party", "first-party", "local-folder"]
```

### 3.2 import 顺序

```python
# 1. future imports
from __future__ import annotations

# 2. 标准库
import logging
from datetime import datetime

# 3. 第三方库
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

# 4. 本项目（first-party）
from api.deps import get_db, get_current_user
from api.errors.exceptions import ModuleNotFoundError
from api.schemas.module_schema import ModuleCreate, ModuleResponse
from api.services.module_service import create_module

# 5. local（同目录相对 import，能避免就避免）
```

### 3.3 强制项（精选规则要点）

| 规则 | 要求 | 反例 |
|------|------|------|
| 函数签名 | 强制类型注解（参数+返回） | `def f(x): return x` ❌ |
| 字符串 | 强制双引号 | `'hello'` ❌ |
| f-string | 优先 f-string，禁止 `%` 和 `.format()` | `"hello %s" % name` ❌ |
| Optional | 用 `T \| None` 不用 `Optional[T]` | `Optional[int]` ❌ |
| Union | 用 `T \| U` 不用 `Union[T, U]` | `Union[int, str]` ❌ |
| 异常 | 不裸 `except:`，必须指定异常 | `except: pass` ❌ |
| logger | 用 `logger = logging.getLogger(__name__)`，禁止 print | `print(...)` ❌ |
| typing | 启用 `from __future__ import annotations` | — |
| 行长度 | ≤100 字符（formatter 自动） | — |

### 3.4 docstring 规约

- **公开函数 / 类**：必须有 docstring
- **格式**：Google style
- **私有函数**：可选

```python
def create_module(
    db: Session,
    user_id: int,
    project_id: int,
    payload: ModuleCreate,
) -> Module:
    """Create a new module under the project.

    Args:
        db: Database session.
        user_id: Acting user ID (for activity_log).
        project_id: Target project ID (tenant scope).
        payload: Module creation request.

    Returns:
        The created module.

    Raises:
        ProjectNotFoundError: If project_id doesn't exist or user has no access.
    """
    ...
```

**强制方式**：

- CI 跑 `ruff check .` + `ruff format --check .`
- pre-commit hook：`ruff format` + `ruff check --fix`
- 失败 → PR 阻塞合并

---

## 4. TypeScript 代码风格（A）

**适用范围**：前端

**工具**：eslint + prettier（无 ruff 等价物，组合是行业标准）

### 4.1 eslint 配置（`web/eslint.config.mjs`）

```javascript
import { FlatCompat } from "@eslint/eslintrc";
import tseslint from "typescript-eslint";

const compat = new FlatCompat({ baseDirectory: import.meta.dirname });

export default [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  ...tseslint.configs.recommendedTypeChecked,
  {
    rules: {
      "@typescript-eslint/no-explicit-any": "error",        // 禁止 any
      "@typescript-eslint/no-unused-vars": "error",
      "@typescript-eslint/consistent-type-imports": "error", // import type
      "@typescript-eslint/no-floating-promises": "error",   // 禁止漏 await
      "@typescript-eslint/no-misused-promises": "error",
      "@typescript-eslint/naming-convention": [
        "error",
        { selector: "variable", format: ["camelCase", "PascalCase", "UPPER_CASE"] },
        { selector: "function", format: ["camelCase", "PascalCase"] },
        { selector: "typeLike", format: ["PascalCase"] },
      ],
      "no-console": ["error", { allow: ["warn", "error"] }], // 禁止 console.log
      "react-hooks/exhaustive-deps": "error",
    },
  },
];
```

### 4.2 prettier 配置（`web/.prettierrc.json`）

```json
{
  "semi": true,
  "singleQuote": false,
  "tabWidth": 2,
  "trailingComma": "all",
  "printWidth": 100,
  "arrowParens": "always",
  "endOfLine": "lf"
}
```

### 4.3 import 顺序（eslint-plugin-import）

```typescript
// 1. React / Next 相关
import { useState } from "react";
import Link from "next/link";

// 2. 第三方库
import { z } from "zod";

// 3. 本项目 alias（@/...）
import { ModuleCard } from "@/components/business/ModuleCard";
import { getModules } from "@/services/module-service";

// 4. 相对路径
import { localUtil } from "./utils";

// 5. 类型 import 单独一段
import type { Module } from "@/types/api";
```

### 4.4 强制项

| 规则 | 要求 | 反例 |
|------|------|------|
| any | 禁止显式 any | `let x: any = ...` ❌ |
| 类型 import | 类型用 `import type` | `import { Module } from ...` 当只用类型时 ❌ |
| 漏 await | Promise 必须 await 或显式 void | `fetch(url)` 不 await ❌ |
| console | 禁止 `console.log`（warn/error 可） | — |
| React hooks | 必须遵守 exhaustive-deps | — |
| Server Actions | 文件顶部 `"use server"` | — |

**强制方式**：

- CI：`tsc --noEmit`（0 errors）+ `eslint .` + `prettier --check .`
- pre-commit：`prettier --write` + `eslint --fix`
- 失败 → PR 阻塞合并

---

## 5. 分层架构边界（A）

**适用范围**：全部

**呼应**：`design/00-architecture/04-layer-architecture.md` + 06-design-principles.md 原则 2

### 5.1 后端三层职责对照

| 层 | 必须做 | 禁止做 | 越界示例 |
|------|--------|--------|----------|
| **Router** | 参数校验（Pydantic）/ 调 Depends 拿 user / 调 Service / 返回 ResponseModel | 直查 DB / 业务判断 / 调其他 Router / 写文件 | `db.query(Module).filter(...)` 出现在 router ❌ |
| **Service** | 业务逻辑 / 调 DAO / 调 Queue / 写 activity_log | 直接 SQL / 直接 HTTP / 直接读 env / `from fastapi import` | `requests.get(url)` 出现在 service ❌（应封装到外部 client） |
| **DAO** | SQLAlchemy 查询 / **必须含 tenant 过滤** | 业务判断（`if module.status == "active"`） / 跨表 JOIN（除非有理由并显式标注） | `if not module: raise BizError` 出现在 dao ❌（DAO 返回 None，Service 判断） |

### 5.2 前端分层职责

| 层 | 必须做 | 禁止做 |
|------|--------|--------|
| **Page (`src/app/`)** | 数据获取（fetch / Server Action 调用）/ 渲染 | 调 dao / 写业务规则 |
| **Server Action** | 参数收集（zod schema）/ session 校验 / 调 services 或 FastAPI | 业务逻辑 / 直查 DB |
| **Service (`src/services/`)** | API client（调 FastAPI）/ 类型从 OpenAPI codegen | 直查 DB / 业务判断 |
| **Component** | UI 渲染 / 事件转发 | 直接调 services（应通过 Server Action 或 props 传入） |

### 5.3 跨层调用 lint 规则

**Python（importlinter）**：

```toml
# .importlinter
[importlinter]
root_packages = ["api"]

[[importlinter.contracts]]
name = "Layered architecture"
type = "layers"
layers = [
    "api.routers",      # 顶层
    "api.services",
    "api.dao",
    "api.models",       # 底层
]
# 上层只能 import 下层，禁止反向

[[importlinter.contracts]]
name = "Routers can't import models or dao directly"
type = "forbidden"
source_modules = ["api.routers"]
forbidden_modules = ["api.models", "api.dao"]
# Router 必须经 Service 拿数据
```

**TypeScript（eslint-plugin-boundaries）**：

```javascript
"boundaries/elements": [
  { type: "app", pattern: "src/app/**" },
  { type: "actions", pattern: "src/actions/**" },
  { type: "services", pattern: "src/services/**" },
  { type: "components", pattern: "src/components/**" },
],
"boundaries/rules": [
  { from: "components", disallow: ["actions", "services"] },
  { from: "app", allow: ["actions", "services", "components"] },
]
```

### 5.4 跨层反例对照

```python
# ❌ Router 直查 DB
@router.get("/modules/{id}")
def get(id: int, db: Session = Depends(get_db)):
    return db.query(Module).filter(Module.id == id).first()

# ✅ Router 调 Service
@router.get("/modules/{id}")
def get(id: int, user: User = Depends(get_current_user), svc: ModuleService = Depends()):
    return svc.get(user.id, id)
```

```python
# ❌ DAO 写业务判断
def get_module(db, module_id):
    m = db.query(Module).filter(Module.id == module_id).first()
    if m and m.status == "archived":
        raise BizError("Cannot access archived")  # 业务判断不属于 DAO
    return m

# ✅ DAO 只查，Service 判断
# dao
def get_module(db, module_id, user_id):
    return db.query(Module).filter(
        Module.id == module_id,
        Module.user_id == user_id,  # tenant 过滤
    ).first()

# service
def get_module(self, user_id, module_id):
    m = self.dao.get_module(self.db, module_id, user_id)
    if m and m.status == "archived":
        raise ModuleArchivedError()
    return m
```

**强制方式**：

- Python：`importlinter` 在 CI 跑（违反阻塞合并）
- TypeScript：`eslint-plugin-boundaries` 在 lint 时跑
- 运行时：单元测试覆盖"跨层调用"的反例

---

## 6. Git commit 规范（A）

**适用范围**：全部

**约定**：[Conventional Commits 1.0](https://www.conventionalcommits.org/)

**本项目的务实调整**（保留与现有仓库一致的中文习惯）：
- **type + scope 强制必填**（机器可解析的元数据层，不可省）
- **subject 保留中文为主风格**（延续 prism-0420 仓库现有 commit 历史习惯，单人项目可读性更好）
- 不强制英文动词原型——中文用动词开头即可
- 跟随仓库已有风格（如 `docs(arch): 06-design-principles 定稿`）

### 6.1 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 6.2 type 清单

| type | 含义 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(m01): add module create API` |
| `fix` | bug 修复 | `fix(m05): correct tenant filter in DAO` |
| `docs` | 文档变更 | `docs(adr): add ADR-002 queue choice` |
| `style` | 格式调整（无业务变化） | `style(api): apply ruff format` |
| `refactor` | 重构（无功能变化） | `refactor(m03): extract validation logic` |
| `test` | 测试代码 | `test(m02): add empty state cases` |
| `chore` | 杂项（依赖更新等） | `chore: bump arq to 0.26` |
| `build` | 构建系统 | `build: switch to ruff` |
| `ci` | CI 配置 | `ci: add importlinter check` |
| `perf` | 性能优化 | `perf(m18): add index on module.created_at` |

### 6.3 scope 清单

- 模块：`m01`-`m20`
- 子系统：`api` / `web` / `infra` / `docs` / `design`
- 跨模块：`*`（慎用）

### 6.4 subject 规则

- ≤72 字符
- 末尾不加句号
- **中文为主风格**（延续 prism-0420 仓库现有习惯，如 `fix(reviewer-r3): 处理第三轮 reviewer 4 个问题`）
- 中文时：用动词开头（"新增"/"修复"/"删除"/"重构"），避免名词化
- 英文时：用动词原型（add / fix / remove，不用 added / fixed）、首字母小写
- 中英混用允许但不推荐（可读性差）

### 6.5 breaking change

```
feat(m05)!: change module status enum

BREAKING CHANGE: status field removes "pending", use "draft" instead.
Migration required for existing data.
```

### 6.6 body / footer

- body：解释**为什么**（不是什么 —— 看 diff）
- footer：关联 issue / PR / ADR
  - `Refs: ADR-002`
  - `Closes: #123`
  - `BREAKING CHANGE: ...`

### 6.7 反例

```
# ❌ 无 type（缺机器可解析的元数据）
"add module create API"
"添加 module create API"

# ❌ 无 scope（无法按模块过滤）
"feat: add module create API"
"feat: 新增模块创建接口"

# ❌ type 不在清单
"update(m01): fix bug"

# ❌ subject 名词化（没有动作）
"feat(m05): module changes"
"feat(m05): 模块变更"

# ⚠️ 中英混用（不禁止，但可读性差）
"feat(m05): 添加 module create API"
```

### 6.8 commit 验证

- pre-commit：commitlint 校验格式
- CI：检查 PR 内所有 commit 是否符合规范（不符合 → 阻塞合并）
- merge 策略：squash merge 时 PR title 也必须符合规范

**强制方式**：

- pre-commit hook（commitlint）
- GitHub Action：`amannn/action-semantic-pull-request`
- 不符合 → PR 阻塞合并

---

## 7. 错误处理规约（A）

**适用范围**：全部

**呼应**：06-design-principles.md 原则 5（多人架构）

### 7.1 设计要点

- **唯一 ErrorCode 枚举**：`api/errors/codes.py` 是真相源，前端通过 OpenAPI codegen 同步
- **AppError 类层级**：业务错误必须用 AppError 子类，禁止裸 `raise Exception`
- **三层 wrap 策略**：DAO 抛底层错 → Service wrap 成业务错 → Router wrap 成 HTTP → 前端识别 ErrorCode
- **前后端错误码 1:1 对应**：前端有专门的错误码常量，从后端 OpenAPI 生成

### 7.2 ErrorCode 枚举（`api/errors/codes.py`）

```python
from enum import Enum

class ErrorCode(str, Enum):
    # 通用
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NOT_FOUND = "NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFLICT = "CONFLICT"                          # 乐观锁冲突
    RATE_LIMITED = "RATE_LIMITED"

    # 认证
    UNAUTHENTICATED = "UNAUTHENTICATED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    LOGIN_LOCKED = "LOGIN_LOCKED"

    # 模块（M01）
    MODULE_NOT_FOUND = "MODULE_NOT_FOUND"
    MODULE_ARCHIVED = "MODULE_ARCHIVED"

    # 项目（M02）
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    PROJECT_QUOTA_EXCEEDED = "PROJECT_QUOTA_EXCEEDED"

    # ... 按模块续加
```

**命名规则**：`{模块或域}_{具体错误}`，全部 SCREAMING_SNAKE。

### 7.3 AppError 类层级（`api/errors/exceptions.py`）

```python
from .codes import ErrorCode

class AppError(Exception):
    """所有业务错误的基类。"""
    code: ErrorCode = ErrorCode.INTERNAL_ERROR
    http_status: int = 500
    message: str = "Internal error"

    def __init__(self, message: str | None = None, **details):
        self.message = message or self.message
        self.details = details
        super().__init__(self.message)

class NotFoundError(AppError):
    code = ErrorCode.NOT_FOUND
    http_status = 404
    message = "Resource not found"

class PermissionDeniedError(AppError):
    code = ErrorCode.PERMISSION_DENIED
    http_status = 403
    message = "Permission denied"

class ValidationError(AppError):
    code = ErrorCode.VALIDATION_ERROR
    http_status = 422

class ConflictError(AppError):
    code = ErrorCode.CONFLICT
    http_status = 409
    message = "Concurrent modification detected"

# 模块特定
class ModuleNotFoundError(NotFoundError):
    code = ErrorCode.MODULE_NOT_FOUND
    message = "Module not found"

class ModuleArchivedError(AppError):
    code = ErrorCode.MODULE_ARCHIVED
    http_status = 410
    message = "Module is archived"
```

### 7.4 三层 wrap 策略

```python
# DAO：抛 SQLAlchemy 原生异常 或 返回 None（不 wrap 成业务错）
def get_module(db, module_id, user_id) -> Module | None:
    return db.query(Module).filter(
        Module.id == module_id,
        Module.user_id == user_id,
    ).first()

def update_module(db, module_id, user_id, version, **fields) -> int:
    rows = db.query(Module).filter(
        Module.id == module_id,
        Module.user_id == user_id,
        Module.version == version,
    ).update({**fields, "version": Module.version + 1})
    return rows  # 0 = 冲突或不存在

# Service：wrap 成业务错
def get_module(self, user_id, module_id):
    m = self.dao.get_module(self.db, module_id, user_id)
    if not m:
        raise ModuleNotFoundError(module_id=module_id)
    return m

def update_module(self, user_id, module_id, version, **fields):
    rows = self.dao.update_module(self.db, module_id, user_id, version, **fields)
    if rows == 0:
        # 区分"不存在"和"冲突"
        if not self.dao.get_module(self.db, module_id, user_id):
            raise ModuleNotFoundError()
        raise ConflictError()
    self.activity.log(user_id, "module.update", module_id)
    return rows

# Router：FastAPI 全局 exception handler 把 AppError 转成 HTTP 响应
@app.exception_handler(AppError)
async def app_error_handler(request, exc: AppError):
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "error": {
                "code": exc.code.value,           # ← 前端识别这个
                "message": exc.message,
                "details": exc.details,
            }
        },
    )
```

### 7.5 前端错误处理（与后端 1:1 对应）

```typescript
// web/src/errors/codes.ts （从 OpenAPI codegen，禁止手写偏离）
export enum ErrorCode {
  INTERNAL_ERROR = "INTERNAL_ERROR",
  NOT_FOUND = "NOT_FOUND",
  PERMISSION_DENIED = "PERMISSION_DENIED",
  VALIDATION_ERROR = "VALIDATION_ERROR",
  CONFLICT = "CONFLICT",
  // ... 与后端完全一致
  MODULE_NOT_FOUND = "MODULE_NOT_FOUND",
  MODULE_ARCHIVED = "MODULE_ARCHIVED",
}

// web/src/lib/api-error.ts
export type ApiError = {
  code: ErrorCode;
  message: string;
  details?: Record<string, unknown>;
};

export class ApiCallError extends Error {
  constructor(public payload: ApiError, public httpStatus: number) {
    super(payload.message);
  }
}

// 使用
try {
  await updateModule({ id, version, ...payload });
} catch (e) {
  if (e instanceof ApiCallError) {
    if (e.payload.code === ErrorCode.CONFLICT) {
      toast.error("有人刚改过，请刷新重试");
    } else if (e.payload.code === ErrorCode.MODULE_ARCHIVED) {
      toast.error("模块已归档");
    } else {
      toast.error(e.payload.message);
    }
  }
}
```

### 7.6 强制项

| 规则 | 要求 |
|------|------|
| 业务错误 | 必须 `raise <AppError 子类>`，禁止 `raise Exception` / `raise ValueError` |
| 错误码 | 新错误必须在 `ErrorCode` 枚举注册 |
| 前后端一致 | 前端 `ErrorCode` 必须从 OpenAPI 生成（CI 校验差异为 0） |
| 异常 wrap | DAO 抛低层 / Service wrap 成 AppError / Router 全局 handler |
| 错误响应格式 | 统一 `{"error": {"code", "message", "details"}}` |

### 7.7 反例

```python
# ❌ 裸 raise
raise ValueError("module not found")

# ❌ 错误信息硬编码无 code
raise HTTPException(status_code=404, detail="Module not found")

# ❌ DAO 抛业务错
def get_module(db, id):
    m = db.query(...).first()
    if not m:
        raise ModuleNotFoundError()  # 应在 Service 层

# ❌ Service 直接抛 HTTP
raise HTTPException(status_code=403, ...)  # 应抛 PermissionDeniedError
```

**强制方式**：

- ruff 自定义规则：扫 service / dao 层，发现 `raise HTTPException` / `raise Exception` / `raise ValueError` → 失败
- CI 校验：前端 `ErrorCode` 与后端 OpenAPI 生成结果 diff 为 0
- 失败 → PR 阻塞合并

---

# B 档 强制（PR review checklist 必须勾过）

## 8. PR 流程 + 模板（B）

**适用范围**：全部

**呼应**：`design/00-architecture/06-design-principles.md` 原则 5（多人架构）、本规约第 6 条（commit）

### 8.1 设计要点

- prism-0420 是单人实验项目，但 PR 流程仍走完整流——为了：
  - ① 给 AI 实现的每批代码一道 human gate
  - ② 留下可回顾的"AI 输出历史"（对照 Prism 做数据化分析的基础）
  - ③ 未来扩展到多人时不用改流程
- **合并门**：self-review checklist 勾过 6 项 + CI 绿灯
- **大小上限**：≤ 400 行 diff（超过需在描述说明原因）
- **Merge 策略**：squash merge（唯一允许方式）

### 8.2 PR 标题规范

格式与 commit 规约（第 6 条）一致：`<type>(<scope>): <subject>`

| 判断 | 示例 |
|------|------|
| ✅ | `feat(m01): 新增模块创建 API` |
| ✅ | `fix(m05): 修复 DAO tenant 过滤遗漏 project_id` |
| ✅ | `docs(adr): 新增 ADR-002 queue 选型` |
| ❌ | `update module`（无 type / scope） |
| ❌ | `修 bug`（无 type / scope / 无具体信息） |
| ❌ | `feat: changes`（无 scope） |

squash merge 时 squash commit 的 subject 沿用 PR title（不拼接 PR 内部 commit 列表）。

**强制**：GitHub Action `amannn/action-semantic-pull-request` 校验 PR title，不合规阻塞合并。

### 8.3 PR 描述模板

**文件位置**：`.github/pull_request_template.md`

内容（6 段固定结构）：

1. **背景（为什么做）**—— 关联 ADR / 设计文档 / 需求
2. **改动点（做了什么决定）**—— 不抄 diff，说"决定"
3. **测试**—— 勾选项 + 手动冒烟说明
4. **风险（说不出风险就是没看清）**—— 列 2-3 条可能问题或显式写"无"+理由
5. **关联**—— ADR / 设计文档 / 模块 / Issue
6. **Self-review checklist**—— 6 项合并门

完整模板见 `.github/pull_request_template.md`（首次建仓时从本节 8.7 复制）。

### 8.4 Self-review checklist（6 项合并门）

合并前必须**全部勾过**：

- [ ] **分层未越界**：router 不直查 DB / service 不直接 HTTP / dao 不做业务判断 / 模型无业务方法（对应规约 5）
- [ ] **命名合规**：文件 / 变量 / 表 / API 路径符合规约 2
- [ ] **错误 wrap 规范**：service 层抛 `AppError` 子类 / router 走全局 handler / 无裸 `raise Exception` / `raise ValueError`（对应规约 7）
- [ ] **Tenant 过滤**：新增 DAO 查询必含 `user_id + project_id`；若例外需在代码注释显式标注理由
- [ ] **测试已跑**：新增 / 修改代码有对应测试；`uv run pytest` + `pnpm test` 全绿；贴终端输出片段证明
- [ ] **文档同步**：改 schema → 改 OpenAPI；加 ErrorCode → 改 errors 说明；改架构 → 改 ADR / `design/`

**每一项都对应 AI 最常犯的一类错误**——checklist 是"AI 输出验收单元"的可量化形式，不是装饰。

### 8.5 PR 大小规则

| 规模 | diff 行数 | 处理 |
|------|---------|------|
| Small | ≤ 100 | 默认可合 |
| Medium | 100-400 | 默认可合 |
| Large | 400-800 | PR 描述开头说明原因 + 建议 reviewer 按 commit 顺序读 |
| XL | > 800 | 原则上拆分；不拆需在 PR 描述"为什么不能拆"里写满 |

**拆分建议**（从易到难）：

1. 先拆"格式变更 / 重命名" → 单独 PR（`type=style` / `refactor`）
2. 再按"model/schema → dao → service → router"顺序分层拆
3. 前后端跨仓库：后端 PR 先合 → 前端 OpenAPI codegen → 再提前端 PR

### 8.6 Draft PR vs Ready for review

| 状态 | 含义 | CI | 可合并 |
|------|------|-----|-------|
| Draft | 代码不全 / 测试未过 / 想早获反馈 | 跑 | ❌ |
| Ready for review | checklist 全勾 + CI 绿 + 自觉可合 | 跑 | ✅ |

状态切换：GitHub 界面 "Ready for review" 按钮，或命令行 `gh pr ready`。

### 8.7 PR 模板文件

`.github/pull_request_template.md` 固定内容：

~~~markdown
## 背景（为什么做）

<!-- 关联 ADR / 设计文档 / 需求。例："按 ADR-001 实现 M01 模块骨架。" -->

## 改动点（做了什么决定）

<!-- 按模块/层次分点。不抄 diff，说"做了什么决定"。 -->
- 
- 

## 测试

- [ ] 单元测试（`uv run pytest api/tests/` 全绿）
- [ ] 前端类型检查（`pnpm tsc --noEmit` 0 errors）
- [ ] 前端 lint（`pnpm lint` 0 errors）
- [ ] 本地启动验证（`uv run uvicorn` + `pnpm dev` 能跑）
- [ ] 手动冒烟（说明覆盖路径）：

## 风险（说不出风险就是没看清）

<!-- 列 2-3 条可能出问题的地方，或显式写"无"+理由。 -->
- 

## 关联

- ADR: 
- 设计文档: 
- 模块: M__
- Issue: #

## Self-review checklist（合并前必须全部勾过）

- [ ] 分层未越界（router 不直查 DB / service 不直接 HTTP / dao 不做业务判断）
- [ ] 命名合规（规约 2：文件/变量/表/API 路径）
- [ ] 错误 wrap 规范（service 抛 AppError 子类 / 无裸 raise）
- [ ] Tenant 过滤（新增 DAO 查询必含 user_id + project_id）
- [ ] 测试已跑（pytest / vitest 全绿，贴输出片段）
- [ ] 文档同步（改 schema/errors/架构 → 改 OpenAPI/errors 说明/ADR）
~~~

### 8.8 Merge 策略

- **squash merge**（GitHub repo 设置里**只开** squash merge，关 merge commit 和 rebase merge）
- 原因：PR 内部 commit 在迭代中可能凌乱（`wip` / `fix typo`），squash 后 main 只保留"一个 PR 一个干净 commit"，配合第 6 条 commit 规约保证 main 历史可读
- squash commit subject = PR title（GitHub 自动）；body 必要时手改为 PR description 精简版

### 8.9 强制方式

| 手段 | 覆盖 | 失败后果 |
|------|------|---------|
| `.github/pull_request_template.md` | 所有新 PR 自动加载 | 软提示（作者自觉填） |
| GitHub Action `action-semantic-pull-request` | PR title 格式 | PR 不能合并 |
| Branch protection（main）| 必过 CI + PR + 线性历史 | push / 合并阻塞 |
| PR 描述 checklist 勾选 | self-review 6 项 | 作者自检 + 未来可加 Action 扫描 |
| GitHub repo 设置"只允许 squash merge" | merge 方式 | 其他方式按钮不可用 |

### 8.10 反例

```
❌ PR 描述空白
标题：fix bug
描述：（空）

❌ 一句话描述
标题：feat(m01): 新增模块
描述："实现 M01"

❌ 抄 diff
描述：
- 新增 api/models/module.py
- 新增 api/dao/module_dao.py
（只说"做了什么文件"，没说"做了什么决定"、风险在哪）

❌ checklist 全勾但测试没跑（最危险）
—— 解决：勾"测试已跑"项时必须贴 pytest / vitest 输出片段
```

---

## 9. Git 分支策略（B）
## 10. 依赖管理（B）
## 11. 文档维护规约（B）
## 12. 类型安全门槛（B）

> B-09 起待后续填充

---

# C 档 参考（写到文档但不机械强制）

> 待第 2 次填充

## 13. Code review 清单（C）
## 14. 版本号规则（C）
## 15. 代码注释规范（C）

---

# 强制清单总览

> 待第 3 次填充（哪些走 lint、哪些走 CI、哪些走 PR review、哪些走人工约定）

---

# 完成度判定

- [x] A 档 7 条全部填写
- [ ] B 档 5 条全部填写
- [ ] C 档 3 条全部填写
- [ ] 强制清单总览
- [ ] 与 ADR-001 / 06-design-principles.md 引用关系明确
- [ ] AI 完整性质疑通过
- [ ] 对抗式 Reviewer 三轮通过

---

# 关联参考

- **架构骨架**：`design/00-architecture/04-layer-architecture.md`、`05-module-catalog.md`
- **设计原则**：`design/00-architecture/06-design-principles.md`（原则 2 / 原则 5）
- **核心 ADR**：`design/adr/ADR-001-shadow-prism.md`
- **方法论**：`/root/cy/ai-quality-engineering/02-技术/架构设计/设计前置执行方法论-人机协作与对抗式Reviewer.md`
- **Prism 对照**：`/root/cy/prism/CLAUDE.md`（Prism 现有规约散落点，对照报告时引用）
