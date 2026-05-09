"use client";

import { useState } from "react";
import Link from "next/link";
import {
  PanelLeftClose,
  PanelLeft,
  FileText,
  Users,
  Server,
  GitBranch,
  Lightbulb,
  TestTube,
  ClipboardList,
  Building,
  ChevronRight,
  History,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Card } from "@/components/ui/card";
import { ProtoDimensionCard } from "@/components/proto/dimension-card";
import { ProtoFeatureTree } from "@/components/proto/feature-tree";
import { ProtoVersionTimeline } from "@/components/proto/version-timeline";
import { treeData } from "@/lib/tree-data";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Separator } from "@/components/ui/separator";
import { testAnalysisData } from "@/lib/test-analysis-data";

// Version timeline data
const versionData = [
  {
    version: "v3.9.3",
    label: "当前版本",
    isCurrent: true,
    summary: "新增拼卡能力，支持多卡虚拟化共享",
    details:
      "本版本重点优化了多GPU场景下的资源利用效率，支持将单张物理GPU虚拟化为多个vGPU实例，并实现了跨节点的资源池化调度。",
  },
  {
    version: "v3.7",
    summary: "新增自动扩缩容，支持定时策略",
    details:
      "引入基于HPA的自动扩缩容能力，支持按CPU/GPU利用率、QPS等指标触发扩缩容，同时支持定时扩缩容策略配置。",
  },
  {
    version: "v1.6",
    summary: "首次上线：基础 GPU 类型选择",
    details: "产品首个正式版本，支持NVIDIA GPU的基础调度能力，包括型号选择和数量配置。",
  },
];

