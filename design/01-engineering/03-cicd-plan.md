# 03 - CI/CD 规划

> 本期只画流水线设计，不写实际 yml。

---

## 1. CI 平台选型

| 候选 | 优点 | 缺点 |
|------|------|------|
| GitHub Actions | 免费额度大、与 GitHub 集成好 | 私有 runner 需自管 |
| GitLab CI | 一体化 | 需 GitLab |
| Jenkins | 灵活 | 需自管 |

### CY 决策

```
选择：
理由：
```

---

## 2. 流水线阶段设计

> [CY 画出来]

```mermaid
flowchart LR
    Push[Push/PR] --> Lint[Lint + Format]
    Lint --> TypeCheck[Type Check]
    TypeCheck --> UnitTest[Unit Test]
    UnitTest --> IntegrationTest[Integration Test]
    IntegrationTest --> Build[Build]
    Build --> Deploy[Deploy]
```

---

## 3. 触发时机

| 事件 | 触发哪些阶段 |
|------|------------|
| Push 到 feature 分支 | |
| PR 创建 | |
| Merge 到 main | |
| 定时（如夜间） | |

---

## 4. 部署策略

> [CY 决策]
> 提示：手动 vs 自动；蓝绿/金丝雀/直接覆盖；回滚机制？

```
[在此填写]
```

---

## 完成度判定

- [ ] 平台选型有理由
- [ ] 流水线阶段图完整
- [ ] 触发时机表填写
- [ ] 部署策略明确（含回滚）
