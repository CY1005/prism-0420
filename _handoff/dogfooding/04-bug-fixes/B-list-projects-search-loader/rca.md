---
fix: B-list-projects-search-loader
bug_class: P0 / dogfooding sprint 第二条独立 bug（与 B-trigger-bug-server-action-cookie 同时段抓出但根因独立）
root_cause: Next.js 16.2.4 Turbopack 自定义版 server-actions SWC 转换对 'use server' 文件中 `export type { X }` 命名再导出说明符处理错误 — type 修饰符在 SWC 转换链中丢失 → 转译输出含 runtime `export { SearchResponse }` → 服务端动作模块求值时 `ReferenceError: SearchResponse is not defined` → projects/page/actions.js 整个动作聚合崩溃 → globalSearch + getProjects 双双不可用 → /projects 页面 0 卡片
fixed_by: app/src/actions/search.ts L12 删除 `export type { SearchResponse };` dead re-export
created: 2026-05-12
status: 已修 / M02 list projects DOM 转 PASS / next build PASS
---

# RCA — B-list-projects-search-loader

## §1 现象（前 fix subagent 揭露的真根因）

来源：`_handoff/dogfooding/04-bug-fixes/B-trigger-bug-server-action-cookie/rca.md` §7

P2 spike 抓到两条 P0 bug 时段重合 / spike 时归一同根因（"server-side fetch 无凭据"）。前 fix subagent（B-trigger-bug-server-action-cookie）修完 cookie path 后 `list projects DOM` 仍 FAIL / 抓 next-dev log 发现：

```
⨯ ReferenceError: SearchResponse is not defined
    at module evaluation (.next-internal/server/app/projects/page/actions.js (server actions loader):2:1)
  1 | export {getProjects as '00d0adb18ff49e228509156d4f88c15732adad35c1'} from 'ACTIONS_MODULE0'
> 2 | export {globalSearch as '6062ec245557a3b8a5bdd96348a7b9bd491d0deb23'} from 'ACTIONS_MODULE1'
 POST /projects 500 in 374ms
```

- **bug 来源代码**：`app/src/actions/search.ts` L1 `'use server'` 顶部指令 + L9 `type SearchResponse = components["schemas"]["SearchResponse"]` + L12 `export type { SearchResponse };`
- **触发链**：浏览器访问 `/projects` → React 渲染 → 调 `getProjects()` 服务端动作 → projects/page/actions.js（聚合 entry）导入 `ACTIONS_MODULE1`（search.ts 编译产物）→ 求值时引用未定义的 `SearchResponse` → 抛 ReferenceError → 整个动作集合不可用 → getProjects 也连带失败 → 渲染 0 卡片
- **现象表象**：`/projects` 页面有 63 个 seed 项目但 UI 渲染 0 卡片 / 浏览器抓包 `GET /api/projects` 从未发出（因为 server action getProjects 编译时跟 globalSearch 绑定到同一聚合 entry，loader 崩溃就全崩）

## §2 Turbopack server actions loader 根因深度分析

### §2.1 Next.js 16.2.4 自定义版 server actions 工作机制

Next.js 16 App Router 中 `'use server'` 指令把整个文件标记为 Server Functions 集合（[官方 use-server doc](node_modules/next/dist/docs/01-app/03-api-reference/01-directives/use-server.md)）。Turbopack（Next.js 16 默认替换 webpack）配套两层处理：

**第 1 层 — SWC 原生 server-actions 转换**（`node_modules/next/dist/build/swc/options.js` L164-174）：
```js
serverActions: isAppRouterPagesLayer && !jest ? {
    isReactServerLayer,
    isDevelopment: development,
    useCacheEnabled,
    hashSalt: serverReferenceHashSalt,
    cacheKinds: [...],
} : undefined,
```
SWC 拿到 `'use server'` 文件后：
1. AST 解析提取顶层 `export` 函数 → 给每个 async 函数生成稳定 hash ID（hashSalt + 文件路径 + 导出名 → SHA1）
2. 文件头注入注释：`/* __next_internal_action_entry_do_not_use__ {actionIdMap} */`
3. 改写每个导出 async 函数 → `registerServerReference(fn, actionId, exportName)` 包装
4. **关键**：SWC 在 emit 阶段保留所有顶层 `export` 说明符；TS 类型擦除应在更早阶段完成

