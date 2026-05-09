export const detailStrings = {
  myProjects: "我的项目",
  projectName: "AI云平台竞品分析",
  searchPlaceholder: "搜索功能、模块、竞品...",
  userName: "陈琦",
  userInitials: "陈",
  productLine: "产品线",
  modules: "功能模块",
  features: "功能项",
  avgCompletion: "平均完善度",
  recentUpdates: "最近更新",
};

export const productLines = [
  {
    name: "私有云",
    completion: 85,
    modules: [
      { name: "推理服务", completion: 90 },
      { name: "训练服务", completion: 75 },
      { name: "运维管理", completion: 85 },
      { name: "资源管理", completion: 80 },
    ],
  },
  {
    name: "智算中心",
    completion: 55,
    modules: [
      { name: "推理服务", completion: 60 },
      { name: "训练服务", completion: 45 },
    ],
  },
  {
    name: "边缘计算",
    completion: 30,
    modules: [{ name: "边缘推理", completion: 30 }],
  },
];

export const recentUpdates = [
  {
    user: "陈",
    action: "更新了 推理服务>创建推理服务 的技术实现",
    time: "2小时前",
  },
  {
    user: "王",
    action: "添加了 训练服务>提交训练任务 的用户场景",
    time: "4小时前",
  },
  {
    user: "李",
    action: "修改了 资源管理>配额管理 的设计决策",
    time: "昨天",
  },
  {
    user: "陈",
    action: "新增了 推理服务>自动扩缩容 的工程经验",
    time: "2天前",
  },
  {
    user: "张",
    action: "完善了 智算中心>推理服务 的功能描述",
    time: "3天前",
  },
];

export const statsLabels = {
  line1: "3 条",
  line2: "42 个",
  line3: "128 个",
  line4: "58%",
};
