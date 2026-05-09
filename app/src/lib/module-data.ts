export interface FeatureItem {
  id: string;
  name: string;
  version: string;
  completion: number;
  dimensionStatus: Array<"green" | "yellow" | "red">;
  lastUpdate: string;
}

export interface ModuleDetailData {
  id: string;
  name: string;
  productLineName: string;
  featureCount: number;
  avgCompletion: number;
  dimensions: {
    name: string;
    current: number;
    total: number;
    percent: number;
  }[];
  features: FeatureItem[];
}

export const moduleDetailData: Record<string, ModuleDetailData> = {
  "inference-service": {
    id: "inference-service",
    name: "推理服务",
    productLineName: "私有云",
    featureCount: 5,
    avgCompletion: 85,
    dimensions: [
      { name: "功能描述", current: 5, total: 5, percent: 100 },
      { name: "用户场景", current: 4, total: 5, percent: 80 },
      { name: "平台技术", current: 3, total: 5, percent: 60 },
      { name: "设计决策", current: 3, total: 5, percent: 60 },
      { name: "工程经验", current: 4, total: 5, percent: 80 },
      { name: "测试分析", current: 2, total: 5, percent: 40 },
      { name: "需求分析", current: 1, total: 5, percent: 20 },
      { name: "竞品参考", current: 2, total: 5, percent: 40 },
    ],
    features: [
      {
        id: "create-inference",
        name: "创建推理服务",
        version: "v1.6",
        completion: 62,
        dimensionStatus: ["green", "green", "green", "green", "green", "yellow", "yellow", "red"],
        lastUpdate: "2小时前",
      },
      {
        id: "auto-scaling",
        name: "自动扩缩容",
        version: "v3.7",
        completion: 90,
        dimensionStatus: ["green", "green", "green", "green", "green", "green", "green", "yellow"],
        lastUpdate: "昨天",
      },
      {
        id: "card-management",
        name: "拼卡管理",
        version: "v3.8",
        completion: 45,
        dimensionStatus: ["green", "green", "green", "yellow", "yellow", "red", "red", "red"],
        lastUpdate: "昨天",
      },
      {
        id: "replica-management",
        name: "副本管理",
        version: "v2.0",
        completion: 70,
        dimensionStatus: ["green", "green", "green", "green", "green", "yellow", "yellow", "red"],
        lastUpdate: "3天前",
      },
      {
        id: "gpu-scheduling",
        name: "GPU调度策略",
        version: "v1.6",
        completion: 30,
        dimensionStatus: ["green", "green", "yellow", "red", "red", "red", "red", "red"],
        lastUpdate: "1周前",
      },
    ],
  },
  "training-service": {
    id: "training-service",
    name: "训练服务",
    productLineName: "私有云",
    featureCount: 3,
    avgCompletion: 60,
    dimensions: [
      { name: "功能描述", current: 3, total: 3, percent: 100 },
      { name: "用户场景", current: 2, total: 3, percent: 67 },
      { name: "平台技术", current: 2, total: 3, percent: 67 },
      { name: "设计决策", current: 2, total: 3, percent: 67 },
      { name: "工程经验", current: 2, total: 3, percent: 67 },
      { name: "测试分析", current: 1, total: 3, percent: 33 },
      { name: "需求分析", current: 1, total: 3, percent: 33 },
      { name: "竞品参考", current: 1, total: 3, percent: 33 },
    ],
    features: [
      {
        id: "submit-training",
        name: "提交训练任务",
        version: "v1.0",
        completion: 70,
        dimensionStatus: ["green", "green", "green", "green", "green", "yellow", "yellow", "red"],
        lastUpdate: "2天前",
      },
      {
        id: "training-monitor",
        name: "训练监控",
        version: "v2.0",
        completion: 55,
        dimensionStatus: ["green", "green", "yellow", "yellow", "green", "red", "red", "red"],
        lastUpdate: "昨天",
      },
      {
        id: "distributed-training",
        name: "分布式训练",
        version: "v3.0",
        completion: 55,
        dimensionStatus: ["green", "yellow", "yellow", "green", "green", "red", "red", "yellow"],
        lastUpdate: "4天前",
      },
    ],
  },
  "ops-management": {
    id: "ops-management",
    name: "运维管理",
    productLineName: "私有云",
    featureCount: 7,
    avgCompletion: 35,
    dimensions: [
      { name: "功能描述", current: 3, total: 7, percent: 43 },
      { name: "用户场景", current: 2, total: 7, percent: 29 },
      { name: "平台技术", current: 1, total: 7, percent: 14 },
      { name: "设计决策", current: 1, total: 7, percent: 14 },
      { name: "工程经验", current: 2, total: 7, percent: 29 },
      { name: "测试分析", current: 0, total: 7, percent: 0 },
      { name: "需求分析", current: 0, total: 7, percent: 0 },
      { name: "竞品参考", current: 1, total: 7, percent: 14 },
    ],
    features: [
      {
        id: "resource-monitor",
        name: "资源监控",
        version: "v1.0",
        completion: 45,
        dimensionStatus: ["green", "green", "yellow", "red", "green", "red", "red", "red"],
        lastUpdate: "5天前",
      },
      {
        id: "log-management",
        name: "日志管理",
        version: "v1.5",
        completion: 40,
        dimensionStatus: ["green", "yellow", "red", "red", "green", "red", "red", "red"],
        lastUpdate: "1周前",
      },
      {
        id: "alert-config",
        name: "告警配置",
        version: "v2.0",
        completion: 35,
        dimensionStatus: ["green", "yellow", "red", "red", "yellow", "red", "red", "red"],
        lastUpdate: "1周前",
      },
      {
        id: "node-management",
        name: "节点管理",
        version: "v1.0",
        completion: 30,
        dimensionStatus: ["yellow", "yellow", "red", "red", "red", "red", "red", "yellow"],
        lastUpdate: "2周前",
      },
      {
        id: "quota-management",
        name: "配额管理",
        version: "v1.2",
        completion: 35,
        dimensionStatus: ["green", "green", "red", "red", "red", "red", "red", "red"],
        lastUpdate: "1周前",
      },
      {
        id: "maintenance",
        name: "系统维护",
        version: "v1.0",
        completion: 25,
        dimensionStatus: ["yellow", "red", "red", "red", "red", "red", "red", "red"],
        lastUpdate: "3周前",
      },
      {
        id: "backup-restore",
        name: "备份恢复",
        version: "v1.0",
        completion: 30,
        dimensionStatus: ["green", "yellow", "red", "red", "red", "red", "red", "red"],
        lastUpdate: "2周前",
      },
    ],
  },
};
