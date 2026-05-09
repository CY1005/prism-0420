export const projectsStrings = {
  searchPlaceholder: "搜索功能、模块、竞品...",
  userName: "陈琦",
  userInitials: "陈",
  myProjects: "我的项目",
  newProject: "新建项目",
  lastUpdated: "最近更新：",
};

export const projectsData = [
  {
    id: "1",
    title: "AI云平台竞品分析",
    type: "产品分析",
    typeColor: "blue",
    description: "系统性分析AI云平台行业竞品设计与技术",
    stats: [
      { value: 3, label: "产品线" },
      { value: 42, label: "模块" },
      { value: "58%", label: "完善度" },
    ],
    lastUpdated: "2小时前",
    members: ["陈", "王", "李"],
  },
  {
    id: "2",
    title: "OpenClaw",
    type: "系统架构",
    typeColor: "green",
    description: "个人AI陪伴系统，Telegram+Claude全栈",
    stats: [
      { value: 4, label: "系统层" },
      { value: 15, label: "组件" },
      { value: "45%", label: "完善度" },
    ],
    lastUpdated: "昨天",
    members: ["陈"],
  },
  {
    id: "3",
    title: "MappingStudio",
    type: "研究平台",
    typeColor: "purple",
    description: "AI驱动的科技公司研究报告平台",
    stats: [
      { value: 5, label: "模块" },
      { value: 23, label: "功能" },
      { value: "30%", label: "完善度" },
    ],
    lastUpdated: "3天前",
    members: ["陈", "张"],
  },
  {
    id: "4",
    title: "Prism",
    type: "自定义",
    typeColor: "orange",
    description: "用Prism分析Prism，dogfooding验证",
    stats: [
      { value: 3, label: "阶段" },
      { value: 12, label: "模块" },
      { value: "20%", label: "完善度" },
    ],
    lastUpdated: "刚刚",
    members: ["陈", "M"],
  },
];
