"use client";

import { useActionState } from "react";
import { login } from "@/actions/auth";
import Link from "next/link";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";

export default function LoginPage() {
  const [state, formAction, isPending] = useActionState(login, {});

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
            {state?.error && (
              <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">{state.error}</div>
            )}
            <form action={formAction} className="space-y-4">
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
