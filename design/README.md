# Design Documents

设计文档总入口，按"档位"组织。

## 阅读顺序

1. **00-architecture/**：先看这里——极简架构骨架，理解系统全貌
2. **01-engineering/**：工程规约决策记录
3. **02-modules/**：进入具体模块的详细设计
4. **99-comparison/**：设计完成后与 Prism 现状对照
5. **adr/**：架构决策记录（按编号查阅）

## 文档约定

- 所有图表用 **Mermaid**（不要用截图）
- 状态机用 `stateDiagram-v2`
- ER 图用 `erDiagram`
- 流程图用 `flowchart`
- 时序图用 `sequenceDiagram`

## 设计完成度判定

每个文档底部都有"完成度判定"——满足全部条件才能 close。

## 当前进度

### 档位 A：架构骨架（必须完整做）

- [x] 01-PRD.md
- [x] 02-context-diagram.md
- [x] 03-tech-stack.md（含双 ORM 风险评估）
- [ ] 04-layer-architecture.md（含权限中间件、事务边界）
- [ ] 05-module-catalog.md（建 M 编号体系 + 多人影响标注）
- [ ] 06-design-principles.md（≤5 条硬约束）
- [ ] adr/ADR-001-shadow-prism.md（基础 4 节）
- [ ] adr/ADR-001 多人架构核心预设（M1/B1/B2）

### 档位 B：工程规约（决策记录，0/5）

- [ ] 01-engineering-spec.md
- [ ] 02-quality-spec.md
- [ ] 03-cicd-plan.md
- [ ] 04-observability-plan.md
- [ ] 05-security-baseline.md

### 档位 C：模块详细设计（暂不展开）

- [ ] M{?} 模块详细设计（编号待档位 A 完成后定）

### 对照报告

- [ ] {模块} vs Prism F{?} 对照
