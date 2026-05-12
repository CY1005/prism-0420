# 给 Claude 的交接文档

更新时间：2026-04-21

## 1. 这是什么仓库

这是 `prism-0420` 的设计前置仓，不是实现仓。

- 当前仓库只有设计文档和说明文件，没有 `api/`、`web/`、`tests/`、`.github/`、`scripts/` 等实现目录。
- 目标不是立刻写业务代码，而是把 Prism 的 20 个模块先用设计文档和 reviewer 流程收口，再进入 Phase 2 实现。
- 用户明确提醒：这是一个“还在开发中的项目”。不要把“尚未实现”直接当成缺陷，重点看设计流程是否足以支撑后续落地。

## 2. 你接手时已经确认的事实

### 仓库现状

- 根目录当前只有：
  - `README.md`
  - `CLAUDE.md`
  - `design/`
- 最新提交停在：
  - `ff7568c feat(modules): 第三批 A1 4 模块 M08/M09/M10/M15 转 status=accepted (CY 2026-04-21 ack)`

### 模块设计推进状态

`design/02-modules/README.md` 显示：

- Pilot 1：`M04` 已 accepted
- Pilot 2：`M17` 已 accepted
- 第一批、第二批、第三批 A1 多个模块已 accepted
- 待开：
  - `M01`
  - `M13 / M16 / M18`
  - `M20`

### 工程文档成熟度

`design/01-engineering/` 里 5 份文档成熟度不一致：

- `01-engineering-spec.md`
  - 内容很长，已经写了大量规约
  - 但文件尾部仍显示未完全收口，包含：
    - 强制清单总览未填完
    - AI 完整性质疑未勾
    - 对抗式 reviewer 三轮未勾
- `02-quality-spec.md`
  - 大量空表和 `[在此填写]`
- `03-cicd-plan.md`
  - 平台、触发时机、部署策略都还没定
- `04-observability-plan.md`
  - 基本还是占位稿
- `05-security-baseline.md`
  - 基本还是占位稿

## 3. 文档可信度排序

不要默认所有入口文档都是同步的。当前建议按下面顺序取信：

1. `design/02-modules/README.md`
   - 目前最接近真实推进状态
   - 已经反映 pilot、批次、accepted 状态和基线补丁 TODO
2. 各模块 `00-design.md` / `tests.md`
   - 用于确认单模块决策细节
3. `design/adr/*.md`
   - 用于确认被接受的横切决策
4. `design/01-engineering/01-engineering-spec.md`
   - 可作为“目标规约”，但不要误以为已经完全落地
5. `design/README.md`
   - 当前进度板有漂移，不能单独当真
6. `README.md`
   - 已明显滞后，只适合看项目初始定位，不适合看当前进度

## 4. 当前最重要的矛盾

### 矛盾 1：入口文档和实际推进状态不一致

`README.md` 还写着：

- 只产出设计文档，不写业务代码
- 聚焦 1 个模块走完整设计流程

但 `design/02-modules/README.md` 已经显示多批模块 accepted。

这意味着：

- 新接手的人如果先读 `README.md`，会误判项目还停在单模块阶段
- “项目目的”和“当前真实进度”没有单一真相源

### 矛盾 2：B 档总入口状态和单文件状态不一致

`design/README.md` 仍写：

- 档位 B：工程规约（决策记录，0/5）

但 `01-engineering-spec.md` 文件底部又写：

- `B 档 5 条全部填写`

与此同时，`02-quality-spec.md`、`03-cicd-plan.md`、`04-observability-plan.md`、`05-security-baseline.md` 仍大量留空。

结论：

- “B 档已完成”这个说法现在不能直接相信
- 需要先定义清楚：B 档是“有骨架”算完成，还是“可支撑 Phase 2”才算完成

### 矛盾 3：`accepted` 状态过强，但文档自己承认后面还要回扫

`design/02-modules/README.md` 已明确写了：

- 已 accepted 模块仍要做 `baseline-patch-batch3`
- 且预判多个模块“高概率需改”

这意味着：

- `accepted` 目前更像“本轮 reviewer 流程结束”
- 还不能自然等同于“后续实现可直接照着干”

如果不澄清这个语义，后面很容易出现：

- Claude 以为 accepted = 稳定设计
- 结果开始实现后，又被新模板或新 ADR 反向改设计

