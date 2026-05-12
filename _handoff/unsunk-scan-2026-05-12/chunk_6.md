# Chunk 6 Findings (05-08 ~ 05-09, 18 sessions)

## Summary

扫描数：18 sessions（1.02MB）。其中直接涉及 prism-0420 的 session：11 个（M05/M06/M13/M14/M15/M16/M17/M18/M19 sprint 实施 + M17 启动期两个 session）；与 prism 无关的 session：7 个（hotfix SQL 测试、技术日报×3、学习月报×1、播客/B站 skill 安装×1、播客/ASR API 设置×1）。识别有价值的 findings：14 个。主要主题：reconcile pass 三栏分类方法论演进、跨 sprint 范式积累、LLM 集成首发教训、M15 纯读范式稳定、M17/M18 大型模块新挑战。

---

## Findings

### F-6.1. 闸门 2.5 三栏分类"仪式化自审"失效信号——首次实证沉淀

- **类型**: 方法论
- **来源 session**: `152bff88` (2026-05-09, M05 sprint)
- **摘要**: M05 sprint reconcile pass 中，Claude 把 5 个已有规则机械应用项（covering 索引范式、quality-spec 关键路径、M04 punt 到期工序等）错误列为 B 栏让 CY 拍板，被 CY 一句"按照步骤分析做决定，做不出决定就是分析不对"点出。根因：reconcile 自审"真有候选吗"问了但没 grep design/audit/memory 既有规则就答"真权衡 ✅"——自审仪式化。修正后 B 栏归零，并把"自审前必先做 5 步分层第 1-2 步（识别+定层+找既有锁定项），grep 命中→A 或 C 栏；grep miss 才进 L2 候选枚举"作为失效信号沉淀进 `feedback_problem_layered_analysis`。
- **关键引用**: "我把'我有倾向 + 看似取舍 = B 栏'混成一个判别式。但这个公式漏了第 0 步：我倾向的那个候选，是不是恰好就是既有规则机械应用的结果？是的话 = A 栏，不是 B 栏。"
- **推荐沉淀去向**: `design/audit/lessons-learned.md` 新增条目；`feedback_problem_layered_analysis.md` 已在会话内更新（确认落地状态）
- **置信度**: 高

---

### F-6.2. M05 list_by_node 排序方向 design 内部矛盾（§6 ASC vs §9 DESC）

- **类型**: bug 教训 / design 决策
- **来源 session**: `152bff88` (2026-05-09, M05 R1-A review)
- **摘要**: M05 design §6 R-X3 段写 `ORDER BY created_at ASC`，§9 代码示例写 DESC，实装 dao/service 均用 DESC。R1-A Opus 抓出此矛盾——§6 是 M16 pilot 基线补丁锁定的对外契约，跨模块消费方将按 ASC 期待，M16 sprint 启动 reconcile pass 必撞此 seam。在 sprint 末 design 回写时已将 §6 统一为 DESC。
- **关键引用**: "design §6 R-X3 段是 M16 pilot 基线补丁锁定的对外契约，跨模块消费方将按 ASC 期待。M16 sprint 启动 reconcile pass 会撞此 seam。"
- **推荐沉淀去向**: `design/02-modules/M05-version-timeline/00-design.md`（已回写 DESC，确认已落）；`design/audit/lessons-learned.md` 新增"design §6 R-X3 对外契约语义修改须同步 sprint 末 design 回写，不能仅靠实装自然对齐"
- **置信度**: 高

---

### F-6.3. service docstring 事务边界声明 vs 实装漂移——M02-M05 跨 sprint 文字债

