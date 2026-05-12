# Chunk 5 Findings（2026-05-06 ~ 2026-05-08，18 sessions）

## Summary

扫描 18 sessions（0.53 MB）/ 识别 12 个 findings / 主要主题：M02-M04+M11 sprint 实施经验、设计体系时间维度升级沉淀收口、P5 audit 修复方法论、sprint runner 自动化讨论、测试 helper 提取模式

---

## Findings

### F-5.1. conftest 预查规则未立为 memory — sprint test helper reuse check

- **类型**: memory 缺失
- **来源 session**: root__09283375（M03 sprint）
- **摘要**: R1-B C1 发现 `_make_user_and_project` 在 3 个文件中重复，提取为 `conftest.py` 的 `make_project` fixture，并在 R1-B 关闸时新增"test helper 重用检查"维度。该检查规则已有双数据点（M03+M04 conftest 提取），但尚未立为独立 memory 文件。
- **关键 quote**: "R1-B C1（新增）测试辅助函数重用检查：新模块的测试中如果出现已有辅助函数的复制，必须先提取到 conftest 再继续。"
- **推荐落点**: 新建 `feedback_sprint_test_helper_reuse_check.md`
- **置信度**: 高

---

### F-5.2. 三 Agent 流水线 v2 确认 — R1=3 并行 / R2=1 合并 Opus

- **类型**: memory 升级
- **来源 session**: root__dc8ef034（M02）+ root__09283375（M03）
- **摘要**: M02 首次建立三 agent 流水线（R1=3 subagent 并行：spec+quality / reuse / quality+efficiency；R2=1 合并 Opus endpoint 精审）。M03 验证该结构稳定。三 agent pipeline 已有对应 memory，但 v2 详细分工（含 R1-A / R1-B / R2 职责表）以及"M01 因预算跳过用 self-audit 替代"决策记录尚未写入。
- **推荐落点**: 升级现有 `feedback_subagent_sprint.md` 中的 R1+R2 流水线段，补充职责列表与跳过条件
- **置信度**: 高

---

### F-5.3. docstring 不凌驾 design 表 — simplify-checklist 候选维度 17

- **类型**: KB 规则 + memory 候选
- **来源 session**: root__09283375（M03 R2-1）
- **摘要**: M03 R2-1 发现 `reorder` endpoint 在 docstring 中写了"returns NodeTreeResponse"，但接口契约表定义为 NodeListResponse。pattern 命名："docstring 单方面改契约"。已识别为 simplify-checklist 维度 17 候选，但未写入 KB 或 memory。
- **关键 quote**: "docstring 自承单方面改契约——候选 simplify-checklist 维度 17。"
- **推荐落点**: KB `设计阶段如何避免结构性漂移.md` 新增维度 17；或新建 `feedback_docstring_not_above_spec.md`
- **置信度**: 中

---

### F-5.4. NodeChildrenServiceProtocol 4-param 升级 — 5 处设计真相源回写状态待确认

- **类型**: 设计文档修复状态确认
- **来源 session**: root__f22e5bc4（M04 R1-A P1）
- **摘要**: 代码中 `NodeChildrenServiceProtocol` 已升级为 4 参数（新增 `actor_user_id`），但 R1-A 检查时发现 M03 设计 §6/§8、M06 设计 §6/§8、M07 设计 §6/§8、README R-X2 共 5 处仍为 3 参数。R1-A 评定 P1 blocking。本 session 是否已全部完成回写尚无 evidence，需自验。
- **推荐落点**: 确认并修复 `/root/workspace/projects/prism-0420/design/modules/M03/`、`M06/`、`M07/` 对应 §6 §8 及 README R-X2
- **置信度**: 高

---

### F-5.5. R-X1 orchestrator 新约束 — 子任务跳过必须 raise，completed 不允许 silent pass

- **类型**: 设计规则新增
- **来源 session**: root__4b88a9bb（M11 sprint）
- **摘要**: M11 sprint 冷启动 CSV 上传实施时，R-X1 orchestrator 模式新增约束：当子任务被跳过时（如 CSV 行已存在），orchestrator 必须 `raise` 明确异常而非静默 `pass`；completed 状态不允许 silent pass。该约束尚未写入 R-X1 正文。
- **关键 quote**: "R-X1 新发现：orchestrator 子任务跳过必须 raise + completed 不允许 silent pass。"
- **推荐落点**: `design/principles/R-X1-orchestrator.md` 或 `design/audit/m11-pilot-template-validation.md` 新增约束段
- **置信度**: 高

---

### F-5.6. M11 activity_log frontmatter dot vs underscore 不一致 — P1 已识别待修

- **类型**: 设计文档修复
- **来源 session**: root__4b88a9bb（M11 sprint P1）
- **摘要**: M11 设计文档 frontmatter 中 `produces_action_types` 字段存在 dot notation（如 `cold_start.upload`）与 underscore notation（如 `cold_start_upload`）混用，R1-A 识别为 P1。需统一为 underscore（与 activity_log 表的 `action_type` 枚举保持一致）。
- **推荐落点**: `/root/workspace/projects/prism-0420/design/modules/M11/` frontmatter 统一修复
- **置信度**: 高

---

### F-5.7. M04 db.get(DimensionType) 绕过 DimensionTypeDAO — punt pool 待修复

