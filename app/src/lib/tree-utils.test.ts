import { describe, expect, it } from "vitest";
import { findInTree } from "./tree-utils";

interface MiniNode {
  id: string;
  children: MiniNode[];
}

const n = (id: string, children: MiniNode[] = []): MiniNode => ({ id, children });

describe("findInTree", () => {
  it("空数组返 null", () => {
    expect(findInTree<MiniNode>([], "x")).toBeNull();
  });

  it("匹配根节点", () => {
    const tree = [n("a"), n("b")];
    expect(findInTree(tree, "b")?.id).toBe("b");
  });

  it("匹配嵌套节点", () => {
    const tree = [n("a", [n("a1"), n("a2", [n("a2a")])]), n("b")];
    expect(findInTree(tree, "a2a")?.id).toBe("a2a");
  });

  it("查不到返 null", () => {
    const tree = [n("a", [n("a1")]), n("b")];
    expect(findInTree(tree, "z")).toBeNull();
  });

  it("第一个匹配优先（深度优先）", () => {
    const tree = [n("dup", [n("inner")]), n("dup")];
    expect(findInTree(tree, "dup")?.children.length).toBe(1);
  });
});
