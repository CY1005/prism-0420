export const comparisonData = {
  selectedFeature: "创建推理服务",
  competitors: [
    { id: "aws", name: "AWS SageMaker" },
    { id: "aliyun", name: "阿里PAI" },
  ],
  comparisonTable: [
    {
      dimension: "功能覆盖",
      ourProduct: { text: "CPU/GPU物理卡/虚拟卡三类选择", score: 0 },
      aws: { text: "Instance Type隐式选GPU", score: 0 },
      aliyun: { text: "GPU型号+规格族", score: 0 },
    },
    {
      dimension: "GPU 支持",
      ourProduct: { text: "NVIDIA/昇腾/海光/寒武纪", score: 1 },
      aws: { text: "仅NVIDIA", score: -1 },
      aliyun: { text: "NVIDIA/昇腾", score: 0 },
    },
    {
      dimension: "资源配置",
      ourProduct: { text: "实例规格选择或自定义", score: 0 },
      aws: { text: "预定义实例类型", score: 0 },
      aliyun: { text: "规格族+自定义", score: 0 },
    },
    {
      dimension: "虚拟化",
      ourProduct: { text: "GPU共享调度+显存隔离", score: 1 },
      aws: { text: "无原生vGPU", score: -1 },
      aliyun: { text: "cGPU", score: 0 },
    },
    {
      dimension: "扩缩容",
      ourProduct: { text: "手动+定时+HPA", score: 0 },
      aws: { text: "Application Auto Scaling", score: 1 },
      aliyun: { text: "弹性ESS", score: 0 },
    },
  ],
  conclusions: [
    { type: "advantage" as const, text: "多厂商GPU支持范围最广（4家 vs AWS仅NVIDIA）" },
    { type: "advantage" as const, text: "原生虚拟GPU能力" },
    { type: "disadvantage" as const, text: "扩缩容能力弱于AWS（缺少预测性扩缩容）" },
    { type: "disadvantage" as const, text: "无Spot/竞价实例降本方案" },
  ],
};
