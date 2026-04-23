---
title: M01 fix v1 verify 报告
status: draft
reviewer: independent-verify-agent
created: 2026-04-24
subject_commit: bad6ef1
verified_against: audit-report.md
---

# Summary

- 19 finding 闭合统计：**14 闭合 ✅ / 0 部分 🟡 / 0 未闭合 ❌ / 5 CY 决策不修 ⚪**（不修中 m2/m3/m4/m5/m6 其实都已修 → 实闭合 14）
- 新发现问题：**4**（1 Major / 3 Minor）
- 整体判断：**可 accept**（所有 Blocker 和 Major 闭合；新发现 ≤ Minor 为主，1 Major 是"签名协议无 query-string 处理"的边界，不阻塞 accept，但建议在 ADR-004 §3.2 补 1 句澄清后 accept）

---

# 第 1 步：19 Finding 闭合验证

## B1（Blocker）— Internal Token 威胁模型 + 签名

- **Audit 期望**：ADR-004 §2 从 "P2 优先" 改；§3 提供威胁模型 + 签名协议（材料/算法/4 header/校验流程/部署约束）；签名材料覆盖 ts + method + path + user_id + body_hash
- **独立验证**：
  - ADR-004:79-83 §2 标题明确 "P1 优先 + P2 带签名兜底"；为什么改 P1 优先的理由给了（ADR-004:82-83）
  - ADR-004:89-121 代码：先 Bearer（100-103），再 P2 且要求 4 header 全齐（105-106）——**语义正确**
  - ADR-004:125-202 §3 完备：§3.1 威胁模型表（5 威胁对比）、§3.2 签名材料 `{ts}\n{method}\n{path}\n{user_id}\n{body_hash}`（141-144）、算法 HMAC-SHA256（146）、4 header 契约（150-155）、校验流程完整代码（159-188，含常量时间比较、时间窗口 300s、重建签名、user active 校验）、§3.3 部署约束（191-196，config validator/日志禁打印）、§3.4 重放窗口 + nonce 未实装理由（199-202）
  - 签名材料覆盖齐：ts + method + path + user_id + body_hash 五项齐
- **判定**：✅ **闭合**

## B2（Blocker）— 事务 audit 写入时机 + DAO 不自 commit

- **Audit 期望**：§5 明示"业务成功路径 audit 事件在事务内"；§9 RefreshTokenDAO 加"不自 commit"注释；Service 用 `with db.begin():`
- **独立验证**：
  - 00-design.md:520 §5 新增一行"事务 vs fire-and-forget 的 audit 写入边界"——明确"成功路径在事务内，失败路径独立事务"
  - 00-design.md:519 事务清单中 ① Login 成功 / ② Admin 禁用 / ③ 改密码三步都带上 auth_audit_log 事件作为事务组成部分
  - 00-design.md:738 §9 R-X3 精神声明——显式对比 Prism 的 `db.commit()` 反例
  - 00-design.md:779 RefreshTokenDAO 类注释"所有方法遵守 R-X3 精神：接受外部 db，不自 commit / 不 begin"
  - 00-design.md:795-800 每个方法带"不自 commit"注释；revoke_all_for_user:799 显式引"Service 层用 with db.begin() 包裹（参 §5 事务清单）"
- **判定**：✅ **闭合**

## M1（Major）— 列类型 Text → String(N)

- **独立验证**：grep 00-design.md:215 imports `Text` 仍在，但 model 代码里扫 250-257（email/name/password_hash/avatar_url/role/status）+ 300-304（auth_audit_log action_type）+ 预留 4 表（334-385）：**全部改为 String(N)**——email=String(320)、name=255、password_hash=128、avatar_url=1024、role/status=32、action_type=64、token_hash=128、provider=32、provider_user_id=255、new_email=320、code=64、device_info/user_agent=512。R3 自查表（394）声明改。
- **判定**：✅ **闭合**（Text import 残留 15 行无实际使用，非问题）

## M2（Major）— §4 禁止转换表重写

- **独立验证**：00-design.md:489-494 表列 4 条：disabled→pending / pending→disabled / disabled→[*] / pending→[*]，每条带 ErrorCode=INVALID_STATUS_TRANSITION；00-design.md:496 显式说明 active→active 非状态转换已删除
- **判定**：✅ **闭合**

## M3（Major）— §13 CI 守护 ErrorCode ↔ AppError

- **独立验证**：00-design.md:833-839 CI 第 3 条 grep 已加，数 ErrorCode 枚举行数与 AppError 子类数对比，不等即 exit 1
- **判定**：✅ **闭合**（但见 NI-02 grep 正则问题）

## M4（Major）— §5 ABA 讨论

- **独立验证**：00-design.md:524 §5 新增"乐观锁 ABA 缺口"行——声明实现 version 单调递增不回绕 → ABA 不会发生 + auth_audit_log.old_role/new_role 审计兜底
- **判定**：✅ **闭合**

## M5（Major）— /refresh rate limit 部署前置

