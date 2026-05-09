// OpenClaw project data (System Architecture type)
export const openclawStrings = {
  searchPlaceholder: "搜索功能、模块、竞品...",
  userName: "陈琦",
  userInitials: "陈",
  myProjects: "我的项目",
  projectName: "OpenClaw",
  productLine: "系统层",
  modules: "组件",
  features: "功能",
  avgCompletion: "平均完善度",
  recentUpdates: "最近更新",
};

export const openclawStatsLabels = {
  line1: "4个",
  line2: "15个",
  line3: "38个",
  line4: "45%",
};

export const openclawSystemLayers = [
  {
    name: "消息层",
    completion: 60,
    modules: [
      { name: "Telegram Bridge", completion: 55 },
      { name: "消息队列", completion: 70 },
    ],
  },
  {
    name: "路由层",
    completion: 50,
    modules: [
      { name: "FastAPI Router", completion: 55 },
      { name: "意图识别", completion: 40 },
    ],
  },
  {
    name: "技能层",
    completion: 40,
    modules: [
      { name: "日报技能", completion: 60 },
      { name: "健康打卡", completion: 45 },
      { name: "学习复盘", completion: 30 },
      { name: "面试练习", completion: 25 },
    ],
  },
  {
    name: "记忆层",
    completion: 35,
    modules: [
      { name: "核心记忆", completion: 50 },
      { name: "工作记忆", completion: 40 },
      { name: "长期记忆", completion: 25 },
    ],
  },
];

export const openclawRecentUpdates = [
  {
    user: "陈",
    action: "修复了 技能层>日报技能 的cron报错",
    time: "2天前",
  },
  {
    user: "陈",
    action: "更新了 记忆层>核心记忆 的接口规范",
    time: "3天前",
  },
  {
    user: "陈",
    action: "新增了 路由层>FastAPI Router 的设计决策",
    time: "5天前",
  },
];

// Tree data for sidebar navigation
export const openclawTreeData = [
  {
    id: "message-layer",
    name: "消息层",
    type: "folder" as const,
    completionPercent: 60,
    children: [
      {
        id: "telegram-bridge",
        name: "Telegram Bridge",
        type: "folder" as const,
        completionPercent: 55,
        children: [
          {
            id: "msg-send-receive",
            name: "消息收发",
            type: "file" as const,
            completionPercent: 67,
          },
          { id: "polling", name: "轮询机制", type: "file" as const, completionPercent: 40 },
        ],
      },
      {
        id: "msg-queue",
        name: "消息队列",
        type: "folder" as const,
        completionPercent: 70,
        children: [
          { id: "queue-manage", name: "队列管理", type: "file" as const, completionPercent: 70 },
        ],
      },
    ],
  },
  {
    id: "router-layer",
    name: "路由层",
    type: "folder" as const,
    completionPercent: 50,
    children: [
      {
        id: "fastapi-router",
        name: "FastAPI Router",
        type: "folder" as const,
        completionPercent: 55,
        children: [
          { id: "msg-routing", name: "消息路由", type: "file" as const, completionPercent: 60 },
          { id: "intent-detect", name: "意图识别", type: "file" as const, completionPercent: 40 },
        ],
      },
    ],
  },
  {
    id: "skill-layer",
    name: "技能层",
    type: "folder" as const,
    completionPercent: 40,
    children: [
      { id: "daily-report", name: "日报技能", type: "file" as const, completionPercent: 60 },
      { id: "health-check", name: "健康打卡", type: "file" as const, completionPercent: 45 },
    ],
  },
  {
    id: "memory-layer",
    name: "记忆层",
    type: "folder" as const,
    completionPercent: 35,
    children: [
      { id: "core-memory", name: "核心记忆", type: "file" as const, completionPercent: 50 },
      { id: "working-memory", name: "工作记忆", type: "file" as const, completionPercent: 40 },
    ],
  },
];
