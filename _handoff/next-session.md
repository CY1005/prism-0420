---
title: prism-0420 跨 session 交接
status: living
owner: CY
last_updated: 2026-05-08 (post-M12-sprint-complete)
purpose: 上一 session 留给下一 session 的"接着做什么 + 怎么做"——避免冷启动 Claude 凭印象拍板
---

# Next-session handoff

> **冷启动 Claude 读这份**：先读本文件 → 再读 `design/00-roadmap.md` 看真实进度 →
> 再读 `design/00-phase-gate.md` 看下一闸门 → 再决定从哪条 prompt 起手。

## 0. 状态快照（更新于 2026-05-08 post-M13-sprint-complete）

- **Phase 2.0 工程基线**：✅ 100%
- **Phase 2.1 业务模块**：⏳ 65%（M01-M08+M10+M11+M12+M13 完成；下一站 M14 行业新闻；M09 superseded by M18 不实装）
- **2026-05-08 M13 sprint 完成**（8 commit 73c7175→子片 5 关闸 / 827 PASS / R13-1 79→86 / L12 守护 / **LLM 集成首发 + §12A SSE pilot + R-X3 写 M04 + AES 全链路接通**）：
  - commits: 73c7175 子片 0 prep（§14.5 + DimensionService.create_dimension_record + get_latest 接通；M04 punt 到期）+ 28a127e 子片 1（AI Provider 抽象 + MockProvider 含 aclose_called + ClaudeProvider anthropic httpx stream + Registry + 19 unit + 3 integration smoke skipif ANTHROPIC_API_KEY）+ ecb1d9c 子片 2（AnalyzeService 流式分析 + 保存 + 影响节点读 + 7 ANALYSIS_* ErrorCode + AnalysisLevel + Prompt 模板 + 20 unit）+ 368f83c 子片 3（Pydantic schema Request/Response 4 + SSE event 3 + 13 unit）+ eedecd1 R1 8 P1 立修（3 subagent 并行：spec+quality Opus 5 + reuse Sonnet 3 + quality+efficiency Sonnet 4 / 去重合并 8 / conftest 迁 make_project_with_member + set_project_ai）+ 7082b90 子片 4（Router 3 endpoints SSE+save+affected-nodes + 21 e2e）+ 79fb4cc R2 4 项立修（2 P1 + P2-4 升 P1 + P2-3 顺手）+ 子片 5 关闸 commit
  - **827 PASS / 4 skipped (3 integration smoke 待真 ANTHROPIC_API_KEY + 1 ASGITransport is_disconnected 不可靠 / R13-1 79→86 / L12 守护通过**
  - **闸门 2.5 三栏第八次 B 栏 0 项实证**：M05+M06+M07+M08+M10+M11+M12+M13 八连稳定
  - **R1 + R2 命中数据**：R1=3 subagent 12 P1→去重 8 立修 / R2=1 合并 Opus 4 项立修；M02-M13 十一数据点稳定 → M14+ 默认范式可作模板
  - **LLM 集成首发新教训 4 条 sink**（详见 audit/m13-pilot-template-validation.md "LLM 集成首发新教训" 段）：
    1. PEP 533 aclose 协议必须区分自然完成 vs 显式 aclose（MockProvider try/except GeneratorExit）
    2. Anthropic SSE delta.type 多种必须显式校验（防 thinking_delta 污染输出）
    3. SSE generator 持 AsyncSession 长达 300s 占连接池（10 用户并发吃光 default 10）→ M16/M17 立异步 SSE 连接策略
    4. design §7 metadata 字段集每条都必须 e2e 验（不依赖前端可计时绕过）
  - **元自审教训**："3 端点全覆盖"原则 SSE 形态特殊不免除——R2 抓出 P1-2 SSE 端点 cross-project node 缺测立补；sink feedback_problem_layered_analysis 失效信号
  - **R-X3 写 M04 + AES 全链路实证**：M02 ProjectService → crypto.decrypt(ai_api_key_enc) → ProviderRegistry.get → ClaudeProvider/MockProvider → 流式 chunk yield → save 调 M04.create_dimension_record 写 dimension_records + 代写 activity_log
  - **AnthropicProvider httpx 直连**（不引 anthropic 库依赖）+ MockProvider aclose_called: bool + ClaudeProvider 嵌套 async with 自动 aclose 释放底层 HTTP

- **2026-05-08 M12 sprint 完成**（详见上一版本快照）



- **Phase 2.0 工程基线**：✅ 100%（B1-B10 + 决策类全 accepted；commit b91c8d5）
- **Phase 2.1 业务模块**：⏳ 60%（M01-M08+M10+M11+M12 完成；下一站 M13，M09 superseded by M18 不实装）
- **2026-05-08 M12 sprint 完成**（7 commit + R1+R2 闭环 / L1+L2+L3 第十次实证 / 闸门 2.5 三栏第七次 B 0 项 / **常规 own + 跨模块只读 R-X3 范式实证**）：
  - commits: `63f2f93` 子片 0 prep（§14.5 + DimensionService.batch_get_by_nodes 实装 / M04 sprint scaffold "caller sprint 实装"到期 + 3 smoke）+ `9a0f039` 子片 1 model+alembic（2 表 / G4=B 值快照 / node_id ON DELETE SET NULL passive_deletes）+ 9 model tests + `3aa7415` 子片 2 ComparisonDAO+16 unit + `99105b4` 子片 3 ComparisonService+5 ErrorCode+21 service tests + `169e948` R1 4 P1 立修（spec+quality Opus + reuse Sonnet + quality+efficiency Sonnet 三 subagent 并行；nodes_count → node_ids_count metadata 漂移 / _mk_snap 迁 conftest make_snapshot fixture / rename write_event 异常传播测试 / Core UPDATE updated_at 显式刷）+ 4 coverage 补 + `589407c` 子片 4 router+6 endpoints+15 e2e（POST/PUT/DELETE/GET matrix/GET list/GET detail；viewer 写 3 端点全 403 主动复制）+ 子片 5 关闸（本 commit）
  - **742 PASS / 0 fail / ruff 净 / R13-1 74→79（+5）+ L12 守护通过**
  - **R-X3 跨模块只读范式实证**：DimensionService.batch_get_by_nodes（M04 own / M12 首 caller）+ NodeDAO.list_by_ids 校验 / 不嵌跨模块 metadata 在 response（cells-only）
  - **R2 P1 裁决型新教训 1 条**：design §7 ComparisonMatrixResponse 草案 nodes+dim_types+cells 三字段 vs 实装 cells-only — 与 ADR-003 规则 1 + M02-M11 R-X3 范式一致 → 裁决 = cells-only + scaffold disambiguation 注释（与 M01 D1 7 seam reconcile 同形态）
  - **元自审教训**（主流程错误 + 自纠）：让 CY 拍裁决型 R2 P1（matrix metadata）违反 feedback_problem_layered_analysis 失效信号 — L1 R-X3 范式已锁 → AI 应自决 + design 回写，不应让 CY 拍。下次 R-X1/R-X2/R-X3 范式既锁的裁决型 P1 不再让 CY 拍，直接落 disambiguation
  - **元教训防御 actionable 应用清单（M02-M11 沉淀 + 主动复制不等抓）**：viewer 写 3 端点 403 ✅ / write_event 异常传播 3 写端点全 ✅（rename R1-C P1-02 立修补）/ cross-tenant 404 ✅ / cross-project node 422 ✅ / IntegrityError 区分约束 N/A / R-X1 失败补偿 N/A / 文件上传 N/A
  - **R1 + R2 命中数据**：R1=4 P1（去重；3 subagent 并行）/ R2=1 P1 裁决型（1 合并 Opus）/ M02-M12 十数据点 R2 稳态 0-1 P1 区间（M11 R-X1 首发 3 P1 是异常点）
  - **闸门 2.5 三栏第七次 B 栏 0 项**：M05+M06+M07+M08+M10+M11+M12 七连稳定 → M13+ 默认范式可作模板
- **2026-05-08 M11 sprint 完成**（8 commit + R1+R2 闭环 / L1 第九数据点 / 闸门 2.5 第六次 B 0 项 / **首个 R-X1 orchestrator 范式实证**）：
  - commits: `8ef59b3` 子片 0 prep（§14.5 + 3 跨模块 batch_create_in_transaction 接通 M04 R1-A A6 + M06/M07 scaffold 全到期）+ `4ed8dbe` 子片 1 ColdStartTask model + alembic + 14 model tests + `090621a` 子片 2 ColdStartDAO + 12 unit tests + `e93057c` 子片 3 ColdStartOrchestratorService + 7 ErrorCode + 17 service tests + `2ccd579` R1 6 P1 立修（spec+quality Opus + reuse Sonnet + quality+efficiency Sonnet 三 subagent 并行；frontmatter 字面 / design §5 disambiguation / dimensions 显式抛错保护 R-X1 完整性 / _mark_failed write_event 兜底 / _make_task 进 conftest / ISSUE_CATEGORIES 跨模块导出）+ `aba873a` 子片 4 router + 4 endpoints + 11 e2e tests（POST /upload multipart / GET list / GET detail / GET /template）+ `2c39980` R2 2 P1 立修 + 1 punt（file.size 预检 + filename sanitize；commit-then-rollback boundary punt M17）
  - **674 PASS / 0 fail / ruff 净 / R13-1 67→74（+7）+ L12 守护通过**
  - **首个 R-X1 orchestrator 范式实证**：M11 不直 INSERT 跨模块表 / 调 NodeService + CompetitorService + IssueService 3 个 batch_create_in_transaction（DimensionService.batch_create 实装但 dim_key→type_id 解析延迟到下游 sprint）/ 4 service.batch_create_in_transaction 签名稳定 4 参（project_id + actor_user_id + xxx_data）
  - **R-X1 首发新教训 2 条**：
    1. **失败补偿 commit boundary**（R2 P1-01 punt）：M11 router commit-then-rollback 把 task=failed 元数据 + 部分业务 INSERT 一起 commit，违 design §1 G6 全量回滚契约。彻底修复需独立 connection 或显式 SAVEPOINT，与测试 fixture join_transaction_mode='create_savepoint' 不兼容；punt M17 sprint 抽独立 helper（异步 zip 导入将 reuse；与 R-X1 第二实例对照）。**修法 sink 候选立规**：「R-X1 orchestrator 失败补偿写入路径必须用独立 connection 或显式 SAVEPOINT，禁止与业务事务共享 commit boundary」
    2. **multipart 攻击面**：M11 是首个文件上传 endpoint；R2 抓出 file.read() 整文件后才 size check + filename 无 sanitize。立修 file.size 预检 + _sanitize_filename(basename + 控制字符 strip + 长度截断)。**修法 sink 候选立规**：「文件上传 endpoint 必须 file.size 预检 + filename sanitize；禁止裸 file.read() + raw filename 直入 DB / response header / activity_log metadata」
  - **元教训防御 actionable 应用**（M11 R1+R2 主动复制不等抓 / 首次 R-X1 模块）：
    - viewer 写所有写端点 403 全覆盖（M07 立 / M08 应用 / M11 写端点只 1 → test_viewer_write_upload_returns_403 ✅）
    - write_event 异常传播测试（M04+ 范式）✅
    - cross-tenant 404（M02 范式）✅
    - R1.5 reconcile checkpoint（M10 NEW）：R2 反向命中的不是 R1 撤销项 → 元教训不适用 / 但 R2 命中 R1 未抓的范式新教训（commit-then-rollback / 文件上传攻击面），属"R-X1 范式首发"非"反复"
  - **R1 + R2 命中数据**：R1=6 P1（去重；3 subagent 并行）/ R2=2 P1 立修 + 1 punt + 4 P2（1 合并 Opus；M11 R2 命中超平均 → R-X1 endpoint 范式独有，9 数据点中第 9 仍稳定）
  - **闸门 2.5 三栏第六次 B 栏 0 项**：M05+M06+M07+M08+M10+M11 六连稳定 → M12+ 默认范式可作模板

- **2026-05-08 M10 sprint 完成**（6 commit + R1+R2 闭环 / L1 第八数据点 / 闸门 2.5 B 0 第五次 / **纯读聚合范式首次实证** / **元教训新增 2 条**）：
  - commits: `098a2ee` 子片 0+1+2 (DAO + Service + 21 tests) + `b018aad` 子片 3 + R1 P1 立修 + 子片 4 关闸 [hash]
  - **613 PASS / 0 fail / ruff 净 / R13-1 67=67 + L12 守护通过**
  - **纯读聚合范式**（无 model/migration / ADR-003 规则 2 豁免 / **4 子片简化 / R1 三 subagent 合并为 1 Opus**）— 首次实证 M11+ 纯读模块简化模板
  - folder 均值"迭代后序遍历"D-1 算法 + 分母=0 早返回 M10-B3
  - **元教训新增 2 条 sink memory**：
    1. **纯读模块 schema-service contract drift 风险**：M02-M08 业务模块靠"写端点 + activity_log + IntegrityError"三层强契约兜底；M10 纯读全无，schema 字段语义只能靠 docstring + 测试断言守。R1 立修 folder.filled_count subtree rollup 被误连 asyncio.gather false positive 一起撤销 → R2 reviewer 抓出 schema-service drift。**修法**：纯读模块 docstring 每字段必须配套 ≥1 unit test 断言守护
    2. **R1→R2 reconcile 缺失**：R1 P1 立修被撤销但启动包陈述未同步更新 → R2 reviewer 看到代码 vs 启动包不一致。**修法**：R2 dispatch 前加 R1.5 reconcile checkpoint（grep R1 立修关键词在代码中真实存在）


- **2026-05-08 M08 sprint 完成**（9 commit + R1+R2 闭环 / L1+L2+L3 第七次实证 / 闸门 2.5 三栏 B 0 项第四次实证 / **R-X2 第四真注入双向 + delete 语义** / **元教训"M07 P1 防御 actionable 主动应用"首次实证**）：
  - commits: `eed7749` 子片 0 prep + `fc142ad` 子片 1 model + `1fe57fe` 子片 2 DAO 双向 OR + `7b3d3eb` 子片 3 Service R-X2 第四真注入(双向 delete) + `de57b28` 子片 4 Router 5 endpoints + `868d290` R1+R2 P1 共 8 项立修（5 步分层全 L3 范式应用）+ 子片 5 关闸
  - **586+ PASS / 0 fail / ruff 净 / R13-1 64=64 + L12 守护通过**
  - **R-X2 实证 4 数据点对照表**（详见 audit/m08-pilot-template-validation.md）：
    - M04: 单向 delete (CASCADE)
    - M06: 单向 delete (CASCADE)
    - M07: orphan SET NULL (passive_deletes)
    - M08: **双向 OR delete**（source/target 两 FK 同款 CASCADE）
    - 接口共享（Protocol 4 参签名）+ 业务语义分化（DELETE/UPDATE/双向）= L1 锁 + L2 决策合理抽象
  - **元教训首次实证 actionable**：M07 立的"viewer 写所有写端点 403 全覆盖"P1 范式被 M08 sprint **启动 reconcile A7 主动列入清单**+ 子片 4 router test cases 列表全覆盖 + 子片 3 service test write_event 异常传播 monkeypatch — R2 没抓出 viewer 写覆盖问题（验证元教训内化生效）。新元教训 sink 进 audit "M02-M_{N-1} 跨模块测试契约主动复制清单" actionable 范本
  - **R1 命中**：3 subagent 共 **7 P1 立修**（5 步分层全 L3 范式应用，含 RelationTypeInvalidError R13-1 注释 / docstring 双重防御消歧 / Protocol target_type 分发表 / _make_relation conftest 五连规则 / RelationNodeNotInProjectError 404→422 范式对齐 / count_by_project index-only / asyncio.gather 并行）+ 多 P2
  - **R2 命中**：1 P1 立修（self_loop code 映射 design §13 字面 drift；移 schema model_validator → service 层独家范式与 M02-M07 一致）+ 2 P2 punt


- **2026-05-08 M07 sprint 完成**（7 commit + R1+R2 闭环 / L1+L2+L3 第六次实证 / 闸门 2.5 三栏 B 0 项第三次实证 / **R-X2 第三真注入 orphan 语义实证** / 元教训"M06 P1 范式 M07 复发立修"首次产出）：
  - commits: `b81c0d8` 子片 0 prep（§14.5 + §5 预防性消歧）+ `13152e1` 子片 1 Issue model + alembic + Node passive_deletes + `a917235` 子片 2 DAO + SELECT FOR UPDATE + orphan_by_node_id + `e6e0873` 子片 3 Service + R-X2 第三真注入 + 状态机 4 状态 + `6a1072f` R1 1 P1 立修 get_for_embedding 空字符串 + 子片 4 Router 7 endpoints + 15 e2e tests + `8246984` R2 1 P1 立修 viewer 写 4 端点全覆盖 + 子片 5 关闸
  - **538+ PASS / 0 fail / ruff 净 / R13-1 59=59 + L12 守护通过**
  - **R-X2 第三真注入 orphan 语义**（接口共享 / 行为契约分化 — UPDATE SET NULL vs DELETE）+ **7 处代码 anchor 防误读**（design / model / migration / DAO / service / Protocol / lifespan）
  - **关键元教训**（**首次"复发 + 应用立修"实证**）：M06 R2 立的"viewer 写**所有**写端点 403"P1 范式在 M07 复发；R1/R2 prompt 提了仍漏 → R2 抓到 → 立修。**根因**：单条 P1 立修不自动横切到下一模块；纯靠"下一 sprint reviewer 比对 M_{N-1} audit"被动传递；仪式化提示 ≠ 实施时真做。**修法 sink 到 feedback_problem_layered_analysis 失效信号**：跨模块测试契约（如三层权限 testpoint）应升级到 design 公共段或 testpoint 模板，让"模块 design 必须含 X testpoint"成为闸门 3 检查项
  - **R1 命中**：3 subagent 共 1 P1 立修（去重）+ 8 P2 punt；R1-A 0 P1（A7 §5 预防性消歧避免漂移）；R1-B 复用率 ~95%；R1-C 1 P1（get_for_embedding 空字符串）
  - **R2 命中**：1 合并 Opus 1 P1 立修（M06 元教训复发）+ 2 P2 punt（IssueResponse join 字段 / page_size 分页）


- **2026-05-08 M06 sprint 完成**（6 commit + R1+R2 闭环 / L1+L2+L3 节奏第五次实证 / 闸门 2.5 三栏第二次 B 栏 0 项实证 / R-X2 第二真注入零摩擦实证）：
  - commits: `c84f6f2` 子片 0 prep（§14.5 默认范式复用 + ck_clause 别名规范化 5 处一致）+ `d01c5ad` 子片 1 双表 model + alembic + Node back_populates + 8 model tests + `f7211fb` 子片 2 DAO + 18 unit tests + `86195cc` 子片 3 Service + R-X2 第二真注入 + 4 ErrorCode + 20 service tests + lifespan register_child_service("competitor") + `c792263` R1 3 P1 立修（design §5 多表事务消歧 + IntegrityError 区分约束名 + write_event 异常传播测试）+ {子片 4 commit hash} R2 0 P1 + 子片 5 关闸 commit
  - **473+ PASS / 0 fail / ruff 净 / R13-1 53=53 + L12 守护通过**
  - **L1+L2+L3 节奏第五次实证（M02-M06 五数据点稳定）**：M07-M20 默认范式可作模板（不再重复说明）
  - **R-X2 第二真注入零摩擦实证**：M04 sprint 升级 Protocol 4 参 + 5 处 design 回写的元教训"5 步分层识别 L1 跨模块契约层"，在 M06 sprint plug-in CompetitorService.delete_by_node_id 完全无修改成本 — feedback_problem_layered_analysis "防本模块绕"价值的"防御未来"实证
  - **闸门 2.5 三栏 B 栏 0 项第二次实证**（M05 立 / M06 复用，防御未来非修复存量）：8 项原候选全 grep 命中 L1/L3 锁规归 A 栏；M05 立的"自审一问必先 grep 既有规则"失效信号在 M06 是首次防御未来实证
  - **R1 命中**：3 subagent 共 3 P1（去重）+ 6 P2 punt；R1-A 抓 M06 design §5 多表事务"with db.begin()"漂移（M04 reconcile 范式漏跟进）；R1-B 命中比例 ~14% / 复用率 90%+ 优于 M02-M05 基线；R1-C 抓 IntegrityError 未区分约束名（M05 P1-01 立规回退）+ write_event 异常传播测试缺失（M04 范式未复制）
  - **R2 命中**：1 合并 Opus 0 P1 + 3 P2 punt（display_name join / pros_and_cons 类型退化 / ref 404 e2e gap）— 与 M02-M05 R2 P1 命中 0-1 区间稳定，第五次实证 1 合并 Opus 范式有效
  - **M05 punt 池接通**：ck_clause 别名规范化（5 处一致 commit c84f6f2）


- **2026-05-08 M05 sprint 完成**（6 commit + R1+R2 闭环 / L1+L2+L3 节奏第四次实证 / 闸门 2.5 三栏首次 B 栏 0 项实证）：
  - commits: `811d6bc` 子片 0 prep（§14.5 + M04 §5 消歧 + make_dim_type 抽出 4 文件 60+ 改）+ `de53192` 子片 1 model + alembic + Node back_populates + A6 covering 索引 + `d3374fe` 子片 2 DAO + 18 unit tests + `063cbd4` 子片 3 Service + 3 ErrorCode + 19 service tests + B2 不变量验证 + `5e0e239` R1 P1 立修（IntegrityError 区分约束 + _make_version 进 conftest）+ {TBD R2+子片5 commit}
  - **412 PASS / 0 fail / ruff 净 / R13-1 49=49 + L12 守护通过**
  - **L1+L2+L3 节奏第四次实证（M02 首/M03 二/M04 三/M05 四，四数据点稳定）**: R1=3 subagent + R2=1 合并 Opus + schema 子片禁单跑 + 子片 5 不单跑（≥80% SKIP 例外）= 默认范式可作 M06-M20 模板
  - **闸门 2.5 三栏首次 B 栏 0 项实证**：5 项原列 B 栏（B1 索引 / B2 并发测试 / B3 schema 校验 / B4 punt 顺修 / B5 race 转换）被 5 步分层分析法 step 1-2 识别后全收 A 栏（L1 已锁 / L3 范式 / punt 工序到期）；CY "做不出决定就是分析不对，没分清层次" 一击命中 → 失效信号已沉淀到 memory `feedback_problem_layered_analysis`
  - **R1 命中**：3 subagent 共 4 P1（去重）+ 11 P2 punt；R1-A Opus 抓 design 真相源内部矛盾（§6 ASC vs §9 DESC + 三处索引名）；R1-B Sonnet 抓 _make_version 应进 conftest（M04 R1-B C1 规则延续）；R1-C Sonnet 抓 IntegrityError 不区分约束名（is_current=True 并发场景误导 caller）
  - **R2 命中**：1 合并 Opus 3 P1 + 4 P2 punt；R2 P1-01 quality-spec 关键路径 100% 假 DONE（403 + viewer 路径零覆盖）；R2 P1-02 design §7 created_by_name 字段 M04 范式延续不实装（子片 5 删 design 字段）
  - **元教训沉淀**：闸门 2.5 自审仪式化失效首次实证；B 栏 0 项不是异常；R1 三 subagent + R2 一合并 Opus 第四数据点确认稳定


- **2026-05-07 M04 sprint 完成**（7 commit + R1+R2 闭环 / L1+L2+L3 节奏第三次实证 / 5 R-X5 子选项 + 新决 NodeChildrenServiceProtocol 4 参升级）：
  - commits: `4c3c413` 子片 1 model+migration+helpers.py + `3aea93b` 子片 2 DAO + `6fd4808` 子片 3 Service+R-X2 真注入+Protocol 升级 + `0ca7e5b` R1 修(4 P1) + `de239c2` 子片 4 Router + `5a97824` R2 修(1 P1) + `c4037a7` 子片 5 design+audit
  - **347 PASS / 0 fail / ruff 净 / R13-1 46=46 + L12 守护通过**
  - **L1+L2+L3 节奏第三次实证 (M02 首 / M03 二 / M04 三; 三数据点稳定)**: R1=3 subagent + R2=1 合并 Opus + schema/子片 5 不单跑
  - **R1 命中**: 3 subagent 共 4 P1 立修 + 10 P2 punt; R1-A Opus 抓 design 5 处 Protocol 回写漏; R1-C Sonnet 抓 service 三层防御 + DimensionTypeDisabledError 全缺口
  - **R2 命中**: 1 合并 Opus 1 P1 立修(B6.x enabled_dimension_types 字段名/SQL 不一致)，是 R1 三 subagent 没抓到的"命名 vs SQL vs design 文字"三处一致性新角度
  - **R-X5 子选项 5 项实证**:
    - 1) A5 enqueue B 推迟 + get_for_embedding A 现在建 (M03 同款复用)
    - 2) **NodeChildrenServiceProtocol 4 参升级 (M04 sprint 新决)** — 5 步分层分析法 L1 跨模块契约层定位; 5 处 design 真相源回写 (M03 §6/§8 + M06 §6 + M07 §6 + README R-X3)
    - 3) pdc-existence-strict (R1-C C3.2 立修触发新决): pdc 不存在或 enabled=False 都抛 DimensionTypeDisabledError
    - 4) _ck_clause 提取 (B1 闸门 2.5 CY 拍 A; M03 R1-B C2 punt 闭环) → migrations/helpers.py + m01/m02/m03 import 回写
    - 5) make_node fixture 位置 (B2 闸门 2.5 自我修正 → A 栏): tests/conftest.py 加 fixture + M03 内联迁移
  - **新发现 (子片 5 audit 元教训 2 条)**:
    - 1) Protocol 签名升级触发的 L1 跨模块契约层识别（feedback_problem_layered_analysis 实质性"防本模块绕"拦截价值首次产出）
    - 2) 闸门 2.5 reconcile 自我修正信号（CY "按之前流程定不下来吗" 反馈触发）