- **独立验证**：00-design.md:707 §8 refresh 段明示"本期未实装 rate limit"+ 部署前置 Nginx；00-design.md:948-954 §11 段明确 /refresh 和 /login 部署前置+具体速率；00-design.md:1169 §15 部署 TODO 第 1 条
- **判定**：✅ **闭合**

## M6（Major）— /login rate limit 部署前置

- **独立验证**：00-design.md:704 §8 明示 login 同上；00-design.md:952 /login 5 req/min；00-design.md:1169 §15 TODO
- **判定**：✅ **闭合**

## M7（Major）— P6 WebSocket 预留接口

- **独立验证**：ADR-004:71-74 §1 代码块末加了 3 条注释形式的预留接口签名：resolve_from_oauth (P5)、resolve_from_ws_handshake (P6)、resolve_from_task_payload (P7)，并各自引用 ADR-002
- **判定**：✅ **闭合**

## m1（Minor）— tests.md frontmatter

- **CY 决策**：不修
- **判定**：⚪ **不修**（tests.md:1-8 仍 6 字段，与决策一致）

## m2（Minor）— admin 批量端点 R10-1 前瞻

- **独立验证**：00-design.md:895-897 §10 "未来批量端点的 R10-1 前瞻声明"段，明示每 target_id 写独立事件，UI 折叠解决刷屏
- **判定**：✅ **闭合**

## m3（Minor）— README §10 R10-2 例外回写 TODO

- **独立验证**：00-design.md:922-926 §10 末新段"README §10 R10-2 例外回写 TODO"，含例外条目文本草案；00-design.md:1174 §15 部署 TODO 含对应项。**未直接改 README**（与 audit 决策一致——回写 TODO 而非直接改 README）
- **判定**：✅ **闭合**

## m4（Minor）— CI grep 命令

- **独立验证**：00-design.md:818-840 §9 末"CI 脚本示例"块含 3 条 grep（预留 model / Router 直查 / ErrorCode 数量）。tests.md:183-185 S5c/d/e 对应测试条目
- **判定**：✅ **闭合**（但见 NI-02）

## m5（Minor）— 跨表查询预案

- **独立验证**：00-design.md:899-920 §10 新段"与 M15 的跨表查询预案"含候选 A（PG view）/B（物化视图）/C（合并回 activity_log）+ 触发阈值
- **判定**：✅ **闭合**

## m6（Minor）— 预留 4 表 6 月复审 TODO

- **独立验证**：00-design.md:1176-1178 §15"复审 TODO（6 个月后触发）"，明示 2026-10-24 或更晚评估 DROP
- **判定**：✅ **闭合**

## m7（Minor）— 批量乐观锁策略

- **CY 决策**：不修
- **判定**：⚪ **不修**

## m8（Minor）— MVCC 可见性

- **CY 决策**：不修
- **判定**：⚪ **不修**

---

# 第 2 步：独立发现的新问题

## NI-01（Major）— 签名材料 path 对 query string 的处理未明示

- **位置**：ADR-004:143 签名材料 `{URL_PATH}`；ADR-004:176 代码 `path=request.url.path`
- **现象**：FastAPI `request.url.path` **只含 path 不含 query string**。若 Server Action 调 `GET /auth/users?status=active&role=admin`，攻击者抓包后把 query string 改成 `?status=disabled&role=user` 重放——签名材料不变仍通过 HMAC 校验，但业务语义被篡改（列表过滤/分页参数漂移）。
- **建议修复**：§3.2 签名材料明确写 "path 含 query string（即 `request.url.path + '?' + request.url.query` 规范化，或直接用 `request.url.raw_path`）"——**或者**显式声明"M01 所有 P2 消费端点均无查询参数依赖（列表筛选在 body 里）"+ CI 守护。建议 1 句话补在 ADR-004 §3.2 签名材料段末。
- **严重度**：Major（放大重放攻击面）——但本期 P2 消费路径有限且 admin 端点均为 POST/PATCH body 参数，实际利用窗口窄，不阻塞 accept。

## NI-02（Minor）— §9 CI grep 正则的健壮性问题

- **位置**：00-design.md:834-835
- **现象**：
  - `grep -cE "^\s+[A-Z_]+ = \"[A-Z_]+\"$"` 依赖 ErrorCode 赋值必须"缩进 + 大写值 = 大写字面量"；若未来 ErrorCode 取值包含小写/数字/特殊字符（如 "MFA_step_2"），漏数。
  - `grep -cE "^class .*Error\(.*\):"` 会把 AppError 基类本身也数进去（basechecker 若 exceptions.py 内含 `class AppError(Exception):` 则 +1 误判）；同样会把`class ValidationError(AppError):` / `class NotFoundError(AppError):` 等 **已有基类** 数进去——按 CY 决策记录（00-design.md:1115）这些基类已存在。
