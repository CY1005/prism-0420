import type { TreeNode } from "@/components/proto/feature-tree";

export const treeData: TreeNode[] = [
  {
    id: "private-cloud",
    name: "私有云",
    type: "folder",
    completionPercent: 75,
    children: [
      {
        id: "inference-service",
        name: "推理服务",
        type: "folder",
        completionPercent: 85,
        children: [
          { id: "create-inference", name: "创建推理服务", type: "file", completionPercent: 62 },
          { id: "auto-scaling", name: "自动扩缩容", type: "file", completionPercent: 90 },
          { id: "card-management", name: "拼卡管理", type: "file", completionPercent: 45 },
        ],
      },
      {
        id: "training-service",
        name: "训练服务",
        type: "folder",
        completionPercent: 60,
        children: [
          { id: "submit-training", name: "提交训练任务", type: "file", completionPercent: 70 },
          { id: "training-monitor", name: "训练监控", type: "file", completionPercent: 35 },
        ],
      },
    ],
  },
  {
    id: "smart-computing",
    name: "智算中心",
    type: "folder",
    completionPercent: 50,
    children: [
      {
        id: "smart-inference",
        name: "推理服务",
        type: "folder",
        completionPercent: 50,
        children: [
          {
            id: "smart-create-inference",
            name: "创建推理服务",
            type: "file",
            completionPercent: 50,
          },
        ],
      },
    ],
  },
];