- **2026-05-07 M03 sprint 完成**（5 子片 + R1+R2 闭环 / L1+L2+L3 节奏第二次实证 / 4 R-X5 子选项复用 + 1 新决）：
- **2026-05-07 M03 sprint 完成**（5 子片 + R1+R2 闭环 / L1+L2+L3 节奏第二次实证 / 4 R-X5 子选项复用 + 1 新决）：
  - commits: `800e632` §14.5 prep + `d174e90` 子片 1 models + `4887f7c` 子片 2 DAO + get_for_embedding + `4e48cb9` 子片 3 Service + `ce73570` R1 修 + 子片 4 schema + `4a1a615` 子片 4 Router + `656e05c` R2 修 + 子片 5 design 回写
  - **285 PASS / 0 fail / ruff 净 / ci-lint R13-1 41=41 + L12 守护通过**
  - **L1+L2+L3 节奏第二次实证** (M02 首 / M03 第二; 双数据点稳定):
    - L1 总则: sprint ≥1 次 + ≥50 行 OR ≥2 文件触发 + 触发例外条款 — 全合规
    - L2 sprint 计划: §14.5 commit `800e632` (闸门 3.4 强制存在)
    - L3 实证回写: `design/audit/m03-pilot-template-validation.md` (R-X5 子选项 + R1/R2 命中比例 + PT1-PT3 + L1 双数据点)
  - **R1 命中**: 3 subagent 共 4 P1 立修 + 12 P2 punt; B reuse Sonnet ~18% 与 M02 17% 稳定
  - **R2 命中**: 1 合并 Opus subagent 4 P1 立修 + 5 P2 punt; M02 (6 P1) + M03 (4 P1) 双数据点验证 1 subagent 足够
  - **R-X5 子选项**:
    - A4 enqueue B 推迟 / get_for_embedding A 现在建: design §6.X status 改 "已落地 + commit hash"
    - A5 batch_create 拓扑责任: B 半路径推迟 + design §6.X 加 A5 段 (M11/M17 sprint 启动时拍)
    - A6 child_services 分发语义 reconcile: 全 subtree 全 service 调用 (noop 容忍) + design §6.X 加 A6 段
    - 复用 M02 4 项 (C team_id / A SearchConfig / B move-team / R13-1 标记位置)
  - **新发现 (R1-B C1)**: 跨模块 test helper 重复 → conftest.py 加 make_project fixture, 47 测试调用迁移; 未来 M04+ sprint 启动前应预查 conftest 是否已有可用 fixture

