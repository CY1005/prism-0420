"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { listTemplates, deleteTemplate, type Template } from "@/actions/templates";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";

const CATEGORIES: Record<string, string> = {
  general: "通用",
  functional: "功能分析",
  performance: "性能分析",
  security: "安全分析",
};

export default function TemplatesPage() {
  const params = useParams();
  const projectId = params.projectId as string;
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string | undefined>(undefined);

  const loadTemplates = async () => {
    setLoading(true);
    const result = await listTemplates(projectId, filter);
    if (result.success) {
      setTemplates(result.data.templates);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadTemplates();
  }, [projectId, filter]);

  const handleDelete = async (id: string) => {
    if (!confirm("确定删除此模板？")) return;
    const result = await deleteTemplate(id);
    if (result.success) {
      loadTemplates();
    }
  };

  return (
    <div className="mx-auto max-w-5xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">分析模板</h1>
          <p className="text-muted-foreground mt-1 text-sm">
            从 AI 分析经验中提炼的可复用模板，下次分析时自动匹配加载
          </p>
        </div>
      </div>

      {/* Category filter */}
      <div className="mb-4 flex gap-2">
        <Button
          variant={filter === undefined ? "default" : "outline"}
          size="sm"
          onClick={() => setFilter(undefined)}
        >
          全部
        </Button>
        {Object.entries(CATEGORIES).map(([key, label]) => (
          <Button
            key={key}
            variant={filter === key ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter(key)}
          >
            {label}
          </Button>
        ))}
      </div>

      {loading ? (
        <p className="text-muted-foreground">加载中...</p>
      ) : templates.length === 0 ? (
        <Card>
          <CardContent className="text-muted-foreground py-12 text-center">
            <p>还没有分析模板</p>
            <p className="mt-2 text-sm">完成一次 AI 分析后，可以将分析经验保存为模板</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {templates.map((t) => (
            <Card key={t.id} className="hover:border-primary/50 transition-colors">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CardTitle className="text-lg">
                      <Link
                        href={`/projects/${projectId}/templates/${t.id}`}
                        className="hover:underline"
                      >
                        {t.name}
                      </Link>
                    </CardTitle>
                    <Badge variant="secondary">{CATEGORIES[t.category] || t.category}</Badge>
                    <Badge variant="outline">v{t.version}</Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground text-xs">使用 {t.usage_count} 次</span>
                    <Button variant="ghost" size="sm" onClick={() => handleDelete(t.id)}>
                      删除
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground text-sm">{t.description || "无描述"}</p>
                {Array.isArray(t.content?.pitfalls) && t.content.pitfalls.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {t.content.pitfalls.slice(0, 3).map((p, i) => (
                      <Badge key={i} variant="destructive" className="text-xs">
                        {p.length > 30 ? p.slice(0, 30) + "..." : p}
                      </Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
