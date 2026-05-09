"use client";

import { useState, useTransition } from "react";
import { register } from "@/actions/auth";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

export function RegisterForm() {
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function handleSubmit(formData: FormData) {
    setError(null);
    startTransition(async () => {
      try {
        const result = await register(formData);
        if (result.success) {
          router.push("/projects");
        } else {
          setError(result.error);
        }
      } catch {
        setError("注册失败，请稍后重试");
      }
    });
  }

  return (
    <form action={handleSubmit} className="space-y-4">
      {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</div>}

      <div className="space-y-2">
        <Label htmlFor="name" className="text-sm font-medium">
          用户名
        </Label>
        <Input
          id="name"
          name="name"
          type="text"
          required
          placeholder="你的名字"
          className="w-full"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="email" className="text-sm font-medium">
          邮箱
        </Label>
        <Input
          id="email"
          name="email"
          type="email"
          required
          placeholder="your@email.com"
          className="w-full"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="password" className="text-sm font-medium">
          密码
        </Label>
        <Input
          id="password"
          name="password"
          type="password"
          required
          minLength={8}
          placeholder="至少8个字符"
          className="w-full"
        />
      </div>

      <Button type="submit" className="w-full" variant="default" disabled={isPending}>
        {isPending ? "注册中..." : "注册"}
      </Button>

      <p className="text-muted-foreground text-center text-sm">
        已有账号？{" "}
        <Link href="/login" className="text-primary hover:underline">
          登录
        </Link>
      </p>
    </form>
  );
}