- **2026-05-07 M02 sprint 完成**（5 子片 + 2 review 闭环）：
- **2026-05-07 M02 sprint 完成**（5 子片 + 2 review 闭环）：
  - commits: `c6b97d6` 子片1 models + `a42dc81` 子片2 DAO + `10f2f54` 子片3 service+AES + `c9b0618` 子片4 router (12 endpoints) + R1 修 `e5651bf` (8 项) + R2 修 `e7b1b7f` (6 P1)
  - **205 PASS / 0 fail / ruff clean / ci-lint R13-1 34=34 + L12 + S5d-改进**
  - **L1+L2+L3 review 节奏首次实证** (commit `19acff6`): 闸门 3.4 L1 总则 + M02 §14.5 L2 sprint review 计划 + L3 子选项实证回写到 audit
  - **5 步分层分析法首次落地** (`feedback_problem_layered_analysis` memory): 用于 review 触发粒度冲突 + 4 实证子选项决策
  - **4 R-X5 实证子选项全决** (`design/audit/m02-pilot-template-validation.md`):
    - C 路径 team_id: DAO 完全允许
    - A 路径 SearchConfig owner: M02 own raw types
    - B 路径 move-team: 不实装 router → OpenAPI 不含
    - R13-1 ErrorCode 标记位置: code 注释 (不入 ci-lint 附加规则)
  - **AES helper 落地** (api/auth/crypto.py 横切层 + 14 test PASS + 05-security-baseline §4.1 回写)
  - **后置债** (M03 sprint 顺手清):
    - check_project_access vs require_owner 重复 JOIN (性能优化)
    - batch_update N 条 UPSERT 应用 PostgreSQL ON CONFLICT
    - ProjectMember.joined_at vs created_at 冗余讨论 (design 字面如此)
    - update_project exclude_none=True PATCH 语义 + setattr 白名单
