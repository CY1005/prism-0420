import { z } from "zod";
import { actionError, type ActionResult, AppError } from "./errors";
import { ErrorCode } from "./error-codes";

/**
 * Server Action 统一入口：强制 schema 校验
 *
 * 用法：
 * ```ts
 * const createNodeSchema = z.object({
 *   projectId: z.string().uuid(),
 *   parentId: z.string().uuid().nullable(),
 *   name: z.string().min(1).max(100).trim(),
 *   type: z.enum(["folder", "file"]).default("file"),
 * });
 *
 * export const createNode = defineAction(
 *   createNodeSchema,
 *   async ({ projectId, parentId, name, type }) => {
 *     const user = await requireAuth();
 *     // ... 业务逻辑
 *     return actionSuccess({ id });
 *   },
 * );
 * ```
 *
 * 设计原则：
 * - schema 是第一公民，没 schema 过不了编译
 * - 校验失败自动返回 VALIDATION_ERROR，业务逻辑拿到的 input 已 parse 并类型收紧
 * - Action 签名从"位置参数"统一为"对象参数"
 *
 * 详见 docs/adr/014-input-validation-zod.md
 */
export function defineAction<TSchema extends z.ZodTypeAny, TResult>(
  schema: TSchema,
  handler: (input: z.infer<TSchema>) => Promise<ActionResult<TResult>>,
): (raw: z.input<TSchema>) => Promise<ActionResult<TResult>> {
  return async (raw) => {
    const parsed = schema.safeParse(raw);
    if (!parsed.success) {
      const firstIssue = parsed.error.issues[0];
      const message = firstIssue?.message || "输入格式错误";
      return actionError(new AppError(message, "blocking", ErrorCode.VALIDATION_ERROR, 400));
    }
    try {
      return await handler(parsed.data);
    } catch (e) {
      return actionError(e);
    }
  };
}
