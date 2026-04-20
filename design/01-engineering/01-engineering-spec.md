# 01 - 工程规约（engineering-spec）

**状态**：draft（A 档已填，B/C 档待填）
**定稿日期**：—
**档位**：B
**关联**：`design/00-architecture/04-layer-architecture.md`、`design/00-architecture/06-design-principles.md`、`design/adr/ADR-001-shadow-prism.md`
**宏观讲解**（为什么这么定）：知识库 `/root/cy/ai-quality-engineering/02-技术/架构设计/工程规约详解-AI时代工程素养基石.md`

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
│   ├── src/lib/                   # 工具函数 + 类型（kebab-case 文件）
│   ├── src/contexts/              # React Context
│   ├── src/errors/                # 错误码（从后端 OpenAPI 同步生成）
│   ├── src/types/api.ts           # OpenAPI codegen 输出（不手写）
│   ├── src/**/*.test.ts(x)        # vitest 测试文件（与源文件同目录，.test 后缀）
│   ├── package.json
│   └── pnpm-lock.yaml             # 依赖锁（必须提交，见规约 10）
│
├── docs/                          # 项目文档（所有 MD 含 frontmatter，见规约 11.3）
│   ├── adr/                       # 架构决策（ADR-NNN-题目.md，accepted 后不可改）
│   ├── architecture/              # 技术架构（arc42 格式）
│   ├── product/                   # PRD
│   └── skills/                    # 开发触发型 skills
│
├── design/                        # 设计前置文档（所有 MD 含 frontmatter，见规约 11.3）
│   ├── 00-architecture/           # 档位 A：架构骨架
│   ├── 01-engineering/            # 档位 B：工程规约
│   ├── 02-modules/                # 档位 C：模块详细设计（M01-M20）
│   ├── 99-comparison/             # 与 Prism 对照报告
│   └── adr/                       # 设计阶段 ADR
│
├── .github/                       # GitHub 配置
│   ├── workflows/                 # CI 工作流（见规约 3/4/10/12 的 CI 强制项）
│   └── pull_request_template.md   # PR 模板（见规约 8.7）
│
├── scripts/                       # 工具脚本（部署 / 数据迁移 / 验证）
├── tests/                         # 跨服务集成测试（前后端联调）
│
├── pyproject.toml                 # Python 项目配置（[project]/[tool.ruff]/[tool.mypy]，见规约 3/10/12）
├── uv.lock                        # Python 依赖锁（必须提交，见规约 10）
├── docker-compose.yml             # 本地开发环境（PostgreSQL / Redis）
├── .gitignore
└── README.md                      # 项目入口
```

**每目录的"禁止做什么"**：

| 目录 | 禁止 |
|------|------|
| `api/main.py` | 写业务逻辑、写 DB 查询 |
| `api/routers/` | 直查 DB、写文件、跨 router 调用 |
| `api/services/` | 直接 SQL、直接 HTTP（必须经 dao 或 queue）、直接读 env |
| `api/dao/` | 业务判断（"if 状态 == X then..."）、跨表 JOIN（除非显式标注理由） |
| `api/models/` | 业务方法（如 `def can_edit()`）—— 业务逻辑放 service |
| `api/schemas/` | 业务方法、SQLAlchemy import、从其他层反向 import |
| `api/queue/` | 业务逻辑（task 体应调 service）、直查 DB（经 dao）、跨 task 直接调用 |
| `api/errors/` | 业务逻辑、SQLAlchemy / FastAPI import（纯错误定义层） |
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
| 外键 | `{表单词}_id` | `module_id`、`user_id` |
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

**工具**：
- 格式化 + lint：**仅用 ruff**（formatter + linter 一体，不引入 black / flake8 / isort）
- 类型检查：**mypy strict**（详见规约 12）—— 本节只覆盖格式/lint；类型注解的静态检查见规约 12.2

理由：ruff 包含 ruff format（black 兼容）+ 所有主流 lint 规则，速度快 10-100 倍，配置一份。

### 3.1 ruff 配置（`pyproject.toml`）

> **注**：本节只展示 `[tool.ruff]` 节。完整 `pyproject.toml`（含 `[project]` / `[dependency-groups]` / `[tool.mypy]`）见规约 10.2 + 规约 12.2。

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
    "ANN",  # flake8-annotations（类型注解强制，支撑规约 12 mypy strict）
    "RUF",  # ruff 专属规则
]
ignore = [
    "S101",    # 允许 assert（测试用）
    "E501",    # line-length 由 formatter 处理
    "ANN101",  # self 不需要类型注解
    "ANN102",  # cls 不需要类型注解
    "ANN401",  # 允许 Any（逃生口由规约 12 的 # type: ignore 机制管理，不二次拦截）
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S", "N802", "ANN"]   # 测试可用 assert / 测试函数命名 + 注解宽松

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
import importPlugin from "eslint-plugin-import";

const compat = new FlatCompat({ baseDirectory: import.meta.dirname });

export default [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  ...tseslint.configs.recommendedTypeChecked,
  {
    plugins: {
      import: importPlugin,
    },
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
        { selector: "enumMember", format: ["UPPER_CASE"] },   // 枚举值 SCREAMING_SNAKE
      ],
      "no-console": ["error", { allow: ["warn", "error"] }], // 禁止 console.log
      "react-hooks/exhaustive-deps": "error",
      "import/order": ["error", {                             // 4.3 import 顺序强制
        "groups": ["builtin", "external", "internal", ["parent", "sibling"], "type"],
        "newlines-between": "always",
        "alphabetize": { "order": "asc", "caseInsensitive": true },
      }],
      "import/no-duplicates": "error",
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

[[importlinter.contracts]]
name = "Schemas are independent data models"
type = "forbidden"
source_modules = ["api.schemas"]
forbidden_modules = ["api.routers", "api.services", "api.dao", "api.models", "api.queue"]
# schemas 只被 import，不 import 其他层（纯 Pydantic 数据模型层）

[[importlinter.contracts]]
name = "Queue is only invoked from services"
type = "forbidden"
source_modules = ["api.routers", "api.dao", "api.models"]
forbidden_modules = ["api.queue"]
# 除 services 外任何层都不能直调 Queue（保证事务边界 + activity_log 责任归属）

[[importlinter.contracts]]
name = "Errors layer is framework-independent"
type = "forbidden"
source_modules = ["api.errors"]
forbidden_modules = ["api.routers", "api.services", "api.dao", "api.models", "api.queue", "fastapi", "sqlalchemy"]
# errors/ 是纯错误定义层，不 import 任何业务层和框架
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
| `hotfix` | 紧急修复（从 main 拉 `hotfix/` 分支，走加速流程，见规约 9.6）| `hotfix(m02): 紧急修复 tenant 过滤泄漏` |
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

**SQLAlchemy 原生异常的 wrap（IntegrityError 场景）**：

唯一约束冲突、外键约束、NOT NULL 违反等是高频场景，Service 层必须捕获并 wrap：

```python
from sqlalchemy.exc import IntegrityError

