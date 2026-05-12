"use client";

import { useState } from "react";
import { createTemplate, type TemplateContent } from "@/actions/templates";
import { Button } from "@/components/ui/button";

interface TemplateSaveDialogProps {
  projectId: string;
  analysisResult: string;
  onSaved?: () => void;
  onClose: () => void;
}

export function TemplateSaveDialog({
  projectId,
  analysisResult,
  onSaved,
  onClose,
}: TemplateSaveDialogProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("general");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSave = async () => {
    if (!name.trim()) {
      setError("请输入模板名称");
      return;
    }
    setSaving(true);
    setError("");

    const content: TemplateContent = {
      trigger_conditions: [],
      analysis_steps: [],
      pitfalls: [],
      verification: [],
      prompt_template: analysisResult.slice(0, 5000),
    };

    const result = await createTemplate({
      projectId,
      name: name.trim(),
      description: description.trim() || undefined,
      category,
      content,
    });

    if (result.success) {
      onSaved?.();
      onClose();
    } else {
      setError("保存失败，请重试");
    }
    setSaving(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-background w-full max-w-md rounded-lg p-6 shadow-lg">
        <h2 className="mb-4 text-lg font-semibold">保存为分析模板</h2>
        <p className="text-muted-foreground mb-4 text-sm">
          将本次分析经验保存为模板，下次分析类似需求时自动匹配加载。
        </p>

        <div className="space-y-3">
          <div>
            <label className="text-sm font-medium">模板名称 *</label>
            <input
              className="mt-1 w-full rounded border px-3 py-2"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="例如：API 接口需求分析"
            />
          </div>
          <div>
            <label className="text-sm font-medium">描述</label>
            <input
              className="mt-1 w-full rounded border px-3 py-2"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="一句话描述适用场景"
            />
          </div>
          <div>
            <label className="text-sm font-medium">分类</label>
            <select
              className="mt-1 w-full rounded border px-3 py-2"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="general">通用</option>
              <option value="functional">功能分析</option>
              <option value="performance">性能分析</option>
              <option value="security">安全分析</option>
            </select>
          </div>
        </div>

        {error && <p className="text-destructive mt-3 text-sm">{error}</p>}

        <div className="mt-6 flex justify-end gap-2">
          <Button variant="outline" onClick={onClose} disabled={saving}>
            取消
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "保存中..." : "保存模板"}
          </Button>
        </div>
      </div>
    </div>
  );
}
