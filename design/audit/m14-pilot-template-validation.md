---
title: M14 sprint 实证 + R1/R2 命中比例 + L1 第十二数据点（**首个全局豁免业务模块** + 首发 write_event project_id Optional）
status: accepted
owner: CY
created: 2026-05-08
purpose: |
  M14 sprint 闸门 2.5 reconcile + R1/R2 review 沉淀（**首个全局豁免业务模块 / 首发 write_event project_id=None / 首发 owner-or-admin 替代 viewer 写 403 元教训**）。

  - 闸门 2.5 三栏：A 2 / B 0 / C 7（**第九次 B 栏 0 项**；M05+M06+M07+M08+M10+M11+M12+M13+M14 九连稳定）
  - R1=3 subagent 并行（spec+quality Opus 3 + reuse Sonnet 1 + quality+efficiency Sonnet 3 / 去重合并 6 P1 立修）
  - R2=1 合并 Opus subagent endpoint 单审（4 P1 立修）
  - L1+L2+L3 节奏第十二次实证 / M02-M14 默认范式作 M15+ 模板
  - 全局豁免业务模块首发新教训 3 条 sink（write_event 升 Optional / N/A 元教训显式声明 / endpoint 形态特殊不免除契约纪律）
last_reviewed_at: 2026-05-08
---

# M14 sprint 实证 + Review 命中比例

## 模块特性（与 M02-M13 对比）

| 维度 | M02-M08 业务 | M10 纯读 | M11 R-X1 | M12 R-X3 只读 | M13 LLM+SSE | **M14 全局豁免** |
|---|---|---|---|---|---|---|
| 写自表 | ✅ | ❌ | ✅ | ✅ | ❌ | ✅（2 表）|
| project_id 字段 | ✅ | N/A | ✅ | ✅ | N/A | **❌（首发 / design §9 豁免）** |
| tenant 过滤 DAO | ✅ | N/A | ✅ | ✅ | N/A | **❌ 显式豁免**（清单 5）|
| project role | ✅ | ✅ | ✅ | ✅ | ✅ | **❌（design §8 已登录即可写）** |
| owner-vs-admin 校验 | N/A | N/A | N/A | N/A | N/A | **✅（首发 _check_news_owner_or_admin）** |
| activity_log project_id | UUID | UUID | UUID | UUID | UUID | **None → "global"（首发 write_event Optional 升级）** |
| 关联跨 project node | N/A | N/A | N/A | N/A | N/A | **✅（design §1 灰区 2 ack 允许）** |
| 流式/异步 | ❌ | ❌ | ❌ | ❌ | ✅ SSE | ❌（同步 CRUD）|
| LLM 集成 | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| 文件上传 | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |

---

## 闸门 2.5 reconcile 三栏（**第九次 B 栏 0 项**）

| 栏 | 项数 | 关键项 |
|---|---|---|
| **A 机械可做** | 2 | A1 §14.5 sprint review 计划段补 / A2 元教训防御 actionable 主动复制（write_event 异常传播 service 层 + IntegrityError 区分约束名 + N/A 元教训显式声明）|
| **B 待 CY 决策** | **0** | （第九次 B 栏 0 项 / M05+M06+M07+M08+M10+M11+M12+M13+M14 九连稳定）|
| **C 已自我消解** | 7 | C1 R-X1 失败补偿 N/A / C2 文件上传 N/A / C3 LLM/SSE N/A / C4 R-X2 child service N/A / C5 viewer 写 403 N/A（design §8 已锁全局豁免无 project role）/ C6 cross-tenant 404 N/A（M14 无 tenant）/ C7 LLM hot path N/A |

---

## R1 review 命中（3 subagent 并行 / 子片 0+1+2+3 合并审 / 共 7 P1 / 去重合并 6 P1 立修）

### R1-A spec+quality Opus 命中（3 P1 立修 + 8 P2 punt）

