export interface ModuleData {
  id: string;
  name: string;
  featureCount: number;
  completion: number;
  dimensions: {
    name: string;
    current: number;
    total: number;
  }[];
  lastUpdate: {
    user: string;
    action: string;
    time: string;
  };
}

export interface ProductLineData {
  id: string;
  name: string;
  moduleCount: number;
  featureCount: number;
  avgCompletion: number;
  modules: ModuleData[];
}

export const productLinesData: Record<string, ProductLineData> = {
  "private-cloud": {
    id: "private-cloud",
    name: "私有云",
    moduleCount: 3,
    featureCount: 15,
    avgCompletion: 72,
    modules: [
      {
        id: "inference-service",
        name: "推理服务",
        featureCount: 5,
        completion: 85,
        dimensions: [
          { name: "功能描述", current: 5, total: 5 },
          { name: "用户场景", current: 4, total: 5 },
          { name: "平台技术", current: 3, total: 5 },
          { name: "设计决策", current: 3, total: 5 },
          { name: "工程经验", current: 4, total: 5 },
          { name: "测试分析", current: 2, total: 5 },
          { name: "需求分析", current: 1, total: 5 },
          { name: "竞品参考", current: 2, total: 5 },
        ],
        lastUpdate: { user: "陈玥", action: "更新了 创建推理服务", time: "2小时前" },
      },
      {
        id: "training-service",
        name: "训练服务",
        featureCount: 3,
        completion: 60,
        dimensions: [
          { name: "功能描述", current: 3, total: 3 },
          { name: "用户场景", current: 2, total: 3 },
          { name: "平台技术", current: 2, total: 3 },
          { name: "设计决策", current: 2, total: 3 },
          { name: "工程经验", current: 2, total: 3 },
          { name: "测试分析", current: 1, total: 3 },
          { name: "需求分析", current: 1, total: 3 },
          { name: "竞品参考", current: 1, total: 3 },
        ],
        lastUpdate: { user: "王工", action: "更新了 训练监控", time: "昨天" },
      },
      {
        id: "ops-management",
        name: "运维管理",
        featureCount: 7,
        completion: 35,
        dimensions: [
          { name: "功能描述", current: 3, total: 7 },
          { name: "用户场景", current: 2, total: 7 },
          { name: "平台技术", current: 1, total: 7 },
          { name: "设计决策", current: 1, total: 7 },
          { name: "工程经验", current: 2, total: 7 },
          { name: "测试分析", current: 0, total: 7 },
          { name: "需求分析", current: 0, total: 7 },
          { name: "竞品参考", current: 1, total: 7 },
        ],
        lastUpdate: { user: "李工", action: "更新了 资源监控", time: "5天前" },
      },
    ],
  },
  "smart-computing": {
    id: "smart-computing",
    name: "智算中心",
    moduleCount: 2,
    featureCount: 8,
    avgCompletion: 50,
    modules: [
      {
        id: "smart-inference",
        name: "推理服务",
        featureCount: 4,
        completion: 55,
        dimensions: [
          { name: "功能描述", current: 3, total: 4 },
          { name: "用户场景", current: 2, total: 4 },
          { name: "平台技术", current: 2, total: 4 },
          { name: "设计决策", current: 2, total: 4 },
          { name: "工程经验", current: 1, total: 4 },
          { name: "测试分析", current: 1, total: 4 },
          { name: "需求分析", current: 1, total: 4 },
          { name: "竞品参考", current: 1, total: 4 },
        ],
        lastUpdate: { user: "张工", action: "更新了 创建推理服务", time: "3天前" },
      },
      {
        id: "smart-training",
        name: "训练服务",
        featureCount: 4,
        completion: 45,
        dimensions: [
          { name: "功能描述", current: 2, total: 4 },
          { name: "用户场景", current: 2, total: 4 },
          { name: "平台技术", current: 1, total: 4 },
          { name: "设计决策", current: 1, total: 4 },
          { name: "工程经验", current: 2, total: 4 },
          { name: "测试分析", current: 1, total: 4 },
          { name: "需求分析", current: 0, total: 4 },
          { name: "竞品参考", current: 1, total: 4 },
        ],
        lastUpdate: { user: "陈玥", action: "更新了 分布式训练", time: "1周前" },
      },
    ],
  },
};
