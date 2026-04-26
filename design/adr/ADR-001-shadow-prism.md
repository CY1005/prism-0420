# ADR-001：建立 Prism Shadow 项目用于设计训练

- **状态**：accepted（§预设 3 部分 superseded by ADR-005，2026-04-26）
- **日期**：2026-04-20
- **决策者**：CY
- **partial_superseded_by**：[ADR-005-team-extension.md] —— §预设 3 整段（命名 + 类型 + FK 三件）

---

## Context（背景）

- 2026-04-20 CY 反思 Prism VibeCoding 实战：
  > "我从业务层面看似想清楚了产品逻辑和设计，但是对于数据的流转、状态的变化都没想清楚"
- Prism 代码质量塌方的根因（归因链）：
  ```
  设计缺位 → AI 乱发挥 → 人不 Review → 债务累积
     ↑                                        ↓
     └──── 没有重构节点 ←── 没有测试不敢改 ←──┘
  ```
- 直接重构 Prism 受既有代码束缚，自由度低
- 需要在**干净环境**验证「设计前置方法论」，并对照验证其价值
- 已沉淀方法论：`/root/cy/ai-quality-engineering/02-技术/架构设计/软件工程设计前置方法论.md`

---

## Decision（决策）

**核心定位**：prism-0420 和 Prism 是"**同样的需求、不同的开发策略、最终都实现完整功能**"——用来对照验证设计前置方法论的价值。

### 与 Prism 的本质对比

| 维度 | Prism（原项目） | prism-0420（Shadow） |
|------|---------------|--------------------|
| **需求** | 20 个功能（F1-F20） | 同样 20 个功能（M1-M20） |
| **开发策略** | VibeCoding 边做边想 | 设计前置 → AI 实现 |
| **速度** | 11 天做完（git log 证据：4/3→4/14） | 预估 10-15 天（设计 2-3 天 + 实现 7-12 天） |
| **代价** | 质量差，4/17 后持续工程治理 | 前期设计投入，期望更低返工 |
| **产出** | 完整 20 功能 | **同样完整 20 功能**（不是简化版、不是 demo） |

### 关键决策点

1. **需求完全复用** Prism（F1-F20 对应 M1-M20），不重新设计功能
2. **开发策略完全不同**：
   - **Phase 1（当前）**：完整设计文档（PRD / 架构骨架 / 模块清单 / 设计原则 / ADR）
   - **Phase 2**：基于设计文档用 AI 完整实现 20 个模块
   - **Phase 3**：对照 Prism 做"代码质量 vs 开发时间"的数据化对比
3. **本期只做设计文档，不写代码**
4. **用户**：个人（CY），架构按多人完整产品设计（即使本期只有 1 人）
5. **架构差异**：单 ORM（SQLAlchemy）+ OpenAPI 契约（vs Prism 双 ORM 同步）
6. **首个实现模块**：候选 M4（功能项档案页）/ M17（AI 导入）/ M13（需求分析），档位 A+B 完成后选定

---

## Consequences（影响）

### 正向

- **对照价值**：同需求 × 两种开发策略 = 可数据化验证"设计前置"的效益
  - 维度 1：最终代码质量（bug 数 / 工程债务 / 重构成本）
  - 维度 2：开发速度（Prism 11 天 vs prism-0420 设计+实现总天数）
  - 维度 3：设计决策的可追溯性（prism-0420 有完整 ADR 链）
- **可产出有说服力的 STAR 素材**（"做了 A/B 对照实验证明设计前置的价值"）
- **方法论可复用**：设计前置方法论已沉淀到知识库，下一个项目直接套用
- **未来给同事开放**：架构已按多人设计，无需返工

### 负向

- **同需求双实现的时间投入**：Prism 已花 11 天，prism-0420 再花 10-15 天
- **前置设计阶段 2-3 天**：可能和 Prism 工程质量治理（Week 3）分流注意力
- **新工具链学习**：Alembic + openapi-typescript（但学了之后其他项目也能用）
- **真实风险**：可能设计完发现和 Prism 差距不大——这本身也是有效的负面验证，记录在此不回避

---

## Alternatives Considered（替代方案）

### 方案 1：直接重构 Prism

**否决理由**：
- 既有代码束缚自由度（路径依赖）
- 重构风险高，可能破坏已有功能
- 无法验证"零起点的设计前置方法论"——总是在修补既有代码
- 心理负担重（担心影响现有 Prism 进度）

### 方案 2：独立小项目（Todo / Blog 等）

**否决理由**：
- 和 Prism 无关，失去"设计 vs 实现"对照价值
- 学习价值有限（简单 CRUD 无法训练多人架构、事务、异步）
- 不能产出与当前工作直接相关的 STAR 素材
- 规模小，架构训练空间小

### 方案 3：B 简化版 shadow（只做 3-5 个核心模块）

**否决理由**：
- 训练目标是"完整产品设计能力"，简化版失去多人协作架构训练价值
- Prism 实际 11 天做完 20 功能（git log 证据），完整 fork 时间成本可控
- 失去"完整功能对照"的数据化对比价值
- 未来如需开放给同事协作，架构已有则无需返工

---

## 多人架构核心预设（回应 reviewer M1 / B1 / B2）

这节记录的是 **schema 级 / 架构级决策**——现在不定清楚，未来改动成本极高。

### 预设 1：并发策略 — 乐观锁（version 字段）

- 任何可能并发编辑的实体必须有 `version: int` 字段
- 更新时 `WHERE version = expected`，影响行数 0 则抛 ConflictError
- 冲突处理：前端弹窗"数据已被他人修改，请刷新后重试"

**为什么不选悲观锁**：
- Prism 的维度编辑多人同时发生概率低
- 悲观锁的"一人编辑时其他人卡住"体验差
- DB 连接锁耗尽风险高

