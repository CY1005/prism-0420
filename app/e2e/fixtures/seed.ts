import type { APIRequestContext } from "@playwright/test";

// Sprint 2 Task 2.1 — DB seed fixture（API 路径，cleanup-plan §370 选项 A）
// 与生产路径一致 / 一次创建一个完整种子项目供 e2e #2-#10 复用

const E2E_EMAIL = "e2e@example.com";
const E2E_PASSWORD = "Password123!";

export interface SeededProject {
  accessToken: string;
  user: { id: string; email: string };
  project: { id: string; name: string };
  node: { id: string; name: string };
  issue: { id: string; title: string };
}

const API_BASE = process.env.E2E_API_URL ?? "http://localhost:8000";

export async function loginE2EAdmin(api: APIRequestContext): Promise<{
  accessToken: string;
  user: { id: string; email: string };
}> {
  const res = await api.post(`${API_BASE}/auth/login`, {
    data: { email: E2E_EMAIL, password: E2E_PASSWORD },
  });
  if (!res.ok()) {
    throw new Error(
      `e2e admin login failed: ${res.status()} ${await res.text()} (run \`uv run python scripts/seed_e2e_admin.py\` first)`,
    );
  }
  const body = await res.json();
  return { accessToken: body.access_token, user: body.user };
}

export async function seedFullProject(
  api: APIRequestContext,
  opts: { suffix?: string } = {},
): Promise<SeededProject> {
  const { accessToken, user } = await loginE2EAdmin(api);
  const auth = { Authorization: `Bearer ${accessToken}` };
  const suffix = opts.suffix ?? `${Date.now()}`;

  const projectRes = await api.post(`${API_BASE}/api/projects`, {
    headers: auth,
    data: {
      name: `E2E Project ${suffix}`,
      description: "Sprint 2 Task 2.1 seed fixture",
      template_type: "custom",
    },
  });
  if (!projectRes.ok()) {
    throw new Error(`project create failed: ${projectRes.status()} ${await projectRes.text()}`);
  }
  const project = await projectRes.json();

  const nodeRes = await api.post(`${API_BASE}/api/projects/${project.id}/nodes`, {
    headers: auth,
    data: { name: "Root Module", type: "folder", description: "seed root node" },
  });
  if (!nodeRes.ok()) {
    throw new Error(`node create failed: ${nodeRes.status()} ${await nodeRes.text()}`);
  }
  const node = await nodeRes.json();

  const issueRes = await api.post(`${API_BASE}/api/projects/${project.id}/issues`, {
    headers: auth,
    data: {
      node_id: node.id,
      category: "bug",
      title: "Seed issue",
      description: "Auto-created by e2e seed fixture",
    },
  });
  if (!issueRes.ok()) {
    throw new Error(`issue create failed: ${issueRes.status()} ${await issueRes.text()}`);
  }
  const issue = await issueRes.json();

  return {
    accessToken,
    user: { id: user.id, email: user.email },
    project: { id: project.id, name: project.name },
    node: { id: node.id, name: node.name },
    issue: { id: issue.id, title: issue.title },
  };
}