def create_module(self, user_id: int, project_id: int, payload: ModuleCreate) -> Module:
    try:
        m = self.dao.create_module(self.db, user_id, project_id, payload)
        self.db.commit()
    except IntegrityError as e:
        self.db.rollback()
        # 通过约束名或 SQLSTATE 精确分辨冲突类型
        msg = str(e.orig)
        if "uq_modules_project_id_name" in msg:     # 业务唯一约束：项目内模块名不重复
            raise ModuleNameDuplicateError(
                project_id=project_id, name=payload.name
            ) from e
        if "fk_modules_project_id" in msg:          # 外键约束：project 不存在
            raise ProjectNotFoundError(project_id=project_id) from e
        # 未识别的完整性错误 → 通用 ConflictError（不要裸 raise）
        raise ConflictError() from e
    self.activity.log(user_id, "module.create", m.id)
    return m
```

**纪律**：
- DAO 抛 `IntegrityError` 不 wrap（保留原始栈）
- Service 捕获 + 根据约束名分辨 + 抛具体 AppError 子类
- 未识别的 IntegrityError 一律抛 `ConflictError`，禁止裸传到 Router
- 每个业务唯一约束对应一个 ErrorCode（如 `MODULE_NAME_DUPLICATE`），登记在 `api/errors/codes.py`

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
- **合并门**：self-review checklist 勾过 7 项 + CI 绿灯
- **大小上限**：目标 ≤ 400 行 diff；具体分级处理见 8.5（Large / XL 需额外说明）
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
6. **Self-review checklist**—— 7 项合并门

完整模板见 `.github/pull_request_template.md`（首次建仓时从本节 8.7 复制）。

### 8.4 Self-review checklist（7 项合并门）

合并前必须**全部勾过**：

- [ ] **分层未越界**：router 不直查 DB / service 不直接 HTTP / dao 不做业务判断 / 模型无业务方法（对应规约 5）
- [ ] **命名合规**：文件 / 变量 / 表 / API 路径符合规约 2
- [ ] **错误 wrap 规范**：service 层抛 `AppError` 子类 / router 走全局 handler / 无裸 `raise Exception` / `raise ValueError`（对应规约 7）
- [ ] **Tenant 过滤**：新增 DAO 查询必含 `user_id + project_id`；若例外需在代码注释显式标注理由
- [ ] **测试已跑**：新增 / 修改代码有对应测试；`uv run pytest` + `pnpm test` 全绿；贴终端输出片段证明
- [ ] **文档同步**：改 schema → 改 OpenAPI；加 ErrorCode → 改 errors 说明；改架构 → 改 ADR / `design/`
- [ ] **类型检查通过**：`uv run mypy api/` + `pnpm tsc --noEmit` 0 errors（对应规约 12）

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

- [ ] 后端单元测试（`uv run pytest api/tests/` 全绿）
- [ ] 前端单元测试（`pnpm test` 全绿）
- [ ] 后端类型检查（`uv run mypy api/` 0 errors）
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
- [ ] 类型检查通过（`uv run mypy api/` + `pnpm tsc --noEmit` 0 errors）
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
| PR 描述 checklist 勾选 | self-review 7 项 | 作者自检 + 未来可加 Action 扫描 |
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

**适用范围**：全部

**呼应**：规约 6（commit）、规约 8（PR 流程）

### 9.1 设计要点

- 分支模型：**GitHub Flow**（main 唯一长命分支 + feature branch 短命）
- 不用 git-flow：prism-0420 无版本发布周期（不是 SaaS 产品的 rolling release / 也不是软件包的 semver release）
- main 受保护：禁直推 + PR 必需 + CI 必过 + self-review checklist（规约 8）
- 分支生命周期短：AI 实现单模块应在 3-5 天内合回 main

### 9.2 分支模型示意

```
main     o────o────o────o────o────o────o──── ... （唯一长命，只接受 squash merge）
          \    \         \         \
           o────o         o────o    o────o
           feat/m01       fix/m05   docs/adr-002
           （短命，合并即删）
