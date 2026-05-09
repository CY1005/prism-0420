import { z } from "zod";

const NAME_MAX = 100;
const PATH_SAFE = /^[^/\\<>\0]+$/;

export const createNodeSchema = z.object({
  projectId: z.string().uuid("无效的项目 ID"),
  parentId: z.string().uuid().nullable(),
  name: z
    .string()
    .min(1, "名称不能为空")
    .max(NAME_MAX, `名称最多 ${NAME_MAX} 个字符`)
    .regex(PATH_SAFE, "名称包含非法字符")
    .trim(),
  type: z.enum(["folder", "file"]).default("file"),
});

export const renameNodeSchema = z.object({
  nodeId: z.string().uuid("无效的节点 ID"),
  name: z
    .string()
    .min(1, "名称不能为空")
    .max(NAME_MAX, `名称最多 ${NAME_MAX} 个字符`)
    .regex(PATH_SAFE, "名称包含非法字符")
    .trim(),
});

export const deleteNodeSchema = z.object({
  nodeId: z.string().uuid("无效的节点 ID"),
});

export const createDimensionRecordSchema = z.object({
  nodeId: z.string().uuid("无效的节点 ID"),
  dimensionTypeId: z.number().int().positive("无效的维度类型"),
  // content 是动态 JSONB，允许任意结构但限制总大小
  content: z
    .record(z.string(), z.unknown())
    .refine((v) => JSON.stringify(v).length <= 100_000, "内容总长度不能超过 100KB"),
});

export type CreateNodeInput = z.infer<typeof createNodeSchema>;
export type RenameNodeInput = z.infer<typeof renameNodeSchema>;
export type DeleteNodeInput = z.infer<typeof deleteNodeSchema>;
export type CreateDimensionRecordInput = z.infer<typeof createDimensionRecordSchema>;
