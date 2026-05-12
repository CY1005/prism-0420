"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  getTemplate,
  getTemplateHistory,
  updateTemplate,
  revertTemplate,
  type Template,
  type TemplateVersion,
} from "@/actions/templates";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function TemplateDetailPage() {
  const params = useParams();
  const router = useRouter();
  const templateId = params.templateId as string;
  const projectId = params.projectId as string;

  const [template, setTemplate] = useState<Template | null>(null);
  const [versions, setVersions] = useState<TemplateVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");

  const load = async () => {
    setLoading(true);
    const [tplRes, histRes] = await Promise.all([
      getTemplate(templateId),
      getTemplateHistory(templateId),
    ]);
    if (tplRes.success) {
      setTemplate(tplRes.data);
      setEditName(tplRes.data.name);
      setEditDesc(tplRes.data.description || "");
    }
    if (histRes.success) {
      setVersions(histRes.data);
    }
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, [templateId]);

  const handleSave = async () => {
    const result = await updateTemplate(templateId, {
      name: editName,
      description: editDesc,
      changeSummary: "手动编辑名称/描述",
    });
    if (result.success) {
      setEditing(false);
      load();
    }
  };

  const handleRevert = async (versionNumber: number) => {
    if (!confirm(`确定回滚到 v${versionNumber}？`)) return;
    const result = await revertTemplate(templateId, String(versionNumber));
    if (result.success) {
      load();
    }
  };

  if (loading) return <p className="text-muted-foreground p-6">加载中...</p>;
  if (!template) return <p className="text-muted-foreground p-6">模板不存在</p>;

  const content = template.content;

  return (
    <div className="mx-auto max-w-4xl p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push(`/projects/${projectId}/templates`)}
          >
            &larr; 返回模板列表
          </Button>
          {editing ? (
            <div className="mt-2 space-y-2">
              <input
                className="w-full rounded border px-3 py-1 text-lg font-bold"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
              />
              <input
                className="w-full rounded border px-3 py-1 text-sm"
                value={editDesc}
                onChange={(e) => setEditDesc(e.target.value)}
                placeholder="描述"
              />
              <div className="flex gap-2">
                <Button size="sm" onClick={handleSave}>
                  保存
                </Button>
                <Button size="sm" variant="outline" onClick={() => setEditing(false)}>
                  取消
                </Button>
              </div>
            </div>
          ) : (
            <>
              <h1 className="mt-2 text-2xl font-bold">{template.name}</h1>
              <p className="text-muted-foreground text-sm">{template.description}</p>
            </>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary">v{template.version}</Badge>
          <Badge variant="outline">使用 {template.usage_count} 次</Badge>
          {!editing && (
            <Button size="sm" variant="outline" onClick={() => setEditing(true)}>
              编辑
            </Button>
          )}
        </div>
      </div>

      {/* Content sections */}
      <div className="grid gap-4">
        {Array.isArray(content?.trigger_conditions) && content.trigger_conditions.length > 0 && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">适用条件</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="list-inside list-disc space-y-1 text-sm">
                {content.trigger_conditions.map((c: string, i: number) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        {Array.isArray(content?.analysis_steps) && content.analysis_steps.length > 0 && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">分析步骤</CardTitle>
            </CardHeader>
            <CardContent>
              <ol className="list-inside list-decimal space-y-1 text-sm">
                {content.analysis_steps.map((s: string, i: number) => (
                  <li key={i}>{s}</li>
                ))}
              </ol>
            </CardContent>
          </Card>
        )}

        {Array.isArray(content?.pitfalls) && content.pitfalls.length > 0 && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">常见陷阱</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-1 text-sm">
                {content.pitfalls.map((p: string, i: number) => (
                  <li key={i} className="text-destructive">
                    &#9888; {p}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        {Array.isArray(content?.verification) && content.verification.length > 0 && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">验证方法</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="list-inside list-disc space-y-1 text-sm">
                {content.verification.map((v: string, i: number) => (
                  <li key={i}>{v}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Version history */}
      <div className="mt-8">
        <h2 className="mb-4 text-lg font-semibold">版本历史</h2>
        {versions.length === 0 ? (
          <p className="text-muted-foreground text-sm">暂无版本记录</p>
        ) : (
          <div className="space-y-2">
            {versions.map((v) => (
              <div
                key={v.id}
                className="flex items-center justify-between rounded-lg border px-4 py-3"
              >
                <div>
                  <span className="font-mono text-sm font-medium">v{v.version_number}</span>
                  <span className="text-muted-foreground ml-3 text-sm">
                    {v.change_summary || "无摘要"}
                  </span>
                  <span className="text-muted-foreground ml-3 text-xs">
                    {new Date(v.created_at).toLocaleString("zh-CN")}
                  </span>
                </div>
                {v.version_number !== template.version && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleRevert(v.version_number)}
                  >
                    回滚
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
