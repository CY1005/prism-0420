---
title: 质量规约决策（Lint / Formatter / 测试 / 覆盖率 / pre-commit）
status: accepted
owner: CY
created: 2026-04-20
accepted: 2026-04-26
phase: Phase 2.0 启动决策（A1+A2）
parent: ../00-roadmap.md
---

# 02 - 质量规约决策

> Phase 2.0 闸门 1 的决策类产出。每项含**候选清单 + 优缺点对比 + 决定 + 理由 + 替代触发条件**。

**Prism 现状参考**：
- 后端：`pytest>=8.0` + `httpx>=0.27.0`，无 ruff / black / mypy / coverage
- 前端：`eslint ^9 + eslint-config-next` only，无 Prettier / Biome / Vitest / Playwright
- **观察**：Prism 工具链很薄，几乎无自动化质量保障 —— prism-0420 设计前置方法论应在此做出对照差异

---

## 1. Lint 工具

### 1.1 Python lint

| 候选 | 优 | 缺 |
|------|----|----|
| **A ruff（lint+format 一体）** | Astral Rust 实现 / 比 black+flake8 快 100x / 单依赖 / FastAPI/Pydantic/poetry 都用 / 2026 主流 | 生态 < 5 年，部分 pylint 规则未覆盖 |
| B black + flake8 | 历史最深 / 文档多 | 双工具 / 慢 |
| C black + ruff（split）| 折中 | 重叠工作 |
| D pylint | 检查最严 | 慢 / 配置麻烦 / 业界已边缘 |

**决定**：✅ **A ruff 一体**

**理由**：
1. 速度优势在 17 模块 × N 文件规模下明显（pre-commit < 2s vs black+flake8 30s）
2. 单依赖减少 pyproject.toml 复杂度
3. 行业趋势已确立（FastAPI 官方推荐）
4. Prism 没用任何工具 → 选 A 是清晰的方法论差异

**替代触发**：若 ruff 未来出现重大缺陷 / 项目规模 >> 现规模需要更细粒度规则 → 切 B

### 1.2 TypeScript lint

| 候选 | 优 | 缺 |
|------|----|----|
| **A ESLint v9 + typescript-eslint** | 行业标准 / Next 16 一等公民 / Prism 同款（前端继承零摩擦）| 配置相对啰嗦 |
| B Biome | Rust 一体化 / 快 | 1.9 现状成熟但部分 ESLint 规则未对齐 / Next 兼容窗口期 |
| C 仅 ESLint v9（Prism 现状）| 与 Prism 完全一致 | 无 format → 格式漂移 |

**决定**：✅ **A ESLint v9 + typescript-eslint + 配 Prettier（见 §2.2）**

**理由**：
1. 前端继承 Prism → ESLint 必须保留（不破坏继承）
2. Prettier 解决格式漂移问题，单独装无摩擦
3. Biome 半年内被 ESLint v10 + flat config 反超概率不低，避免赌新生态

**替代触发**：未来 Biome 1.x 大规模商用稳定（Vercel / Next 官方推荐）→ 评估切 B

---

## 2. Formatter

### 2.1 Python formatter

| 候选 | 优 | 缺 |
|------|----|----|
| **A ruff format** | 与 ruff lint 同进程 / Astral 维护 | 与 black 99% 兼容但非完全相同 |
| B black | 业界标杆 / 0 配置 | 单独工具 |

**决定**：✅ **A ruff format**（与 §1.1 ruff 一致）

**理由**：合并 lint + format 单依赖，与 §1.1 决定一致

**替代触发**：ruff format 出现兼容性 bug → 切 B

### 2.2 TS formatter

| 候选 | 优 | 缺 |
|------|----|----|
| **A Prettier** | 行业标准 / Next 16 默认推荐 / 与 ESLint 集成成熟 | 与 ESLint 双工具 |
| B Biome | 一体 | §1.2 同 Biome 风险 |

**决定**：✅ **A Prettier**

**理由**：与 §1.2 ESLint 路线一致

---

## 3. 测试框架

### 3.1 后端测试框架

| 候选 | 优 | 缺 |
|------|----|----|
| **A pytest** | 生态最广 / fixture 灵活 / parametrize 简洁（baseline-patch §F3.2 拆批 17 模块依赖此能力）/ Prism 同款 | 第三方依赖（无关紧要）|
| B unittest | 0 依赖 / Python 标准库 | 模板冗余 / fixture 弱 / 不支持 parametrize |

**决定**：✅ **A pytest**

**理由**：
1. baseline-patch-m20 §17 模块拆批策略明确依赖 pytest parametrize
2. Prism 同款 → 后续若有人对照测试代码无认知摩擦
3. unittest 后悔成本高（已写测试要重写）

**替代触发**：无（pytest 是 Python 测试事实标准）

### 3.2 前端测试框架（单元 + 组件）

| 候选 | 优 | 缺 |
|------|----|----|
| **A vitest + Testing Library** | 启动 < 1s / TS 原生 / Next 16 兼容好 | 生态相对新 |
| B jest + Testing Library | 历史最深 / 文档多 | 启动 > 5s / Next 16 兼容坑 |
| C 不写前端单测（Prism 也没）| 省时间 / 直接做对照 | 前端 bug 全靠 E2E + 手测兜底 |

**决定**：✅ **A vitest**

**理由**：
1. M20 团队管理页面是 prism-0420 唯一全新前端代码（非继承），需要单元测试兜底
2. 继承 Prism 的页面也可补 vitest 测试，逐步加质量
3. Phase 3 数据对照仍可直接看「设计前置全栈 vs VibeCoding 全栈」差异