```

**禁止的反模式**：
- ❌ develop / release / staging 等中间分支
- ❌ 个人长命分支（`feat/my-experiments`）
- ❌ 按环境分支（`prod` / `dev`——环境用部署配置区分，不用分支）

### 9.3 分支命名

格式：`<type>/<scope>-<slug>` 或 `<type>/<slug>`

| 前缀 | 用途 | 示例 |
|------|-----|------|
| `feat/` | 新功能 | `feat/m01-create-module` |
| `fix/` | bug 修复 | `fix/m05-tenant-filter` |
| `docs/` | 文档 | `docs/adr-002-queue-choice` |
| `refactor/` | 重构 | `refactor/m03-extract-validation` |
| `chore/` | 杂项（依赖升级等） | `chore/bump-arq-0.26` |
| `test/` | 测试代码 | `test/m02-empty-state-cases` |
| `hotfix/` | 紧急修复 | `hotfix/m02-tenant-leak` |

**规则**：

- type 与 commit 规约（第 6 条）一致
- scope 可选；用时必须对应 commit scope（`m01`-`m20` / `api` / `web` / `infra` / `docs` / `design`）
- slug：kebab-case，2-5 词，说明"做什么决定"
- 总长度 ≤ 50 字符

**反例**：

```
❌ my-feature          无 type
❌ test123             无意义
❌ fix                 无 slug
❌ feat/M01            scope 大写（应 m01）
❌ feat/m01_create     下划线（应 kebab-case）
❌ feat/m01-and-m05    一分支多模块（违反"一分支一模块"）
```

### 9.4 分支生命周期

标准流程（6 步）：

1. **拉出**：从最新 main `git checkout -b feat/m01-create-module main`
2. **推远**：`git push -u origin feat/m01-create-module`（第一次 push 时加 `-u` 追踪）
3. **开 PR**：可先 Draft（代码未完整）
4. **迭代**：commit + push，CI 跑，Draft 中持续改
5. **合并**：checklist 7 项全勾 + CI 绿 + `Ready for review` → squash merge
6. **清理**：GitHub 开启 `auto-delete head branches`，合并后自动删远端分支；本地 `git branch -d feat/m01-create-module`

**AI 实现节奏参考**：单模块从拉分支到合并 3-5 天收口。

### 9.5 main 分支保护规则

GitHub 仓库 Settings → Branches → Add rule 的强制项：

| 规则 | 启用 | 原因 |
|------|------|------|
| Require a pull request before merging | ✅ | 禁止直推，强制 PR（规约 8） |
| Require status checks to pass before merging | ✅ | CI 必绿（ruff / mypy / eslint / tsc / 分层 lint） |
| Require branches to be up to date before merging | ✅ | 合并前必须 rebase 到最新 main（减少合并后 CI 红） |
| Require conversation resolution before merging | ✅ | PR review 评论必须 resolve |
| Require linear history | ✅ | 配合 squash merge，main 无 merge commit |
| Do not allow bypassing the above settings | ✅ | 管理员也不例外（单人项目自律关键） |
| Require signed commits | ❌ | 可选，单人项目先不强制 |
| Required approving reviewers | **0** | 单人项目用 self-review checklist（规约 8）替代；未来扩多人改为 1 |

**关键差异（与标准 GitHub Flow 的区别）**：
- Required approving reviewers = 0 是**刻意选择**：单人项目靠 checklist，不是靠人 review
- 未来扩多人时改 1 即可，流程不变

### 9.6 hotfix 流程

prism-0420 **无 release 分支**，hotfix 走 feature 流程：

1. 从 main 拉 `hotfix/xxx`（不从其他分支拉）
2. 修 + 测 + PR（PR title 必须标 `hotfix` type，不用 `fix`）
3. PR description 开头写"紧急"说明（原因、受影响范围、回滚方案）
4. **checklist 7 项仍全勾 + CI 仍必绿**（紧急不等于绕过质量门）
5. squash merge

**禁止**：
- ❌ 紧急修 → 跳 CI 直推 main（branch protection 会拦）
- ❌ 紧急修 → 跳过 checklist（紧急恰恰是最容易出错的时刻）

### 9.7 长命分支禁令

| 存活时长 | 处理 |
|---------|------|
| ≤ 1 周 | 默认正常 |
| 1-2 周 | PR 描述说明进度 |
| 2-4 周 | PR 描述"为什么长命"必填 + 拆分可行性评估 |
| > 4 周 | 应拆分或废弃重建（远离 main 的分支易积累合并冲突） |

**AI 实现场景观察指标**：
- 单模块分支存活 > 2 周 → AI 卡在某问题 / 设计拆得不够细 / 人工 review 跟不上
- 这个时长是"AI 开发效率"的**可量化信号**

### 9.8 禁止模式

```
❌ 直推 main（branch protection 会拦，但禁止尝试）
git push origin main                    # 在 feature branch 上

❌ force push 到 main
git push --force origin main

❌ 一分支多模块
feat/m01-and-m05-rewrite

❌ 在 feature branch 上直接 merge main 回来（制造 merge commit）
git merge main                          # 应该 rebase：git rebase main

❌ 长期 stash 工作（不可见、易丢）
git stash; git stash; git stash         # 应该 WIP commit 推远程

❌ 分支命名无 type
my-cool-feature
```

### 9.9 强制方式

| 手段 | 覆盖 | 失败后果 |
|------|------|---------|
| GitHub branch protection on `main` | 直推 / 非 PR / CI 未过 | push / 合并阻塞 |
| 分支命名 Action（可选，如 `deepakputhraya/action-branch-name`）| 命名格式校验 | PR 阻塞 |
| GitHub repo 设置 "Automatically delete head branches" | 合并后远端分支 | 自动删除，无冗余 |
| `git config --local pull.rebase true` | pull 默认 rebase | 减少 merge commit |
| PR template 提示长命分支 | 人工自律 | 软提示（未来可加 Action 扫描） |

### 9.10 AI 实现时的分支建议

AI 开单个模块的典型流程：

```
# 1. 从最新 main 开分支
git checkout main && git pull
git checkout -b feat/m01-create-module

# 2. AI 按目录顺序生成（规约 1 的 10 步）
#    每 2-3 个文件一个 commit（见规约 6）

# 3. 每次 commit 后 push 保持远程同步
git push

# 4. 开 Draft PR，持续看 CI 反馈

# 5. 模块完成 → checklist 7 项勾过 → Ready for review → squash merge
```

**关键纪律**：
- 一个 PR 不跨模块（跨模块 = 对照数据混乱）
- 分支名 = 模块名 = commit scope，三轴对齐

---

## 10. 依赖管理（B）

**适用范围**：全部

**呼应**：规约 3（Python 风格 / ruff 选型）、规约 8（PR 审批清单）

### 10.1 设计要点

| 维度 | 选型 | 理由 |
|------|------|------|
| Python 包管理 | **uv** + `pyproject.toml` + `uv.lock` | Rust 写，比 pip 快 10-100×；与 ruff 同源（astral-sh）；PEP 621 标准；内建 Python 版本管理（免 pyenv） |
| TS 包管理 | **pnpm** + `package.json` + `pnpm-lock.yaml` | 严格依赖隔离（禁止幽灵依赖，防 AI 用未显式声明的 transitive dep）；共享 store 省磁盘 5-10×；比 npm 快 2-3× |
| Lock 文件 | **必须提交** | 可复现性基础 |
| 依赖扫描 | CI 强制 | 漏洞不等人工发现 |

### 10.2 Python 依赖管理（uv）

**配置**（`pyproject.toml`）：

```toml
[project]
name = "prism-0420-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "sqlalchemy>=2.0",
    "alembic>=1.13",
    "pydantic>=2.7",
    "pydantic-settings>=2.4",
    "arq>=0.26",
    "psycopg[binary]>=3.2",
]

[dependency-groups]
dev = [
    "ruff>=0.4",
    "mypy>=1.11",
    "pydantic[mypy]>=2.7",       # 支撑 mypy 的 pydantic.mypy 插件（见规约 12.2）
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",  # pytest 下的 TestClient
]

