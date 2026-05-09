"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Bell, ChevronRight, LogOut, Settings, Shield, Folder } from "lucide-react";
import { GlobalSearchBar } from "@/components/global-search-bar";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
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
import { productLinesData } from "@/lib/product-line-data";
import { usePageContext } from "@/lib/use-page-context";
import { cn } from "@/lib/utils";

function getStatusColor(percent: number) {
  if (percent >= 80) return "bg-green-500";
  if (percent >= 40) return "bg-yellow-500";
  return "bg-red-500";
}

function getDimensionBadgeStyle(current: number, total: number) {
  const ratio = current / total;
  if (ratio >= 0.8) return "bg-green-50 text-green-700";
  if (ratio >= 0.4) return "bg-yellow-50 text-yellow-700";
  return "bg-red-50 text-red-700";
}

export default function ProductLineOverviewPage() {
  const params = useParams();
  const projectId = params.projectId as string;
  const plId = params.plId as string;
  const { projectName, userName, userInitials } = usePageContext(projectId);

  const productLine = productLinesData[plId] || productLinesData["private-cloud"];

  return (
    <div className="bg-background flex min-h-screen flex-col">
      {/* Header */}
      <header className="border-border bg-card flex h-14 items-center justify-between border-b px-6">
        <Link
          href="/projects"
          className="text-foreground hover:text-primary text-lg font-semibold transition-colors"
        >
          Prism
        </Link>
        <GlobalSearchBar />
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
            <Link href="/admin">
              <Shield className="text-muted-foreground h-4 w-4" />
            </Link>
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
            <Link href={`/projects/${projectId}/settings`}>
              <Settings className="text-muted-foreground h-4 w-4" />
            </Link>
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <Bell className="text-muted-foreground h-4 w-4" />
          </Button>
          <div className="flex items-center gap-2">
            <Avatar className="h-8 w-8">
              <AvatarFallback className="bg-muted text-sm">{userInitials || "?"}</AvatarFallback>
            </Avatar>
            <span className="text-foreground text-sm">{userName}</span>
          </div>
          <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
            <Link href="/login">
              <LogOut className="text-muted-foreground h-4 w-4" />
            </Link>
          </Button>
        </div>
      </header>

      {/* Breadcrumb */}
      <div className="px-6 py-4">
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink href="/projects">我的项目</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator>
              <ChevronRight className="h-4 w-4" />
            </BreadcrumbSeparator>
            <BreadcrumbItem>
              <BreadcrumbLink href={`/projects/${projectId}/overview`}>
                {projectName || "加载中..."}
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator>
              <ChevronRight className="h-4 w-4" />
            </BreadcrumbSeparator>
            <BreadcrumbItem>
              <BreadcrumbPage>{productLine.name}</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </div>

      {/* Tab Navigation */}
      <div className="border-border flex items-center gap-6 border-b px-6">
        <Link
          href={`/projects/${projectId}/overview`}
          className="text-muted-foreground hover:text-foreground pt-2 pb-3 text-sm"
        >
          全景图
        </Link>
        <Link
          href={`/projects/${projectId}/product-lines/private-cloud`}
          className="border-primary text-primary border-b-2 pt-2 pb-3 text-sm font-medium"
        >
          产品线
        </Link>
        <Link
          href={`/projects/${projectId}/analysis`}
          className="text-muted-foreground hover:text-foreground pt-2 pb-3 text-sm"
        >
          需求工作台
        </Link>
        <Link
          href={`/projects/${projectId}/comparison`}
          className="text-muted-foreground hover:text-foreground pt-2 pb-3 text-sm"
        >
          竞品对比
        </Link>
        <Link
          href={`/projects/${projectId}/issues`}
          className="text-muted-foreground hover:text-foreground pt-2 pb-3 text-sm"
        >
          问题沉淀
        </Link>
        <div className="flex-1" />
        <Link
          href={`/projects/${projectId}/settings`}
          className="text-muted-foreground hover:text-foreground flex items-center gap-1 pt-2 pb-3 text-sm"
        >
          <Settings className="h-3.5 w-3.5" />
          设置
        </Link>
      </div>

      {/* Main Content */}
      <ScrollArea className="flex-1">
        <div className="mx-auto max-w-4xl p-6">
          {/* Stats Cards */}
          <div className="mb-6 grid grid-cols-3 gap-4">
            <Card className="border-border/60 p-4 shadow-sm">
              <span className="text-foreground text-3xl font-bold">{productLine.moduleCount}</span>
              <p className="text-muted-foreground text-sm">功能模块</p>
            </Card>
            <Card className="border-border/60 p-4 shadow-sm">
              <span className="text-foreground text-3xl font-bold">{productLine.featureCount}</span>
              <p className="text-muted-foreground text-sm">功能项</p>
            </Card>
            <Card className="border-border/60 p-4 shadow-sm">
              <span className="text-primary text-3xl font-bold">{productLine.avgCompletion}%</span>
              <Progress value={productLine.avgCompletion} className="mt-2 h-2" />
              <p className="text-muted-foreground mt-1 text-sm">平均完善度</p>
            </Card>
          </div>

          {/* Module List */}
          <div className="space-y-3">
            {productLine.modules.map((module) => (
              <Link key={module.id} href={`/projects/${projectId}/modules/${module.id}`}>
                <Card className="border-border/60 hover:border-primary/30 cursor-pointer p-4 shadow-sm transition-colors">
                  {/* Top Row */}
                  <div className="flex items-center gap-3">
                    <div className="bg-primary/10 flex h-8 w-8 items-center justify-center rounded-md">
                      <Folder className="text-primary h-4 w-4" />
                    </div>
                    <span className="text-foreground font-medium">{module.name}</span>
                    <div className="flex-1" />
                    <span className="text-muted-foreground text-sm">
                      {module.featureCount}个功能项
                    </span>
                    <span
                      className={cn("h-2.5 w-2.5 rounded-full", getStatusColor(module.completion))}
                    />
                    <span className="text-foreground text-sm font-medium">
                      {module.completion}%
                    </span>
                    <ChevronRight className="text-muted-foreground h-4 w-4" />
                  </div>

                  {/* Dimension Tags */}
                  <div className="mt-3 flex flex-wrap gap-2">
                    {module.dimensions.map((dim) => (
                      <span
                        key={dim.name}
                        className={cn(
                          "rounded px-2 py-0.5 text-xs",
                          getDimensionBadgeStyle(dim.current, dim.total),
                        )}
                      >
                        {dim.name} {dim.current}/{dim.total}
                      </span>
                    ))}
                  </div>

                  {/* Last Update */}
                  <p className="text-muted-foreground mt-2 text-xs">
                    最近更新：{module.lastUpdate.user} {module.lastUpdate.action} —{" "}
                    {module.lastUpdate.time}
                  </p>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}
