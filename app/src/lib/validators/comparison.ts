import { z } from "zod";

// M12 功能对比矩阵 — zod validators
// 对应 design/02-modules/M12-comparison/00-design.md §7 + §13。
// 与后端 SnapshotCreateRequest / SnapshotUpdateRequest（api/schemas/comparison_schema.py）字段约束对齐：
//   name: 1-128 / description: optional / node_ids: min_length=1 / dimension_type_ids: min_length=1
//   expected_version: ge=1（rename 乐观锁）

const NAME_MAX = 128;
const DESC_MAX = 5000;

export const createSnapshotSchema = z.object({
  projectId: z.string().uuid(),
  name: z.string().min(1, "快照名不能为空").max(NAME_MAX, `快照名最多 ${NAME_MAX} 个字符`).trim(),
  description: z.string().max(DESC_MAX, `描述最多 ${DESC_MAX} 个字符`).trim().optional(),
  nodeIds: z.array(z.string().uuid()).min(1, "至少选择 1 个节点"),
  dimensionTypeIds: z.array(z.number().int().positive()).min(1, "至少选择 1 个维度"),
});

export const renameSnapshotSchema = z.object({
  projectId: z.string().uuid(),
  snapshotId: z.string().uuid(),
  name: z.string().min(1, "快照名不能为空").max(NAME_MAX, `快照名最多 ${NAME_MAX} 个字符`).trim(),
  description: z.string().max(DESC_MAX, `描述最多 ${DESC_MAX} 个字符`).trim().optional(),
  expectedVersion: z.number().int().min(1, "expected_version 必须 ≥ 1"),
});
