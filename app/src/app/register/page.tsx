import Link from "next/link";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

/**
 * Phase 2.2 子片 2：自助注册暂未开放。
 * M01 design §4 字面：开放自助注册（POST /auth/register）属本模块未来扩展（Q1=B/C/D）。
 * 当前账号开通走管理员邀请通道（POST /auth/users by platform_admin）。
 */
export default function RegisterPage() {
  return (
    <div className="bg-background flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <Card className="border-border/60 shadow-sm">
          <CardHeader className="space-y-1 pb-4">
            <h1 className="text-foreground text-2xl font-bold">Prism</h1>
            <p className="text-muted-foreground text-sm">创建账号</p>
          </CardHeader>
          <CardContent className="space-y-4">
            <Separator />
            <div className="rounded-md bg-amber-50 p-4 text-sm text-amber-900">
              <p className="font-medium">暂未开放自助注册</p>
              <p className="mt-1 text-amber-800">请联系管理员开通账号。后续版本将开放公开注册。</p>
            </div>
            <p className="text-muted-foreground text-center text-sm">
              已有账号？{" "}
              <Link href="/login" className="text-primary hover:underline">
                登录
              </Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