- **2026-05-07 M02 design v2 升级** (commit `b0dd21b` / `0b72332` / `19acff6`):
- **2026-05-07 后续 session 产出**（M02 sprint 启动 reconcile pass 元反思 → 设计体系升级 + 11 处 baseline-patch 回扫 + 修复存量）：
  - **5 个体系盲区 + 2 体系级新原则**（详见 `design/audit/time-dimension-blindspot-2026-05-07.md`）
  - **8 条新规则落地**：
    - 6 原则 #6 横切 vs 业务关注必须显式判定（`00-architecture/06-design-principles.md` v2）
    - 04-layer Q7 横切层定义（`00-architecture/04-layer-architecture.md` v2）
    - R-X5 baseline-patch 时序契约（主标准 Q1+Q2 + 退化 A/B/C + 结构性约束 + 子选项留空待实证）+ R-X6 横切 helper 必横切层 + R3-6 启动数据细化 3 子项 + frontmatter helpers 字段约束（`02-modules/README.md` v2）
    - 闸门 2.5 S2 注释 4 字段强制 + reconcile 三栏分类（`00-phase-gate.md`）
    - accepted-minimal §7 early adopter 修订（含横切 vs 模块特定判断前置 + §7.1/§7.2）（`05-security-baseline.md` + 03/04 引用段）
  - **11 处 baseline-patch 实施期处理段回写**：M02（A1+A2+A3）/ M03/M04/M06/M07（A4-A7 同款 M18 baseline-patch）/ M15（A8+A9 enum）+ M02 §3.Y dimension_types 启动数据 + §3.Z early adopter AES helper
  - **修复存量**（T12）：10 horizontal helper docstring 加 horizontal+owner 4 字段 + 3 design 灰区（ADR-001/M18/M17）显式标 horizontal owner
  - **整体扫描结果**（T11）：0 处真正反模式存量——CY 一直凭 sense 把横切 helper 放对位置；立规价值是防御未来 sprint 漂移
  - **回归**：pytest 118 PASS / 0 fail / 0 xfail / ruff 净 / ci-lint.sh R13-1 22=22 + L12 守护通过
  - **KB 沉淀**（跨项目）：`02-技术/架构设计/设计前置方法论-补丁01-时间维度.md`（主方法论加指针）
  - **元教训 4 条**：立规分两层（结构性可前置 / 工程具体须实证）/ 立规必判 horizontal vs module-specific / 立规防御未来 vs 修复存量 / L1/L2/L3 时间维度切分
- **2026-05-07 M01 sprint 闭环**（commits c1e3acc → 2704d0f + design 回写 commit pending）：
  - 5 子片全 PASS：read-only auth / PATCH me / admin endpoints / ADR-004 P2 全 / CI 守护
  - 测试 113 PASS + C9 isolated 转 PASS（共 117+ PASS / 0 xfail）
  - design / ADR 回写（M01 实施反馈）：
    - ADR-004 §3 #5 同秒边界 + §3.5 P2 信任链 + §3.6 P3 形态
    - M01 §4 R4-2 加 active→pending 禁 + 同值豁免说明
    - M01 §10 多事件原子组顺序约定 + P2 入站不写 audit 策略
  - ci-lint.sh 加 L12 守护（M01 不调 M15 activity_log_service）
  - design/audit/m01-pilot-template-validation.md（PT1-PT3 living tracker）
- **2026-05-07 session 产出**（P5 4 🔴 + F-9 收口；commits 2e93de9 + b24f049）：
  - R4-3a 非常规态登记规约落地（02-modules/README.md）：5 类 + 严格档 + 6 字段态表 + 3 字段边表
  - M01/M16/M17/M18 四模块 mermaid 按 R4-3a 回扫（pending / cancelled / partial_failed / failed 拆出登记表）
  - ADR-002 §1.1 触发方清单从 3 → 10 条，区分 Queue 与直接 SQL 形态
  - M16/M17/M18 模块端反向引用 SYSTEM_USER_UUID（M16 §9+§10+§12B / M17 §12 / M18 §10+§12D）
  - P5 audit 5 finding 标 fixed（F-1/F-4/F-6/F-7/F-9）
- **2026-05-06 session 产出**（设计前置 audit 16h）：
  - `design/audit/lessons-learned.md`（8 元教训 + 6 校准）
  - `design/audit/scaffold-design-reconcile.md`（7 对错型 seam）
  - `design/audit/full-reconcile-pass.md`（11 结构性 seam）
  - `design/audit/contracts-draft.md`（4 条对账契约）
  - `design/audit/p5-state-machine-reachability.md`（10 findings：🔴4 / 🟡3 / 🟢3）
  - `design/00-architecture/08-namespaces.md`（命名空间登记 + 业界标准）
  - 4 个 baseline-patch commit（ErrorCode value lower / ActionType CRUD split + dot→snake / ADR-002 §1.1 SYSTEM_USER_UUID / 20 模块 references frontmatter 回填）

## 1. 推荐 prompt 顺序

### Prompt 0 — M14 sprint 启动（**当前推荐 / M13 已完整收官 / 复制下方代码块到新 session**）

```
继续 prism-0420 M14 sprint 实施代码（M14 行业新闻；M13 sprint 已收官 8 commit / 子片 5 关闸 [hash] / 827 PASS / R13-1 86=86 / L12 守护 / Phase 2.1 65%）。

冷启动按序读：
1. /root/workspace/projects/prism-0420/CLAUDE.md（协作规则 + "快速上手"序）
2. /root/workspace/projects/prism-0420/_handoff/next-session.md（§0 状态快照 post-M13-sprint-complete + Prompt 0 M14 启动 reconcile checklist）
3. /root/workspace/projects/prism-0420/design/00-roadmap.md（Phase 2.1 65%，下一站 M14）
4. /root/workspace/projects/prism-0420/design/00-phase-gate.md（闸门 2.5 + 闸门 3.4 L1 review 触发粒度规则）
5. /root/workspace/projects/prism-0420/design/02-modules/M14-industry-news/00-design.md（M14 design）
6. /root/workspace/projects/prism-0420/design/audit/m13-pilot-template-validation.md（M13 sprint 实证 + R1 8 P1 + R2 4 项 + Punt 池 16 项 + LLM 首发新教训 4 条 + 元自审）
7. memory feedback_problem_layered_analysis（含 M13 NEW 失效信号"3 端点全覆盖"原则 SSE 形态不免除）
8. memory feedback_monkeypatch_not_verification（M13 强实证 — unit MockProvider + integration skipif）
9. memory feedback_three_agent_pipeline + feedback_problem_layered_analysis + feedback_decision_transparency + feedback_code_first + feedback_completion_audit + feedback_subagent_completion_check + feedback_subagent_interface_contract + feedback_git_push_kb（标准红线集）

任务：M14 sprint TDD 实施。

启动顺序（严格按 M02-M13 范式 / 第十一数据点稳定）：

1. **闸门 2.5 reconcile pass**（M14 sprint 启动当天必跑）：
   - 预查 conftest.py 已有 fixture（M13 R1-B 新增 make_project_with_member + set_project_ai；九连规则延续）
   - grep M14 引用的所有 horizontal helper（含 NodeChildrenServiceProtocol 4 参 / write_event / DimensionService.create_dimension_record / IssueService.list_by_project / AI Provider 抽象等）
   - 按闸门 2.5 三栏分类（A 机械可做 / B 待 CY 决策 / C 已自我消解）
   - 自审一问："这真有候选吗 / 还是延续既有规则？" — 不允许把"机械应用既有规则"列为 B 栏

2. **闸门 3.4 L1 总则触发**：M14 design 必须含 §14.5 sprint review 拆分计划段（M02-M13 十一数据点稳定 → R1=3 subagent / R2=1 合并 Opus / 子片 5 不单跑 / schema 子片禁单跑 = 默认范式）。若缺先补。

3. **M14 写代码 5 子片**（参 M13 sprint 范式）：按 design 拆。

4. **R1+R2 review 按 §14.5 计划跑**：
   - R1（子片 3 完成）→ 3 subagent 并行 background mode；>5min 无通知主动 ping
   - R2（子片 4 完成）→ 1 合并 Opus subagent

5. **simplify-checklist 自动判断**：≥50 行 OR ≥2 文件触发；schema/migration 子片 ≥80% checklist 条目天然 SKIP

红线（M02-M13 实证后强化 / 元教训防御 actionable 主动复制）：
- viewer 写所有写端点 403 全覆盖（M07 立 / M08+M11+M12+M13 应用第 9-10 数据点）
- write_event 异常传播测试（M04+ 范式）
- cross-tenant 404（M02 范式）
- cross-project node 404（M06+M07+M08+M12+M13 范式 / **3 端点全覆盖含 SSE 形态特殊不免除** — M13 R2 抓出元教训）
- IntegrityError 区分约束名（M05 P1-01 立规延续）
- M12 元自审：L1 范式既锁裁决型 P1 不让 CY 拍
- M13 元自审：spec §7 metadata 字段集每条 e2e 验

M14 模块特定要素（参 design/02-modules/M14-industry-news/00-design.md）：
- 待启动时确认 design 范式（own / R-X1 / R-X2 / R-X3 / 纯读 / 流式 SSE 哪类）
- 是否复用 M13 AI Provider 抽象？若 M14 也 LLM 触发，复用 api/services/ai/ + ProviderRegistry
- prompt injection 局部防御（M13 P2-12 punt）：M14 若同样接受用户输入 + 喂 LLM 必须立 prompt-injection 防御

启动注意：
1. 不要在同一会话连续跑多个 sprint：M11+M12+M13 单 sprint 都堆到大 context，下次开新窗口
2. 当前周 usage（Asia/Tokyo Reset 周三 6pm；本周 reset ~5/13）—— 启动 M14 前先 /usage 同步 + 更新 memory feedback_usage_budget.md 基线
3. M14 design 内是否含完整 §14.5？冷启动第一步 grep "## 14.5\\|sprint review 拆分" design/02-modules/M14-industry-news/00-design.md 确认；缺则子片 0 prep 补齐
```

