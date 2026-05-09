"use server";

import { db } from "@/db";
import { nodes, dimensionRecords } from "@/db/schema";
import { eq, and, isNull, asc } from "drizzle-orm";
import { revalidatePath } from "next/cache";
import { requireAuth } from "@/lib/auth";
import { checkProjectAccess } from "@/services/permission.service";
import { logger } from "@/lib/logger";
import { type ActionResult, actionError, actionSuccess, AppError } from "@/lib/errors";
import { ErrorCode } from "@/lib/error-codes";
import { logActivity } from "./activity-log";

// ─── Auto-create modules from ZIP structure ──────────

export async function createModulesFromZipTree(
  projectId: string,
  tree: FileTreeNode,
): Promise<ActionResult<{ folders: { id: string; name: string; path: string; depth: number }[] }>> {
  try {
    const user = await requireAuth();
    await checkProjectAccess(user.id, projectId, "editor");

    const createdFolders: { id: string; name: string; path: string; depth: number }[] = [];

    // Collect top-level folders from the ZIP tree
    const topFolders = tree.children?.filter((c) => c.type === "folder") ?? [];

    for (let i = 0; i < topFolders.length; i++) {
      const folder = topFolders[i];
      const [newNode] = await db
        .insert(nodes)
        .values({
          projectId,
          parentId: null,
          name: folder.name,
          type: "folder",
          depth: 0,
          sortOrder: i,
          path: "",
          createdBy: user.id,
        })
        .returning();

      createdFolders.push({
        id: newNode.id,
        name: newNode.name,
        path: newNode.name,
        depth: 0,
      });

      // Create sub-folders (depth 1)
      const subFolders = folder.children?.filter((c) => c.type === "folder") ?? [];
      for (let j = 0; j < subFolders.length; j++) {
        const sub = subFolders[j];
        const [subNode] = await db
          .insert(nodes)
          .values({
            projectId,
            parentId: newNode.id,
            name: sub.name,
            type: "folder",
            depth: 1,
            sortOrder: j,
            path: newNode.id,
            createdBy: user.id,
          })
          .returning();

        createdFolders.push({
          id: subNode.id,
          name: subNode.name,
          path: `${newNode.name} / ${subNode.name}`,
          depth: 1,
        });
      }
    }

    // If ZIP has no folders (all files at root), create a default module
    if (createdFolders.length === 0) {
      const [defaultNode] = await db
        .insert(nodes)
        .values({
          projectId,
          parentId: null,
          name: "导入文档",
          type: "folder",
          depth: 0,
          sortOrder: 0,
          path: "",
          createdBy: user.id,
        })
        .returning();

      createdFolders.push({
        id: defaultNode.id,
        name: defaultNode.name,
        path: defaultNode.name,
        depth: 0,
      });
    }

    logger.action("import.auto_create_modules", user.id, {
      projectId,
      folderCount: createdFolders.length,
    });

    revalidatePath(`/projects/${projectId}`);
    return actionSuccess({ folders: createdFolders });
  } catch (error) {
    return actionError(error);
  }
}

// ─── Types ───────────────────────────────────────────

export interface ParsedFile {
  path: string;
  name: string;
  format: "markdown" | "csv" | "text";
  content: string;
  size: number;
  rows?: number;
  columns?: number;
}

export interface FileTreeNode {
  name: string;
  type: "file" | "folder";
  format?: string;
  children?: FileTreeNode[];
}

export interface UploadResult {
  files: ParsedFile[];
  tree: FileTreeNode;
}

export interface ImportItem {
  fileName: string;
  content: string;
  targetNodeId: string; // parent module node id
  nodeName: string;
  dimensionTypeId?: number; // which dimension to populate with content
}

// ─── Upload Zip (calls FastAPI) ──────────────────────

export async function uploadZip(formData: FormData): Promise<ActionResult<UploadResult>> {
  try {
    const user = await requireAuth();
    const file = formData.get("file") as File | null;

    if (!file) {
      return actionError(new AppError("请选择文件", "blocking", "VALIDATION_ERROR", 400));
    }

    const apiBase = process.env.API_URL ?? "http://localhost:8001";
    const res = await fetch(`${apiBase}/api/import/upload`, {
      method: "POST",
      body: (() => {
        const fd = new FormData();
        fd.append("file", file);
        return fd;
      })(),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: "上传失败" }));
      return actionError(
        new AppError(body.detail || "上传失败", "blocking", ErrorCode.INTERNAL_ERROR, res.status),
      );
    }

    const data: UploadResult = await res.json();

    logger.action("import.upload", user.id, {
      fileCount: data.files.length,
    });

    return actionSuccess(data);
  } catch (error) {
    return actionError(error);
  }
}

// ─── Confirm Import (batch create nodes + dimension records) ──

export async function confirmImport(
  projectId: string,
  items: ImportItem[],
): Promise<ActionResult<{ imported: number; errors: string[] }>> {
  try {
    const user = await requireAuth();
    await checkProjectAccess(user.id, projectId, "editor");

    if (!items.length) {
      return actionError(new AppError("没有要导入的项目", "blocking", "VALIDATION_ERROR", 400));
    }

    const errors: string[] = [];
    let importedCount = 0;

    for (let i = 0; i < items.length; i++) {
      const item = items[i];

      try {
        // Resolve parent node
        const [parent] = await db.select().from(nodes).where(eq(nodes.id, item.targetNodeId));

        if (!parent) {
          errors.push(`"${item.nodeName}": 目标模块不存在`);
          continue;
        }

        // Calculate depth and path
        const depth = parent.depth + 1;
        const path = parent.path ? `${parent.path}/${parent.id}` : parent.id;

        // Calculate sort order
        const siblings = await db
          .select()
          .from(nodes)
          .where(and(eq(nodes.projectId, projectId), eq(nodes.parentId, item.targetNodeId)));
        const sortOrder = siblings.length;

        // Insert node
        const [newNode] = await db
          .insert(nodes)
          .values({
            projectId,
            parentId: item.targetNodeId,
            name: item.nodeName,
            type: "file",
            depth,
            sortOrder,
            path,
            createdBy: user.id,
          })
          .returning();

        // If dimensionTypeId provided, create a dimension record with the content
        if (item.dimensionTypeId && item.content) {
          await db.insert(dimensionRecords).values({
            nodeId: newNode.id,
            dimensionTypeId: item.dimensionTypeId,
            content: { text: item.content },
            createdBy: user.id,
          });
        }

        importedCount++;
      } catch (err) {
        const msg = err instanceof Error ? err.message : "未知错误";
        errors.push(`"${item.nodeName}": ${msg}`);
      }
    }

    logger.action("import.confirm", user.id, {
      projectId,
      importedCount,
      errorCount: errors.length,
    });
    logActivity({
      projectId,
      userId: user.id,
      actionType: "import",
      targetType: "node",
      targetId: projectId,
      summary: `批量导入${importedCount}个功能项`,
      metadata: { importedCount, errorCount: errors.length },
    });
    revalidatePath(`/projects/${projectId}`);

    return actionSuccess({ imported: importedCount, errors });
  } catch (error) {
    return actionError(error);
  }
}