- **类型**: bug 教训 / 技术坑
- **来源 session**: `152bff88` (2026-05-09, M05 R1-A + R2 review)
- **摘要**: M05 VersionService docstring 字面声明"所有产生副作用方法用 `async with db.begin()` 包裹"，实装全部由 Router/conftest 管事务，service 不显式开事务（R-X3 范式）。这是 M02-M05 四个 sprint 的同款漂移，R1-A Opus 抓出后在 sprint 末统一顺修 M04+M05 docstring 为"事务由 caller(router) 管理，本 service 遵循 R-X3 外部 session 约定"。M06/M13 同款仍可能存在。
- **关键引用**: "service 模块文档声称的事务边界与实装不符，是 R1 唯一硬阻塞——此外 M05 sprint 子片 1+2+3 在 spec 对齐与质量两维都干净"
- **推荐沉淀去向**: `design/audit/lessons-learned.md` 新增"service docstring `with db.begin()` 声明是历史写法，必在 sprint 末顺修为 R-X3 caller 管事务范式"
- **置信度**: 高

---

### F-6.4. IntegrityError 约束名区分规则——M05 立规后 M06 首次回退

- **类型**: bug 教训 / 技术坑
- **来源 session**: `152bff88` (2026-05-09, M06 R1-C review)
- **摘要**: M05 R1-C P1-01 立规"IntegrityError 区分约束名，避免错误码语义误导 caller"，M05 version_service 实现了 UNIQUE(label) vs UNIQUE(is_current) 的区分（str(e.orig) 检查）。M06 create_ref 的 except IntegrityError 无差别转换为 CompetitorRefDuplicateError，既未区分 uq_competitor_ref_node_competitor（UNIQUE）vs FK IntegrityError（competitor 被并发删）。这是 M05 规则在 M06 的首次复现，说明"copy 注释描述但未复制实现模式"是高风险点。
- **关键引用**: "M06 create_ref IntegrityError handler 是 copy 了 M05 注释描述但未复制 M05 的约束名区分实现——M05 version_service.py:164-173 的 err_text 检查模式在 M06 完全缺席，这是本次 review 最高价值命中。"
- **推荐沉淀去向**: `design/audit/lessons-learned.md` 新增"注释可以抄但模式不能省：IntegrityError 区分约束名必须在代码层面实现，不能仅在 docstring 层面声明"；`design/01-engineering/01-engineering-spec.md` 已有 清单 6 约束（确认已落）
- **置信度**: 高

---

### F-6.5. M13 LLM 集成首发——ClaudeProvider 不引 anthropic SDK 用 httpx 直解析 SSE

- **类型**: 设计决策
- **来源 session**: `540ed1be` (2026-05-08, M13 sprint)
- **摘要**: M13 是 prism-0420 LLM 集成首发，ClaudeProvider 决定不引 `anthropic` 库依赖，直用 `httpx.stream` 解析 anthropic SSE 协议，理由是"避免 SDK 升级耦合"。这是一个显式技术选型决策，且与 prism-0420 design §14.5 写明了"真 SDK 范围已锁 Mock+Claude / skipif integration smoke / 全链路 AES 接通"，但该决策在 design 文档中未找到 ADR 级别的记录。
- **关键引用**: "ClaudeProvider 不引 `anthropic` 库依赖（避免 SDK 升级耦合），直用 `httpx.stream` 解析 anthropic SSE 协议"
- **推荐沉淀去向**: `design/adr/` 新建 ADR-006-llm-provider-no-sdk-dependency.md（记录 httpx 直解析 vs anthropic SDK 的取舍）；或在 `design/02-modules/M13-requirement-analysis/00-design.md` §6 补充 disambiguation 注释
- **置信度**: 高

---

### F-6.6. M13 SSE MockProvider aclose_called 协议——PEP 533 GeneratorExit 触发区分

