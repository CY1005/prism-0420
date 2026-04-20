# 02 - 质量规约决策

---

## 1. Lint 工具

| 语言 | 候选 | CY 决策 |
|------|------|--------|
| TypeScript | ESLint + typescript-eslint | |
| Python | ruff / pylint / flake8 | |

---

## 2. Formatter

| 语言 | 候选 | CY 决策 |
|------|------|--------|
| TypeScript/JS | Prettier / Biome | |
| Python | black / ruff format | |

---

## 3. 测试框架

| 层 | 候选 | CY 决策 |
|----|------|--------|
| 前端单测 | Vitest / Jest | |
| 前端 E2E | Playwright / Cypress | |
| 后端单测 | pytest / unittest | |
| API 集成测试 | pytest + httpx | |

---

## 4. 测试金字塔比例

> [CY 写]

例：单测 70% / 集成 20% / E2E 10%

```
[在此填写]
```

---

## 5. 覆盖率门槛

> [CY 写 + 理由（为什么是这个数）]

```
[在此填写]
```

---

## 6. Pre-commit hook

> [CY 决策：是否启用 + 跑哪些检查]

```
[在此填写]
```

---

## 完成度判定

- [ ] 6 项全部决策
- [ ] 每项都有理由（特别是覆盖率门槛——为什么是这个数）
