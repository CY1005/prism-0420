"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { createProject } from "@/actions/projects";
import { handleActionResult } from "@/lib/client-error";

const templates = [
  {
    id: "product_analysis",
    name: "产品竞品分析",
    description: "适合分析竞品产品设计与技术实现",
    hierarchy: "产品线 → 模块 → 功能项",
    dimensions: [
      "功能描述",
      "用户场景",
      "技术实现",
      "设计决策",
      "工程经验",
      "测试分析",
      "需求分析",
      "竞品参考",
    ],
  },
  {
    id: "system_architecture",
    name: "系统架构项目",
    description: "适合记录系统设计与架构演进",
    hierarchy: "系统层 → 组件 → 功能",
    dimensions: ["功能描述", "接口规范", "设计决策", "工程经验", "部署配置", "测试分析"],
  },
  {
    id: "research_platform",
    name: "开源项目研究",
    description: "适合开源项目和研究工具分析",
    hierarchy: "应用层 → 模块 → 功能",
    dimensions: [
      "功能描述",
      "用户场景",
      "设计决策",
      "工程经验",
      "质量指标",
      "成本分析",
      "测试分析",
    ],
  },
  {
    id: "custom",
    name: "自定义",
    description: "自由选择维度组合和层级名称",
    hierarchy: "自定义",
    dimensions: [] as string[],
    isCustom: true,
  },
];

export default function NewProjectPage() {
  const [selectedTemplate, setSelectedTemplate] = useState("product_analysis");
  const [projectName, setProjectName] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  const handleCreate = () => {
    if (!projectName.trim()) {
      setError("请输入项目名称");
      return;
    }
    setError("");
    const formData = new FormData();
    formData.set("name", projectName.trim());
    formData.set("description", projectDescription.trim());
    formData.set("templateType", selectedTemplate);

    startTransition(async () => {
      const result = await createProject(formData);
      const handled = handleActionResult(result, router, {
        currentPath: "/projects/new",
      });
      if (handled.ok) {
        router.push(`/projects/${handled.data.id}`);
      } else if (!handled.autoHandled) {
        setError(handled.message);
      }
    });
  };

  return (
    <div className="bg-background min-h-screen">
      <header className="border-border bg-card flex h-14 items-center justify-between border-b px-6">
        <div className="flex items-center gap-4">
          <Link
            href="/projects"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <h1 className="text-foreground text-lg font-semibold">新建项目</h1>
        </div>
        <Link href="/projects" className="text-muted-foreground hover:text-foreground text-sm">
          返回项目列表
        </Link>
      </header>

      <div className="mx-auto max-w-5xl space-y-8 p-6">
        {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</div>}

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">项目名称</Label>
            <Input
              id="name"
              placeholder="输入项目名称"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">项目描述</Label>
            <Textarea
              id="description"
              placeholder="简要描述项目目标和范围"
              value={projectDescription}
              onChange={(e) => setProjectDescription(e.target.value)}
              rows={3}
            />
          </div>
        </div>

        <div className="space-y-4">
          <h2 className="text-lg font-semibold">选择模板</h2>
          <div className="grid grid-cols-4 gap-4">
            {templates.map((template) => (
              <Card
                key={template.id}
                className={cn(
                  "cursor-pointer p-5 transition-all hover:shadow-md",
                  selectedTemplate === template.id
                    ? "border-primary border-2"
                    : "border-border hover:border-border/80",
                )}
                onClick={() => setSelectedTemplate(template.id)}
              >
                <h3 className="text-foreground mb-2 text-base font-semibold">{template.name}</h3>
                <p className="text-muted-foreground mb-4 text-sm">{template.description}</p>

                <div className="space-y-3">
                  <div>
                    <p className="text-muted-foreground mb-1 text-xs font-medium">层级结构</p>
                    <p className="text-foreground text-sm">{template.hierarchy}</p>
                  </div>

                  <div>
                    <p className="text-muted-foreground mb-2 text-xs font-medium">预设维度</p>
                    {template.isCustom ? (
                      <p className="text-muted-foreground text-xs">创建后在项目设置中配置</p>
                    ) : (
                      <div className="flex flex-wrap gap-1">
                        {template.dimensions.map((dim) => (
                          <Badge key={dim} variant="secondary" className="text-xs">
                            {dim}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>

        <div className="border-border flex justify-end gap-3 border-t pt-4">
          <Link href="/projects">
            <Button variant="outline">取消</Button>
          </Link>
          <Button variant="default" onClick={handleCreate} disabled={isPending}>
            {isPending ? "创建中..." : "创建项目"}
          </Button>
        </div>
      </div>
    </div>
  );
}