- **类型**: 代码质量问题（punt pool）
- **来源 session**: root__f22e5bc4（M04 R1-B B2.4, P3）
- **摘要**: M04 service 中直接使用 `db.get(DimensionType, ...)` 而非通过 `DimensionTypeDAO`，违反 DAO 封装原则。R1-B 分类为 P3（punt pool），标注 M15 sprint 前修复。尚未有 KB 或 memory 记录该 punt。
- **推荐落点**: M04 punt pool 记录（`design/modules/M04/punt-pool.md` 或 sprint 关闸文档）
- **置信度**: 中

---

### F-5.8. make_dim_type conftest 提取 — M04 sprint 前置要求

- **类型**: 代码质量问题（conftest 提取）
- **来源 session**: root__f22e5bc4（M04 R1-B B1.1 P2）
- **摘要**: M04 测试中 `make_dim_type` helper 在多个测试文件中重复定义，R1-B B1.1 识别为 P2，要求提取到 `conftest.py`。属于 F-5.1 规则的应用实例，但具体修复状态未 evidence。
- **推荐落点**: M04 conftest 更新确认；可与 F-5.1 memory 关联
- **置信度**: 中

---

### F-5.9. Sprint runner 硬中断判准 — 4 类中断设计值得沉淀

- **类型**: 方法论沉淀
- **来源 session**: root__be0bdb5d（sprint runner 讨论）
- **摘要**: CY 询问能否将整个开发流程自动化。讨论确立 4 类不可越过的硬中断：(1) 设计契约不确定；(2) 外部依赖阻塞；(3) P0 bug 需人工判断；(4) 资源/成本超阈值。最终选 Pack 2（contracts §2 + structural-audit.sh）。该判准与现有 sprint 关闸规则互补，但未写入 KB。
- **推荐落点**: KB `sprint-runner-interrupt-criteria.md` 或 `feedback_subagent_sprint.md` 新增硬中断段
- **置信度**: 中

---

### F-5.10. 工业级 harness 研究 — Kiro / Cursor .mdc / Meta-Policy Reflexion

- **类型**: 研究 ingest（KB 入库候选）
- **来源 session**: root__be0bdb5d
- **摘要**: CY 要求搜索成熟 harness/vibe-coding 项目。研究了 AWS Kiro（spec-driven AI IDE，类似 Cursor + waterfall 闸门）、Cursor .mdc rules（frontmatter layer 标注 L1/L2/L3）、Meta-Policy Reflexion（错误→reflection→规则更新循环）。三者精华已有口头分析，但未走 6 步 KB ingest workflow 落盘。
- **关键 quote**: "Kiro + Cursor + Meta-Policy 三家精华"——对应 `feedback_research_ingest_workflow` 要求的 KB ingest
- **推荐落点**: KB `10-项目/Prism/研究参考/harness-vibe-coding-research.md`；或 `80-学习地图/` 下
- **置信度**: 中

---

### F-5.11. R4-3a 非常规态登记规约 — 工业级对比研究沉淀确认

- **类型**: KB 沉淀确认
- **来源 session**: root__833e89f7
- **摘要**: P5 audit 建立了 R4-3a（异常状态独立注册表规则），并与 K8s、Temporal、Step Functions、Stripe、Shopify、UML PSSM 进行了工业级对比。对比结论已有分析，但是否已写入 `设计阶段如何避免结构性漂移.md` §10 及 R4-3a 规则文件中需确认。4 个模块（M01/M16/M17/M18）的补丁状态也需确认 evidence。
- **推荐落点**: 确认 `/root/workspace/projects/prism-0420/design/` 中 R4-3a 规则文件 + `设计阶段如何避免结构性漂移.md` §10 已落盘；工业对比可补入 KB 研究参考
- **置信度**: 中

---

### F-5.12. Cursor .mdc `layer:` frontmatter 建议 — design 文件 AI 规则派生标注

- **类型**: 工程改进建议
- **来源 session**: root__be0bdb5d
- **摘要**: 研究 Cursor .mdc rules 时发现其 frontmatter 支持 `layer: L1|L2|L3` 标注，可明确告知 AI 当前规则属于哪个设计层级，避免 AI 错误派生或越层覆盖。Prism 设计文件目前无此标注。属于低优先级改进，但若实施可增强 sprint runner 的规则识别精度。
- **推荐落点**: `design/principles/` 文件加 `layer:` frontmatter；或记入 `feedback_design_system_audit.md` 作为 scaffold 改进项
- **置信度**: 低

---

## 未扫描 / 低优先级跳过

| session | 大小 | 跳过原因 |
|---|---|---|
| root__22caaebb | 7.6KB, 27 msgs | 小 session，内容已被大 session 覆盖 |
| root__64869523 | 7.1KB, 2 msgs | 极短，可能为收口/handoff |
| root__2d88c327 | 6.0KB, 2 msgs | 极短 |
| root__a8dc0aa6 | 4.9KB, 3 msgs | 2026-05-06，早期，极短 |
| root__10d25239 | 14.8KB, 14 msgs | 中等，与主要 sprint session 内容重叠度高 |
| root__21945aa6 | 9.7KB, 9 msgs | 小 session |
| root__9ca526c4 | 8.6KB, 9 msgs | 小 session |
| root__bb6626fa | 8.4KB, 2 msgs | 极短 |
| root__9638b21b | 21.0KB, 50 msgs | 内容已在并行 agent 扫描中覆盖 |

> 注：以上 session 中若有漏网 finding，建议在 chunk 5 review 时补扫。