[tool.uv]
package = true
```

**常用命令**：

| 操作 | 命令 |
|------|------|
| 安装环境 | `uv sync` |
| 加依赖 | `uv add fastapi` |
| 加 dev 依赖 | `uv add --group dev pytest` |
| 升级单个包 | `uv lock --upgrade-package fastapi` |
| 升级所有 | `uv lock --upgrade` |
| 运行命令 | `uv run pytest` / `uv run ruff check .` |
| 安装 Python | `uv python install 3.12` |
| 生成 requirements | `uv export --no-hashes > requirements.txt`（CI Docker 场景） |

**禁止**：
- ❌ `pip install xxx`（绕开 uv，lock 失效）
- ❌ 直接改 `uv.lock` 手工编辑
- ❌ 提交 `requirements.txt` 作为真相源（应从 pyproject.toml 生成）

### 10.3 TypeScript 依赖管理（pnpm）

**配置**（`web/package.json`）：

```json
{
  "name": "prism-0420-web",
  "private": true,
  "packageManager": "pnpm@9.0.0",
  "engines": {
    "node": ">=20.0.0",
    "pnpm": ">=9.0.0"
  },
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "eslint .",
    "typecheck": "tsc --noEmit",
    "test": "vitest"
  },
  "dependencies": { },
  "devDependencies": { }
}
```

**常用命令**：

| 操作 | 命令 |
|------|------|
| 安装 | `pnpm install` |
| CI 严格安装 | `pnpm install --frozen-lockfile` |
| 加依赖 | `pnpm add next` |
| 加 dev 依赖 | `pnpm add -D vitest` |
| 升级 | `pnpm update` |
| 升级单个 | `pnpm update next` |
| 运行脚本 | `pnpm run dev` / `pnpm dev` |
| 审计 | `pnpm audit --audit-level high` |

**严格依赖隔离**（pnpm 核心价值）：

```
package.json 只声明了 next
→ 代码 import "react" 时：
  - npm：能跑（react 是 next 的 transitive dep，node_modules 里有）
  - pnpm：报错 Module not found（未显式声明）
```

这是 AI 代码质量的关键护栏：AI 常写"没装但能用"的 import，pnpm 会在**开发期**就暴露问题，而不是某天依赖树变了才崩。

**禁止**：
- ❌ `npm install` / `yarn add`（生成不兼容的 lock）
- ❌ 混用多个包管理器（`package-lock.json` + `pnpm-lock.yaml` 并存）
- ❌ `pnpm i --no-frozen-lockfile` 在 CI（会默默修改 lock）

### 10.4 新增依赖审批清单

**每次 `uv add` / `pnpm add` 前**，在 PR 描述里勾过以下 5 项（写进 PR template 的"改动点"段附注）：

- [ ] **维护状态**：GitHub 最近 6 个月有 commit / 不是 archived / 不是 unmaintained
- [ ] **License 合规**：MIT / Apache-2.0 / BSD / ISC 直接 OK；GPL / AGPL / 商用协议需先起 ADR 评估
- [ ] **安装量**：PyPI `downloads/month > 10k`（边缘 1k-10k 需说明）；npm `weekly downloads > 50k`（边缘 5k-50k 需说明）
- [ ] **替代品评估**：已有依赖能做吗？30 行手写能做吗？—— 能则不装
- [ ] **必要性说明**：一句话——"为什么这个依赖值得带来这些维护债"

**触发场景**：
- `uv add xxx` 或 `pnpm add xxx` 直接依赖
- 升级 major 版本（等同新增风险）
- devDependencies 也要走（测试框架切换影响整个项目）

### 10.5 版本约束策略

**Python（`pyproject.toml`）**：

```toml
dependencies = [
    "fastapi>=0.115",      # 主流库用下限 + 主版本号自动隐含
    "sqlalchemy>=2.0,<3",  # 明确主版本边界（防 major 升级意外）
    "arq>=0.26,<0.27",     # 0.x 包的 minor 视同 major（保守）
]
```

规则：
- 1.x 及以上库：`>=X.Y`（允许 minor + patch 升）
- 0.x 库：`>=X.Y,<X.(Y+1)`（每个 minor 视同 major，保守锁）
- `uv.lock` 锁死所有**间接依赖**具体版本

**TypeScript（`package.json`）**：

```json
{
  "dependencies": {
    "next": "^16.2",            // 允许 patch + minor
    "react": "19.2.4",          // 精确锁（框架级，不随便升）
    "zod": "^4.3"               // 主流库允许 minor
  }
}
```

规则：
- 框架层（next / react / typescript）：精确或 minor 锁
- 工具层（zod / lodash）：允许 minor
- `pnpm-lock.yaml` 锁死间接依赖

### 10.6 升级策略

| 变更类型 | 频率 | 触发 | 处理 |
|---------|------|------|------|
| **安全补丁** | 立即 | Dependabot / audit 报高危 | 自动 PR（dependabot），24h 内合并 |
| **Patch 升级** | 月度 | 手动 | `uv lock --upgrade` / `pnpm update` |
| **Minor 升级** | 季度 | 手动 | 读 changelog → 升 → 跑全量测试 |
| **Major 升级** | 按需 | 需要新 feature / 停维护 | 起 ADR 评估 breaking change → 分离 PR |

**关键纪律**：
- 绝不"借着加新功能顺手升 major 依赖"——升级必须独立 PR
- Major 升级 PR 描述必须含：changelog 摘要 / breaking change 清单 / 迁移方案

### 10.7 依赖扫描

**CI 强制项**：

| 扫描 | 命令 | 阻塞级别 |
|------|------|---------|
| Lock 一致性（Python） | `uv lock --check` | PR 阻塞 |
| Lock 一致性（TS） | `pnpm install --frozen-lockfile` | PR 阻塞 |
| 漏洞扫描（Python） | `uvx pip-audit` | high/critical 阻塞 |
| 漏洞扫描（TS） | `pnpm audit --audit-level high` | high/critical 阻塞 |
| GitHub Dependency Review | Action | PR 新增依赖含漏洞阻塞 |
| Dependabot alerts | 自动开 PR | 24h 内合并 |

**建议开启**：
- GitHub repo Settings → Security → Dependabot alerts + security updates
- GitHub repo Settings → Security → Dependency graph

### 10.8 禁止模式

```
❌ 全局安装项目依赖
pip install fastapi                 # 应 uv add
npm install -g next                 # 不需要

❌ 绕开包管理器
pip install xxx                     # 应 uv add
yarn add xxx                        # 应 pnpm add

❌ 不提交 lock
.gitignore 里写 uv.lock             # 严重违规
.gitignore 里写 pnpm-lock.yaml      # 严重违规

❌ 手改 lock 文件
vim uv.lock                         # 破坏确定性

❌ git 依赖
"some-pkg": "git+https://..."       # 除非 ADR 明确记录