| 命中 | 项 | 处理 |
|---|---|---|
| P1-1 | NewsResponse.linked_nodes 契约链断裂（NewsNodeLink 缺 node relationship → DAO 拿不到 node_name/project_id）| **立修** commit 6ab088d：model 加 NewsNodeLink.node relationship + DAO 全部双层 selectinload(node_links → node) |
| P1-2 | unlink_node 权限裁决型 spec 灰区未回写 disambiguation 注释（M12 元自审教训复用）| **立修** design §8 表新增 link/unlink 行 + 完整 disambiguation 注释段（已登录即可，与 IndustryNews 主资源 update/delete 不同）|
| P1-3 | update_news raw UPDATE + db.refresh 协议脆弱（与 M02-M13 ORM mutate 范式偏离）| **立修** 改 ORM mutate (setattr + flush) 替代 dao.update raw SQL，最后 _get_or_raise 重新带 selectinload |

### R1-B reuse Sonnet 命中（1 P1 立修 + 1 P2 punt）

| 命中 | 项 | 处理 |
|---|---|---|
| P1-01 | _make_news 内联 12 处 → 迁 conftest 作 make_news fixture（**跨文件 helper 规则十连**：M03 / M04 / M05 / M06 / M07 / M08 / M10 / M11 / M12 / M13 / M14）| **立修** tests/conftest.py 加 make_news fixture / tests/test_m14_dao.py 12 处调用迁移 |

### R1-C quality+efficiency Sonnet 命中（3 P1 立修 + 3 P2 punt）

| 命中 | 项 | 处理 |
|---|---|---|
| P1-1 | update_news fields 过滤 v is not None 误吞 tags=[] 清空操作语义 | **立修**（与 R1-A P1-3 合并）改 ORM mutate + 不滤 None；caller 用 model_dump(exclude_unset=True) 控制；source_type 仍强滤 |
| P1-2 | page/page_size <= 0 行为不可预测（LIMIT 0 返空） | **立修** DAO list_all 入口 ValueError 拒绝；FastAPI Router Query ge=1 双层兜底（router 层 422 / DAO 层 ValueError 单元测试覆盖）|
| P1-3 | tags 单元素无 max_length 约束（与 title max_length=200 严密性不一致）| **立修** schema NewsCreate + NewsUpdate 加 field_validator 共用 _check_tag_lengths（max_length=50）|

**R1 P1 立修汇总（去重合并 6 项）**：commit `6ab088d`
- A1 NewsNodeLink.node relationship + DAO 双层 selectinload + e2e 链通验证
- A2 + B 路径合一：design §8 + 测试 + service 层联动 disambiguation
- A3 + C1 合并：update_news ORM mutate（解决 raw UPDATE 协议脆弱 + None 滤吞清空操作）
- B1 make_news 迁 conftest（跨文件 helper 规则十连）
- C2 page/page_size <= 0 ValueError + 三路径单元测试
- C3 tags max_length=50 + 2 schema 单元测试

---

## R2 review 命中（1 合并 Opus subagent / 子片 4 endpoint 单跑 / 4 P1 立修 + 4 P2 punt）

| 命中 | 项 | 处理 |
|---|---|---|
| P1-1 | write_event 异常传播 e2e 5 写路径 0 用例（M04+ 范式纪律失守）| **立修** commit 059c7ea 补 2 e2e（create + link 路径 500 / 其余 3 路径 service 层已覆盖 punt 池）|
| P1-2 | design §10 字面 metadata 字段集 e2e 0 断言（M13 NEW 失效信号"design metadata 字段集每条都必须实装 + e2e 字面验证"复用失守）| **立修** 补 2 e2e（create set 严格断言 = {source_type, tags_count} + link node_id 字面 + project_id=None 全局豁免）|
| P1-3 | list_news_by_node 分页字段语义漂移（page_size=len(responses) or 1 → 空列表 page_size=1 与 items=[] 矛盾）| **立修** 选修法 (b)：disambiguation 不分页（page=1 / page_size=total / 空列表 page_size=0）+ design §7 endpoint 表注释字面 + e2e 验空列表 page_size=0 |
| P1-4 | source_type 用户绕过守卫 e2e 0 用例（design §3 灰区 1 字面"service 层拒绝创建非 manual 的记录"）| **立修** 补 2 e2e（create + update 路径源 source_type='rss' → 落 manual）|

