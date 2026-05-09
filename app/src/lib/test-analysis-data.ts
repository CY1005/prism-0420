export interface IssueItem {
  id: string;
  type: "Bug" | "技术债";
  title: string;
  description: string;
  priority: "P1" | "P2" | "P3";
  version: string;
  foundDate: string;
}

export interface TestCaseItem {
  id: number;
  name: string;
  source: "AI生成" | "手动";
  priority: "P0" | "P1" | "P2";
  status: "通过" | "失败" | "未执行";
}

export const testAnalysisData = {
  issues: [
    {
      id: "issue-1",
      type: "Bug" as const,
      title: "拼卡模式下副本数显示不一致",
      description: "前端显示3个副本，实际运行2个。原因：拼卡状态下激活副本和总副本数统计口径不同。",
      priority: "P1" as const,
      version: "v3.9.3",
      foundDate: "2026-03-28",
    },
    {
      id: "issue-2",
      type: "技术债" as const,
      title: "GPU调度队列高并发死锁",
      description: "多个拼卡任务同时申请资源时，调度队列偶现死锁...",
      priority: "P2" as const,
      version: "v3.9.3",
      foundDate: "2026-03-15",
    },
  ],
  testCases: {
    total: 12,
    aiGenerated: 8,
    manual: 4,
    items: [
      {
        id: 1,
        name: "拼卡开关开启后创建推理服务",
        source: "AI生成" as const,
        priority: "P0" as const,
        status: "通过" as const,
      },
      {
        id: 2,
        name: "运行中修改拼卡配置",
        source: "AI生成" as const,
        priority: "P0" as const,
        status: "失败" as const,
      },
      {
        id: 3,
        name: "国产卡环境拼卡验证",
        source: "手动" as const,
        priority: "P1" as const,
        status: "未执行" as const,
      },
      {
        id: 4,
        name: "拼卡+定时扩缩容联动",
        source: "AI生成" as const,
        priority: "P1" as const,
        status: "通过" as const,
      },
    ],
  },
};
