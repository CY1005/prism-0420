"use client";

import { useState } from "react";
import Link from "next/link";
import {
  PanelLeftClose,
  PanelLeft,
  FileText,
  FileCode,
  GitBranch,
  Lightbulb,
  TestTube,
  Server,
  ChevronRight,
  History,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { ProtoDimensionCard } from "@/components/proto/dimension-card";
import { ProtoFeatureTree } from "@/components/proto/feature-tree";
import { ProtoVersionTimeline } from "@/components/proto/version-timeline";
import { openclawTreeData } from "@/lib/openclaw-data";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

// Date-based version timeline for OpenClaw
const versionData = [
  {
    version: "2026-04-07",
    label: "最新",
    isCurrent: true,
    summary: "修复 cron 报错，升级 router v2 架构",
    details:
      "优化了日报技能的定时任务调度，修复了因时区问题导致的cron执行异常。同时升级路由层至v2架构，支持更灵活的意图分发。",
  },
  {
    version: "2026-03-28",
    summary: "新增人格记忆系统，支持多人格切换",
    details:
      "引入人格记忆机制，支持在对话中切换不同的AI人格，每个人格保持独立的记忆上下文和对话风格。",
  },
  {
    version: "2026-03-15",
    summary: "初始部署：基础消息收发 + 日报技能",
    details: "系统首次上线，实现Telegram消息的基础收发功能，以及每日日报的自动生成与推送。",
  },
];

export default function OpenClawFeaturePage() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [selectedFeature, setSelectedFeature] = useState("msg-send-receive");

  const completedDimensions = 4;
  const totalDimensions = 6;
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
              OpenClaw
            </Link>
            <Badge
              variant="outline"
              className="border-green-200 bg-green-50 text-xs text-green-700"
            >
              系统架构
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
              data={openclawTreeData}
              selectedId={selectedFeature}
              onSelect={setSelectedFeature}
              defaultExpanded={[
                "message-layer",
                "telegram-bridge",
                "router-layer",
                "fastapi-router",
                "skill-layer",
                "memory-layer",
              ]}
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
                  <BreadcrumbLink href="/projects/2">OpenClaw</BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator>
                  <ChevronRight className="h-4 w-4" />
                </BreadcrumbSeparator>
                <BreadcrumbItem>
                  <BreadcrumbLink href="/projects/2">消息层</BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator>
                  <ChevronRight className="h-4 w-4" />
                </BreadcrumbSeparator>
                <BreadcrumbItem>
                  <BreadcrumbLink href="/projects/2">Telegram Bridge</BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator>
                  <ChevronRight className="h-4 w-4" />
                </BreadcrumbSeparator>
                <BreadcrumbItem>
                  <BreadcrumbPage>消息收发</BreadcrumbPage>
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
                通过 Telegram Bot API 的 getUpdates
                长轮询接收用户消息，经消息队列转发至路由层处理，通过 sendMessage
                返回AI响应。支持文本、图片、文件三种消息类型。
              </p>
            </ProtoDimensionCard>

            {/* Card 2: 接口规范 (System Architecture specific) */}
            <ProtoDimensionCard
              title="接口规范"
              icon={FileCode}
              entryCount={1}
              defaultExpanded={true}
              onAdd={() => {}}
            >
              <div className="border-border overflow-hidden rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead className="font-medium">方向</TableHead>
                      <TableHead className="font-medium">协议</TableHead>
                      <TableHead className="font-medium">端点</TableHead>
                      <TableHead className="font-medium">说明</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow>
                      <TableCell className="font-medium">入站</TableCell>
                      <TableCell>HTTPS</TableCell>
                      <TableCell className="font-mono text-xs">
                        api.telegram.org/bot{"{token}"}/getUpdates
                      </TableCell>
                      <TableCell className="text-muted-foreground">长轮询接收消息</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="font-medium">出站</TableCell>
                      <TableCell>HTTP</TableCell>
                      <TableCell className="font-mono text-xs">
                        localhost:8900/webhook/telegram
                      </TableCell>
                      <TableCell className="text-muted-foreground">转发至Router处理</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="font-medium">出站</TableCell>
                      <TableCell>HTTPS</TableCell>
                      <TableCell className="font-mono text-xs">
                        api.telegram.org/bot{"{token}"}/sendMessage
                      </TableCell>
                      <TableCell className="text-muted-foreground">返回响应给用户</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>
            </ProtoDimensionCard>

            {/* Card 3: 设计决策 */}
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
                    消息接收需要选择 Webhook 还是长轮询
                  </p>
                </div>
                <div>
                  <h4 className="text-muted-foreground text-xs font-medium tracking-wider uppercase">
                    决策
                  </h4>
                  <p className="text-foreground mt-1 text-sm">选择长轮询（getUpdates）</p>
                </div>
                <div>
                  <h4 className="text-destructive text-xs font-medium tracking-wider uppercase">
                    放弃的方案
                  </h4>
                  <p className="text-muted-foreground mt-1 text-sm">
                    Webhook 需要公网 HTTPS 域名和证书，当前服务器不具备条件
                  </p>
                </div>
                <div>
                  <h4 className="text-muted-foreground text-xs font-medium tracking-wider uppercase">
                    后果
                  </h4>
                  <p className="text-foreground mt-1 text-sm">
                    消息延迟略高（1-2秒），但部署零依赖，适合个人服务器
                  </p>
                </div>
              </div>
            </ProtoDimensionCard>

            {/* Card 4: 工程经验 */}
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
                    <h4 className="text-foreground text-sm font-medium">Telegram API 限流踩坑</h4>
                    <p className="text-muted-foreground mt-1 text-sm">
                      getUpdates 频率超过 30次/秒会被临时封禁
                      token。根因：轮询间隔设得太短。修复：间隔从 0.5秒 改为 2秒，增加 429
                      状态码自动退避。
                    </p>
                    <div className="mt-3 flex flex-wrap gap-1">
                      <Badge className="bg-red-100 text-red-700 hover:bg-red-100">踩坑</Badge>
                      <Badge className="bg-blue-100 text-blue-700 hover:bg-blue-100">API限流</Badge>
                      <Badge className="bg-purple-100 text-purple-700 hover:bg-purple-100">
                        Telegram
                      </Badge>
                    </div>
                  </div>
                </div>
              </div>
            </ProtoDimensionCard>

            {/* Card 5: 部署配置 (System Architecture specific) */}
            <ProtoDimensionCard
              title="部署配置"
              icon={Server}
              entryCount={1}
              defaultExpanded={true}
              onAdd={() => {}}
            >
              <div className="border-border bg-muted/30 rounded-md border p-4">
                <h4 className="text-foreground text-sm font-medium">systemd 服务配置</h4>
                <p className="text-muted-foreground mt-1 text-sm">
                  服务名 telegram-polling.service，开机自启（WantedBy=multi-user.target），异常退出
                  3秒后自动重启（RestartSec=3）。依赖 message-router.service 先启动。
                </p>
                <div className="mt-2 flex flex-wrap gap-1">
                  <Badge variant="secondary">systemd</Badge>
                  <Badge variant="secondary">自动重启</Badge>
                  <Badge variant="secondary">服务依赖</Badge>
                </div>
              </div>
            </ProtoDimensionCard>

            {/* Card 6: 测试分析 (collapsed) */}
            <ProtoDimensionCard
              title="测试分析"
              icon={TestTube}
              entryCount={1}
              collapsedSummary="已记录 1 个测试场景"
              defaultExpanded={false}
              onAdd={() => {}}
            >
              <p className="text-muted-foreground text-sm">测试分析内容...</p>
            </ProtoDimensionCard>

            {/* Version Timeline Section - Date based */}
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