❌ 混用包管理器
package-lock.json + pnpm-lock.yaml 并存

❌ CI 用非严格模式
pnpm install                        # 在 CI 应 --frozen-lockfile
```

### 10.9 强制方式

| 手段 | 覆盖 | 失败后果 |
|------|------|---------|
| CI: `uv lock --check` | Python lock 与 pyproject.toml 一致 | PR 阻塞 |
| CI: `pnpm install --frozen-lockfile` | TS lock 与 package.json 一致 | PR 阻塞 |
| CI: `uvx pip-audit` / `pnpm audit` | 已知漏洞 | high/critical 阻塞 |
| GitHub Dependency Review Action | PR 新增依赖风险评估 | 高危阻塞 |
| `.gitignore` 不得含 `uv.lock` / `pnpm-lock.yaml` | 强制提交 | 人工 review |
| `engines` + `packageManager` 字段 | Node/pnpm 版本锁定 | 用错工具会报错 |
| PR 描述"新增依赖清单" | 5 项审批勾选 | 软强制（review 时核） |
| Dependabot | 自动 PR 升级 | 手动决定合/不合 |

### 10.10 AI 实现时的依赖纪律

**AI 最常的错误模式**：
- "为了这个功能，我需要装 `some-helper-lib`"—— 90% 情况不需要
- 无 License 审查 —— AI 不检查也不会主动提醒
- 装完就用，不问替代方案

**规约执行时的强制点**：
1. AI 建议装包 → 人工走审批清单 5 项
2. 每项打钩 / 叉 / 注明理由，留在 PR 描述
3. 勾不过 → 不装
4. 装完 PR → CI 跑漏洞扫描

### 10.11 反例

```python
# ❌ 代码里 import 一个未在 pyproject.toml 声明的包
import requests  # 但 pyproject.toml 没 requests（借用 transitive dep）
# → 应先 uv add requests 再用
```

```typescript
// ❌ import 一个 transitive 依赖
import lodash from "lodash";  // package.json 没 lodash
// pnpm 会直接报错（幽灵依赖防护生效）
// → 应先 pnpm add lodash
```

---

## 11. 文档维护规约（B）

**适用范围**：全部

**呼应**：规约 1（目录结构 `docs/` 和 `design/`）、规约 6（commit type=docs）、规约 8（PR checklist 文档同步项）

### 11.1 设计要点

- **单一真相源**：同一事实只在一处写（schema 看代码、决策看 ADR、契约看 OpenAPI）
- **文档生命周期**：frontmatter 显式标注 `status`，不允许"长期 draft"
- **ADR 不变性**：accepted 后禁止原地修改，只能起新 ADR 标记 `Supersedes`
- **代码-文档配对**：改代码必须同步改文档（否则 PR 阻塞）
- **文档是代码的一部分**：进同一 PR、走同一 CI、同一份 review

### 11.2 文档分层与职责对照

| 目录 / 文件 | 内容 | 真相源性质 | 更新频率 |
|------------|-----|----------|---------|
| `design/00-architecture/` | 架构骨架（档位 A） | 设计前置真相源 | B/C 档迭代中可改；accepted 后走 ADR |
| `design/01-engineering/` | 工程规约（本档） | 设计前置真相源 | 迭代期可改 |
| `design/02-modules/M{NN}/` | 模块详细设计（档位 C） | 设计前置真相源 | 实现前冻结 |
| `design/adr/` | 设计阶段 ADR | 决策真相源 | **accepted 后不可改，只能新 ADR supersede** |
| `docs/adr/` | 实现阶段 ADR | 决策真相源 | 同上 |
| `docs/architecture/` | 运行时架构（arc42 格式） | 代码与设计的交叉真相 | 架构改动时同步 |
| `docs/product/` | PRD | 产品需求真相源 | 需求变更时改 |
| `docs/skills/` | 开发触发型 skills | AI 协作行为（非必需） | 按需加 |
| `CLAUDE.md` | 项目协作指南 | AI 协作真相源 | 协作方式变化时改 |
| `README.md` | 项目入口 | 外部访客第一印象 | 大版本里程碑时改 |
| `api/alembic/versions/` | 数据库迁移 | schema 历史真相源 | 每次 schema 变更时新增 |
| OpenAPI schema | API 契约 | 前后端契约真相源 | FastAPI 自动生成，禁手写 |

**禁止交叉的真相源**：

| 事实 | 真相源 | 禁止当真相源 |
|------|-------|-------------|
| 字段类型 | `api/models/*.py` | schemas / docs / 注释 |
| API 行为 | OpenAPI（自动生成） | README / 设计文档 |
| 架构决策 | ADR | 散落的代码注释 / CLAUDE.md |
| 模块列表 | `design/00-architecture/05-module-catalog.md` | PRD / README |

### 11.3 文档生命周期（frontmatter 规范）

所有 `design/` 和 `docs/` 下的 Markdown 必须有 frontmatter：

```yaml
---
title: 04-layer-architecture
status: accepted      # draft / accepted / superseded / deprecated
owner: CY
created: 2026-04-15
accepted: 2026-04-18
supersedes: []        # 若此文档替代旧 ADR，填旧 ADR 编号
superseded_by: null   # 若此文档被新 ADR 替代，填新编号
---
```

**状态流转**：

```
draft ──accepted──> accepted ──superseded──> superseded
                         └─deprecated──> deprecated（不再维护）
```

| 状态 | 含义 | 可改性 |
|------|------|-------|
| `draft` | 讨论中 | 自由改 |
| `accepted` | 已定稿 | ADR 不可改；设计文档走迭代需备注 |
| `superseded` | 被新版替代 | 不改（历史存根） |
| `deprecated` | 弃用但保留 | 不改（历史存根） |

**长期 draft 禁令**：任何文档 `status=draft` 超过 2 周 → doc-rot 扫描报警 → 要么推进到 accepted，要么合入其他文档，要么显式 deprecated。

### 11.4 代码-文档配对更新规则

**改动类型 → 必须同步的文档**：

| 改了什么 | 必须同步改什么 |
|---------|--------------|
| 新增/改 SQLAlchemy model | alembic 迁移 + schemas Pydantic + OpenAPI 重新生成 + 前端 `web/src/types/api.ts` 重 codegen |
| 新增/改 ErrorCode | `api/errors/codes.py` + `api/errors/exceptions.py` + 前端 `web/src/errors/codes.ts`（从 OpenAPI 生成） |
| 新增模块 | `design/00-architecture/05-module-catalog.md` 加编号 + `design/02-modules/M{NN}/` 详细设计 |
| 改架构（跨层 / tenant / 异步 / 并发）| 起新 ADR + 改 `design/00-architecture/04-layer-architecture.md` 或 `06-design-principles.md` |
| 改目录结构 | 改本规约（第 1 条）+ 相应的 importlinter / eslint-plugin-boundaries 配置 |
| 改 commit / 分支 / PR 流程 | 改本规约（第 6 / 9 / 8 条） |
| 改协作规则 | 改 `CLAUDE.md` |
| 改依赖工具链（uv / pnpm 等） | 改本规约（第 10 条）+ CI 配置 + `pyproject.toml` / `package.json` |

**原则**：这些是**同一 PR 内必须一起改**的——不允许"后补文档"。

### 11.5 ADR 不变性（核心纪律）

**ADR（Architecture Decision Record）一旦 `status=accepted`，禁止原地修改**：

- 改内容 → 起**新 ADR**，在 frontmatter `supersedes` 字段填旧 ADR 编号
- 旧 ADR 状态改为 `superseded`，`superseded_by` 填新 ADR 编号
- 旧 ADR 内容**不删不改**（作为历史存根）

**示例**：
```
ADR-003 选用 Redis Queue（accepted 2026-04-20）
  ↓ 半年后改为 RabbitMQ
ADR-012 Queue 方案变更 - 从 Redis 切 RabbitMQ（accepted 2026-10-15）
  - frontmatter: supersedes: [ADR-003]

ADR-003 同时更新：
  - frontmatter: status: superseded, superseded_by: ADR-012
  - 内容不动
```

**允许的例外**（**不算"改"**）：
- 纠正错别字 / 链接失效修复 → 在 PR 描述注明
- 添加 "Note: superseded by ADR-XXX" 的顶部警示横幅

**禁止**：
- ❌ 改 ADR 的决策部分（理由、备选、结论）
- ❌ 改 ADR 的日期 / 状态（除状态流转外）
- ❌ 删除旧 ADR

**理由**：ADR 是决策**历史**的锚。改 ADR = 改历史 = 未来的 AI / 人读到的是"假历史"，无法复现当时的判断逻辑。

### 11.6 设计文档演进规则

`design/` 下的设计文档（非 ADR）：

- **B/C 档填充期**（prism-0420 当前阶段）：自由迭代，`status=draft` 合理
- **accepted 后**：
  - 小改（错字 / 链接 / 细节补充）→ 直接改，PR 描述说明
  - 中改（某一节重写）→ 起新 ADR 记录变更 + 改文档
  - 大改（推翻原设计）→ 起新 ADR + 原文档 `status=superseded`

**判断"小 / 中 / 大"**：
- 改动是否影响**已生成的代码**：否 = 小，是 = 中/大
- 改动是否影响**已做的决策**：否 = 小/中，是 = 大

### 11.7 PR 文档同步勾选

规约 8.4 的 checklist 第 6 项是"文档同步"——在 B-11 定义具体内容：

**勾选这项 = 作者声明已做以下检查**：

- [ ] 改了 schema → OpenAPI 重新生成 + 前端 codegen 跑过
- [ ] 改了 ErrorCode → 前端 `errors/codes.ts` 同步
- [ ] 新模块 → `05-module-catalog.md` 更新 + `02-modules/M{NN}/` 建好
- [ ] 架构决策 → 新 ADR 已起
- [ ] 改目录 / 分支 / commit / PR 流程 → 本规约对应条目已改
- [ ] 协作方式变 → `CLAUDE.md` 已改
- [ ] 新 / 改依赖 → 本规约第 10 条审批清单已在 PR 描述勾过

**规则**：凡涉及以上任一，必须**同 PR 内**完成，不允许"后补"。

### 11.8 禁止模式

```
❌ 改代码不改文档
改了 model 加字段，没改 schemas / 没重新生成 OpenAPI

❌ 真相源分散
字段说明同时写在 model docstring / schemas docstring / docs/architecture/
（改一处漏两处）

❌ 文档长期 draft
status=draft 超 3 个月，没人负责推进

❌ 原地改 accepted ADR
ADR-003 原地改决策内容（破坏历史锚）

❌ 后补文档
PR merge 后再提"docs: update after M01" PR
（违反"代码-文档配对"原则）

❌ 用 README 当真相源
"M01 的详细设计看 README"
（README 是入口，不承载设计）
```

### 11.9 强制方式

| 手段 | 覆盖 | 失败后果 |
|------|------|---------|
| PR template 第 6 项 checklist | 作者自检 | 软强制 |
| `frontmatter-check` CI Action | 所有 `design/` 和 `docs/` MD 必须有 frontmatter | PR 阻塞 |
| doc-rot 扫描（每周跑） | 超 2 周的 draft 报警 | 提醒（无硬阻塞） |
| 代码路径映射检查（可选 Action） | 改 `api/models/*.py` 同 PR 内必含 `api/alembic/versions/*` | PR 阻塞 |
| `git log` 扫描 | `type=feat` commit 若未伴随 `type=docs` 或 design 文件改动，review 时核 | 人工 |
| OpenAPI codegen diff CI | 前端 `types/api.ts` 与后端 OpenAPI 差异 = 0 | PR 阻塞 |

### 11.10 反例

```yaml
# ❌ 无 frontmatter
# 直接正文开始
# 设计讨论
...

# ❌ frontmatter 缺 status
---
title: 04-layer
owner: CY
---

# ❌ status=draft 半年不动
---
status: draft
created: 2025-10-15
---

# ❌ accepted 改决策（破坏历史）
---
status: accepted
accepted: 2026-04-18
---
## 决策
~~Redis Queue~~ RabbitMQ（半年后改了）   # 应起新 ADR
```

---

## 12. 类型安全门槛（B）

**适用范围**：全部

**呼应**：规约 3（Python 风格）、规约 4（TS 风格）、规约 7（错误处理 / ErrorCode 枚举）、规约 11（OpenAPI 作为前后端类型真相源）

### 12.1 设计要点

| 维度 | 选型 | 理由 |
|------|------|------|
| Python 类型检查 | **mypy 全项目 strict**（`tests/` 放宽） | FastAPI + Pydantic + SQLAlchemy 官方对齐；strict 覆盖面广；避免"分级导致的 Any 污染传染" |
| TS 类型检查 | **tsc strict: true + noUncheckedIndexedAccess + exactOptionalPropertyTypes** | 基线 strict 已含 8 项；额外 2 项拦住 AI 最常犯的 `array[0].method()` 和 optional 字段语义混淆 |
| 前后端类型闭环 | **OpenAPI → codegen → `web/src/types/api.ts`** | 禁手写；前端 zod 在 Server Action 层二次校验 |
| Pydantic | API 边界（router 入参 / 出参）必用 | 运行时校验（编译期类型 + 运行期 schema 双重保证） |
| 逃生口 | `any` / `Any` / `# type: ignore` / `@ts-expect-error` 必须带注释 + TODO | 局部债务必须可追溯 |

### 12.2 Python 类型检查（mypy 全 strict）

**配置**（`pyproject.toml`）：

```toml
[tool.mypy]
python_version = "3.12"
strict = true
files = ["api"]
exclude = [
    "alembic/versions",   # 自动生成，不强制
]
plugins = [
    "pydantic.mypy",       # Pydantic 模型识别
    "sqlalchemy.ext.mypy.plugin",  # SQLAlchemy 2.0 已内建类型支持，此插件兼容性好
]

# tests 放宽（测试里 assert 时类型推断常失败，不强制）
# 注：ruff per-file-ignores 用文件路径（tests/**/*.py），mypy overrides 用模块名（api.tests.*）
# 两者指向同一目录，前提是 pyproject.toml 的 [tool.uv] package=true 使 api/ 成为 Python package root
[[tool.mypy.overrides]]
module = "api.tests.*"
disallow_untyped_defs = false        # 测试函数允许无返回类型
disallow_incomplete_defs = false
check_untyped_defs = true            # 但 body 仍要类型正确
warn_return_any = false
```

**strict 模式包含的关键检查**（mypy `--strict`）：

| 检查项 | 作用 |
|-------|------|
| `disallow_untyped_defs` | 禁止无类型注解的函数 |
| `disallow_incomplete_defs` | 禁止部分注解（有参数无返回或反之） |
| `check_untyped_defs` | 即便函数无注解也检查 body |
| `disallow_untyped_decorators` | 禁止无类型的装饰器 |
| `no_implicit_optional` | `def f(x: int = None)` 报错（应 `int \| None`） |
| `warn_redundant_casts` | 多余 `cast()` 报警 |
| `warn_unused_ignores` | 多余的 `# type: ignore` 报警 |
| `warn_return_any` | 返回 Any 报警 |
| `strict_equality` | `1 == "1"` 不允许（类型不同） |