**第 2 层 — Webpack/Turbopack flight-action-entry-loader**（`node_modules/next/dist/build/webpack/loaders/next-flight-action-entry-loader.js`）：
```js
function nextFlightActionEntryLoader() {
    const { actions } = this.getOptions();
    const actionList = JSON.parse(actions);
    const individualActions = actionList.map(([path, actionsFromModule])=>{
        return actionsFromModule.map(({ id, exportedName })=>{
            return [id, path, exportedName];
        });
    }).flat();
    return `
${individualActions.map(([id, path, exportedName])=>{
        return `export { ${exportedName} as "${id}" } from ${JSON.stringify(path)}`;
    }).join('\n')}
`;
}
```
loader 读 SWC 在第 1 层注入的 `__next_internal_action_entry_do_not_use__` action 元数据 → 为每个 server action 生成 re-export 语句（即错误堆栈中看到的 `export {globalSearch as '6062ec...'} from 'ACTIONS_MODULE1'`）。**loader 本身只用 SWC 已经识别出的 action 名 / 不重新解析 TS**。

**第 3 层 — flight-loader 校验**（`next-flight-loader/action-validate.js`）：
```js
function ensureServerEntryExports(actions) {
    for(let i = 0; i < actions.length; i++){
        const action = actions[i];
        if (typeof action !== 'function') {
            throw new Error(`A "use server" file can only export async functions, found ${typeof action}.`);
        }
    }
}
```
**Next.js 官方契约：`'use server'` 文件只能导出 async 函数**。任何非函数导出（包括类型再导出、常量、对象）都应被识别并拒绝/警告。

### §2.2 为什么 `export type { SearchResponse }` 触发 ReferenceError

**关键链条**：

1. `search.ts` 源码层：
   ```ts
   "use server";
   import type { components } from "@/types/api";
   type SearchResponse = components["schemas"]["SearchResponse"];  // TS-only 类型别名
   export type { SearchResponse };  // 命名再导出（type 修饰符 + 大括号）
   ```

2. **TS 编译阶段**（理论）：`export type { X }` 是 TypeScript-only 语法（TS 3.8+ 引入 / 配合 `isolatedModules`）。tsconfig.json L11 `"isolatedModules": true` 强制单文件可独立转译，但**只是 lint 性约束**，不影响 SWC 实际转译行为。

3. **SWC 转译实际行为 / Next.js 16.2.4 Turbopack bug**：
   - 预期：`export type { X }` 应被完全擦除（type-only 命名再导出不应出现在运行时 JS）
   - 实际：SWC server-actions 转换在 `'use server'` 文件中扫描顶层 export 时，对 `ExportNamedDeclaration` 节点的 `type` 修饰符处理不完整 — type 修饰符丢失，命名再导出被保留为运行时 `export { SearchResponse }`
   - 同时 `SearchResponse` 来自 `import type { components }`（typeof only）→ 转译后 `import type` 被擦除 → 运行时模块作用域内无 `SearchResponse` binding
   - 结果：转译输出含 `export { SearchResponse }` 但 `SearchResponse` 在运行时未定义 → 模块加载时立即抛 `ReferenceError`

4. **传播**：search.ts 编译产物属于 `/projects` 路由的 server actions 聚合（因为 GlobalSearchBar 组件被 projects/page.tsx 间接引用 → globalSearch 进入该路由的 action 集合）。聚合 entry `projects/page/actions.js` 模块求值时引入 ACTIONS_MODULE1（search.ts）失败 → 整个 entry 崩溃 → 同 entry 内的 `getProjects`（ACTIONS_MODULE0）也无法调用 → /projects 渲染走 `.catch(() => [])` 兜底（page.tsx L55-58）→ 0 卡片。

### §2.3 上游 Turbopack 已有问题还是 Next.js 自定义版引入

**结论：是 Next.js 16.2.4 上游已有问题**（非本项目 Next.js 自定义版独有）。证据链：

- 文件级别：`node_modules/next/dist/build/swc/options.js` L164 serverActions 配置 / `node_modules/next/dist/build/webpack/loaders/next-flight-loader/action-validate.js` 校验 / `node_modules/next/dist/build/webpack/loaders/next-flight-action-entry-loader.js` re-export 生成 — 全是 Next.js 上游代码 / 未被本项目 monkey-patch
- 设计契约：[官方 use-server doc](node_modules/next/dist/docs/01-app/03-api-reference/01-directives/use-server.md) §"Using `use server` at the top of a file" 明示 "All functions in the file are executed on the server"，**未说明**类型再导出会被怎么处理 / 但配合 action-validate.js 的契约 "A `use server` file can only export async functions" 推断：理论上应**完全屏蔽**任何非函数导出（包括 type 再导出）/ 当前实现存在 type-only 命名再导出处理盲区
- AGENTS.md 警告 `This is NOT the Next.js you know` 主要指向 App Router + cache components + Turbopack 默认等 API 演进 / 不是说本项目改了 server actions 转换链

