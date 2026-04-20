# 03 - 技术栈表

> 这次设计训练**强烈建议照搬 Prism 现有技术栈**——不要分心做技术选型。

---

## Q1：照搬 Prism 还是简化？

> [CY 选择 + 说明]
> - A. 完全照搬
> - B. 简化（请说明哪部分简化、为什么）

```
选择：
理由：
```

---

## Q2：技术栈表

| 层 | 技术选型 | 理由（一句话） |
|----|---------|--------------|
| 前端框架 | | |
| 状态管理 | | |
| UI 库 | | |
| CSS | | |
| 后端框架 | | |
| ORM | | |
| 数据库 | | |
| 认证方案 | | |
| AI 集成 | | |
| 部署 | | |

---

## Prism 现状参考（来自 prism/CLAUDE.md）

- 前端：Next.js 16 + React 19 + TypeScript + shadcn/ui + Tailwind 4
- 状态：Server Actions + React Context
- 后端：FastAPI + SQLAlchemy 2.0 + Pydantic 2
- 数据库：PostgreSQL 16 + pgvector
- ORM：Drizzle（前端单一真相源）+ SQLAlchemy（后端只读镜像）
- 认证：Auth.js v5 + JWT + RBAC
- AI 集成：AI Provider 抽象层（Claude / DeepSeek / Kimi / OpenAI / Mock）
- 部署：Docker Compose

---

## 完成度判定

- [ ] 每行的"理由"都不为空（不能光选不说为什么）
- [ ] AI 完整性质疑通过
