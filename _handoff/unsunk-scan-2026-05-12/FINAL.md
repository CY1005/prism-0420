# prism0420 未沉淀内容扫描 — 最终报告

> 扫描：140 session 精华（4/23 - 5/12）× 8 个 Sonnet subagent 并行 → 95 raw findings → 合并去重后 78 条
> 已剔除：subagent transcript、非 prism 内容、已确认沉淀的执行细节
> 生成时间：2026-05-12

---

## 阅读方式

按"沉淀去向"聚合（不按时间），每条 1 行：`P级 | 置信度 | 标题 | 来源 chunk-编号`。

- **P1**：高价值方法论 / 跨 session 反复出现 / 安全或正确性关键 → 建议本周内沉淀
- **P2**：中价值，本月内沉淀
- **P3**：低价值，可以只标记不落盘
- **置信度**：高=对话里看得很清楚 | 中=可能已部分覆盖需自验 | 低=可能误判

---

## A. design/adr/（新建 ADR 候选）

| P | 置信 | 标题 | 来源 |
|---|------|------|------|
| P1 | 高 | **ADR-006 LLM provider 不引 anthropic SDK，用 httpx 直解析 SSE**（M13 拍定但无 ADR 级记录） | C6-F5 |
| P1 | 高 | **ADR-004 §P2 internal_token = 全域 root 风险**：泄露=系统沦陷，无二次防线，需补"已知风险+缓解"段 | C1-F1 |
| P2 | 高 | **ADR 写法红线**：M20 ADR-005 supersede 只写"命名"实际改了 INT→UUID+FK+rename 三件事 → ADR 描述必须覆盖全部实质改动 | C2-F3 |
| P2 | 中 | **HARD-GATE 规则演进时 pilot 更新策略**：accepted pilot 不改 + 规则进化导致接口空洞冲突时如何破例 | C1-F4 |
| P2 | 中 | **M18 OpenAI api_key 走 env vs M13 走 ProjectSettings AES 解密路径不统一** → 需对齐到统一 key 管理范式（R1-C 标 P1，sprint 末是否对齐需自验） | C6-F14 |
| P2 | 中 | **产品定位"方法≠产品"**：mythic 老师误读"规范开发流程产品"暴露 prism-0420 设计文档以方法盖过产品本身 → 立 `product-positioning-principle.md` | C3-F1 |

## B. design/audit/lessons-learned.md（密集补丁）

| P | 置信 | 标题 | 来源 |
|---|------|------|------|
| P1 | 高 | **闸门 2.5 三栏分类自审仪式化失效**：M05 sprint 把 5 个机械应用项误归 B 栏 → 必先 grep 既有规则 | C6-F1 |
| P1 | 高 | **跨 sprint baseline-patch 反向修复工序**（M14 action_type 命名漂移 → M15 reconcile 自决回写 5+7+1 处） | C6-F10 |
| P1 | 高 | **reconcile 工作量必 grep 真实代码**：M16 估 14 处实际 31 处（2×偏差，触发 `feedback_decision_codefirst_validation` 场景） | C6-F11 |
| P2 | 高 | **LLM 集成首发 R1-A P1 数量基线高 3-5 倍**：M13 sprint R1-A 5 P1 vs M02-M12 基线 0-2 P1 | C6-F7 |
| P2 | 高 | **service docstring 事务边界声明 vs 实装漂移**：M02-M05 同款（doc 写 `db.begin()` 实装由 router 管）→ sprint 末顺修 | C6-F3 |
| P2 | 高 | **IntegrityError 注释可以抄但模式不能省**：M05 立规约束名区分，M06 copy 注释但漏实现 → 范式复制陷阱 | C6-F4 |
| P2 | 高 | **PATCH endpoint 禁 `v is not None` 过滤**：M14 update_news 用 None 过滤 → summary=None 想清空被静默丢弃 → 用 `exclude_unset` 区分未传 vs 置空 | C6-F8 |
| P2 | 高 | **design §6 R-X3 对外契约修改必同步 sprint 末 design 回写**：M05 §6 ASC vs §9 DESC vs 实装 DESC 三处不一致 | C6-F2 |
| P2 | 高 | **M13 reviewer 驳回范式**：主对话读 M15 §5 反证 + verify agent 独立确认（reviewer 不必盲从） | C1-F11 |
| P2 | 高 | **§12B BackgroundTasks fire-and-forget audit 4 火坑**：幂等约束矛盾 / content dict / 心智错 / 跨 project 越权 | C2-F14 |
| P2 | 高 | **asyncpg + create_savepoint 测试架构约束**：compensation_session 必 monkeypatch 不能构造独立连接 | C6-F12 |
| P2 | 中 | **M17 partial_failed 状态不可达**：design §10 写了但实装 all-or-nothing → 加 `[v1 unreachable]` 注脚 | C6-F13 |
| P2 | 中 | **M20 删 team 强 vs 移成员软的哲学不对称**（移成员副作用实际更严重但更宽松）→ 可逆性+安全哲学权衡框架 | C2-F4 |
| P2 | 中 | **handoff 跨 session 可见性盲区**：提示词只活在对话 history 冷启动 Claude 看不到 → 必落盘 _handoff/ | C4-F1 |
| P3 | 中 | **current-Prism.md 状态滞后**（Phase 2.0 25% 实际 100%）作为 status 字面化案例 | C4-F8 |