**适用对象**（示例）：
- `dimension_records`（Prism 已有 version 字段）
- `features` / `projects` / `version_records` 等有编辑场景的实体

### 预设 2：Redis Queue Worker 数 — 可配置，本期 = 1

- 配置项 `WORKER_COUNT`（环境变量或 config.py）
- 本期默认 1（单进程）
- 未来开放多人 / 负载增加时改成 2+，无需代码改动

```python
# config.py
WORKER_COUNT = int(os.getenv("WORKER_COUNT", "1"))

# worker_manager.py
for i in range(WORKER_COUNT):
    Worker(queue_name="ai_tasks").start()
```

### 预设 3：space_id 形态 — 预留列无 FK ⚠️ **整段 superseded by ADR-005（2026-04-26）**

> ⚠️ 本节于 2026-04-26 被 [ADR-005-team-extension.md](./ADR-005-team-extension.md) **整段 superseded**，三件实质变更：
> 1. **命名**：`space_id` → `team_id`（对齐 PRD F20「团队」+ Prism 实跑命名）
> 2. **类型**：`INT NULL` → `UUID NULL`（对齐项目 UUID 范式）
> 3. **FK**：原"无 FK 预留口"放弃，正式启用 `ondelete=RESTRICT`（M20 Q8「强制前置迁出」依赖）
>
> 本节内容仅作历史记录保留，新设计请直接参 ADR-005 §3 baseline-patch + M20-team/00-design.md §3。「最小预留口 + 未来扩展」精神保留，但字面上的「INT / 无 FK / 预留」全部废弃。

- 所有 project 相关表预留 `space_id INT NULL` 字段
- 本期不建 spaces 表，不加 FK 约束
- 未来加空间层迁移步骤：
  1. 建 spaces 表
  2. 批量为现有记录填 space_id
  3. Alembic 迁移加 FK 约束

**为什么不选 nullable 外键**：要求 spaces 表现在就存在（即使空的），违反 YAGNI。

```python
class Project(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    space_id: Mapped[Optional[int]]  # 预留，无 FK
```

### 预设 4：AI Provider 抽象设计

#### 4.1 接口签名 — 流式 + 同步双支持

```python
class LLMProvider:
    def generate(self, prompt: str) -> str:
        """同步：返回完整结果"""
        ...

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        """流式：逐字返回"""
        ...
```

- **交互式 AI 功能**（F13 / F12 / F14）用 `stream()`——用户盯着屏幕等，避免空白焦虑
- **后台任务**（F17 导入 worker）用 `generate()`——用户不在等，不需要流式复杂度

**aclose 协议约定**（M13 pilot 2026-04-25 补充）：`stream()` 返回的 `AsyncIterator[str]` 必须支持 PEP 533 的 `aclose()` 协议，用于客户端断开时释放底层 HTTP / SDK 连接。真实 Provider（anthropic ≥0.x / openai ≥1.x / Kimi SDK）的 streaming 对象原生满足；Mock / 测试 Provider 必须实现可断言的 `aclose_called` 标志（见 M13 tests.md S4）。消费方（如 M13 Service 层）在检测 `request.is_disconnected()` 后**必须** `await stream.aclose()`，不得依赖 GC 隐式释放。

#### 4.2 失败重试 — 3 次指数退避 1s/2s/4s

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3),
       wait=wait_exponential(min=1, max=4))
def call_provider(provider, prompt):
    return provider.generate(prompt)
```

**原因**：业界标准，Claude / OpenAI / Kimi 瞬时错误通常 1-4 秒内恢复。

#### 4.3 Provider 自动切换 — 不自动切换

- 用户配置什么 Provider 就用什么
- Provider 失败 → 直接抛错给用户
- 用户手动切换 Provider（UI 里选）

**原因**：自动降级会隐藏真实故障（用户以为 Claude 能用，实际一直在用 DeepSeek）。

### 预设 5：Redis Queue 任务失败策略

#### 5.1 失败感知 — 用户轮询任务状态

- 前端每 5 秒 `GET /api/tasks/{task_id}`
- 任务状态：`pending` / `processing` / `success` / `failed`
- 失败时响应带 `error` 信息

**未来扩展**（不在本期）：WebSocket 推送。

#### 5.2 重试策略 — 指数退避 1min/10min/1h

```python
RETRY_DELAYS = [60, 600, 3600]  # 秒
# 第 1 次失败 → 等 1 分钟 → 重试
# 第 2 次失败 → 等 10 分钟 → 重试
# 第 3 次失败 → 等 1 小时 → 最后一次重试
# 3 次都失败 → 标记 failed，用户感知
```

**原因**：AI API 瞬时错误可能需要几分钟到一小时恢复，指数退避给足够窗口。

#### 5.3 超时时间 — 按任务类型配置

```python
TASK_TIMEOUTS = {
    "ai_import": 30 * 60,        # 30 分钟：zip 解析 + AI 分析可能长
    "need_analysis": 5 * 60,     # 5 分钟：单需求分析
    "ai_snapshot": 10 * 60,      # 10 分钟：版本历史生成
    "ai_embedding": 15 * 60,     # 15 分钟：批量 embedding
}
```

**原因**：统一超时要么浪费（短任务等太久才能重试）要么不够（长任务被截断）。

---

## 完成度判定

- [x] Context 4 点（反思 / 归因链 / 既有代码限制 / 方法论沉淀）
- [x] Decision 核心定位明确（同需求 × 不同策略 × 完整功能）
- [x] Decision 6 个关键决策点
- [x] Consequences 正向 4 条 + 负向 4 条（含真实风险）
- [x] Alternatives 3 方案各有否决理由
- [x] 多人架构核心预设 5 项（9 个子决策）
- [x] AI 完整性质疑通过