- **类型**: 技术坑
- **来源 session**: `540ed1be` (2026-05-08, M13 sprint 子片 1)
- **摘要**: M13 MockProvider 设计了 `aclose_called: bool` 标志，用于 SSE cancel 路径核心契约验证。关键细节：自然完成（stream 读完）不触发 `aclose_called=True`，只有 caller 显式调用 `.aclose()` 才触发（PEP 533 GeneratorExit 才设）。这区分了"正常结束"和"被取消"两种路径，是 R1-A Opus review 的校验点。这个区分在 design §12 已写但具体实现细节（GeneratorExit 触发条件）不在 design 正文中。
- **推荐沉淀去向**: `design/02-modules/M13-requirement-analysis/00-design.md` §12 MockProvider 段补充"aclose_called=False 表自然完成；PEP 533 GeneratorExit 才设 True，区分取消路径"的 disambiguation 注释
- **置信度**: 高

---

### F-6.7. M13 R1-A 5 个 P1 集中——metadata 字段名 hash vs length 错误

- **类型**: bug 教训
- **来源 session**: `540ed1be` (2026-05-08, M13 R1-A review)
- **摘要**: M13 sprint R1-A Opus 抓出 5 个 P1，其中 metadata 字段名不匹配（设计写 `hash` 实装用 `length`）是典型 spec-to-code 字面漂移。另 4 个：`_fetch_node_context` 漏 wrap NodeNotFoundError、Anthropic delta.type 缺校验（content_block_delta 以外的 type 会 KeyError）、ConflictError 被吞（M04 DuplicateError 未在 M13 service 层 re-raise）、covering 索引缺口。本次 R1-A P1 数量（5 个）显著高于 M02-M12 基线（0-2 个），说明 LLM 集成首发的复杂度使 spec 对齐风险提高。
- **关键引用**: "5 个 P1 立修必须本 sprint review 修；P1-1 metadata 字段名（hash vs length）+ P1-3 Anthropic delta.type 是子片 5 关闸前最优先的两条。"
- **推荐沉淀去向**: `design/audit/lessons-learned.md` 新增"LLM 集成首发 sprint R1-A P1 数量会显著高于基线，需在 §14.5 明确强化 spec 字面对齐检查频次"
- **置信度**: 高

---

### F-6.8. M14 R1-C P1-1: update_news v is not None 过滤导致合法置空静默丢弃

- **类型**: bug 教训 / 技术坑
- **来源 session**: `c61e4bae` (2026-05-08, M14 sprint R1-C review)
- **摘要**: `industry_news_service.update_news` 用 `{k: v for k, v in fields.items() if k != "source_type" and v is not None}` 过滤，导致 `summary=None`（用户想清空摘要）被静默丢弃，字段保持原值且不报错。修法是 Router 侧用 `model.model_fields_set` 筛出实际传入字段，不过滤 None 值。这是"PATCH 语义中 None 表置空 vs None 表未传"的经典坑，在 M02-M13 中均未明确记录范式。
- **关键引用**: "这是一条静默吞逻辑路径，不是防御性除错，是业务语义错误。"
- **推荐沉淀去向**: `design/01-engineering/01-engineering-spec.md` 新增规范"PATCH endpoint service 层禁止 `v is not None` 过滤——使用 `model.model_fields_set` / `exclude_unset=True` 区分未传和置空"；`design/audit/lessons-learned.md` 同步
- **置信度**: 高

---

### F-6.9. M15 纯读模块 R1 范式确立——纯读 = 1 合并 Opus，非 3 subagent 并行

- **类型**: 方法论
- **来源 session**: `fb1ffdc9` (2026-05-08, M15 sprint)
- **摘要**: M15 sprint 触发了"纯读聚合模块 R1 范式"的第二次实证。M15 §14.5 写了默认 R1=3 subagent，CY 提醒"20x Pro 应该够用，新会话会不会丢失语义"，Claude 自我纠正：M15 与 M10 同款（纯读/无写自表），M10 实证已锁"纯读模块 R1=1 合并 Opus"，§14.5 应回写"纯读模块（M10/M15）R1=1 合并 Opus / 业务模块 R1=3 subagent 并行"。这是范式分叉的首次明确记录。
- **关键引用**: "R1=3 subagent 是业务模块（M02-M09/M11/M12/M14）特化，不是'默认'。M10 的实证已锁纯读模块 R1=1 合并 Opus。"
- **推荐沉淀去向**: `design/00-phase-gate.md` §14.5 默认范式段补充纯读 vs 业务模块的 R1 范式分叉说明；`design/audit/lessons-learned.md` 新增
- **置信度**: 高