### 矛盾 4：工程流程写得很完整，但真实执行器还不存在

`01-engineering-spec.md` 里已经写了完整实现期流程：

- feature branch
- Draft PR
- CI 绿灯
- checklist 7 项
- Ready for review
- squash merge

但仓库当前没有：

- CI workflow
- 代码目录
- 测试目录
- 部署配置

而 `03-cicd-plan.md` 还没选平台、没定触发、没定回滚。

结论：

- 当前“开发流程”更多是目标流程，不是已落地流程
- 后续讨论时要区分“制度设计”和“现已生效”

## 5. 下一步优先级建议

如果用户继续让你推进，不建议直接扩新模块。建议优先做下面 4 件事：

1. 先统一“当前状态入口”
   - 最小动作：补一份总览文档或修 `README.md`
   - 目标：让任何新会话一进仓就知道真实阶段，不会被旧描述误导

2. 先执行 `baseline-patch-batch3`
   - 理由：模块 README 已经明确这是 accepted 设计的已知回扫项
   - 如果不先补，后面继续开 `M01` 或 AI 模块，模板债会继续扩散

3. 补齐 B 档 4 份明显未收口的工程文档
   - `02-quality-spec.md`
   - `03-cicd-plan.md`
   - `04-observability-plan.md`
   - `05-security-baseline.md`
   - 至少要达到“进入实现前不会让人误解为已经定案”的状态

4. 定义 Phase 2 开始门槛
   - 明确什么叫“设计可以进入实现”
   - 否则 `accepted`、`draft`、`B 档完成` 这些状态都会继续漂移

## 6. 你应该先问 CY 的问题

不要替 CY 猜。优先把下面几个问题问清楚：

1. 现在仓库的“单一真相源”是哪份文档？
   - `README.md`
   - `design/README.md`
   - `design/02-modules/README.md`
   - 还是需要新增一份统一状态页？

2. `accepted` 的语义到底是什么？
   - 本轮审稿收口
   - 可进入实现
   - 还是“允许后续基线回扫但不算推翻”？

3. `baseline-patch-batch3` 要不要作为 `M01` 启动前的硬前置？

4. B 档完成标准是什么？
   - 有骨架即可
   - 每份文档必须消灭 `[在此填写]`
   - 还是必须足以支撑真实工程落地？

5. Phase 2 的开始门槛是什么？
   - 某几个模块 accepted 即可
   - B 档补齐即可
   - 还是必须先做对照报告 / 基线补丁 / 进度板统一？

## 7. 你接手时不要踩的坑

- 不要把 `README.md` 当成最新进度。
- 不要把 `design/README.md` 的 `0/5` 直接当真。
- 不要把 `accepted` 直接理解成“后续不会再改”。
- 不要假装仓库已经有 CI / 测试 / 分支保护落地；目前大多还是目标流程。
- 不要去“补代码骨架”来证明设计可实现；用户当前要的是设计和流程层面的严谨推进。
- 不要覆盖用户现有未提交修改。

## 8. 工作树注意事项

交接时 `git status` 显示：

- `README.md` 已修改
- `CLAUDE.md` 已修改

这些改动不是这份交接文档产生的。动这两个文件前先重新读取，避免误覆盖用户手头修改。

## 9. 本地环境备注

本机已安装 `superpowers` 到：

- `C:\Users\chenyue\.codex\superpowers`
- `C:\Users\chenyue\.agents\skills\superpowers`

如果你当前会话支持从 `~/.agents/skills` 自动发现技能，可以使用它；但仍要以本仓的 `AGENTS.md` 和用户当前指令为准。

## 10. 推荐的接手顺序

如果你要继续推进，建议按这个顺序读：

1. `HANDOFF-TO-CLAUDE.md`
2. `CLAUDE.md`
3. `design/02-modules/README.md`
4. `design/adr/ADR-001-shadow-prism.md`
5. `design/adr/ADR-002-queue-consumer-tenant-permission.md`
6. `design/adr/ADR-003-cross-module-read-strategy.md`
7. `design/01-engineering/01-engineering-spec.md`
8. 再决定是：
   - 做 `baseline-patch-batch3`
   - 还是先统一入口文档
   - 还是先补 B 档空白文档

## 11. 一句话总结

这个项目现在最大的风险不是“设计太少”，而是“设计推进很快，但状态定义、入口同步和进入实现的门槛还没有被明确钉死”。