**M14 R2 命中 4 项**（M02-M13 R2 P1 0-1 + M11 R-X1 首发 3 P1 + M12 R-X3 1 裁决型 + M13 LLM+SSE 首发 4 项）→ 第十二数据点 R2 范式全局豁免业务模块首发命中合理；下个全局豁免模块（M15 / M14 baseline-patch）应能压到 1-2 P1。

---

## L1+L2+L3 节奏第十二次实证（**十二数据点稳定 → M15+ 默认范式作模板**）

| 层 | 内容 |
|---|---|
| L1 总则 | sprint ≥1 次 review + ≥50 行 OR ≥2 文件触发；触发例外条款全合规 |
| L2 sprint 计划 | design §14.5 sprint review 拆分计划段（commit 3afbbdb 子片 0 prep 落地 / 全局豁免业务模块特化）|
| L3 实证回写 | 本文件 |

**M14 默认范式（M02-M13 复用 + 全局豁免业务模块首发增强）**：
- R1 = 3 subagent 并行（spec+quality Opus / reuse Sonnet / quality+efficiency Sonnet）
- R2 = 1 合并 Opus subagent endpoint 单审
- 子片 5 不单跑（≥80% SKIP 例外）
- M14 schema 子片合并到 R1（≥80% SKIP）
- 全局豁免业务模块首发增强：R1 必审 DAO 类 docstring "GLOBAL DATA — NO TENANT FILTER" 字面 + Service _check_news_owner_or_admin 含 platform_admin 豁免；R2 必审 viewer 写 / cross-tenant 元教训 N/A 显式声明

---

## 元教训防御 actionable 应用情况（**M14 R1+R2 主动复制不等抓** / **9 项元教训应用结果**）

| # | 元教训 | M14 应用结果 |
|---|---|---|
| 1 | viewer 写所有写端点 403 全覆盖（M07 立 / M08+M11+M12+M13 应用 / 第 9-10 数据点）| **✅ N/A 显式声明**（design §8 已锁全局豁免无 project role；测试文件 docstring + design §14.5 字面声明）|
| 2 | write_event 异常传播测试（M04+ 范式）| **R1 ⚠️ service 层覆盖（create + link）→ R2 ❌ e2e 0 用例 → R2 P1-1 立修 ✅ 补 2 e2e** |
| 3 | cross-tenant 404（M02 范式）| **✅ N/A 显式声明**（M14 无 tenant；用 owner-vs-other 403 + 已登录 401 替代覆盖跨用户写防御）|
| 4 | cross-project node 404（M06+M07+M08+M12+M13 / 3 端点全覆盖原则）| **部分适配 ✅**（design §1 灰区 2 ack：link 端点反向断言 cross-project 允许；list_by_node + unlink 端点 N/A 合理 — node 不存在则 link 必无；与 M13 元自审"SSE 形态特殊不免除"对照下 M14 是真 N/A 不破例）|
| 5 | IntegrityError 区分约束名（M05 P1-01）| **✅** uq_news_node_link 显式映射 NewsLinkDuplicateError（test_link_node_duplicate_returns_409）|
| 6 | M12 元自审 — L1 锁裁决型 P1 自决不让 CY 拍 | **✅ 多处自决**（link/unlink 已登录即可 + cross-project 允许 + list_by_node 不分页 disambiguation 全部自决落 design 注释）|
| 7 | R1.5 reconcile checkpoint（M10 NEW）| **✅** R1 立修对 R2 dispatch 前 grep 验证 / R2 抓出 P1 与 R1 立修无冲突（属 R1 漏检不是反复）|
| 8 | M11 NEW R-X1 失败补偿 commit boundary | **N/A**（M14 无 R-X1 orchestrator）|
| 9 | M11 NEW 文件上传 file.size + sanitize | **N/A**（M14 无上传）|
| 10 | M13 NEW "3 端点全覆盖"原则 SSE 形态特殊不免除 | **✅** list_by_node 形态特殊但分页字段漂移 R2 P1-3 抓出（同思想：形态特殊不免除契约纪律）|
| 11 | M13 NEW design metadata 字段集每条都必须实装 + e2e 字面验证 | **R1 ❌ 0 断言 → R2 P1-2 立修 ✅ 补 2 e2e（create + link 字面）** |

---