## C. AIQE KB Prism/（10-项目层）

| P | 置信 | 路径建议 | 标题 | 来源 |
|---|------|---------|------|------|
| P1 | 高 | `02-Bug与审计/` | **Phase 3 STAR 数据**：设计前置 -39% fix commits / -43% 时间（跳槽代表作核心量化点） | C8-F4 |
| P1 | 高 | `02-Bug与审计/` | **CI 4 连坑 "spec→impl drift"**（P420-001~004：pytest-cov 缺、pnpm-workspace 缺 packages、死 import、APP_ENV）已 v1 bugs/INDEX 有但 AIQE KB 无 | C8-F5 |
| P1 | 高 | `02-Bug与审计/` | **远程访问 6 项关闸 checklist**（127.0.0.1 / 同源 / Next rewrites / cookie secure 白名单 / SYSTEM_USER 排除 / happy path）已 memory 有但 KB 无 | C8-F1 |
| P1 | 高 | `05-测试体系/`（新建） | **dogfooding 5 阶段 + 6 智能体 + T1-T6 接口契约**（P1=21/21 模块 2327 testpoint $23），_handoff/ 有但未通用化 | C8-F7 |
| P2 | 高 | `02-Bug与审计/` | **Newspy 白盒 bug #6**：pub_time 解析失败 → NaN<cutoff=false → credit 漏斗 + cursor 不推进（whitebox-testpoints 首次实战案例） | C2-F5 |
| P2 | 高 | `02-Bug与审计/` | **OpenClaw GTD 进度统计 9 结构性缺陷** P1-P9（CY 要求先 bug 单 session 截断未完成） | C1-F7 |
| P2 | 高 | `00-需求与决策/` | **30min 核心评审包 + 2h 扩展包**（mythic 老师 onboarding 路径）—— 复用资产 | C3-F3 |
| P2 | 中 | `01-实现/` | **产品工作台精确定义**："3 件事：沉淀+评价+生成测试 / 以功能模块为中心而非文档目录" | C3-F2 |
| P2 | 中 | `01-实现/VibeCoding 或新文件` | **weekly-report 16× context 超时根因 + 调优范式**（300→600 + chat_history 3 天/15 条） | C1-F8 |
| P2 | 中 | `02-Bug与审计/` | **dogfooding "create project → redirect login" bug**（CY 在 cloudflare tunnel 验证段发现，未 RCA） | C8-F11 |
| P2 | 中 | `_MOC.md` 反向引用 | **两篇结构性方法论文章**（"找结构性问题" + "避免设计阶段漂移"已在 50-工具与方法论 但 Prism MOC 无指针） | C4-F5 |
| P2 | 中 | `_MOC.md` 或新文件 | **P1 testpoint 5 大跨模块元发现**：R-X3 第三方实体真注入 / viewer 写端点 403 / 跨项目 422 / db.begin 主纪律 / escalation surface ≥100 | C8-F8 |
| P3 | 高 | `02-Bug与审计/` | **CI cookie secure 白名单范式**：`==production` 而非 `!=local`（避免新 env 名落黑名单陷阱） | C8-F6 |
| P3 | 中 | 通用工程 KB | **pre-commit + git mv stash bug**（memory 已有 §6，AIQE KB 通用层无） | C8-F9 |

