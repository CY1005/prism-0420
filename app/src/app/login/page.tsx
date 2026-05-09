"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { ApiError } from "@/services/http-client";
import { loginSchema } from "@/lib/validators/auth";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function handleSubmit(formData: FormData) {
    setError(null);
    const parsed = loginSchema.safeParse({
      email: formData.get("email"),
      password: formData.get("password"),
    });
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? "输入格式错误");
      return;
    }
    startTransition(async () => {
      try {
        await login(parsed.data.email, parsed.data.password);
        router.push("/projects");
      } catch (e) {
        if (e instanceof ApiError) {
          if (e.status === 401) setError("邮箱或密码错误");
          else if (e.status === 403) setError(e.message || "账号不可用");
          else if (e.status === 423) setError("账号已被锁定，请稍后再试");
          else if (e.status >= 500) setError("服务暂不可用，请稍后再试");
          else setError(e.message || "登录失败");
        } else {
          setError("网络错误，请检查后端服务");
        }
      }
    });
  }

  return (
    <div className="bg-background flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <Card className="border-border/60 shadow-sm">
          <CardHeader className="space-y-1 pb-4">
            <h1 className="text-foreground text-2xl font-bold">Prism</h1>
            <p className="text-muted-foreground text-sm">行业知识管理与分析平台</p>
          </CardHeader>
          <CardContent className="space-y-4">
            <Separator />
            {error && (
              <div className="rounded-md bg-red-50 p-3 text-sm text-red-600" role="alert">
                {error}
              </div>
            )}
            <form action={handleSubmit} className="space-y-4">
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
                  placeholder="••••••••"
                  className="w-full"
                />
              </div>
              <Button type="submit" className="w-full" variant="default" disabled={isPending}>
                {isPending ? "登录中..." : "登录"}
              </Button>
            </form>
          </CardContent>
        </Card>
        <p className="text-muted-foreground mt-4 text-center text-sm">
          没有账号？{" "}
          <Link href="/register" className="text-primary hover:underline">
            注册
          </Link>
        </p>
      </div>
    </div>
  );
}