## 全局豁免业务模块首发新教训 3 条 sink（M15+ baseline-patch 复制 / sink memory）

### 新教训 1：write_event project_id 类型必须 Optional[UUID]
**Why**：M02-M13 全模块都强 project_id；M14 是首个全局共享数据模块（design §9 + 06-design-principles 清单 5 豁免）。write_event 签名原 UUID 强制——M14 必须改 UUID | None。
**How to apply**：M15 ActivityLog 实装时 add column NULLABLE + UI 时间线为"全局事件"分组；structlog stub None 序列化为字面 "global"（scaffold 简化决策注释 4 字段已沉淀 api/services/activity_log_service.py）。

### 新教训 2：N/A 元教训必须显式声明
**Why**：M14 全局豁免使 viewer 写 403 / cross-tenant 404 两条核心元教训不再适用；若 R1+R2 prompt 不显式说明 N/A，reviewer 容易把"未覆盖"当 P1 抓 → 噪音 P1。
**How to apply**：每个新模块若有元教训 N/A 必在 design §14.5 sprint review 计划段 + 测试文件 docstring 双重显式声明（被 R1+R2 prompt 引用作豁免证据）。

### 新教训 3：endpoint 形态特殊不免除契约纪律（M13 NEW 复用 + 强化）
**Why**：M13 SSE 形态 + M14 list_by_node 不分页形态——两次特殊形态都触发了"design 字面 vs 实装"漂移（M13 cross-project node 404 漏 / M14 NewsListResponse 复用未 disambiguate 是否分页）。规律：endpoint 形态特殊（流式 / 关联表 / 反查）反而更需要 design disambiguation 注释字面，否则 review 抓不到。
**How to apply**：M15+ 任何形态特殊 endpoint（自定义返回结构 / 复用通用 schema / 流式 / 反查）必在 design §7 endpoint 表 + §14.5 sprint review 计划段双重 disambiguation 注释；R1 必审 design §7 字面 vs 实装是否需要 disambiguation。

---

## 元自审教训（无主流程错误）

M14 sprint **无主流程错误**——R1+R2 命中均按 M02-M13 范式处理：
- 闸门 2.5 三栏第九次 B 0 项稳定
- L1 R-X3 范式既锁裁决型 P1 全部 AI 自决（M12 元自审教训应用合规）
- "3 端点全覆盖"M13 元自审教训应用合规（list_by_node 形态特殊抓出而非免除）
- R1.5 reconcile checkpoint M10 元教训应用合规（R1+R2 立修无冲突）

---

## design 回写（关闸 commit 同 commit）

- §6/§9 同步代码示例（`db.query()` / `Session`）写于 2026-04-21；实施按 async 范式落地（M02-M13 子片 5 关闸惯例延续）
- §7 endpoint 表 list_news_by_node 添加 disambiguation 注释字面（R2 P1-3 立修 / "不分页：page=1 / page_size=total / 空列表 page_size=0"）
- §8 权限三层防御点表新增 link/unlink 行 + 完整 disambiguation 注释段（R1-A P1-2 立修）
- §10 metadata 字段集与实装对齐：create {source_type, tags_count} / update {updated_fields:[...]} / delete {title} / link {node_id, news_title} / unlink {node_id, news_title}
- §13 4 ErrorCode AppError 子类 http_status 表（404/409/404/403）已与实装对齐
- §15 完成度 checklist 三轮 reviewer audit 勾选

---

## Punt 池总表（M14 sprint 完成期 / 后续 sprint 顺手清）