**替代触发**：你想故意做"纯后端对照"实验 → 切 C 不写前端测试

### 3.3 E2E 测试

| 候选 | 优 | 缺 |
|------|----|----|
| A Playwright | 多浏览器 / Microsoft 维护 / API 强 | API 比 Cypress 啰嗦 |
| B Cypress | UX 好 / 调试可视化强 | 单浏览器 / 收购后维护节奏慢 |
| **C 暂不做（Phase 2.3 集成时再决）** | 现在写太早 / 后端没起 / 节省 1 周 | E2E 缺位 |

**决定**：✅ **C 暂不做**（推到 Phase 2.3 集成验证决策）

**理由**：
1. 现在写 E2E 太早，后端没起测什么
2. Phase 2.3 集成验证时所有模块就位，再决工具更准确

**替代触发**：Phase 2.3 启动时（roadmap §8 锚定）

### 3.4 API 集成测试

| 候选 | 优 | 缺 |
|------|----|----|
| **A pytest + httpx**（Prism 同款）| 与单测共享 fixture / async 友好 | 无 |
| B requests | 同步阻塞 | 不适配 FastAPI async |

**决定**：✅ **A pytest + httpx**

**理由**：与 §3.1 + Prism 一致，无需额外学习成本

---

## 4. 测试金字塔比例

**候选**：
- A 严格金字塔 70/20/10（单测/集成/E2E）
- B 倒金字塔（很少单测，多集成）
- **C 不强制比例 + critical path 必测**

**决定**：✅ **C 不强制比例**

**理由**：
1. 每模块 tests.md 的 critical path（如 M20 G1-G10 + C1-C7 + E1-E16）已锁定 100% 必过
2. 强制比例容易把 AI 实现逼到写无意义测试凑数
3. 真值是「critical path 100% PASS」，不是百分比

**替代触发**：实施后发现某模块 critical path 测试不够 → 在该模块 tests.md 补 case，不动总比例

---

## 5. 覆盖率门槛

| 候选 | 优 | 缺 |
|------|----|----|
| A ≥80% 硬门槛 | 严格 | 容易逼 AI 写无意义测试凑数 / critical path 真门槛被稀释 |
| **B 不设硬门槛 + critical path 100% PASS 是真门槛** | critical path 已是真门槛 / 不绑架 AI | 覆盖率裸奔风险 |
| C ≥60% 软门槛 | 折中 | 折中容易两头失守 |

**决定**：✅ **B 不设硬门槛**

**理由**：
1. critical path（每模块 tests.md G/C/E 类）已锁 100%，是真门槛
2. PR 模板要求「覆盖率下降需在描述里解释」（§A3.3 拒合并条件）
3. coverage 报告仍跑（CI 展示数字），仅不做硬门槛

**替代触发**：累计 ≥3 次 PR 因覆盖率裸奔出 bug → 评估切 A

**配套**：coverage 工具用 `coverage.py`（pytest-cov 插件）

---

## 6. Pre-commit hook

### 6.1 工具链

| 候选 | 优 | 缺 |
|------|----|----|
| **A `pre-commit` Python 包** | 跨语言 / 配置统一 / 单仓覆盖前后端 | Python 依赖 |
| B husky + lint-staged | JS 生态主流 | 仅前端 / 后端要单独配 |
| C Git native hooks（脚本）| 0 依赖 | 维护成本高 |

**决定**：✅ **A `pre-commit` Python 包**

**理由**：单一工具管前后端两边比 husky+ruff 单独配清爽

### 6.2 hook 检查项

启用：
- [x] ruff lint（后端）
- [x] ruff format check（后端）
- [x] ESLint（前端）
- [x] Prettier check（前端）
- [x] commit message 长度 < 100 字符首行（项目内约定）
- [x] 阻塞 .env / 大文件（>1MB）
- [x] trailing whitespace + EOF newline

不启用：
- ❌ 跑全套 test（commit 时太慢，CI 兜底）
- ❌ Conventional Commits 强制（§7 决定不强制）

---

## 7. Commit message 格式

| 候选 | 优 | 缺 |
|------|----|----|
| A Conventional Commits 强制 | 行业标准 / 自动 changelog | 学习成本 / 单人项目过度 |
| B 自由 | 0 约束 | 无规律 |
| **C 项目内约定（沿用现风格）** | 已自然形成「模块：动作 + 关键 finding ID」 | 仅本项目认 |

**决定**：✅ **C 项目内约定**

**理由**：
1. M20 commit message 已自然形成「`M20 三轮 audit + 4 批修复闭环：39 finding 全收敛`」风格
2. 单人项目，强 Conventional 反而约束过度
3. Co-Authored-By 字段保留（KB 规则 + Claude Code 默认）

**模板**：
```
<模块>: <动作概要>（关键 ID/范围）

可选 multi-line description

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

## 完成度判定

- [x] §1-2 lint + formatter（后端 ruff / 前端 ESLint+Prettier）决策完成
- [x] §3 测试框架（pytest + vitest + 暂不做 E2E + httpx）决策完成
- [x] §4 测试金字塔（不强制比例 + critical path 必测）决策完成
- [x] §5 覆盖率门槛（不设硬门槛，critical path 是真门槛）决策完成
- [x] §6 pre-commit hook（pre-commit 包 + 检查项 7 启 2 禁）决策完成
- [x] §7 commit message（项目内约定）决策完成
- [x] 每项都有「候选 + 决定 + 理由 + 替代触发」四要素
