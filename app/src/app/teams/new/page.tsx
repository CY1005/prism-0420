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
import { createTeam } from "@/actions/teams";
import { handleActionResult } from "@/lib/client-error";

export default function NewTeamPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();

  const handleCreate = () => {
    if (!name.trim()) {
      setError("请输入团队名称");
      return;
    }
    setError("");

    const formData = new FormData();
    formData.append("name", name.trim());
    if (description.trim()) formData.append("description", description.trim());

    startTransition(async () => {
      const result = await createTeam(formData);
      const handled = handleActionResult(result, router);
      if (handled.ok) {
        router.replace(`/teams/${handled.data.id}`);
      } else if (!handled.autoHandled) {
        setError(handled.message);
      }
    });
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-16 max-w-4xl items-center gap-4 px-6">
          <Link href="/teams">
            <Button variant="ghost" size="sm" className="gap-2">
              <ArrowLeft className="h-4 w-4" />
              返回团队列表
            </Button>
          </Link>
          <h1 className="text-lg font-semibold text-slate-900">新建团队</h1>
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-6 py-10">
        <Card className="p-6">
          <div className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="name">
                团队名称 <span className="text-red-500">*</span>
              </Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="例如：产品研发团队"
                maxLength={100}
                disabled={isPending}
                autoFocus
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">描述</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="简单介绍这个团队的目标或职责（可选）"
                maxLength={500}
                rows={4}
                disabled={isPending}
              />
            </div>

            {error && (
              <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-600">
                {error}
              </div>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <Link href="/teams">
                <Button variant="outline" disabled={isPending}>
                  取消
                </Button>
              </Link>
              <Button onClick={handleCreate} disabled={isPending || !name.trim()}>
                {isPending ? "创建中…" : "创建团队"}
              </Button>
            </div>
          </div>
        </Card>
      </main>
    </div>
  );
}