参考来源（详见）：`_handoff/sprint-prompts-M05-M20.md` § "## M14 — 行业新闻" + `design/02-modules/M14-industry-news/00-design.md` + `design/audit/m13-pilot-template-validation.md`。

### Prompt 0' — M13 sprint 启动（已完成 2026-05-08，仅供历史追溯）

```
继续 prism-0420 M13 sprint 实施代码（M13 AI 需求分析；M12 sprint 已收官 7 commit / 子片 5 关闸 4bc096c / 742 PASS / R13-1 79=79 / L12 守护 / Phase 2.1 60%）。

冷启动按序读：
1. /root/workspace/projects/prism-0420/CLAUDE.md（协作规则 + "快速上手"序）
2. /root/workspace/projects/prism-0420/_handoff/next-session.md（§0 状态快照 post-M12-sprint-complete + Prompt 0 M13 启动 reconcile checklist）
3. /root/workspace/projects/prism-0420/design/00-roadmap.md（Phase 2.1 60%，下一站 M13）
4. /root/workspace/projects/prism-0420/design/00-phase-gate.md（闸门 2.5 + 闸门 3.4 L1 review 触发粒度规则）
5. /root/workspace/projects/prism-0420/design/02-modules/M13-requirement-analysis/00-design.md（M13 design）
6. /root/workspace/projects/prism-0420/design/audit/m12-pilot-template-validation.md（M12 sprint 实证 + R1 4 P1 + R2 1 P1 裁决型 + Punt 池 13 项 + 元自审教训）
7. memory feedback_problem_layered_analysis（含 M12 NEW 失效信号"L1 范式既锁裁决型 P1 错抛 CY 拍" — M13 reviewer P1 抓 design vs 实装漂移时必走 step 1-2 grep L1 锁定项）
8. memory feedback_llm_hotpath_math（M13 接 LLM 进 hot path 必报频率×延迟×cost 4 数字 + 3 红线）
9. memory feedback_monkeypatch_not_verification（LLM monkeypatch ≠ 生产路径；DONE 必区分 unit pass vs integration pass）
10. memory feedback_three_agent_pipeline + feedback_problem_layered_analysis + feedback_decision_transparency + feedback_code_first + feedback_completion_audit + feedback_subagent_completion_check + feedback_subagent_interface_contract + feedback_git_push_kb（标准红线集）

任务：M13 sprint TDD 实施。

启动顺序（严格按 M02-M12 范式）：

1. **闸门 2.5 reconcile pass**（M13 sprint 启动当天必跑）：
   - 预查 conftest.py 已有 fixture（M12 R1-B 新增 make_snapshot；M04+M05+M06+M07+M08+M10+M11+M12 八连规则延续）
   - grep M13 引用的所有 horizontal helper（含 NodeChildrenServiceProtocol 4 参 / write_event / DimensionService 跨模块只读接口 / M07 IssueService.list_by_project 跨模块 pass-through）
   - 按闸门 2.5 三栏分类（A 机械可做 / B 待 CY 决策 / C 已自我消解）
   - 自审一问："这真有候选吗 / 还是延续既有规则？" — 不允许把"机械应用既有规则"列为 B 栏
   - **M12 元自审新规主动应用**：reviewer P1 若抓 design 草案 vs 实装漂移，先 grep L1 锁定项（ADR / 跨 sprint 范式实证）；命中 → AI 自决 disambiguation 落 design + scaffold 注释，不 AskUserQuestion；grep miss 才让 CY 拍

2. **闸门 3.4 L1 总则触发**：M13 design 必须含 §14.5 sprint review 拆分计划段（M02-M12 十数据点稳定 → R1=3 subagent / R2=1 合并 Opus / 子片 5 不单跑 / schema 子片禁单跑 = 默认范式）。若缺先补。

3. **M13 写代码 5 子片**（参 M12 sprint 范式）：按 design 拆。

4. **R1+R2 review 按 §14.5 计划跑**：
   - R1（子片 3 完成）→ 3 subagent 并行 background mode；>5min 无通知主动 ping
   - R2（子片 4 完成）→ 1 合并 Opus subagent

5. **simplify-checklist 自动判断**：≥50 行 OR ≥2 文件触发；schema/migration 子片 ≥80% checklist 条目天然 SKIP

红线（M02-M12 实证后强化 / 元教训防御 actionable 主动复制）：
- viewer 写所有写端点 403 全覆盖（M07 立 / M08+M11+M12 应用）
- write_event 异常传播测试（M04+ 范式 / 三写端点全覆盖含 M12 R1-C P1-02 立修补）
- cross-tenant 404（M02 范式）
- cross-project node 422（M06+M07+M08+M12 范式）
- IntegrityError 区分约束名（M05 P1-01 立规延续）
- M12 R1-C P1-03 NEW: Core UPDATE 显式刷 updated_at（不依赖 ORM onupdate）
- M12 元自审 NEW: L1 范式既锁裁决型 P1 不让 CY 拍

M13 模块特定要素（参 _handoff/sprint-prompts-M05-M20.md M13 段）：
- **第一个真 LLM 集成模块**（feedback_llm_hotpath_math 触发：必报频率×延迟×cost 4 数字 + 3 红线 单跑<周期/2 + flock + cost ceiling）
- **流式 SSE**（design §12 A 流式 vs 同步 vs queue 三选一；design 应已决；若同步 → 接口 SLA 估算）
- **M04 punt 接通**：M13 是 M04 DimensionService.create_dimension_record + get_latest 的第一 caller → M04 service 层此 sprint 期实装两接口（含 extra_activity_metadata 合并机制）
- **M07 list_by_project 跨模块 pass-through**（已 pilot 登记）
- **LLM monkeypatch ≠ 生产路径**（feedback_monkeypatch_not_verification）：DONE 必区分 unit pass vs integration pass；端到端需真 LLM smoke
- 安全：LLM 不接管 dimension content schema 校验（jsonschema 仍 service 层做）

启动注意：
1. 不要在同一会话连续跑多个 sprint：M11+M12 单 sprint 都堆到大 context，下次开新窗口
2. 当前周 usage（Asia/Tokyo Reset 周三 6pm；本周 reset ~5/13）—— 启动 M13 前先 /usage 同步 + 更新 memory feedback_usage_budget.md 基线
3. M13 design 内是否含完整 §14.5？冷启动第一步 grep "## 14.5\\|sprint review 拆分" design/02-modules/M13-requirement-analysis/00-design.md 确认；缺则子片 0 prep 补齐
```

参考来源（详见）：`_handoff/sprint-prompts-M05-M20.md` § "## M13 — AI 需求分析" + `design/02-modules/M13-requirement-analysis/00-design.md` + `design/audit/m12-pilot-template-validation.md`。

### Prompt 0' — M12 sprint 启动（已完成 2026-05-08，仅供历史追溯）

参 `_handoff/sprint-prompts-M05-M20.md` § "## M12 ..." 段（M11 sprint 已收官 commit 子片 5 关闸 / 674 PASS / Phase 2.1 55%）。

M12 sprint 启动 reconcile checkpoint（必查）：
- **元教训防御 actionable 5 + R-X1 NEW 2 条**（M11 sprint 启动 reconcile A7 主动列入清单的延续）：
  1. viewer 写**所有**写端点 403 全覆盖（M07 立 / M08+M11 应用）
  2. write_event 异常传播测试（M04+ 范式）
  3. cross-tenant 404（M02 范式）
  4. cross-project node 422（M06+M07+M08 范式）
  5. IntegrityError 区分约束名（M05 P1-01 立规延续）
  6. **NEW from M10 纯读模块**：纯读模块 docstring 每字段 ≥1 unit test 断言（业务模块不适用，但"绿测 ≠ 范式正确"通用）
  7. **NEW from M11 R-X1**：orchestrator 失败补偿独立 commit boundary（M17 sprint 实装；M12 若是 R-X1 第二实例则触发）
  8. **NEW from M11 R-X1**：文件上传 endpoint file.size 预检 + filename sanitize（M17 异步 zip 导入实装时复用 _sanitize_filename）
- **L1 review 节奏第九数据点稳定** → R1=3 subagent + R2=1 合并 Opus 默认范式作模板
- **闸门 2.5 B 0 项第六次稳定** → M12+ 启动 reconcile 自审一问"这真有候选吗"已稳定，禁制造假决策

### Prompt 0' — M11 sprint 已完成（仅供历史追溯）

M11 sprint 完成 commits 见 §0 状态快照。**M11 子片 0 prep 已完成（commit `8ef59b3` 2026-05-08）**：
- ✅ design §14.5 sprint review 拆分计划段补

**M11 子片 0 prep 已完成（commit `8ef59b3` 2026-05-08）**：
- ✅ design §14.5 sprint review 拆分计划段补
- ✅ **3 跨模块 batch_create_in_transaction 接通**（M04 punt R1-A A6 + M06/M07 scaffold "M11 期实装" 全到期）：
  - `DimensionService.batch_create_in_transaction(dimensions_data)` ✅
  - `CompetitorService.batch_create_in_transaction(competitors_data)` ✅
  - `IssueService.batch_create_in_transaction(issues_data)` ✅
  - `NodeService.batch_create_in_transaction` 已存在（M03 sprint） → **R-X1 4 接口齐全**