**运行**：
```bash
uv run mypy api/
# CI 阻塞：返回非 0 → PR 不能合
```

### 12.3 TypeScript 类型检查（strict + 两个额外严格项）

**配置**（`web/tsconfig.json`）：

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "esnext",
    "strict": true,

    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,

    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,

    "moduleResolution": "bundler",
    "esModuleInterop": true,
    "jsx": "preserve",
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src/**/*.ts", "src/**/*.tsx", "next-env.d.ts"]
}
```

**`strict: true` 已含的 8 项**（TypeScript 自动启用）：
- `noImplicitAny` / `strictNullChecks` / `strictFunctionTypes` / `strictBindCallApply`
- `strictPropertyInitialization` / `noImplicitThis` / `alwaysStrict` / `useUnknownInCatchVariables`

**额外开的两项含义**：

#### noUncheckedIndexedAccess

```typescript
const items = ["a", "b", "c"];

// 不开
const first = items[0];           // 类型: string
first.toUpperCase();              // ✅ 编译过；items[5] 运行时崩

// 开
const first = items[0];           // 类型: string | undefined
first.toUpperCase();              // ❌ Object is possibly 'undefined'
if (first) first.toUpperCase();   // ✅

// Record 同理
const map: Record<string, User> = {};
const u = map["missing"];         // 开: User | undefined / 不开: User
```

**防的是**：AI 最常犯的"数组 / Record 越界访问"运行时 undefined。

#### exactOptionalPropertyTypes

```typescript
interface User {
  name: string;
  email?: string;
}

