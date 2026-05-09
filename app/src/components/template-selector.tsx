"use client";

import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export interface ProjectTemplate {
  id: string;
  name: string;
  description: string;
  hierarchy: string;
  dimensions: string[];
  isCustom?: boolean;
}

export const PROJECT_TEMPLATES: ProjectTemplate[] = [
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
    dimensions: [],
    isCustom: true,
  },
];

interface TemplateSelectorProps {
  value: string;
  onChange: (templateId: string) => void;
  templates?: ProjectTemplate[];
}

export function TemplateSelector({
  value,
  onChange,
  templates = PROJECT_TEMPLATES,
}: TemplateSelectorProps) {
  return (
    <div className="grid grid-cols-4 gap-4">
      {templates.map((template) => (
        <Card
          key={template.id}
          className={cn(
            "cursor-pointer p-5 transition-all hover:shadow-md",
            value === template.id
              ? "border-primary border-2"
              : "border-border hover:border-border/80",
          )}
          onClick={() => onChange(template.id)}
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
  );
}