## D. feedback memory（候选新建 / 升级）

| P | 置信 | 操作 | 标题 | 来源 |
|---|------|------|------|------|
| P1 | 高 | 新建 `feedback_implementation_activation.md` | **预防性代码 4 步判断框架**（Q1 决策 vs 实施 / Q2 有真 consumer / Q3 反暴露漏洞 / Q4 触发条件字面化），ci.yml + embedding_backfill + e2e skeleton 实证 ~560 行删除 | C7-F9 |
| P1 | 高 | 升级 `feedback_memory_lifecycle.md` | **SNR 崩塌 5 机制**：context dilution / SSoT 碎片 / sink 无人读 / trigger 碰撞 / MEMORY.md 降级（5/9 重塑日志仅一句话覆盖） | C7-F3 |
| P1 | 高 | 升级 `feedback_decision_layering.md` | **矛盾根源诊断 = 原则未分上下层**：A/B 让 CY 拍的元根因，CY 两次"哪个原则上层"提问提炼 | C7-F8 |
| P1 | 高 | 升级 `feedback_subagent_sprint.md` | **三 Agent 流水线 v2 详细分工**（R1-A spec+quality / R1-B reuse / R1-C quality+efficiency / R2 合并 Opus），M01 跳过 self-audit 替代决策 | C5-F2 |
| P2 | 高 | 新建 | **conftest test helper 重用检查**（M03+M04 双数据点，R1-B C1 已用） | C5-F1 |
| P2 | 高 | 升级 `feedback_subagent_sprint.md` §R1 清单 | **R-X3 service 层禁 db.rollback()**（M20 R1 抓 update_team 违规） | C7-F7 |
| P2 | 高 | 升级 `feedback_decision_codefirst_validation.md` | **TS 错误估算必先 `tsc --noEmit \| sort \| uniq -c` 分类**（workspace.tsx 10× 偏差实证） | C8-F12 |
| P2 | 高 | 升级 `feedback_external_behavior_lookup.md` | **GitHub fine-grained PAT 不能访问 collaborator 私有 repo**（必 classic token / OAuth） | C1-F12 |
| P2 | 高 | 升级 `feedback_external_behavior_lookup.md` | **WebSearch URL 验证：音视频/Podcast 必 WebFetch dual-source 交叉验证** | C7-F13 |
| P2 | 高 | 升级 `feedback_gtd_workflow.md` 或 cron 附录 | **Linux cron OR 语义陷阱**：`0 10 1-7 * 1` = day-of-month(1-7) OR day-of-week(Mon)，非"每月第一个周一" | C7-F6 |
| P2 | 中 | 新建 | **Sprint runner 硬中断 4 类**：契约不确定 / 外部依赖阻塞 / P0 需人判 / 资源超阈 | C5-F9 |
| P2 | 中 | 升级 `feedback_gtd_workflow.md` SSoT 段 | **current-*.md 退化为只读渲染视图**（v2-active / current / 本周承诺三角 SSoT 失效根因） | C7-F5 |
| P2 | 中 | 新建 `reference_ai_shared_rules.md` | **AI shared-rules 仓 + symlink 双 AI 协作机制**（Claude+Codex 51 规则迁仓，含两仓隐私边界 + Codex 不支持 @import 坑） | C2-F9 |
| P2 | 中 | 合并到上条 | **feedback_kiko_mode.md 被 Codex 读写隐私风险**（单一权威源 + AGENTS.md 只留指针原则） | C2-F10 |
| P2 | 中 | 升级 `feedback_mirror_style.md` | **真镜子操作锚点**：先查 emotion repo / "站住命名" / 反射 CY 历史高质量判断（不生成新概念） | C7-F4 |
| P3 | 中 | 决定是否新建 | **AI 启动提示词不入 repo**（旧 feedback_prompts_not_in_repo.md 是否被 5/9 重塑删了需自验） | C1-F13 |

## E. project_/reference_ memory & 长期资产

