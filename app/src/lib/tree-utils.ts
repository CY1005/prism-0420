/**
 * Sprint 1 Task 1.3（P22-3c-5 收口）— findInTree 横向化。
 *
 * 三处旧实装（actions/nodes.ts:270 / actions/panorama.ts:33 / actions/relations.ts:206）
 * 签名一致：(tree: NodeOverview[], id: string) → NodeOverview | null。
 * 抽到通用层 / 泛型 T 仅约束 {id, children}。
 */

export interface TreeNode<T> {
  id: string;
  children: T[];
}

export function findInTree<T extends TreeNode<T>>(tree: T[], id: string): T | null {
  for (const n of tree) {
    if (n.id === id) return n;
    const sub = findInTree(n.children, id);
    if (sub) return sub;
  }
  return null;
}