| # | 项 | 来源 | 推荐时机 |
|---|----|------|---------|
| B1 | link_node IntegrityError race FK 路径未映射成 NOT_FOUND（与 M02-M13 race 池一致归 punt）| R1-A | M02-M13 race 池统一处理 |
| B2 | _check_node_exists 用基类 NotFoundError 非独立 NEWS_NODE_NOT_FOUND code | R1-A | M14 baseline-patch 时 CY 拍是否升 |
| B3 | create_news published_date: Any 类型卫生 | R1-A | 关闸 simplify |
| B4 | DAO update 接受任意 dict 无字段白名单（caller 责任）| R1-A | 防御加固 |
| B5 | list_all total count 双查 vs window function | R1-A | 性能 sprint |
| B6 | unlink_node get_by_pair + delete_by_pair 双查 round-trip | R1-A | 性能 sprint |
| B7 | _make_news fake_httpx 内联（M16 M17 sprint 启动评估）| R1-B | M16/M17 sprint 启动时再评估 |
| B8 | _to_response 列表 N+1（每 item db.get(User)） | R2 | 性能 sprint / M16+ 引入 selectinload(creator) 时统一 |
| B9 | link_node router 重复查询（service 已建 link → router 再 get_by_pair + selectinload） | R2 | 子片 5 simplify |
| B10 | update_news router 二次 svc.get_news 与 service 内部 _get_or_raise 重复 | R2 | 子片 5 simplify |
| B11 | NewsCreate 未 extra='forbid' 全 schema 立规（防御性立规）| R2 | 与 P1-4 配套 / 全 schema 立规候选 |
| B12 | write_event 异常传播 e2e 仅补 create+link 两路径；update/delete/unlink 三路径 punt | R2 | M14 baseline-patch / 与其他端点形态稳定后统一立 |

---

## sprint 总览数据

- **commits**：7 主提交
  - 3afbbdb 子片 0 prep（§14.5 sprint review 计划段）
  - c2858f7 子片 1（IndustryNews + NewsNodeLink models + alembic + 9 model tests）
  - 968b284 子片 2（IndustryNewsDAO + NewsNodeLinkDAO + 18 unit tests / GLOBAL DATA NO TENANT FILTER 字面）
  - e184c8b 子片 3（IndustryNewsService + 4 ErrorCode + AppError + Pydantic schema + 35 unit/schema tests / write_event project_id Optional 升级 / source_type 强制 manual）
  - 6ab088d R1 6 P1 立修（3 subagent 并行去重合并：NewsNodeLink.node relationship + design §8 disambiguation + ORM mutate + make_news conftest + page validation + tags max_length）
  - 9028875 子片 4（Router 8 endpoints + 27 e2e）
  - 059c7ea R2 4 P1 立修（write_event e2e 2 + metadata e2e 2 + list_by_node disambiguation + source_type 守 e2e 2）
  - 子片 5 关闸 commit（本 audit + roadmap + handoff + design 回写）
- **测试**：930 PASS / 4 skipped / R13-1 86→90（+4）/ L12 守护通过
- **新增 ErrorCode**：4（NEWS_NOT_FOUND / NEWS_LINK_DUPLICATE / NEWS_LINK_NOT_FOUND / NEWS_FORBIDDEN）
- **新增 endpoints**：8（GET /news / GET /news/{id} / POST /news / PUT /news/{id} / DELETE /news/{id} / POST /news/{id}/links / DELETE /news/{id}/links/{node_id} / GET /nodes/{id}/news）
- **新增模型**：2（IndustryNews + NewsNodeLink）
- **新增表**：2（industry_news + news_node_links）
- **新增横切 helper 升级**：write_event project_id UUID → UUID | None（首发全局豁免支持 / scaffold 简化决策 4 字段注释 / M15 实装时 NULLABLE column）
- **新增 conftest fixture**：make_news（跨文件 helper 规则十连）
- **跨模块接通**：M03 NodeService 只读（_check_node_exists）/ M01 User 只读（_to_response 拼 created_by_name）
- **复用率**：~90%（service 层 100% / conftest fixtures 全调用 / R1-B 立修后 helper 100% 在 conftest）
- **首发新教训**：3 条（write_event project_id Optional / N/A 元教训显式声明 / endpoint 形态特殊不免除契约纪律 M13 NEW 复用强化）

---

## 关联

- design 真相源：design/02-modules/M14-industry-news/00-design.md
- 上游决策：06-design-principles 清单 5（全局豁免）+ ADR-003 规则 1（跨模块只读 _check_node_exists）+ ADR-004 P1（已登录即可读+写 require_user）
- 跨 sprint 元教训沉淀候选：feedback_problem_layered_analysis（M14 N/A 元教训显式声明 + endpoint 形态特殊不免除契约纪律）/ feedback_design_scaffold_reconcile（M14 全局豁免 unlink disambiguation 回写 design 范式延续）