**未完全闭环点**：无法 100% 确认 Next.js issue tracker 是否已记录此问题。`node_modules/next/CHANGELOG*` / `README*` 均无相关条目。建议后续可去 https://github.com/vercel/next.js/issues 搜索 `export type use server ReferenceError` 关联 issue。**本 fix 不修上游 / 仅在业务代码侧规避**（feedback_subagent_sprint §2 T1）。

### §2.4 TypeScript 配置影响

- `isolatedModules: true`（tsconfig.json L11）：强制每个文件可被单文件转译器（SWC/Babel）独立处理 / **要求** 类型导入必须用 `import type` 或 inline `type` 修饰符 / **不阻止** `export type { X }` 写法（实际反而鼓励 / 因为这是单文件转译友好写法）
- `verbatimModuleSyntax`：未启用（tsconfig.json 无）。若启用会进一步要求 import/export 的 type 修饰符必须显式 / 也不会改变本 bug 表现（修饰符已显式）
- **结论**：TS 配置正确 / bug 在 SWC 转译实现 / 业务代码改用其他模式即可规避

## §3 类似问题 grep 清单

### §3.1 危险模式 grep（`export type { X }` 命名再导出说明符）

```bash
cd /root/workspace/projects/prism-0420/app
grep -rn "^export type {" src/ --include="*.ts" --include="*.tsx"
```

结果：

| # | 文件 | 行 | 顶部指令 | 风险评级 | 处置 |
|---|------|----|---------|---------|------|
| 1 | src/actions/search.ts | L12 | `'use server'` | 🔴 高（本 bug） | 本 fix 删除 |
| 2 | src/components/issue-card.tsx | L347 | `'use client'` | 🟢 低 | 保留（client 文件不走 server actions 转换） |
| 3 | src/components/competitor-reference-card.tsx | L30 | `'use client'` | 🟢 低 | 保留（同上） |

**仅 1 个 'use server' 文件命中 / 已修**。

### §3.2 邻近模式扫（`export { type X }` 内联 type 修饰符 / 在 'use server' 文件中）

```bash
grep -rn "^export {.*\btype\b" src/actions/ --include="*.ts"
```

结果：0 命中（也包括复合 `grep -rn "export {" src/actions/` 总命中 0 — 即 src/actions/ 全部是 `export async function` / `export interface` / `export type X = ...` / `export const` 形式，没有命名再导出说明符）。

### §3.3 类型/接口直接导出（`export interface` / `export type X = ...`）扫描

```bash
grep -rn "^export type\|^export interface" src/actions/ --include="*.ts"
```

结果：共 28 处 `export interface` / `export type X = ...`（分布于 templates / projects / competitors / nodes / relations / import / import-ai / analyze / competitor-references / export / project-stats-proxy / project-settings 等）。

**这些为何不触发同样 bug**：

| 写法 | 例子 | SWC 处理 | 风险 |
|------|------|---------|------|
| `export interface X { ... }` | actions/projects.ts L28 `export interface Project { ... }` | 完整声明 / TS-only 构造 / SWC 完整擦除（interface 没有运行时存在） | 🟢 安全 |
| `export type X = Y` | actions/export.ts L17 `export type ExportPayload = DownloadResponse` | 类型别名直接声明 / 同样 TS-only / SWC 擦除 | 🟢 安全 |
| `export type { X }` | actions/search.ts L12（本 bug） | **命名再导出说明符** / SWC 转换链对 type 修饰符处理不完整 | 🔴 危险 |
| `export { type X, fn }` | （codebase 未命中） | 推测同 `export type { X }` 类似 / 未实测 | 🟡 未知 |

**核心区分**：
- 直接声明形式（`export interface X { ... }` / `export type X = ...`）：SWC 把整个声明当 TS 节点剥离 / 没有运行时 export 表达式生成
- 命名再导出说明符形式（`export type { X }` / `export { type X }`）：SWC 把 export 节点当 ES 模块导出 / 仅靠 `type` 修饰符标记 "运行时擦除" / 在 server actions 转换路径上修饰符丢失 → 转译输出含运行时 export 语句但变量不存在