---

### F-6.10. M15 action_type 命名规约 baseline-patch 反向回写——M14 漂移修复流程

- **类型**: 设计决策 / 方法论
- **来源 session**: `fb1ffdc9` (2026-05-08, M15 sprint reconcile)
- **摘要**: M14 sprint 实装 action_type 用 `"create"/"update"/"delete"/"link"/"unlink"` 裸 CRUD，违反了 M02-M13 十一数据点稳定的 `{entity}_{past_verb}` 命名规约（2026-05-06 baseline-patch 建立）。M15 reconcile pass 时 Claude 首先误报 B 栏，被 CY 指出"原则性问题，有现有规则解决不了吗"，重走 5 步分层后自决 α 路线：M14 service.py 5 处 + tests 7 处反向回写，M14 design §10 更新，M15 design §3 同步新值。此过程完整记录了"跨 sprint baseline-patch 反向修复"的工序。
- **关键引用**: "命名规约 baseline-patch 是 CY 自己 2026-05-06 ack 立的，M01-M13 11 模块严格遵守 → M14 是漂移源不是规约新基线"
- **推荐沉淀去向**: `design/audit/lessons-learned.md` 新增"跨 sprint baseline-patch 反向修复工序：先 grep 确认漂移范围 → 5 步分层定 L1 锁规 → AI 自决（不让 CY 拍）→ 机械批量改 service/tests/design"
- **置信度**: 高

---

### F-6.11. M16 reconcile pass 发现 B1 工作量 2× 偏差——crn 枚举漂移实际 31 处非 14 处

- **类型**: bug 教训 / 跨 session 收口
- **来源 session**: `69105db2` (2026-05-08, M16 sprint)
- **摘要**: M16 冷启动 prompt 估算"M03-M08 service ~14 处裸 CRUD action_type"，实际 reconcile grep 后是 ~31 处（含 M02 project_service 2 处、M11 cold_start 3 处 dot→underscore 命名漂移）。工作量从估计 4-6h 实际 8-12h（再加 write_event stub + race window 复审升到 12-16h）。M16 选 β 最小集路线（write_event stub 替换 + 31 处过去式批量改 + M11 命名漂移修复），M07 "unassigned" 设计决策 + race window + e2e 异常传播推独立 sprint。这是 `feedback_decision_codefirst_validation` 场景——决策前未 grep 真实代码导致工作量偏差 2-3×。
- **推荐沉淀去向**: `design/audit/lessons-learned.md` 新增"reconcile pass 工作量估算必须 grep 真实代码，仅靠 design 文字 + 历史印象会系统性低估 2-3×，尤其是批量枚举修复类任务"
- **置信度**: 高

---

### F-6.12. M17 SQLAlchemy create_savepoint + asyncpg 测试坑——同一 connection 不能叠两个 AsyncSession

- **类型**: 技术坑
- **来源 session**: `3231867c` (2026-05-09, M17 sprint)
- **摘要**: M17 sprint 实现 R-X1 失败补偿（compensation_session helper）时遭遇测试架构难题：测试 fixture 使用 `join_transaction_mode='create_savepoint'` 后，不能在同一 db_connection 叠加第二个 AsyncSession（greenlet 桥接冲突 / asyncpg 一连接一活跃操作 / SAVEPOINT 嵌套被两个 session 各自管理）。妥协做法：conftest autouse fixture 把 compensation_session 函数本身 monkeypatch 成 yield 同一 db_session（生产路径独立 connection 留生产 / 集成 e2e 验）。这个模式已落 `design/audit/m17-pilot-template-validation.md` 启动期元教训段，但未在 `design/audit/lessons-learned.md` 全局记录。
- **关键引用**: "测试 fixture 不能在同一 db_connection 叠加第二个 AsyncSession；service 失败补偿不主动 rollback 业务 session"（M17 handoff 元教训段）
- **推荐沉淀去向**: `design/audit/lessons-learned.md` 新增技术坑"asyncpg + SQLAlchemy create_savepoint 测试架构约束：compensation_session 在 fixture 下必须 monkeypatch，不能构造真独立连接"；`design/01-engineering/01-engineering-spec.md` 补充测试注意事项
- **置信度**: 高