| P | 置信 | 操作 | 标题 | 来源 |
|---|------|------|------|------|
| P2 | 高 | 升级 `project_prism_0420_sprint.md` | **Mentor MVP 后双向承诺**（CY 主动看 Mentor screenshare + 展 MVP 给 Mentor），sprint 文件有时间无承诺登记 | C3-F4 |
| P2 | 高 | 升级 `project_prism_0420_sprint.md` 或 phase-gate | **"MVP 跑通"无可验证标准 → 无限期推迟风险**（Happy Path 定义缺口） | C3-F5 |
| P2 | 中 | 升级 `reference_openclaw_file_deps.md` | **KB 路径迁移风险**：message_router.py 34 处硬编码 → 四阶段迁移策略（抽常量 / softlink / 搬迁 / 清理） | C2-F8 |
| P2 | 中 | 升级 `project_router_v3_agent.md` | **TG push model context 截断 = v3 切 pull 的核心动机**（PRISM 状态被报"未启动"实际 Phase 1 ✅） | C4-F3 |
| P2 | 中 | 升级 `project_career_2026q4_jump.md` | **PRISM = A 档唯一代表作（A/B/C 推理）**："5 年后让你值钱的不是 6 件做一点是 1-2 件深度" | C3-F6 |
| P3 | 中 | 待定 | **北极星超前陷阱**：PRISM 超前 22 天 Phase 2.3 done，但 Phase 3 0% / LC+录音+Eval 副线全 0 | C7-F12 |

## F. 已沉淀但状态需自验（不动作 / 自验确认）

| 检查 | 怎么验 | 来源 |
|------|--------|------|
| `feedback_prompts_not_in_repo.md` 是否在 5/9 重塑被删 | `ls /root/.claude/projects/-root/memory/feedback_prompts_not_in_repo.md` | C1-F13 |
| `feedback_prism_behavior_observation.md` 是否含 γ 观察禁区约束 | grep "观察期" + "禁区" | C1-F9 |
| `Claude-Thinking-Effort-Token消耗分析.md` 是否已 commit+push | `cd ~/workspace/projects/ai-quality-engineering && git log --all -- "**/Claude-Thinking-Effort*"` | C1-F14 |
| NodeChildrenServiceProtocol 4-param 5 处回写（M03/M06/M07 各 §6 §8 + README R-X2） | grep `actor_user_id` | C5-F4 |
| R-X1 orchestrator raise 约束是否进 R-X1 正文 | Read `design/principles/R-X1-orchestrator.md` | C5-F5 |
| M11 frontmatter dot/underscore 是否统一为 underscore | grep `produces_action_types` 在 M11 design | C5-F6 |
| M04 db.get(DimensionType) punt 是否登记 | Read `design/02-modules/M04/`punt 区 | C5-F7 |
| R4-3a 工业对比 + M01/M16/M17/M18 补丁状态 | grep R4-3a in design | C5-F11 |
| M18 OpenAI api_key 子片 4/5 是否对齐到 ProjectSettings AES | Read M18 sprint 末 design | C6-F14 |
| F-OPT-001~003 Prism 产品知识 lifecycle 是否已落地 | Read prism-0420 design 或 _handoff | C8-F10 |
| OpenClaw memory 边界协议（TG `HOME=/home/openclaw` 不读 root memory） | Read reference_openclaw_file_deps.md | C4-F7 |

## G. 跨 chunk 累积观察（系统性而非单点）

1. **关闸盲区系列**：#1=phase 完成时迁移完整性未验 / #2=前端继承无 `tsc=0` 硬指标 → phase-gate.md 应显式列出（C8 附）
2. **元发现 #7 立规即犯**：`feedback_decision_codefirst_validation` 建立当天被违反 3 次 → 规则需"强制工具拦截"而非"意识提醒"（C8 附）
3. **baseline-patch punt 池**在 M02/M03/M04/M07 命中 → 系统性技术债，需独立 sprint 而非分散 punt（C8 附）
4. **PRISM 超前陷阱**：造好车但没拍数据，对外可展示成果 = 0，对跳槽贡献接近 0（C7-F12）

---

## 数字总览

- 95 raw → 78 去重后 finding
- 按目标分布：design/adr 6 / lessons-learned 15 / AIQE KB 14 / feedback memory 16 / project+reference memory 6 / 自验 11
- **P1 共 12 条**（建议本周内处理）
- P2 共 50 条 / P3 共 7 条 / 自验 11 条

