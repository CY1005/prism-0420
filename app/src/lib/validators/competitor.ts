import { z } from "zod";

const NAME_MAX = 100;
const DESC_MAX = 1000;
const URL_MAX = 500;

export const createCompetitorSchema = z.object({
  projectId: z.string().uuid("无效的项目 ID"),
  name: z
    .string()
    .min(1, "竞品名称不能为空")
    .max(NAME_MAX, `竞品名称最多 ${NAME_MAX} 个字符`)
    .trim(),
  website: z
    .string()
    .max(URL_MAX, "网址过长")
    .trim()
    .url("网址格式不正确")
    .optional()
    .or(z.literal("")),
  description: z.string().max(DESC_MAX, `描述最多 ${DESC_MAX} 个字符`).trim().optional(),
});

const TEXT_MAX = 5000;

export const createCompetitorReferenceSchema = z.object({
  projectId: z.string().uuid("无效的项目 ID"),
  nodeId: z.string().uuid("无效的节点 ID"),
  competitorId: z.string().uuid("无效的竞品 ID"),
  version: z.string().max(50, "版本标识过长").trim().optional(),
  featureCoverage: z.string().max(TEXT_MAX, `内容最多 ${TEXT_MAX} 个字符`).trim().optional(),
  technicalApproach: z.string().max(TEXT_MAX, `内容最多 ${TEXT_MAX} 个字符`).trim().optional(),
  prosAndCons: z
    .object({
      pros: z.array(z.string().max(500)).max(20, "最多 20 条优点"),
      cons: z.array(z.string().max(500)).max(20, "最多 20 条缺点"),
    })
    .optional(),
});

export type CreateCompetitorInput = z.infer<typeof createCompetitorSchema>;
export type CreateCompetitorReferenceInput = z.infer<typeof createCompetitorReferenceSchema>;
