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
    "src/actions/**",
    "src/services/**",
    "src/contexts/**",
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
    "src/lib/validators/**",
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
    "src/app/login/**",
    "src/app/openclaw/**",
    "src/app/projects/**",
    "src/app/register/**",
    "src/app/search/**",
    "src/app/teams/**",
    "src/app/layout.tsx",
    "src/app/page.tsx",
  ]),
]);

export default eslintConfig;
