---
module: M14
name: industry-news
created: 2026-05-12
generator: P1-testpoint subagent
references:
  - design/02-modules/M14-industry-news/00-design.md
  - design/02-modules/M14-industry-news/tests.md
  - design/00-architecture/01-PRD.md
  - design/00-architecture/06-design-principles.md
prd_ref: F14 行业动态（v0.2 - 能分析、能对比、能追踪）/ US-B2.4
---

# M14 行业动态 测试点

## 业务流程（H1 / 1 行概述）

M14 是首个全局豁免业务模块：编辑者手动录入行业动态（manual source_type CHECK 约束 / 无 tenant / 已登录即可读+写）/ 关联到一/多个跨项目 node / Service 层 owner-or-admin 校验 update/delete / 5 个过去式 action_type 写 activity_log 非事务。

## 测试点（H2 / 按 15 角度）

### 1. 功能性

- [P0] POST /api/news 已登录用户 happy path 返 201 + source_type="manual" + activity_log 写 news_created（design §7 + §10 + tests.md G1）
- [P0] GET /api/news 无过滤返 200 + items 按 created_at DESC + total（design §3 index + tests.md G2）
- [P0] GET /api/news/{news_id} 详情含 linked_nodes 空时返 [] 非 null（design §7 NewsResponse + tests.md G3 / E5）
- [P0] PUT /api/news/{news_id} 本人改 title+summary 返 200 + activity_log 写 news_updated 含 metadata.updated_fields（design §10 + tests.md G4）
- [P0] POST /api/news/{news_id}/links 关联 node 返 201 + activity_log 写 news_linked 含 metadata.node_id（design §7 + §10 + tests.md G5）
- [P0] DELETE /api/news/{news_id} 本人删除返 204 + activity_log 写 news_deleted（design §10 + tests.md G6）
- [P1] DELETE /api/news/{news_id}/links/{node_id} 解除关联返 204 + activity_log 写 news_unlinked（design §7 + §10）
- [P1] GET /api/nodes/{node_id}/news 某 node 反查动态返不分页全集（design §7 disambiguation 2026-05-08）
- [P1] GET /api/news?tag=AI 按单标签过滤命中 GIN 索引（design §3 ix_industry_news_tags + §7）
- [P1] POST /api/news tags=[] 空数组合法接受默认值（design §3 default=list）
- [P1] PUT /api/news/{news_id} 仅传 tags 字段其他字段保留原值（design §7 NewsUpdate Optional）
- [P2] POST /api/news published_date=null 合法接受（design §3 nullable + §7 Optional）

### 2. 边界 / 状态机

- [P0] M14 无状态字段 industry_news 表无 status 列（design §4 显式无状态声明）
- [P1] POST /api/news title 超 200 字返 422 VALIDATION_ERROR（design §7 max_length + tests.md E1）
- [P1] POST /api/news title="" 空标题返 422（tests.md E2）
- [P1] POST /api/news title 恰 200 字边界接受 201（design §7 max_length=200）
- [P1] GET /api/news?page=9999 超出总数返 200 + items=[] 不报错（tests.md E4）
- [P1] GET /api/news?page_size=0 边界处理（design §7 NewsListResponse）
- [P2] POST /api/news source_url="not-a-url" 非合法 URL 返 422（tests.md E6）

### 3. 异常 / 错误

- [P0] GET /api/news/{随机 UUID} 不存在返 NEWS_NOT_FOUND 404（design §13 + tests.md ER1）
- [P0] POST /api/news/{news_id}/links 重复同一 node_id 第二次返 NEWS_LINK_DUPLICATE 409（DB UNIQUE 约束 + design §13 + tests.md ER2）
- [P0] POST /api/news/{news_id}/links node_id 不存在返 NOT_FOUND 404（Service 层 node 存在校验 + tests.md E3）
- [P0] Service 层 source_type 非 manual 创建被拒绝（design §3 CHECK 约束 + §1 灰区 1 service 层拒绝）
- [P1] DELETE /api/news/{news_id}/links/{node_id} 关联不存在返 NEWS_LINK_NOT_FOUND 404（design §13 + tests.md ER3）
- [P1] activity_log 写失败不回滚主操作（design §10 非事务声明 / news_created 已落但 log 缺）
- [P1] DB IntegrityError 非 UNIQUE 约束返 INTERNAL_ERROR 不暴露 SQL（design §13 兜底 + tests.md ER4）
- [P1] news_node_links UNIQUE(news_id, node_id) IntegrityError 必区分约束名映射 NEWS_LINK_DUPLICATE 而非 INTERNAL_ERROR（design §14.5 M05 P1-01 元教训复用）
- [P2] DELETE /api/news/{news_id} 不存在的 news_id 返 NEWS_NOT_FOUND 404（design §13）

