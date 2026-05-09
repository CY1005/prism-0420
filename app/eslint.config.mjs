import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
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
    "src/actions/activity-log.ts",
    "src/actions/admin.ts",
    "src/actions/competitor-references.ts",
    "src/actions/competitors.ts",
    "src/actions/export.ts",
    "src/actions/feed.ts",
    "src/actions/issues.ts",
    "src/actions/project-stats-proxy.ts",
    "src/actions/search.ts",
    "src/actions/teams.ts",
    "src/actions/templates.ts",
    // services/* — http-client.ts + auth-token-store.ts 已是子片 1 新写 / 不 ignore
    // 子片 2-3 改造逐文件移除剩余条目
    "src/services/analyzer.ts",
    // src/services/auth.ts 子片 2 已删除（next-auth 客户端 / spec 06 §2 改 cookie 通道）
    "src/services/comparison.ts",
    "src/services/permission.service.ts",
    "src/services/project-stats.ts",
    "src/services/projects.ts",
    "src/services/relations.ts",
    "src/services/search.ts",
    "src/services/settings.ts",
    // src/contexts/auth-context.{tsx,test.tsx} 子片 2 新写 / 不 ignore
    "src/contexts/project-role-context.tsx",
    // codegen 输出 / 不 lint 是常规
    "src/types/**",
    "src/lib/admin-data.ts",
    "src/lib/comparison-data.ts",
    "src/lib/crypto.ts",
    "src/lib/define-action.ts",
    "src/lib/error-codes.ts",
    "src/lib/errors.ts",
    "src/lib/logger.ts",
    "src/lib/module-data.ts",
    "src/lib/openclaw-data.ts",
    "src/lib/product-line-data.ts",
    "src/lib/project-detail-data.ts",
    "src/lib/projects-data.ts",
    "src/lib/settings-data.ts",
    "src/lib/test-analysis-data.ts",
    "src/lib/tree-data.ts",
    "src/lib/use-page-context.ts",
    // src/lib/validators/auth.ts 子片 2 zod schema / 已合规 / 不 ignore
    "src/lib/validators/competitor.ts",
    "src/lib/validators/issue.ts",
    "src/lib/validators/node.ts",
    "src/lib/validators/project.ts",
    "src/lib/validators/team.ts",
    "src/components/ai-import-wizard.tsx",
    "src/components/ai-mapping-table.tsx",
    "src/components/analysis-result.tsx",
    "src/components/competitor-reference-card.tsx",
    "src/components/dimension-card.tsx",
    "src/components/feature-tree.tsx",
    "src/components/feed-card.tsx",
    "src/components/global-search-bar.tsx",
    "src/components/import-csv-modal.tsx",
    "src/components/issue-card.tsx",
    "src/components/proto/**",
    "src/components/relation-graph.tsx",
    "src/components/snapshot-result.tsx",
    "src/components/template-save-dialog.tsx",
    "src/components/template-selector.tsx",
    "src/components/treemap-view.tsx",
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
    "src/app/teams/**",
    "src/app/layout.tsx",
    "src/app/page.tsx",
  ]),
]);

export default eslintConfig;