// 不开
const u1: User = { name: "a", email: undefined };   // ✅（与 u2 等价）
const u2: User = { name: "a" };                     // ✅

// 开
const u1: User = { name: "a", email: undefined };   // ❌
const u2: User = { name: "a" };                     // ✅
// email 要么"有字段且 string"，要么"字段不存在"；不能"字段存在但 undefined"
```

**防的是**：OpenAPI codegen 生成的 optional 字段被误用 `undefined` 赋值（API 契约层语义精确）。

**运行**：
```bash
pnpm tsc --noEmit
# CI 阻塞：0 errors 才能合
```

### 12.4 Pydantic 边界校验

**规则**：**API 边界处（router 入参 / 出参）必须用 Pydantic**，内部层可用普通类型或 TypedDict。

```python
# Router：Pydantic schema 强制
@router.post("/modules", response_model=ModuleResponse)
def create_module(
    payload: ModuleCreate,                      # ← Pydantic 运行时校验 + mypy 编译期校验
    user: User = Depends(get_current_user),
    svc: ModuleService = Depends(),
) -> Module:
    return svc.create(user.id, user.project_id, payload)

# Service 内部：普通类型 dict 可用（但仍全注解）
def _build_default_fields(project_id: int) -> dict[str, Any]:
    return {"project_id": project_id, "status": "draft"}
```

**双重保证**：
- 编译期：mypy / tsc 查静态类型
- 运行期：Pydantic（后端）/ zod（前端 Server Action）查 schema

**例外**（**不算"违反"**）：
- 内部 helper 函数用 `dict[str, Any]` 转换中间态（带注释说明）
- 三方库返回 `Any` 时显式 `cast()` 到具体类型

### 12.5 前后端类型闭环（OpenAPI codegen）

**架构**：

```
api/schemas/*.py (Pydantic)
         ↓
  FastAPI OpenAPI 自动生成
         ↓
  openapi.json
         ↓
openapi-typescript 或 orval codegen
         ↓
web/src/types/api.ts     ← 禁手写，每次后端改动重新跑
         ↓
web/src/actions/*.ts     ← import type 用
web/src/services/*.ts    ← fetch 返回值类型
```

**规则**：

- `web/src/types/api.ts` 头部必有标识：`/* Auto-generated by openapi-typescript. DO NOT EDIT. */`
- 前端 Server Action 在边界再用 `zod` 做一次运行时校验（防后端契约变化但前端 codegen 未重跑）
- CI 校验：`openapi.json` 生成后 → `types/api.ts` 重新 codegen → `git diff` 为 0（不 0 阻塞 PR）

**示例**（前端 Server Action）：

```typescript
"use server";
import type { ModuleCreate, ModuleResponse } from "@/types/api";
import { z } from "zod";