- ✅ 3 smoke tests / 616 PASS / R13-1 67=67

**M11 闸门 2.5 reconcile 三栏（已分析 / 第六次 B 栏 0 项实证）**：
- A 8 项（其中 4 项已落地子片 0：M04+M06+M07 batch_create + §14.5）
- B 0 项
- C 3 项（queue N/A / R-X1 不是 R-X2 / caller 拓扑责任 design §6 G5 已决）

**M11 剩余子片**（下个 session 接续）：
- **子片 1**: M11 own model `cold_start_tasks` + alembic（design §3）
- **子片 2**: ColdStartDAO（task CRUD + tenant 过滤）
- **子片 3**: ColdStartOrchestratorService（CSV parse + 4 service.batch_create 集成 + 共享 db.begin() / R-X1 严守）
- **子片 4**: Router CSV upload endpoint（multipart/form-data）+ check_project_access editor + 错误行报告
- **子片 5**: 关闸（audit/m11-pilot-template-validation.md + roadmap + handoff）

M11 模块特定要素提示：
- **第一个 R-X1 orchestrator**（不直 INSERT 跨模块表，全走 service.batch_*）
- M11 是同步 HTTP 路径（design §12 N/A queue / 无 SSE / 无 Worker）
- caller 拓扑排序契约（M11 csv 已是层序，design §6 G5 line 238）
- ⚠️ **asyncio.gather AsyncSession 同 session 不安全**（M08 立修 tests pass 是巧合 / SA 抛 "concurrent operations not permitted" / 新模块禁用 / 见 memory feedback_problem_layered_analysis 失效信号）

**M02-M10 元教训防御 actionable 清单**（M11 sprint 启动 reconcile 时主动复制不等 R2 抓）：
1. viewer 写**所有**写端点 403 全覆盖（M07 立 / M08 应用 / M10 N/A 因纯读）
2. write_event 异常传播测试（M04/M06/M07/M08 范式）
3. cross-tenant 404 / cross-project node 422 / IntegrityError 区分约束名
4. **NEW from M10**：纯读模块 docstring 每字段 ≥1 unit test 断言（M10 纯读专属，M11 业务模块不适用，但元教训"绿测 ≠ 范式正确"通用）
5. **NEW from M10**：R1.5 reconcile checkpoint — R2 dispatch 前 grep R1 立修关键词在代码中真实存在

### Prompt 0' — M10 sprint 实施代码启动（已完成 2026-05-08，仅供历史追溯）

参 `_handoff/sprint-prompts-M05-M20.md` § "## M10 — 全景图（overview）" 段；启动当天复制对应 prompt 段落（M08 commits eed7749 → 子片 5 关闸 / 586+ PASS / Phase 2.1 45%）。

**M09 superseded by M18 不实装**（详见 design/00-roadmap.md §6.2）。

M10 模块特定要素提示（详见 sprint-prompts M10 段）：
- 跨模块只读聚合（同 M09 范式）— 项目首页全景视图：节点树 + 维度填充率 + 最近活动
- 与 M15 activity_stream 集成（最近活动；M15 sprint 期可能仍是 B2.3 stub log）
- 全景图 hot path 性能 + ADR-003 规则 2 豁免严守
- G7 删 US-C1.1 → out of scope（M10 不实装"添加节点"功能）

**M08 sprint 元教训防御 actionable 清单**（M10 sprint 启动 reconcile 时主动复制不等 R2 抓）：
1. viewer 写**所有**写端点 403 全覆盖（M07 R2 P1-01 / M08 主动应用）
2. write_event 异常传播测试（M04/M06/M07/M08 R1-C 范式）
3. cross-tenant 404 (project_not_found，M02 范式)
4. cross-project node 422（M06+M07+M08 范式对齐）
5. IntegrityError 区分约束名（M05 P1-01 立规延续）

### Prompt 0' — M08 sprint 实施代码启动（已完成 2026-05-08，仅供历史追溯）

参 `_handoff/sprint-prompts-M05-M20.md` § "## M08 — 模块关系图（module-relation）" 段；启动当天复制对应 prompt 段落（M07 commits b81c0d8 → 子片 5 关闸 commit / 538+ PASS / Phase 2.1 40%）。

M08 模块特定要素提示：
- **不是 R-X2 child service**（关系图节点附属，可能走 DB CASCADE 兜过；design §10 R10-1 batch3 是否要求 per-record activity_log → sprint 启动闸门 2.5 复审）
- 双向关系 vs 单向 + OR 查询：design 应已决；闸门 2.5 不复议
- 图查询防 N+1：邻接表 vs 物化视图 vs 递归 CTE — design 应已选

**M07 sprint punt 池本期到期项核对**（详见 `design/audit/m07-pilot-template-validation.md` Punt 池总表 8 项）：
- B4 IssueCategoryInvalidError R13-1 parity 注释 → M08 sprint 启动前一并清
- B5 _make_issue 跨文件触发时迁 conftest → M08 sprint 启动前评估
- **元教训防御 actionable**：M08 sprint 启动 reconcile 时主动比对 M02-M07 R1/R2 punt 池中"跨模块测试契约"项（**viewer 写**所有**写端点 403** / write_event 异常传播测试 / cross-tenant 404 / 等），**sprint 实施时主动复制不等 R2 抓**

### Prompt 0' — M07 sprint 实施代码启动（已完成 2026-05-08，仅供历史追溯）

```
继续 prism-0420 M07 sprint 实施代码（M07 问题沉淀 / R-X2 第三真注入方 / orphan 语义；M06 sprint 已完成 commits c84f6f2 → 子片 5 关闸 / 473+ PASS / Phase 2.1 35%）。

参 _handoff/sprint-prompts-M05-M20.md § "## M07 — 问题沉淀（issue）" 段。

特定要素：
- R-X2 第三真注入方（orphan 语义 SET NULL，与 M04/M06 delete 不同）
- 状态机 4 状态 + SELECT FOR UPDATE 行锁串行化（design §5）
- M13 pilot list_by_project pass-through（无代码改动；service 层加 method）

红线：
- ON DELETE SET NULL + passive_deletes=True（与 M04/M06 cascade='all,delete-orphan' 显式区分）
- 7 处代码 anchor 标注 orphan 语义防误读
- viewer 写**所有**写端点 403 测试（M06 R2 P1-02 立的元教训）— **不要漏**
```

### Prompt 0'' — M06 sprint 实施代码启动（已完成 2026-05-08，仅供历史追溯）

参 `_handoff/sprint-prompts-M05-M20.md` § "## M07 — 问题沉淀（issue）" 段；启动当天复制对应 prompt 段落，替换 `M{N-1} commits ... / N PASS / Phase 2.1 X%` 为真实最新值（M06 commits c84f6f2 → {子片 5 关闸 commit} / 473+ PASS / Phase 2.1 35%）。

M07 模块特定要素提示：
- M07 是 R-X2 **第三真注入方**（语义不同：orphan_by_node_id SET node_id=NULL 而非 delete；issue 不被真删只变游离）
- 子片 3 实装 IssueService.orphan_by_node_id (4 参 含 actor_user_id) + lifespan register_child_service("issue", ...)
- batch3 基线补丁决策 4：命名 orphan 区分 M04/M06 的 delete（避免误以为真删）
- M13 pilot 登记 list_by_project 跨模块契约（无代码改动；pass-through DAO node_id 过滤）
- activity_log: action_type="orphan" + metadata 含 cascade_source

闸门 2.5 reconcile pass 前必查：
- M06 sprint punt 池本期到期项（详见 `design/audit/m06-pilot-template-validation.md` Punt 池总表 8 项）：B1 _make_competitor/_make_ref 跨文件需求 / B6 CompetitorRefResponse.display_name 接通 / B8 ref 404 e2e test
- M05 sprint punt 池继续（list_by_node id DESC tie-break / VersionNotFoundError reason 字段）
- M04 punt R1-C C6.1（delete_by_node_id N+1 batch 升级，M07 评估是否升级触发，FK orphan 与 delete 行为不同）

---

### Prompt 0' — M06 sprint 实施代码启动（已完成 2026-05-08，仅供历史追溯）

```
继续 prism-0420 M06 sprint 实施代码（M06 竞品参考；R-X2 第二真注入方；M05 sprint 已完成 commits 811d6bc → 6f489db / 412 PASS / Phase 2.1 30%）。

参 _handoff/sprint-prompts-M05-M20.md § "## M06 — 竞品参考（competitor）" 段。

冷启动按序读：
1. CLAUDE.md / _handoff/next-session.md / design/00-roadmap.md / design/00-phase-gate.md
2. design/02-modules/M06-competitor/00-design.md
3. design/audit/m05-pilot-template-validation.md（含闸门 2.5 B 0 项首次实证 + 5 步分层失效信号）
4. memory feedback_problem_layered_analysis（5 步分层 + 失效信号）
5. memory feedback_three_agent_pipeline + 标准红线集

特定要素：
- R-X2 第二真注入方（Protocol 4 参签名稳定复用）
- M18 baseline-patch get_for_embedding（拼接 name + description；url 不参与）
- 多表事务（competitors + competitor_refs 同事务，design Q4）

红线：
- 异常契约严守 delete_by_node_id 不 catch-all
- N+1 punt 接续（单 node refs 数量小不触发）
- IntegrityError race 转换 M05 同款干净起步（区分约束名）
```

### Prompt 0' — M05 sprint 实施代码启动（已完成 2026-05-08，仅供历史追溯）