### 4. 权限 / Auth

- [P0] 未登录 GET /api/news 返 UNAUTHENTICATED 401（design §8 Server Action 层 + tests.md P1）
- [P0] 未登录 POST /api/news 返 UNAUTHENTICATED 401（design §8 + tests.md P2）
- [P0] 非本人 DELETE /api/news/{news_id} 返 NEWS_FORBIDDEN 403（design §8 Service _check_news_owner_or_admin + tests.md P3）
- [P0] 非本人 PUT /api/news/{news_id} 返 NEWS_FORBIDDEN 403（design §8 + tests.md P5）
- [P0] platform_admin DELETE 他人 news 返 204 admin 豁免本人校验（design §8 + tests.md P4）
- [P1] platform_admin PUT 他人 news 返 200 admin 豁免（design §8 owner-or-admin）
- [P1] 已登录用户 A POST /api/news/{B 创建的 news_id}/links 返 201（link 不限 owner / design §8 R1-A P1-2 立修 2026-05-08）
- [P1] 已登录用户 A DELETE /api/news/{B 创建的 news_id}/links/{node_id} 返 204（unlink 已登录即可 / 与 link 对称）
- [P1] M14 写端点不要求 editor/owner project role（design §8 + §14.5 viewer 403 元教训 N/A 显式声明）
- [P2] M14 不存在 owner-only NewsNodeLink 校验代码路径（design §8 disambiguation）

### 5. Tenant 隔离

- [P0] userA(projectA) 与 userB(projectB) GET /api/news 返完全相同列表（design §9 全局豁免 + tests.md T1）
- [P0] 新注册用户未加入任何项目 GET /api/news 返 200 + 全局列表（tests.md T2 / 全局数据无需项目归属）
- [P0] IndustryNewsDAO docstring 含字面 "GLOBAL DATA — NO TENANT FILTER" + 引用 06-design-principles 清单 5 豁免（design §9 line 391 字面 + §14.5 R1 必 grep 字面对齐）
- [P1] IndustryNewsDAO.list_all() 方法签名不接受 project_id 入参（design §9 + §14.5 GLOBAL 豁免专属红线）
- [P1] userA 关联 projectB 的 node_id 返 201（node 存在则允许 / design §灰区 2 cross-project node 允许 + tests.md T4）
- [P1] userA 关联随机不存在 node_id 返 NOT_FOUND 404（Service 校验 node 存在 / tests.md T4）
- [P1] M14 不依赖 M02（project 模块）/ industry_news 表无 project_id 列（design §2 独立性 + §3 ER 图）

### 6. 并发 / 乐观锁

- [P0] 两人 asyncio.gather 同时 DELETE 同一 news_id 一个 204 一个 NEWS_NOT_FOUND 404 不报 500（tests.md C1）
- [P0] 两人 asyncio.gather 同时 POST /links 同 node_id 一个 201 一个 NEWS_LINK_DUPLICATE 409 DB UNIQUE 兜底（tests.md C2 + design §3 UNIQUE 约束）
- [P1] M14 无 version 字段 industry_news 表无乐观锁（design §5 4 维 并发 ❌ + 清单 2 不触发）
- [P2] 两人同时 PUT 同 news 后写者覆盖前写者（无乐观锁 / 设计 ack 全局信息流录入者各管各的 design §5）

### 7. 数据完整性

- [P0] industry_news.source_type CHECK 约束 ck_industry_news_source_type_manual 仅允许 'manual'（design §3 + §1 灰区 1）
- [P0] news_node_links UNIQUE(news_id, node_id) 约束 uq_news_node_link 存在（design §3）
- [P0] industry_news.title NOT NULL（design §3 Mapped[str]）
- [P1] industry_news.tags PG text[] 默认空数组非 null（design §3 default=list）
- [P1] industry_news.created_by FK users.id NOT NULL（design §3）
- [P1] news_node_links.news_id FK ON DELETE CASCADE 删 news 关联级联删（design §3）
- [P1] news_node_links.node_id FK ON DELETE CASCADE 删 node 关联级联删（design §3）
- [P1] industry_news.summary / source_url / published_date nullable（design §3）
- [P2] ix_industry_news_created_at 索引存在支持时间倒序分页（design §3 + §9 list_all order_by）
- [P2] ix_industry_news_tags GIN 索引存在支持数组检索（design §3 postgresql_using="gin"）
- [P2] ix_news_node_link_node 索引存在支持反查某 node 的相关动态（design §3 + §7 GET /api/nodes/{node_id}/news）