// zod schema 与 OpenAPI 独立（但对齐），做运行时二次校验
const CreateModuleInput = z.object({
  name: z.string().min(1).max(100),
  description: z.string().optional(),
});

export async function createModuleAction(
  input: unknown,
): Promise<ModuleResponse> {
  const payload = CreateModuleInput.parse(input) satisfies ModuleCreate;
  // ... 调 FastAPI
}
```

### 12.6 逃生口约束

**`any` / `Any` 原则禁止**。以下情况允许，但必须满足：

1. 必须带注释说明**为什么**需要（三方库无类型 / 复杂泛型推断失败 / 等）
2. 必须带 TODO 追踪（未来能去掉时去掉）
3. 禁止在 service / dao / errors 核心层使用（只能在 utils / 边缘层）

**Python 示例**：

```python
# ✅ 允许：三方库无 stubs，带追踪
# TODO(M05): feedparser 无 type stubs，等官方 typing 支持后去掉
from feedparser import parse  # type: ignore[import-untyped]

# ✅ 允许：复杂 JSON 结构边界转换
raw: Any = json.loads(response.text)  # 来自外部 API
data = ExternalApiSchema.model_validate(raw)  # 立即转 Pydantic

# ❌ 禁止：核心层偷懒
def get_user(id: Any) -> Any:  # 核心 service 层，应写 int / User
    ...
```

**TypeScript 示例**：

```typescript
// ✅ 允许：三方库无类型，带追踪
// TODO(M05): 等 @xyflow/react 官方 type 更精确后去掉
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const flowInstance: any = useReactFlow();

// ✅ 允许：DOM 事件对象复杂推断
function onChange(e: any) {  // 应尽快改 React.ChangeEvent<HTMLInputElement>
  // TODO(M03): 改成精确类型
}

// ❌ 禁止：业务函数参数偷懒
function updateModule(data: any) { ... }   // 应 ModuleUpdate
```

**`# type: ignore` / `@ts-expect-error` 规则**：

```python
# ✅ 带具体 error code + 注释
result = complex_func()  # type: ignore[attr-defined]  # 三方库返回类型有问题，追踪 issue #123

# ❌ 裸 ignore
result = complex_func()  # type: ignore                # 不知道 ignore 什么
```

```typescript
// ✅ 带注释
// @ts-expect-error: Next.js 16 的 params 类型定义有 regression，追踪 next#12345
const { id } = await params;

// ❌ 裸 ignore
// @ts-ignore
const x = someFunction();
```

**mypy 配置**：`warn_unused_ignores = true`（strict 已含）——多余 `ignore` 会报错，强迫定期清理。

### 12.7 强制方式

| 手段 | 覆盖 | 失败后果 |
|------|------|---------|
| CI: `uv run mypy api/` | Python 类型 | 0 errors 才合 |
| CI: `pnpm tsc --noEmit` | TS 类型 | 0 errors 才合 |
| CI: OpenAPI codegen diff | 前后端契约一致 | PR 阻塞 |
| pre-commit: mypy + tsc | 本地拦截 | commit 阻塞 |
| ruff `ANN` 系列规则 | Python 函数参数 / 返回类型注解 | ruff check 阻塞 |
| eslint `@typescript-eslint/no-explicit-any: error` | TS 禁 `any` | eslint 阻塞 |
| 定期 `# type: ignore` 密度扫描 | 逃生口累积情况 | 周报（软强制） |

### 12.8 AI 实现时的类型纪律

**AI 最常犯的类型错误**：

| 错误 | 出现频率 | 防御 |
|------|---------|------|
| 漏写函数返回类型 | 高 | mypy strict 强制 |
| 用 `Any` / `any` 偷懒 | 高 | ruff + eslint 阻塞 |
| `array[0].method()` 不 check | 高 | `noUncheckedIndexedAccess` 拦 |
| 可选字段赋 `undefined`（TS） | 中 | `exactOptionalPropertyTypes` 拦 |
| 前后端字段名不一致 | 高 | OpenAPI codegen 闭环 |
| `# type: ignore` 堆积 | 中 | `warn_unused_ignores` + 密度扫描 |

**AI 实现一个模块时类型的执行顺序**（规约 1.10 步的扩展）：

1. 先写 model（SQLAlchemy 类型自带，强）
2. 再写 Pydantic schema（运行时 + 编译期双重）
3. 再写 DAO / Service / Router（参数 + 返回全注解）
4. 后端 `uv run mypy api/` 跑过
5. 重新生成 OpenAPI（FastAPI 自动）
6. 前端重跑 codegen → `types/api.ts`
7. 写前端 Server Action / Service（import type）
8. 前端 `pnpm tsc --noEmit` 跑过

**禁止**：任何一步跳过类型检查直接跑通功能——类型必须在功能之前绿。

### 12.9 反例

```python
# ❌ 无类型注解
def get_user(id):
    return db.get(id)

# ❌ 用 Any 偷懒（核心层）
def create_module(data: Any) -> Any:
    ...

# ❌ 裸 type: ignore
result = complex_func()  # type: ignore

# ❌ no_implicit_optional 违反
def f(x: int = None):   # 应 int | None = None
    ...

# ❌ 返回 Any（warn_return_any 触发）
def build() -> dict:    # 应 dict[str, Any] 或更精确
    ...
```

```typescript
// ❌ 显式 any
function update(data: any) { ... }

// ❌ 非空断言滥用（绕开 null check）
const name = user.name!;   // 除非逻辑保证非空，带注释

// ❌ as unknown as T 强转
const x = data as unknown as Module;  // 应走 zod 校验

// ❌ 裸 ts-ignore
// @ts-ignore
const result = fetchStuff();
```

### 12.10 逃生口度量（长期指标）

**目标**：逃生口数量随模块数增长而**非线性增长**（模块加倍，逃生口应增长 < 1.5 倍）。

**度量命令**：

```bash
# Python
grep -rn "# type: ignore" api/ | wc -l
grep -rn ": Any" api/services api/dao api/errors | wc -l   # 核心层应 = 0

# TS
grep -rn "@ts-expect-error\|@ts-ignore" web/src/ | wc -l
grep -rn ": any" web/src/ | wc -l
```

放入月度质量报告，看趋势——这是 AI 输出类型纪律的长期观察窗。

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
- [x] B 档 5 条全部填写
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