```
继续 prism-0420 M05 sprint 实施代码（M05 版本时间线；M04 sprint 已完成 commits 4c3c413→c4037a7 / 347 PASS / Phase 2.1 25%）。

冷启动按序读：
1. /root/workspace/projects/prism-0420/CLAUDE.md（协作规则 + "快速上手"序）
2. /root/workspace/projects/prism-0420/_handoff/next-session.md（§0 状态快照 post-M04-sprint-complete + Prompt 0 + §2 历史/后置债）
3. /root/workspace/projects/prism-0420/design/00-roadmap.md（Phase 2.1 25%，下一站 M05）
4. /root/workspace/projects/prism-0420/design/00-phase-gate.md（闸门 2.5 + 闸门 3.4 L1 review 触发粒度规则）
5. /root/workspace/projects/prism-0420/design/02-modules/M05-version-timeline/00-design.md
6. /root/workspace/projects/prism-0420/design/audit/m04-pilot-template-validation.md（M04 sprint 实证 + L1 第三数据点 + 5 R-X5 子选项 + punt 池 17 项）
7. /root/workspace/projects/prism-0420/design/audit/m03-pilot-template-validation.md（M03 sprint 实证）
8. /root/workspace/projects/prism-0420/design/audit/m01-pilot-template-validation.md（PT1-PT3 tracker — M05 sprint 闸门 2.5 时回填 M05 行）
9. memory feedback_problem_layered_analysis（5 步分层分析法 — M04 sprint 实质性产出"防本模块绕"价值）
10. memory feedback_three_agent_pipeline（v2: M02+M03+M04 三数据点稳定 / R1=3 subagent + R2=1 合并 Opus subagent）
11. memory feedback_sprint_test_helper_reuse_check（含 M04 R1-B 验证：4 migration import 形式统一）
12. memory feedback_decision_transparency + feedback_code_first + feedback_completion_audit + feedback_subagent_completion_check + feedback_subagent_interface_contract + feedback_git_push_kb（标准红线集）

任务：M05 sprint TDD 实施。

启动顺序（严格按 M02+M03+M04 范式）：

1. **闸门 2.5 reconcile pass**（M05 sprint 启动当天必跑）：
   - 预查 conftest.py 已有 fixture（make_user / make_project / make_node 等；M04 sprint R1-B 实证规则延续）
   - grep M05 引用的所有 horizontal helper（含 NodeChildrenServiceProtocol — 注意签名是 4 参 含 actor_user_id；M04 sprint R-X5 升级实证）
   - 按闸门 2.5 三栏分类（A 机械可做 / B 待 CY 决策 / C 已自我消解）输出
   - 自审一问："这真有候选吗 / 还是延续既有规则？" — 不允许把"机械应用既有规则"列为 B 栏给 CY 制造假决策（M04 sprint 元教训 2）

2. **闸门 3.4 L1 总则触发**：M05 design 必须含 §14.5 sprint review 拆分计划段（M02+M03+M04 三数据点稳定 → R1=3 subagent / R2=1 合并 Opus subagent / 子片 5 不单跑 / schema 子片禁单跑 = 默认范式）。若缺先补。

3. **M05 写代码 5 子片**（参 M04 sprint 范式）：略，按 design 拆。

4. **R1+R2 review 按 §14.5 计划跑**：
   - R1 (子片 3 完成) → 3 subagent 并行 background mode；>5min 无通知主动 ping
   - R1 finding P1 立修同 commit（M04 范式）；P2 punt 进 audit/m05-pilot-template-validation.md
   - R2 (子片 4 完成) → 1 合并 Opus subagent

5. **simplify-checklist 自动判断**：≥50 行 OR ≥2 文件触发；schema/migration 子片 ≥80% checklist 条目天然 SKIP 可合并到下游

红线（M04 sprint 实证后强化）：
- 5 步分层分析法走（机制冲突/设计缺口）— M04 R-X5 实证此规则首次实质性"防本模块绕"
- NodeChildrenServiceProtocol 现是 4 参签名（含 actor_user_id）— M05 注入时 follow
- M04 sprint punt 池 17 项里有"M05 sprint 启动 reconcile 时消歧"项（A4 §5 vs §6 R-X3 事务边界字面冲突）— 必看
- commit 不主动 push（feedback_git_push_kb）
```

### Prompt 0' — M04 sprint 实施代码启动（已完成 2026-05-07，仅供历史追溯）

```
继续 prism-0420 M04 sprint 实施代码（M04 维度记录；M03 sprint 已完成 commits 800e632→656e05c / 285 PASS）。

冷启动按序读：
1. /root/workspace/projects/prism-0420/CLAUDE.md（协作规则 + "快速上手"序）
2. /root/workspace/projects/prism-0420/_handoff/next-session.md（§0 状态快照 post-M03-sprint-complete）
3. /root/workspace/projects/prism-0420/design/00-roadmap.md（Phase 2.1 20%，下一站 M04）
4. /root/workspace/projects/prism-0420/design/00-phase-gate.md（闸门 3.4 L1 review 触发粒度规则）
5. /root/workspace/projects/prism-0420/design/02-modules/M04-dimension-record/00-design.md
6. /root/workspace/projects/prism-0420/design/audit/m03-pilot-template-validation.md（M03 sprint 实证 + L1 双数据点 + R-X5 子选项）
7. /root/workspace/projects/prism-0420/design/audit/m01-pilot-template-validation.md（PT1-PT3 tracker — M04 sprint 闸门 2.5 时回填 M04 行）
8. memory feedback_problem_layered_analysis（5 步分层分析法）
9. memory feedback_three_agent_pipeline + Prism-simplify-checklist.md（review 流水线原义）

任务：M04 sprint TDD 实施（参 M03 sprint 5 子片 + 2 review 范式，§14.5 sprint review 拆分计划必先存在）。

启动顺序：
1. **闸门 2.5 reconcile pass**（M04 sprint 启动当天必跑）：
   - **预查 conftest.py 已有 fixture**（M03 R1-B C1 新发现的禁忌：跨模块 helper 重复）
   - grep M04 引用的所有 horizontal helper（含 NodeChildrenServiceProtocol — M04 是 M03 R-X2 第一个注入方）
   - 按闸门 2.5 三栏分类（A 机械可做 / B 待 CY 决策 / C 已自我消解）输出
2. **闸门 3.4 L1 总则触发**：M04 design 必须含 §14.5 sprint review 拆分计划段。若缺先补
3. **M04 写代码**：M03 R-X2 第一个真注入 — register_child_service("dimension", DimensionService.delete_by_node_id)
4. **R1+R2 review 按 §14.5 计划跑**（M03 实证: R1=3 subagent / R2=1 合并 subagent 已稳定足够）
5. **simplify-checklist 自动判断**：≥50 行 OR ≥2 文件触发

红线（M03 sprint 实证后强化）：
- 跨模块 helper 复用：sprint 启动前 grep conftest.py / api/auth/ / api/services/ 既有 fixture
- 5 步分层分析法走（机制冲突/设计缺口）
- M04 是 M03 R-X2 第一注入方 — 验证 register_child_service 范式跑通
- M03 NodeChildrenServiceProtocol 异常契约 (R1-C P1-01): 不 catch-all 静默吞错
- commit 不主动 push（feedback_git_push_kb）
```

### Prompt 0' — M02 sprint 实施代码启动（已完成，仅供历史追溯）

```
继续 prism-0420 M02 sprint 实施代码（design 已含完整实施期处理段 + 体系级 v2 修订已落地）。

冷启动按序读：
1. 本 _handoff/next-session.md（看 §0 状态快照 + §2.1 后置债 + 体系级 v2 修订清单）
2. design/02-modules/M02-project/00-design.md（含 §3.X 实施期处理 / §3.Y 启动数据 / §3.Z early adopter AES helper）
3. design/02-modules/README.md v2（R-X5/X6 + R3-6 + frontmatter helpers 约束）
4. design/00-architecture/06-design-principles.md v2（6 原则 #6 横切 vs 业务）
5. design/00-architecture/04-layer-architecture.md v2（Q7 横切层定义）
6. design/audit/time-dimension-blindspot-2026-05-07.md（M02 sprint 启动元反思 + 4 元教训）

任务：
1. M02 sprint 闸门 2.5 reconcile pass：本次会话已确认无矛盾 ✅，可直接进 step 4 TDD 实施
2. M02 写代码顺序（参 M01 sprint 5 子片范式）：
   - 子片 1：models（Project / ProjectMember / ProjectDimensionConfig / DimensionType + 测试兜底 placeholder seed = 1 条 default 类型 alembic data migration 按 R3-6-B）
   - 子片 2：DAO + tenant_filter concrete impl 注入（M02 own only project_members 实现）
   - 子片 3：Service + AES helper 横切层 api/auth/crypto.py 实装（按 §7.1 B'）+ ai_api_key_enc 加解密
   - 子片 4：Router + 11 endpoints + check_project_access Depends（M02 own）
   - 子片 5：tests + ci-lint 守护
3. 三 Agent 流水线（Implementer + Spec Reviewer + Code Quality Reviewer）必须真跑（M01 期 bypass 已是首次，闸门 3 §3.3 不允许第二次 bypass）
4. simplify-checklist 在 ≥50 行或跨 ≥2 文件改动时跑
5. M02 sprint 启动期实证子选项（按 R-X5 子选项清单红线，sprint 写代码时拍 case-by-case + 登记到 design/audit/m02-pilot-template-validation.md）：
   - C 路径 team_id 写入策略（API 不暴露 / Schema 暴露但 service 拒绝 / DAO 完全允许）
   - A 路径 SearchConfig 类型 owner（M02 own raw types / 共享 horizontal）
   - B 路径 OpenAPI 契约层处理（不实装 router / 占位 router 501 stub）
   - R13-1 附加规则标记位置（code 注释 / design §13 加列 / ci-lint.sh 加附加规则）

红线：
- M02 sprint 写代码时严格按 design 实施期处理段走（A1=C / A2=A / A3.1=A / A3.2=B）
- 横切 helper（AES crypto）建在横切层 api/auth/crypto.py，禁止挂 M02 名下（原则 6 + R-X6）
- 三 Agent + simplify 这次必须真跑
- 实证子选项后回写 R-X5 子选项清单段（推动规则升级，元原则 1）

关联：design/audit/time-dimension-blindspot-2026-05-07.md / KB 02-技术/架构设计/设计前置方法论-补丁01-时间维度.md
```