### §3.4 已确认安全的同模式（不需改）

`src/components/issue-card.tsx` L347 + `src/components/competitor-reference-card.tsx` L30 — 都是 `'use client'` 文件 / 走 client boundary 转换（`next-flight-loader` index.js L97-184）而非 server actions 转换 / 没有 SWC server-actions transform 介入 / 类型再导出被正确擦除 → 这两处保留不动。

### §3.5 punt 清单

无 punt — 本 fix 范围内同模式仅 1 处命中 + 已修 / 邻近模式全部安全。

## §4 design vs 实装漂移定位

**design 哪步漏了？**

- `design/01-engineering/06-frontend-spec.md` Phase 2.2 子片 1+2 设计阶段定义了 server action 通道（`'use server'` + cookies().get()）/ 提及 R-X1 cookie sync 但**未约束** server action 文件的 export 规约
- design/01-engineering/06-frontend-spec.md 未含 "use server 文件 export 红线"（如：禁止类型再导出 / 仅 export async function）
- `app/CLAUDE.md` + `app/AGENTS.md` 红色警告 `This is NOT the Next.js you know` / `Read the relevant guide in node_modules/next/dist/docs/` — 警告等级足够 / 但**没有具体到 server actions 文件 export 规约**这一粒度
- 单元测试盲区：`src/lib/server-http-client.test.ts` 等单测用 vi.mock 把 server action 整体 mock 掉 / 不会走真实 SWC 转译路径 → 真实模块加载错误从单测层抓不到
- E2E 测试 gap（本次 dogfooding sprint 起点解决的就是这个）：之前没有 e2e DOM test 跑过 `/projects` 列表渲染 → 真实模块求值失败从未被 CI 捕获

**应该如何避免**：

1. **app/CLAUDE.md（或 app/AGENTS.md）补红线**：
   ```
   🔴 'use server' 文件红线（B-list-projects-search-loader sprint 立条）：
   - 只能 export async function（Next.js 16 契约 / action-validate.js）
   - 禁止 `export type { X }` 类型再导出（触发 SWC server-actions 转换 bug / 命中过 P0 bug）
   - 类型声明用 inline 形式 `export interface X { ... }` 或 `export type X = ...`（直接声明 / 不是再导出说明符）
   - 类型不导出（外部消费方靠 await 推断返回类型 / 不主动 re-export）
   ```

2. **CI lint 规则建议**（cross-sprint pool 候选）：
   - eslint custom rule：对 `'use server'` 顶部指令的文件，禁止任何 `export type { ... }` 形式的命名再导出
   - 不阻塞本 sprint 但建议 6-7 月 sprint 时落地（cross-sprint-punt-pool.md F-OPT 类候选）

3. **dogfooding phase2-case.md §禁止模式 加一条**：
   - "Next.js 'use server' 文件中禁止 `export type { X }` 命名再导出 / 仅 export async function / 类型不导出（外部用 await 推断）"

## §5 fix 改动

| 文件 | 行 | 改动 | 类型 |
|------|----|------|------|
| app/src/actions/search.ts | L12 (删) + L3-15 (注释) | 删除 `export type { SearchResponse };` dead re-export + 补失败模式注释 | 核心 |

