"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Users, BarChart3, Settings, Layers, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getUsers, createUser, toggleUserStatus, updateUserRole } from "@/actions/admin";

type UserRow = {
  id: string;
  name: string;
  email: string;
  role: string;
  status: string;
  createdAt: Date;
};

export default function AdminPage() {
  const [userList, setUserList] = useState<UserRow[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const loadUsers = async () => {
    try {
      const data = await getUsers();
      setUserList(data as UserRow[]);
    } catch {
      // 非管理员会被拒绝
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleCreate = async () => {
    setError("");
    setCreating(true);
    const result = await createUser(newName, newEmail, newPassword);
    if (result.success) {
      setDialogOpen(false);
      setNewName("");
      setNewEmail("");
      setNewPassword("");
      await loadUsers();
    } else {
      setError(result.error);
    }
    setCreating(false);
  };

  const handleToggleStatus = async (userId: string) => {
    await toggleUserStatus(userId);
    await loadUsers();
  };

  const handleRoleChange = async (userId: string, role: string) => {
    await updateUserRole(userId, role);
    await loadUsers();
  };

  return (
    <div className="bg-background flex h-screen">
      <div className="bg-sidebar border-sidebar-border w-[220px] border-r">
        <div className="p-4">
          <Link
            href="/projects"
            className="text-sidebar-foreground hover:text-primary text-lg font-semibold transition-colors"
          >
            Prism 管理后台
          </Link>
        </div>
        <Separator />
        <nav className="space-y-1 p-2">
          <Button variant="ghost" className="bg-sidebar-accent w-full justify-start">
            <Users className="mr-2 h-4 w-4" />
            用户管理
          </Button>
          <Button variant="ghost" className="w-full justify-start">
            <BarChart3 className="mr-2 h-4 w-4" />
            平台统计
          </Button>
          <Button variant="ghost" className="w-full justify-start">
            <Layers className="mr-2 h-4 w-4" />
            维度类型管理
          </Button>
          <Button variant="ghost" className="w-full justify-start">
            <Settings className="mr-2 h-4 w-4" />
            全局配置
          </Button>
        </nav>
      </div>

      <div className="flex-1 p-6">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-xl font-semibold">用户管理</h1>
          <div className="flex items-center gap-3">
            <Badge variant="secondary">共 {userList.length} 名用户</Badge>
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger>
                <Button variant="default">
                  <Plus className="mr-2 h-4 w-4" />
                  创建用户
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>创建用户</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 pt-2">
                  {error && (
                    <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</div>
                  )}
                  <div className="space-y-2">
                    <Label>用户名</Label>
                    <Input
                      value={newName}
                      onChange={(e) => setNewName(e.target.value)}
                      placeholder="用户名"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>邮箱</Label>
                    <Input
                      value={newEmail}
                      onChange={(e) => setNewEmail(e.target.value)}
                      type="email"
                      placeholder="user@example.com"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>初始密码</Label>
                    <Input
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      type="password"
                      placeholder="至少8个字符"
                    />
                  </div>
                  <Button className="w-full" onClick={handleCreate} disabled={creating}>
                    {creating ? "创建中..." : "创建"}
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </div>

        <div className="border-border overflow-hidden rounded-md border">
          <Table>
            <TableHeader className="bg-muted/50">
              <TableRow>
                <TableHead className="w-12">头像</TableHead>
                <TableHead>用户名</TableHead>
                <TableHead>邮箱</TableHead>
                <TableHead>角色</TableHead>
                <TableHead>注册时间</TableHead>
                <TableHead>状态</TableHead>
                <TableHead className="w-20">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {userList.map((user) => (
                <TableRow key={user.id}>
                  <TableCell>
                    <Avatar className="h-8 w-8">
                      <AvatarFallback className="bg-muted text-sm">
                        {user.name.charAt(0)}
                      </AvatarFallback>
                    </Avatar>
                  </TableCell>
                  <TableCell className="font-medium">{user.name}</TableCell>
                  <TableCell className="text-muted-foreground">{user.email}</TableCell>
                  <TableCell>
                    <Select
                      value={user.role}
                      onValueChange={(v) => v && handleRoleChange(user.id, v)}
                    >
                      <SelectTrigger className="h-8 w-28">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="user">用户</SelectItem>
                        <SelectItem value="platform_admin">管理员</SelectItem>
                      </SelectContent>
                    </Select>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(user.createdAt).toLocaleDateString("zh-CN")}
                  </TableCell>
                  <TableCell>
                    {user.status === "active" ? (
                      <Badge className="bg-green-100 text-green-700 hover:bg-green-100">正常</Badge>
                    ) : (
                      <Badge className="bg-red-100 text-red-700 hover:bg-red-100">已禁用</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm" onClick={() => handleToggleStatus(user.id)}>
                      {user.status === "active" ? "禁用" : "启用"}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {userList.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="text-muted-foreground py-8 text-center">
                    暂无用户数据
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}