---

### F-6.13. M17 partial_failed 状态不可达——design 声明 vs 实装差距

- **类型**: bug 教训 / 未完结 TODO
- **来源 session**: `3231867c` (2026-05-09, M17 R1-A review)
- **摘要**: M17 design §4 R4-3a 和 §10 声明了 `import_partial_failed` 状态（importing 部分 item 失败 / ai_step2 部分文件失败），并在 ImportTaskStatus 枚举中登记。实装 `run_batch_insert` 和 `run_ai_step` 异常路径一律走 `_mark_failed`（status=failed），从未触发 partial_failed。测试 `test_retry_partial_failed_to_step3` 通过 fixture 直接造 partial_failed 状态绕过了真实路径，不能证明业务可达。R1-A Opus 判断：M17 设计是 "单事务=all-or-nothing → 真无 partial 可言"，建议在 design §10 `import_partial_failed` 行加 `[v1 unreachable]` 注脚，或明确实装补充 partial 路径。
- **推荐沉淀去向**: `/root/workspace/projects/prism-0420/design/02-modules/M17-ai-import/00-design.md` §10 `import_partial_failed` 行补 `[v1 unreachable: 单事务 all-or-nothing，partial 路径待 v2 多批次场景实装]` 注脚（检查是否已在 sprint 末落地）
- **置信度**: 高

---

### F-6.14. M18 embedding api_key 孤立——OpenAI provider 从 env 取而非走 ProjectSettings AES 解密

- **类型**: 技术坑 / 设计决策
- **来源 session**: `f6e60d31` (2026-05-09, M18 sprint R1-C review)
- **摘要**: M18 OpenAIEmbeddingProvider 从环境变量取 api_key（`os.environ.get("OPENAI_API_KEY")`），而 M13 ClaudeProvider 已走 `ProjectSettings.embedding_api_key_enc` + AES decrypt 全链路（M13 sprint CY 拍定）。两条路径孤立，生产部署时 OpenAI embedding 的 key 管理范式与 Claude LLM 的 key 管理范式不一致。R1-C 标为 P1，建议对齐走 ProjectSettings AES decrypt 路径。
- **关键引用**: "embedding_provider.py:308-313 OpenAI api_key 从 env 取 vs 应走 ProjectSettings.embedding_api_key_enc + AES decrypt"
- **推荐沉淀去向**: `/root/workspace/projects/prism-0420/design/02-modules/M18-semantic-search/00-design.md` 补充 API key 管理范式统一说明；检查 M18 子片 4/5 是否已对齐；若未修，登记 cross-sprint punt 池
- **置信度**: 高

---

## 附注

以下 sessions 被排除（与 prism-0420 无关或为纯执行对话）：
- `730f6d08`：公有云 hotfix SQL 构造，与 prism-0420 无关
- `07c7a62c`：bilibili-render-pdf skill 安装 + Whisper 安装
- `98b3e486`：DashScope ASR API 注册 + 播客测试
- `4682bc29`、`57b92569`、`0bd726b8`、`42d4a6f5`：技术日报 / 学习月报 / 学习综述，与 prism-0420 代码/设计无直接关系
- `634f28a4`：hotfix 心态情绪对话，非 prism-0420 技术内容