export default function FeatureDetailPage() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [selectedFeature, setSelectedFeature] = useState("create-inference");

  const completedDimensions = 5;
  const totalDimensions = 8;
  const completionPercent = Math.round((completedDimensions / totalDimensions) * 100);

  return (
    <div className="bg-background flex h-screen">
      {/* Sidebar */}
      <aside
        className={cn(
          "border-sidebar-border bg-sidebar flex flex-col border-r transition-all duration-300",
          sidebarCollapsed ? "w-0 overflow-hidden" : "w-[280px]",
        )}
      >
        <div className="border-sidebar-border flex h-14 items-center justify-between border-b px-4">
          <div className="flex items-center gap-2">
            <Link
              href="/projects"
              className="text-sidebar-foreground hover:text-primary font-semibold transition-colors"
            >
              AI云平台竞品分析
            </Link>
            <Badge variant="outline" className="border-blue-200 bg-blue-50 text-xs text-blue-700">
              产品分析
            </Badge>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => setSidebarCollapsed(true)}
          >
            <PanelLeftClose className="h-4 w-4" />
          </Button>
        </div>
        <ScrollArea className="flex-1">
          <div className="px-2">
            <ProtoFeatureTree
              data={treeData}
              selectedId={selectedFeature}
              onSelect={setSelectedFeature}
            />
          </div>
        </ScrollArea>
      </aside>

      {/* Main Content */}
      <main className="flex flex-1 flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="border-border bg-card flex h-14 items-center justify-between border-b px-6">
          <div className="flex items-center gap-4">
            {sidebarCollapsed && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setSidebarCollapsed(false)}
              >
                <PanelLeft className="h-4 w-4" />
              </Button>
            )}
            <Breadcrumb>
              <BreadcrumbList>
                <BreadcrumbItem>
                  <BreadcrumbLink href="/projects/1">AI云平台竞品分析</BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator>
                  <ChevronRight className="h-4 w-4" />
                </BreadcrumbSeparator>
                <BreadcrumbItem>
                  <BreadcrumbLink href="/projects/1/product-lines/private-cloud">
                    私有云
                  </BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator>
                  <ChevronRight className="h-4 w-4" />
                </BreadcrumbSeparator>
                <BreadcrumbItem>
                  <BreadcrumbLink href="/projects/1/modules/inference-service">
                    推理服务
                  </BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator>
                  <ChevronRight className="h-4 w-4" />
                </BreadcrumbSeparator>
                <BreadcrumbItem>
                  <BreadcrumbPage>创建推理服务</BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-muted-foreground text-sm">
              {completedDimensions}/{totalDimensions} 维度已填写
            </span>
            <div className="flex items-center gap-2">
              <Progress value={completionPercent} className="h-2 w-24" />
              <span className="text-foreground text-sm font-medium">{completionPercent}%</span>
            </div>
          </div>
        </header>

        {/* Scrollable Content */}
        <ScrollArea className="flex-1">
          <div className="mx-auto max-w-4xl space-y-4 p-6">
            {/* Card 1: 功能描述 */}
            <ProtoDimensionCard
              title="功能描述"
              icon={FileText}
              entryCount={1}
              defaultExpanded={true}
              onAdd={() => {}}
            >
              <p className="text-foreground text-sm leading-relaxed">
                {
                  "支持按需选择 CPU、GPU 物理卡、GPU 虚拟卡三类资源配置任务。用户可根据实例规格卡上的资源量提示直接选择，也可由运维管理员在规格管理中自定义配置。"
                }
              </p>
            </ProtoDimensionCard>

            {/* Card 2: 用户使用场景 */}
            <ProtoDimensionCard
              title="用户使用场景"
              icon={Users}
              entryCount={2}
              defaultExpanded={true}
              onAdd={() => {}}
            >
              <div className="border-border overflow-hidden rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead className="font-medium">角色</TableHead>
                      <TableHead className="font-medium">使用场景</TableHead>
                      <TableHead className="font-medium">用户侧技术栈</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow>
                      <TableCell className="font-medium">算法工程师</TableCell>
                      <TableCell>提交训练任务时选择 GPU 类型和数量</TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Badge variant="outline">PyTorch</Badge>
                          <Badge variant="outline">TensorFlow</Badge>
                        </div>
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="font-medium">运维管理员</TableCell>
                      <TableCell>配置默认资源配额和实例规格</TableCell>
                      <TableCell>
                        <Badge variant="outline">平台管理控制台</Badge>
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>
            </ProtoDimensionCard>

            {/* Card 3: 技术实现 */}
            <ProtoDimensionCard
              title="技术实现"
              icon={Server}
              entryCount={2}
              defaultExpanded={true}
              onAdd={() => {}}
            >
              <div className="space-y-3">
                <div className="border-border bg-muted/30 rounded-md border p-4">
                  <h4 className="text-foreground text-sm font-medium">GPU 调度机制</h4>
                  <p className="text-muted-foreground mt-1 text-sm">
                    GPU 调度基于 Kubernetes device plugin，支持 NVIDIA / 华为昇腾 / 海光 DCU /
                    寒武纪 MLU
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    <Badge variant="secondary">Kubernetes</Badge>
                    <Badge variant="secondary">Device Plugin</Badge>
                    <Badge variant="secondary">多厂商支持</Badge>
                  </div>
                </div>
                <div className="border-border bg-muted/30 rounded-md border p-4">
                  <h4 className="text-foreground text-sm font-medium">虚拟 GPU 实现</h4>
                  <p className="text-muted-foreground mt-1 text-sm">
                    虚拟 GPU 通过 GPU 共享调度器实现，支持显存隔离
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    <Badge variant="secondary">vGPU</Badge>
                    <Badge variant="secondary">显存隔离</Badge>
                  </div>
                </div>
                <p className="text-muted-foreground mt-4 text-xs">
                  参考标准：Volcano (CNCF孵化·华为主导) · KServe (K8s模型serving标准)
                </p>
              </div>
            </ProtoDimensionCard>

            {/* Card 4: 设计决策 */}
            <ProtoDimensionCard
              title="设计决策"
              icon={GitBranch}
              entryCount={1}
              defaultExpanded={true}
              onAdd={() => {}}
            >
              <div className="border-border space-y-4 rounded-md border p-4">
                <div>
                  <h4 className="text-muted-foreground text-xs font-medium tracking-wider uppercase">
                    背景
                  </h4>
                  <p className="text-foreground mt-1 text-sm">
                    需要同时支持物理卡和虚拟卡的资源分配
                  </p>
                </div>
                <div>
                  <h4 className="text-muted-foreground text-xs font-medium tracking-wider uppercase">
                    决策
                  </h4>
                  <p className="text-foreground mt-1 text-sm">
                    统一资源模型，通过 type 字段区分物理卡/虚拟卡
                  </p>
                </div>
                <div>
                  <h4 className="text-destructive text-xs font-medium tracking-wider uppercase">
                    放弃的方案
                  </h4>
                  <p className="text-muted-foreground mt-1 text-sm">
                    物理卡和虚拟卡分成两套模型（否决原因：重复逻辑太多）
                  </p>
                </div>
                <div>
                  <h4 className="text-muted-foreground text-xs font-medium tracking-wider uppercase">
                    后果
                  </h4>
                  <p className="text-foreground mt-1 text-sm">
                    API 更简洁，但需要按类型做差异化校验
                  </p>
                </div>
              </div>
            </ProtoDimensionCard>

            {/* Card 5: 工程经验 */}
            <ProtoDimensionCard
              title="工程经验"
              icon={Lightbulb}
              entryCount={1}
              defaultExpanded={true}
              onAdd={() => {}}
            >
              <div className="border-border rounded-md border bg-amber-50/50 p-4">
                <div className="flex items-start gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-amber-100">
                    <Lightbulb className="h-4 w-4 text-amber-600" />
                  </div>
                  <div>
                    <h4 className="text-foreground text-sm font-medium">NUMA 亲和性问题</h4>
                    <p className="text-muted-foreground mt-1 text-sm">
                      拼卡后推理延迟反而增大。根因：跨 NUMA 节点的显存访问。修复：调度器增加 NUMA
                      拓扑感知。
                    </p>
                    <div className="mt-3 flex flex-wrap gap-1">
                      <Badge className="bg-red-100 text-red-700 hover:bg-red-100">踩坑</Badge>
                      <Badge className="bg-blue-100 text-blue-700 hover:bg-blue-100">GPU</Badge>
                      <Badge className="bg-green-100 text-green-700 hover:bg-green-100">性能</Badge>
                    </div>
                  </div>
                </div>
              </div>
            </ProtoDimensionCard>

            {/* Card 6: 测试分析 */}
            <ProtoDimensionCard
              title="测试分析"
              icon={TestTube}
              entryCount={2}
              collapsedSummary="已记录 2 个问题"
              defaultExpanded={true}
              onAdd={() => {}}
            >
              <div>
                {/* Sub-tabs */}
                <div className="mb-4 flex gap-4 border-b">
                  <span className="text-primary border-primary border-b-2 pb-2 text-sm font-medium">
                    问题列表
                  </span>
                  <span className="text-muted-foreground pb-2 text-sm">测试用例</span>
                </div>

                {/* Add Issue Button */}
                <div className="mb-3 flex justify-end">
                  <Button variant="outline" size="sm">
                    + 记录问题
                  </Button>
                </div>

                {/* Issues */}
                <div className="space-y-3">
                  {testAnalysisData.issues.map((issue) => (
                    <Card key={issue.id} className="border-border/60 p-4">
                      <div className="flex items-center gap-2">
                        <Badge
                          className={
                            issue.type === "Bug"
                              ? "bg-red-100 text-red-700"
                              : "bg-yellow-100 text-yellow-700"
                          }
                        >
                          {issue.type}
                        </Badge>
                        <span className="text-sm font-medium">{issue.title}</span>
                        <div className="flex-1" />
                        <Badge variant="secondary">{issue.priority}</Badge>
                      </div>
                      <p className="text-muted-foreground mt-2 text-sm">{issue.description}</p>
                      <div className="mt-2 flex gap-2">
                        <Badge variant="outline" className="text-xs">
                          {issue.version}
                        </Badge>
                        <span className="text-muted-foreground text-xs">
                          发现于 {issue.foundDate}
                        </span>
                      </div>
                    </Card>
                  ))}
                </div>

                {/* Separator and Test Cases */}
                <Separator className="my-4" />

                <h4 className="mb-1 text-sm font-medium">测试用例</h4>
                <p className="text-muted-foreground mb-3 text-xs">
                  共 {testAnalysisData.testCases.total} 条（{testAnalysisData.testCases.aiGenerated}{" "}
                  条 AI 生成，{testAnalysisData.testCases.manual} 条手动）
                </p>

                <div className="overflow-hidden rounded-md border">
                  <Table className="text-sm">
                    <TableHeader>
                      <TableRow className="bg-muted/50">
                        <TableHead className="w-8">#</TableHead>
                        <TableHead>测试用例</TableHead>
                        <TableHead className="w-16">来源</TableHead>
                        <TableHead className="w-14">优先级</TableHead>
                        <TableHead className="w-16">状态</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {testAnalysisData.testCases.items.map((testCase) => (
                        <TableRow key={testCase.id}>
                          <TableCell>{testCase.id}</TableCell>
                          <TableCell>{testCase.name}</TableCell>
                          <TableCell>
                            <Badge
                              className={
                                testCase.source === "AI生成"
                                  ? "bg-blue-50 text-xs text-blue-700"
                                  : "bg-gray-100 text-xs text-gray-700"
                              }
                            >
                              {testCase.source}
                            </Badge>
                          </TableCell>
                          <TableCell>{testCase.priority}</TableCell>
                          <TableCell>
                            <Badge
                              className={cn(
                                "text-xs",
                                testCase.status === "通过" && "bg-green-50 text-green-700",
                                testCase.status === "失败" && "bg-red-50 text-red-700",
                                testCase.status === "未执行" && "bg-gray-100 text-gray-600",
                              )}
                            >
                              {testCase.status}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            </ProtoDimensionCard>

            {/* Card 7: 需求分析 (collapsed, empty) */}
            <ProtoDimensionCard
              title="需求分析"
              icon={ClipboardList}
              entryCount={0}
              collapsedSummary="未填写"
              defaultExpanded={false}
              onAdd={() => {}}
            >
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <ClipboardList className="text-muted-foreground/40 h-10 w-10" />
                <p className="text-muted-foreground mt-2 text-sm">
                  点击添加，或上传需求文档自动分析
                </p>
              </div>
            </ProtoDimensionCard>

            {/* Card 8: 竞品参考 (collapsed) */}
            <ProtoDimensionCard
              title="竞品参考"
              icon={Building}
              entryCount={3}
              collapsedSummary="已对标 3 家竞品"
              defaultExpanded={false}
              onAdd={() => {}}
            >
              <p className="text-muted-foreground text-sm">竞品参考内容...</p>
            </ProtoDimensionCard>

            {/* Version Timeline Section */}
            <div className="border-border mt-8 border-t pt-6">
              <div className="mb-6 flex items-center gap-2">
                <History className="text-primary h-5 w-5" />
                <h2 className="text-foreground text-lg font-semibold">版本演进</h2>
              </div>
              <ProtoVersionTimeline versions={versionData} />
            </div>
          </div>
        </ScrollArea>
      </main>
    </div>
  );
}