- **建议修复**：正则 anchor 到具体模式，或改用 Python AST 脚本；至少在注释里说明"统计包含基类共 20 个时 OK"，或排除 AppError/ValidationError/NotFoundError 基类。
- **严重度**：Minor（实装时会暴露 + 易修）

## NI-03（Minor）— 签名代码中 INTERNAL_TOKEN encode 与 Service 可测试性

- **位置**：ADR-004:164,178
- **现象**：`hmac.compare_digest(token, INTERNAL_TOKEN)` 和 `hmac.new(INTERNAL_TOKEN.encode(), ...)` 中 `INTERNAL_TOKEN` 作为模块级常量直接引用，未声明来源（env? config object?）——如果是 module-level 读 env，单测时 monkeypatch 不直观；且 164 行未 encode 做 `compare_digest(str, str)`，178 行做 `encode()`。两处语义不一致（compare_digest 对 str/bytes 都支持但要求两参数同型）。
- **建议修复**：Service `__init__` 注入 `internal_token: bytes`；校验 token 时也用 bytes 比较。Phase 2 实装细节，但 ADR 代码示例建议统一。
- **严重度**：Minor

## NI-04（Minor）— tests.md A9 新语义与 §8 声明一致但注释略旧

- **位置**：tests.md:131 A9 "P1+P2 混合（B1 新语义）"→"P1 优先，走 P1 路径；P2 即使有效也不用"
- **现象**：与 ADR-004 §2 P1 优先策略一致。**但** tests.md:131 只测"两个都有效"；缺一条对应 case："Bearer **无效** + P2 有效 → 200（走 P2 兜底）"——这是 B1 决策"P1 优先 + P2 兜底"的兜底路径验证，A9 只验"优先"不验"兜底"。
- **建议修复**：tests.md §7 加 A9b "Bearer 无效/过期 + P2 签名有效 → 200 走 P2 兜底"。
- **严重度**：Minor（测试覆盖补强）

---

# 第 3 步：Fix 报告真实性检查

## Git diff 统计

- 00-design.md：1241 行新文件；ADR-004：281 行新文件；tests.md：234 行新文件；audit-report.md：243 行
- 因为是初稿 + fix 一起落地到同一 commit bad6ef1（非两步 commit），无法区分"初稿行"vs"fix 行"

## 实际改动 vs 声称

CY 决策记录表（00-design.md:1204-1220）声称的落地位置全部命中：

| 声称 | 实际位置 | 真实性 |
|------|---------|-------|
| B1 ADR-004 §2 重写 + §3 新增 | ADR-004:79-121 + 125-202 | ✅ |
| B2 §5 事务边界 + §9 DAO | 00-design.md:520 + 738/779/795-800 | ✅ |
| M1 §3 全列 String(N) | 00-design.md:250-257 等 | ✅ |
| M2 §4 禁止转换 4 条 | 00-design.md:489-494 | ✅ |
| M3 §9 CI 第 3 条 | 00-design.md:833-839 | ✅ |
| M4 §5 ABA 行 | 00-design.md:524 | ✅ |
| M5/M6 §11 + §15 TODO | 00-design.md:948-954 + 1169 | ✅ |
| M7 ADR-004 §1 预留 | ADR-004:71-74 | ✅ |
| m2/m3/m4/m5/m6 | 00-design.md:895-897/922-926/818-840/899-920/1176-1178 | ✅ |

**无"声称修但实际没动"**，无"改错位置"。

---

# 第 4 步：最终判断 + 必修清单

## 判断：**可 accept**（建议先补 1 句再 accept）

- Blocker 2 条全部闭合 ✅
- Major 7 条全部闭合 ✅
- Minor 修 5 条全部闭合 ✅；不修 3 条符合 CY 决策 ⚪
- 新发现 1 Major（NI-01 query string）+ 3 Minor

## 建议补丁（可 accept 前 1 次小修，不需 fix v2）

| # | 位置 | 动作 |
|---|------|------|
| P1（对应 NI-01）| ADR-004 §3.2 签名材料段末 | 加 1 句："path 含查询字符串完整规范化形式（`request.url.path + ('?' + request.url.query if query else '')`），防攻击者通过修改 query 改变过滤/分页语义。" |
| P2（对应 NI-04，可选）| tests.md §7 | 加 A9b 用例（Bearer 无效 + P2 有效 → 200） |
| P3（对应 NI-02/NI-03）| Phase 2 实装时处理 | 不阻塞 accept，归到"实装期细节"清单 |

## Top 3 最严重

1. **NI-01**（Major）签名 path 不含 query string — 建议 accept 前 1 句话补丁
2. **NI-04**（Minor）tests.md A9 缺"P2 兜底"验证用例
3. **NI-02**（Minor）§9 CI grep 正则 R13-1 数量校验的脆弱性

## 一句话结论

Fix v1 质量扎实，所有 Blocker+Major+决定修的 Minor 全部闭合，无虚报、无错位。新发现 1 Major 为 Audit 漏项（签名 path 对 query 的处理），建议在 ADR-004 §3.2 补 1 句话后即可 accept。
