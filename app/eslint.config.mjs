import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Sprint 1 Task 1.8：放开 _ 前缀参数 unused warning（e2e skeletons / NOT_IMPLEMENTED stub
  // 通用范式 / 跟 TS 自带 noUnusedParameters 行为对齐）
  {
    rules: {
      "@typescript-eslint/no-unused-vars": [
        "warn",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
        },
      ],
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Phase 2.2 子片 0 prep — 拷贝层暂禁 lint（待子片 1-3 改造逐目录开启）
    // 锚点：design/01-engineering/06-frontend-spec.md + ADR-001 §6.1
    // 子片 1：lib/types/ + http-client（codegen）→ 该目录从此列表移除
    // 子片 2：actions/auth.ts + lib/auth-client.ts（auth flow）→ 移除
    // 子片 3：actions/* + services/* + app/{各业务路由}（API client 改造）→ 逐文件移除
    // 子片 4：app/teams/* + components/teams/*（M20 新写）→ 移除
    // 子片 3a-ii: actions/{projects,project-settings,versions} 已改 server-http-client / 不 ignore
    // 子片 3b: actions/{nodes,relations,panorama,import,import-ai,analyze} 已改 / 不 ignore
    //   - import / import-ai / analyze SSE+WS 流程显式 actionError(NOT_IMPLEMENTED) → 子片 3c 接 M11/M13/M17/M14 真端点
    // 子片 3c: actions/{competitors,competitor-references,issues,search,admin,activity-log,export,project-stats-proxy} 改 server-http-client / 已合规 / 不 ignore
    //   - templates / feed 全函数 NOT_IMPLEMENTED stub（OpenAPI 无对应域 / 子片 5 后或 Phase 2.3 评估）
    // 子片 4: actions/teams.ts 全 rewrite / app/teams/** 全新写 / validators/team.ts 全 rewrite / 不 ignore
    // services/* — http-client.ts + auth-token-store.ts 已是子片 1 新写 / 不 ignore
    // 子片 2-3 改造逐文件移除剩余条目
    // Sprint 1 Task 1.8 渐进还债：所有 0-issue 文件已从 ignore 移出（25 项）
    // 保留：仍有真实 lint issue 的文件 + codegen 输出 + 第三方 ui
    "src/lib/define-action.ts",
    "src/lib/error-codes.ts",
    "src/lib/errors.ts",
    "src/lib/logger.ts",
    "src/types/**",
    "src/components/ai-import-wizard.tsx",
    "src/components/ai-mapping-table.tsx",
    "src/components/competitor-reference-card.tsx",
    "src/components/dimension-card.tsx",
    "src/components/issue-card.tsx",
    "src/components/proto/**",
    "src/components/relation-graph.tsx",
    "src/components/ui/**",
    "src/components/version-timeline.tsx",
    "src/app/admin/**",
    "src/app/api/**",
    "src/app/feature/**",
    // src/app/login + register 子片 2 改造 / 已合规 / 不 ignore
    "src/app/openclaw/**",
    // 子片 3a-ii: projects/page.tsx + projects/new 已改 / 其他 [projectId] 子页深耦合 3b/3c actions 仍 ignore
    // [projectId] 在 glob 里是 char class / 用 **/projects/** 模式或在条目里加路径段
    "src/app/projects/**/overview/**",
    "src/app/projects/**/settings/**",
    "src/app/projects/**/features/**",
    "src/app/projects/**/modules/**",
    "src/app/projects/**/issues/**",
    "src/app/projects/**/relation-graph/**",
    "src/app/projects/**/comparison/**",
    "src/app/projects/**/import/**",
    "src/app/projects/**/analysis/**",
    "src/app/projects/**/templates/**",
    "src/app/projects/**/product-lines/**",
    "src/app/projects/**/workspace.tsx",
    "src/app/projects/**/[projectId]/page.tsx",
    "src/app/search/**",
    "src/app/layout.tsx",
    "src/app/page.tsx",
  ]),
]);

export default eslintConfig;