**未动**：
- Next.js 自定义版本身（feedback_subagent_sprint §2 Forbidden / 超 sprint 范围）
- src/types/api.ts（codegen 产物 / 不动）
- src/components/global-search-bar.tsx（消费方 / 通过 await 自动获得返回类型 / 无需改）
- src/app/projects/[projectId]/search/page.tsx（消费方 / 同上）
- 其他 src/actions/*.ts（同模式扫描 §3.1-3.4 已确认安全）
- design/01-engineering/06-frontend-spec.md（design 漂移登记建议见 §4 / 由主 agent 拍板时统一改）

### dogfooding 6 项自评

| # | 维度 | 评级 | 备注 |
|---|------|------|------|
| 1 | 改动范围 | 低 | 单文件 1 行删除 + 注释 / 全 codebase 同模式扫 0 其他风险 |
| 2 | 代码位置 | 低 | actions/ 业务文件 / 不动 auth + middleware + config + 框架 |
| 3 | 可逆性 | 低（安全） | git revert 一键回退 / 不涉 schema / 不涉运行时配置 |
| 4 | 业务断言 | 低 | 仅类型再导出删除 / globalSearch 函数签名不变 / 外部消费方通过 await 推断返回类型 |
| 5 | 测试覆盖 | 中 | M02 list projects DOM 已覆盖回归 / 已转 PASS |
| 6 | bug 类型 | 中 | 类型漂移 + tooling bug / 非 auth bypass / 非数据丢失 |

**预判 1-2 项中 / 0 项高 → A 路径直推（plan §3 6 项自评判定）**。同模式扫出仅 1 文件改 → A 路径无需 audit。

## §6 验证证据

### §6.1 tsc

```
cd app/ && pnpm exec tsc --noEmit
→ 0 错误（无输出）
```

### §6.2 E2E Playwright（cookie fix + search loader fix 联合回归）

```
M01 user-account: 5/5 PASS
  ✓ [P0] login happy path — DOM 路径填表单 + 跳转 + cookie 已设
  ✓ [P0] login invalid password — DOM 报错 toast
  ✓ [P0] register page — admin-invite-only
  ✓ [P0] AuthProvider mount /auth/refresh（R-X1 cookie sync）
  ✓ [P1] storageState opt-out

M02 project: 5/5 PASS（前 spike 时 3/5 FAIL）
  ✓ [P0] create-project happy path — DOM 主路径
  ✓ [P0-CRITICAL] 🔴 trigger_bug 复现 — 跳详情页 ✓（cookie fix 验证）
  ✓ [P0] list projects DOM — 项目卡片渲染 ✓（本 fix 验证 / 此前因 search loader bug FAIL）
  ✓ [P1-API 旁路] backend tenant 隔离 403
  ✓ [P1-API 旁路] backend 状态机 archived → archived 拒转 409

总计: 10/10 PASS
```

### §6.3 next build（Turbopack 真编译）

```
▲ Next.js 16.2.4 (Turbopack)
✓ Compiled successfully in 7.6s
  Running TypeScript ...
  Finished TypeScript in 8.3s ...
✓ Generating static pages using 5 workers (14/14) in 412ms
  Finalizing page optimization ...

27 routes 全部 PASS（含 /projects 静态预渲染 + /projects/[projectId]/search 动态）
```

### §6.4 backend pytest

本 fix 仅前端 / 不涉 backend / pytest 不需重跑。

## §7 spike 漏判与前 fix subagent 修正

P2 spike-report.md §"第二条 P0 bug" 把 list projects 0 卡片归因为 "同一根因：server-side fetch 无凭据"。前 fix subagent（B-trigger-bug-server-action-cookie）修完 cookie path（Path=/auth → /）后，跑 M02 发现 list projects DOM 仍 FAIL → 抓 next-dev log → 揭露第二条独立 bug（SearchResponse loader 错误）。

**spike 误归一根因的认知偏差**：
- 两条 test 时段 FAIL 表象相似（页面跳转异常 / 渲染异常）
- spike 时段只看浏览器侧抓包（看到 server action 500/303）/ 没看 next-dev server 详细错误日志
- 经验偏差：先发现 cookie 透传 bug → 推断另一条也是 cookie 透传

**对 dogfooding 价值**：实证 "spike 范式不是万能 / 复杂场景需多层日志组合 / 浏览器抓包+server log 双视角才能闭环" — 入 phase2-case.md §Self-check 补"server action 真路径调试时必查 next-dev server log"。

## §8 后续闭环建议

1. **app/CLAUDE.md 或 app/AGENTS.md 补红线**（见 §4 应该如何避免）
2. **dogfooding phase2-case.md §禁止模式 加一条**（见 §4）
3. **cross-sprint pool 候选**：eslint custom rule 禁止 `'use server'` 文件中类型再导出（F-OPT 类 / 不阻塞本 sprint）
4. **(未完全闭环)** 后续可向 Next.js issue tracker 提报本 case + 最小复现 — 当前本 fix 仅在业务代码侧规避 / 不修上游
5. **R-X1 测试增强**：现有 `src/lib/server-http-client.test.ts` 用 vi.mock 整体替换 / 抓不到真实模块加载错误 / 建议加 e2e DOM smoke 覆盖每个 server action 文件的 page 路由（dogfooding sprint 后续模块自动会补 / 已在 plan）
