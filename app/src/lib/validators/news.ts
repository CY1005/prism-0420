import { z } from "zod";

// M14 行业动态 — zod validators（design/02-modules/M14-industry-news/00-design.md §7 + §13）
// title: 1-200（design schema field constraint） / tags element <=50 chars / max 20 tags (与 issue.ts 一致约束)

const TITLE_MAX = 200;
const SUMMARY_MAX = 5000;
const TAG_MAX = 50;
const TAGS_COUNT_MAX = 20;

const tagsSchema = z
  .array(z.string().min(1, "标签不能为空").max(TAG_MAX, `单个标签最多 ${TAG_MAX} 个字符`).trim())
  .max(TAGS_COUNT_MAX, `最多 ${TAGS_COUNT_MAX} 个标签`)
  .optional();

// 与后端 NewsCreate (AnyHttpUrl) 对齐：空字符串视为未填，否则必须是 http(s) URL
const urlSchema = z
  .string()
  .trim()
  .url("来源链接必须是合法的 URL")
  .optional()
  .or(z.literal("").transform(() => undefined));

// 发布日期：ISO date (YYYY-MM-DD) 或空
const dateSchema = z
  .string()
  .trim()
  .regex(/^\d{4}-\d{2}-\d{2}$/, "日期格式必须是 YYYY-MM-DD")
  .optional()
  .or(z.literal("").transform(() => undefined));

export const createNewsSchema = z.object({
  title: z.string().min(1, "标题不能为空").max(TITLE_MAX, `标题最多 ${TITLE_MAX} 个字符`).trim(),
  summary: z.string().max(SUMMARY_MAX, `摘要最多 ${SUMMARY_MAX} 个字符`).trim().optional(),
  sourceUrl: urlSchema,
  publishedDate: dateSchema,
  tags: tagsSchema,
});

export const updateNewsSchema = z.object({
  newsId: z.string().uuid("无效的动态 ID"),
  title: z
    .string()
    .min(1, "标题不能为空")
    .max(TITLE_MAX, `标题最多 ${TITLE_MAX} 个字符`)
    .trim()
    .optional(),
  summary: z.string().max(SUMMARY_MAX).trim().optional(),
  sourceUrl: urlSchema,
  publishedDate: dateSchema,
  tags: tagsSchema,
});

export const linkNewsNodeSchema = z.object({
  newsId: z.string().uuid("无效的动态 ID"),
  nodeId: z.string().uuid("无效的节点 ID"),
});

export type CreateNewsInput = z.infer<typeof createNewsSchema>;
export type UpdateNewsInput = z.infer<typeof updateNewsSchema>;
export type LinkNewsNodeInput = z.infer<typeof linkNewsNodeSchema>;