### 8. UI / UX

- [P1] 动态列表卡片按 created_at DESC 渲染含关联功能项 tag（design §6 news-card + §7 NewsResponse linked_nodes）
- [P1] 录入表单 title 输入超 200 字前端拦截+提示（design §6 news-form + §7 max_length）
- [P1] 关联功能项 picker 展示 node 名称含项目归属信息（design §6 node-link-picker + §7 NewsNodeLinkResponse.node_name）
- [P1] 重复关联同一 node 前端 toast NEWS_LINK_DUPLICATE 文案"该功能项已关联"（design §13 message）
- [P2] 非本人编辑按钮不可见或点击后 toast NEWS_FORBIDDEN（design §13 message + §8 三层防御）
- [P2] linked_nodes 为空时卡片显示"未关联功能项"占位文案（design §7 + tests.md E5）

### 9. 性能 / 容量

- [P2] GET /api/news 大数据量 10k 条命中 ix_industry_news_created_at 索引分页 <500ms（design §3 index + §7 分页）
- [P2] GET /api/news?tag=X 命中 GIN 索引返回时间随标签筛选维持稳定（design §3 ix_industry_news_tags）

### 10. activity_log 事件完备性（M14 produces 5 action_types）

- [P0] news_created 写 1 行 metadata 含 source_type/tags_count（design §10）
- [P0] news_updated 写 1 行 metadata.updated_fields 列改动字段名（design §10）
- [P0] news_deleted 写 1 行 metadata 含 title 快照（design §10 / 删除后 join 不到主表用 metadata 还原）
- [P1] news_linked 写 1 行 target_type=news_node_link / metadata 含 node_id 和 news_title（design §10）
- [P1] news_unlinked 写 1 行 metadata 含 node_id 和 news_title（design §10）
- [P1] 5 个 action_type 字面全为过去式 {entity}_{past_verb}（design §10 + frontmatter line 47 反向回写命名规约）
- [P1] M14 不订阅 M15 activity_log consumes_action_types=[]（design frontmatter line 44）
- [P2] activity_log 写失败不回滚主操作 Service 层非事务调用（design §10 line 451）

### 11. ErrorCode 映射

- [P1] NEWS_NOT_FOUND 映射 NewsNotFoundError 继承 NotFoundError 返 404（design §13 + R13-1）
- [P1] NEWS_LINK_DUPLICATE 映射 NewsLinkDuplicateError 返 409（design §13）
- [P1] NEWS_LINK_NOT_FOUND 映射 NewsLinkNotFoundError 返 404（design §13）
- [P1] NEWS_FORBIDDEN 映射 NewsForbiddenError 返 403 message "Only the creator or platform admin can modify this news"（design §13）
- [P1] 复用 UNAUTHENTICATED / NOT_FOUND（design §13 + frontmatter codes_used）

### 12. CI 守护 / 设计漂移防御

- [P1] CI grep 守护 IndustryNewsDAO docstring 含 "GLOBAL DATA — NO TENANT FILTER" 字面（design §9 + §14.5）
- [P1] CI grep 守护 IndustryNewsDAO 方法签名不接受 project_id 参数（design §9 豁免 + §14.5 GLOBAL 豁免红线）
- [P1] CI grep 守护 service 层 source_type 只允许 'manual'（design §1 灰区 1 service 层 + §3 CHECK 约束双重）

### 13. idempotency / Queue（显式 N/A）

- [P2] POST /api/news 重复提交相同 title+created_by+published_date 允许多条（无 DB UNIQUE / design §11 无 idempotency 决策）
- [P2] DELETE /api/news/{news_id} 重复调用第二次返 NEWS_NOT_FOUND 404 天然幂等（design §11）
- [P2] M14 不投递 Queue 任务（design §12 显式 N/A 声明）

### 14. 跨模块只读契约（M14 → M03）

- [P1] POST /api/news/{news_id}/links 时 Service 调 M03 nodes 表校验 node_id 存在（design §2 cross_module_reads + frontmatter line 39）
- [P1] M14 不校验 node 的 project 归属允许跨项目关联（design §灰区 2 + §14.5 cross-project node 自然 N/A）