### Prompt 0' — M01 sprint 闸门 3 检查 + M02 启动（已完成，仅供历史追溯）

```
继续 prism-0420，过闸门 3（M01 PR merge ready 检查）+ 启动 M02 sprint。

任务：
1. 闸门 3 检查（design/00-phase-gate.md 闸门 3 checklist）：
   - M01 5 子片 commits 已 push（c1e3acc → 2704d0f + design 回写 commit）
   - 测试矩阵 117+ PASS / 0 xfail / lint 全过 / pre-commit hooks 全过
   - design 反馈已回写 ADR-004 + M01 §4 §10
   - PT1-PT3 tracker 在 design/audit/m01-pilot-template-validation.md
2. 若闸门 3 通过，按 prompt A（重写自 M01 模板）启动 M02。

红线：
- M02 sprint 内必须给 PT1-PT3 第 1 次回写（M02 是否复用 M01 范式）
- M02 涉及 user 跨 project 关系，凭据路径声明段必须引 ADR-004（PT2 校准）
```

### Prompt A' — M01 sprint 已完成（保留作为 M02 起手模板参考）

```
继续 prism-0420，启动 M01 用户系统探针实施 sprint。

任务：按 design-first 方法论 + TDD 跑完 M01（auth pilot 模块）。

必读（按序）：
1. _handoff/next-session.md（本文件，看上下文）
2. design/00-roadmap.md（确认当前真实位置 = Phase 2.1 第 1 模块）
3. design/00-phase-gate.md 闸门 2.5（M01 sprint 启动当天必跑 reconcile）
4. design/02-modules/M01-user-account/00-design.md（含 references frontmatter）
5. ADR-001 + ADR-002 + ADR-004（M01 引用的 3 个 ADR）
6. design/audit/scaffold-design-reconcile.md（已知 7 seam，机械可做项 M01 sprint 第一 commit 内修掉）
7. design/audit/p5-state-machine-reachability.md F-1（M01 mermaid 与禁止转换表自相矛盾——sprint 内必拍 + 修）

启动顺序：
1. 闸门 2.5 reconcile pass：grep 7 seam，分类（机械可做 / 待 CY 拍 / 已自我消解）
2. M01 实施前决策包：把 design 中所有 ⚠️ 占位 + P5 F-1 整理成 A 模式清单（候选 + 优缺点 + 3-5 月后果）让 CY 拍
3. CY 拍完 → 落 design 文档 status=accepted
4. TDD 实施：tests/test_m01_*.py 先写 → router/service/dao 后填
5. 三 Agent 流水线（Implementer + Spec Reviewer + Code Quality Reviewer）每完成一类 endpoint 跑一次
6. simplify checklist 在 ≥50 行或跨 ≥2 文件改动时跑
7. PR 准备：含 M01 tests.md critical path 100% PASS evidence

红线：
- 闸门 3 要求 M01 PR merge 后才能开 M02——本 sprint 必须 merge-ready
- ADR-002 §1.1 SYSTEM_USER_UUID：M01 自身不是 cron 模块但其 activity_log 写入需统一对齐 ADR
- design 任何字段与本次 audit 产出（references frontmatter / namespace 登记）冲突时——design 是真相，audit 是约束 lint
- 决策点 A 模式呈现，禁打包；禁引导

关联：design/00-phase-gate.md 闸门 2.5 / 闸门 3 / feedback_three_agent_pipeline.md
```

---

### Prompt B — P5 audit 🔴 4 finding 收口（建议 M01 sprint 内夹带做）

```
跑 design/audit/p5-state-machine-reachability.md 的 4 条 🔴 finding 收口。

任务：
- F-1（M01 mermaid 与禁止转换表 pending→disabled 自相矛盾）：
  现在就修 design 文档——CY 决策哪边对（mermaid 还是禁止表为真），改另一边一致。
  A 模式呈现两种解读 + 各自语义后果让 CY 拍。
- F-4 / F-6 / F-7（M16 / M17 / M18 cron 模块端 0 处引用 SYSTEM_USER_UUID）：
  现在不写业务代码——在每个模块 §12 cron 段加 1 行明确指引：
  "本 cron 触发的 payload.user_id 必须用 api.queue.base.SYSTEM_USER_UUID 常量
   （ADR-002 §1.1）"。
  把规约从 ADR 落到模块 design 引用层，避免实施时漏。

红线：
- F-1 决策走 A 模式呈现；不预设答案
- F-4/F-6/F-7 不写业务代码，只补模块 design 的引用注释

关联：design/audit/p5-state-machine-reachability.md / ADR-002 §1.1 / feedback_decision_transparency.md
```

---

### Prompt C — 契约 2 + 契约 4 + M14 baseline-patch tail（M01 PR merge 后）

```
完成 design/audit/contracts-draft.md 的 4 条契约（已落契约 1 + 3，剩 2 + 4）+
M14 baseline-patch tail。

任务：
1. 契约 2（referenced_by 反向链）：5 ADR + engineering-spec §7/§8/§12
   + 02-modules/README.md R-X 25 条 → 各自尾部加 `referenced_by` 段。
   双向链格式：见 design/audit/contracts-draft.md §2 形态示例。
2. 契约 4：
   - scripts/structural-audit.sh 写 P1 + P2 + P3 自动扫
     （namespace collision / ADR×Module 矩阵 / Rule×Module 矩阵）
   - pre-commit hook 加 structural-audit
   - 02-modules/README.md 加"横向对账三轮"段（独立于纵向三轮）
3. M14 baseline-patch tail：M14 §10 5 个 action_type
   （create/update/delete/link/unlink）→ 改为 entity 前缀 + 过去式后回写
   M15 ActionType enum：news_created / news_updated / news_deleted /
   news_linked / news_unlinked。同步 namespace 登记表。

红线：
- 契约 2 / 4 形态严格对齐 contracts-draft §2 / §4，不发明新形态
- 与契约 1（references frontmatter）形成双向校验闭环

工时估计：契约 2 ≈ 6-7h / 契约 4 ≈ 3-4h / M14 ≈ 0.5h

关联：design/audit/contracts-draft.md / design/audit/lessons-learned.md
```

---

## 2. 历史 prompt（已完成，仅供追溯）

- ❌ ~~Prompt 0: M03 sprint 实施代码启动~~ → ✅ 2026-05-07 commits 800e632 → 656e05c（5 子片 + R1+R2 闭环；285 PASS / R13-1 41=41 / L12 守护通过）
  - L1+L2+L3 节奏第二次实证（M02 首 / M03 第二，双数据点稳定）
  - R-X5 子选项: A4 enqueue B 推迟 + get_for_embedding A 现在建 ✅ + 新决 A5 batch_create 拓扑 + A6 child_services 分发
  - design/audit/m03-pilot-template-validation.md status=accepted
  - 后置债 (M04+ sprint 顺手清):
    - R-X2 跨模块 stub: M04 sprint 是第一个真注入方 (DimensionService.delete_by_node_id)
    - R1-C R2-3 punt: NodeChildrenServiceProtocol 升级 batch 形态（M04 sprint 期评估）
    - R2-9 punt: NodeService.update_node service 层直调 type 参数测试
    - P-A-09 punt: refresh attribute_names 加 path（防御性）
    - P2-02 punt: batch_create max_sort_order O(N) TODO 注释
    - P2-03 punt: update_paths_in_subtree REPLACE 安全性 docstring
    - C2 punt (R1-B): migrations `_ck_clause` 重复 → migrations/helpers.py（M04 migration 出现前提取）

- ❌ ~~Prompt: Phase 2.0 决策类（quality-spec + engineering-spec §13）~~ → ✅ 2026-05-05 commit b91c8d5
- ❌ ~~Prompt: Phase 2.0 代码地基（5 helper + Makefile + queue scaffold）~~ → ✅ 已落地，B1-B10 全 ✅
- ❌ ~~Prompt B: P5 audit 🔴 4 finding 收口~~ → ✅ 2026-05-07 commits 2e93de9 + b24f049（含 F-9 R4-3a 模板修订一并落地）
- ❌ ~~Prompt A: M01 探针实施 sprint~~ → ✅ 2026-05-07 commits c1e3acc → 2704d0f（5 子片）+ design 回写 commit
  - 117+ tests PASS / 0 xfail / 22=22 R13-1 / L12 守护通过
  - design / ADR 回写 6 处（同秒边界 / P2 信任链 / refresh 形态 / active→pending / 同值豁免 / 多事件顺序）
  - 17 ErrorCode 新增 + 7 表 schema 落地 + ADR-004 P1+P2+P3 全打通

## 2.1 M01 sprint 后置债（不阻断 M02 启动，M02 sprint 内或后续顺手清掉）

| # | 项 | 优先级 | 触发场景 |
|---|----|------|---------|
| D1 | M03/M04/... 模块开工时验证 PT1-PT3（design/audit/m01-pilot-template-validation.md）| 🟢 | 每模块 sprint 闸门 2.5 reconcile 时 |
| D2 | tests.md A22 注释"每次记录 1 行"已被 design §10 校正为本期不写——必要时补 strikethrough | 🟢 | M01 PR review 期或下次扫 tests.md 时 |
| D3 | bcrypt 5.x deprecation warning（passlib `__about__` 缺失）| 🟢 | 升级 passlib 或换 bcrypt 直调（已是直调，仅 warning 噪音）|
| D4 | feedback_three_agent_pipeline 在本 sprint 用 main agent self-audit 替代——M02 起恢复 | 🟡 | M02 sprint 启动时 |

## 3. 维护规则

- 每次 session 结束有遗留任务 → 来这里更新 / 加新 prompt
- prompt 跑完 → 移到 §2 历史，标 commit hash + 日期
- `last_updated` 字段反映最近一次写入

## 4. 关联

- 真实进度：`design/00-roadmap.md`（权威）
- 闸门规则：`design/00-phase-gate.md`
- 协作规约：`CLAUDE.md`
- 本周方法论沉淀：`design/audit/lessons-learned.md`