## 建议下一步

不要试图一口气全部沉淀（会触发 SNR 崩塌反作用）。可以这样切：

1. **本会话或下次会话**：把 P1 的 12 条 + A 段 6 条 ADR 候选 sink 掉（约 1-2h，~$3 cost）
2. **本周内一个 sprint**：把 B 段 lessons-learned 15 条聚合一次性写入（这些密度高、互相印证）
3. **后续按需**：feedback memory 升级零散做（每条 5-10min）
4. **自验区**：找一个空 session 用 grep 批跑确认即可

raw findings 文件在 `/tmp/prism-findings/chunk_{1-8}.md`，本报告在 `/tmp/prism-findings/FINAL.md`。

---

## F.1 路 2 自验结果（2026-05-12 跑完 / cost ~$0.3 / 11 项）

> grep / ls / Read 一行命令确认现状，不需要 subagent。

| # | 检查 | 结果 | 证据 | 后续动作 |
|---|---|---|---|---|
| F1 | `feedback_prompts_not_in_repo.md` 5/9 重塑没删 | ✅ | 5/12 21:35 在 memory 目录 | — |
| F2 | `feedback_prism_behavior_observation.md` 观察期+禁区 | ✅ | L26-37 完整 | — |
| F3 | `Claude-Thinking-Effort-Token消耗分析.md` commit+push | ✅ | auto-sync 4/27 在 `30-技术-自学/AI工具链/Claude生态/` | — |
| F4 | NodeChildrenServiceProtocol 4-param 5 处回写 | ✅ | M03 §6 §8 + M06 §6 §8 + M07 §6 §8 + README R-X2 全到位 | — |
| F5 | R-X1 orchestrator raise 约束 | ✅ | 在 `design/02-modules/README.md` L330（注：`design/principles/` 目录不存在，R-X1 子条款挂 README）| — |
| F6 | M11 produces_action_types underscore 统一 | ✅ | `cold_start_create / cold_start_completed / cold_start_failed` | — |
| F7 | M04 `db.get(DimensionType)` punt 是否登记 | ❌ | M04 design 找不到此 punt；有其他 punt（R1-A A4/A5、enqueue B 推迟）但缺此条 | **升 P1 路 1** |
| F8 | R4-3a M01/M16/M17/M18 补丁 | ✅ | 4 模块全有"非常规态登记表（R4-3a）" + reserved/transient/pseudo-terminal since v1 | — |
| F9 | M18 OpenAI api_key 对齐 ProjectSettings AES | ❌ | M18 只把 OpenAI 当 provider，缺 api_key 来源 vs M13 AES 解密路径对齐 | **升 P1 路 1（原 C6-F14 P2 升 P1）** |
| F10 | F-OPT-001~003 Prism 产品知识 lifecycle | ❌（预期）| punt-pool L655-661 明确"未落地"，约定 dogfooding sprint 后实施 | 按原计划 punt |
| F11 | OpenClaw memory 边界协议 (TG HOME=/home/openclaw) | ✅ | `reference_openclaw_file_deps.md` L36 已落地（2026-05-06）| — |

### 路 1 待沉淀清单新增（路 2 自验产出）

原 P1 共 12 条 → **现 14 条**（+F7 新增 + F9 从 C6-F14 P2 升 P1）：

| # | P | 待沉淀内容 | 来源 |
|---|---|---|---|
| **路 1-13** | P1 | **M04 `db.get(DimensionType)` punt 漏登/失踪**：需 fact-finding 确认 punt 是否被实施未标 / 真漏 / 应在哪个 audit 文件登记 | F7 自验 |
| **路 1-14** | P1 | **M18 OpenAI api_key vs M13 ProjectSettings AES 解密路径对齐**（原 C6-F14 升级）：决策 key 来源统一管理范式 → ADR-006 候选段 / 或 M18/M13 design 加 cross-ref | F9 自验 |

### 路 2 闸门

- ✅ 8 项确认已沉淀（可消掉，不动作）
- ❌ 1 项预期 punt（F10，dogfooding sprint 后处理）
- ❌ 2 项升路 1 真漏洞（F7 + F9）

路 2 状态：**DONE**。下一步路 1 / 路 3 / 路 4 按原计划。
