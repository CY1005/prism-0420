"""Phase 3 数据采集脚本 v0.2

prism-0420 vs prism v1 数据对照 baseline 采集。Shadow 项目核心 KPI。

v0.2 范围（3 维度）:
- 维度 1: 开发速度（commits / 时间跨度 / 按 commit msg pattern 切分）
- 维度 2: Bug 数（fix commit / 真漏 / BUG-xxx 计数）
- 维度 3: 等价完成度对齐（按里程碑切分累计 stats / 解决 v0.1 时间窗口不可比问题）

未做（v0.3+ 迭代）:
- 重工次数（同文件 ≥2 次 substantial 改动）
- 可追溯性（design spec → impl commit 链）
- 关闸盲区（Phase 2.x audit 漏审项）

输出:
- stdout: 数据对照表（markdown）
- design/99-comparison/phase3-data-baseline.md（自动生成段 between 标记）
"""

from __future__ import annotations

import re
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

PRISM_0420 = Path("/root/workspace/projects/prism-0420")
PRISM_V1 = Path("/root/prism")
OUTPUT = PRISM_0420 / "design/99-comparison/phase3-data-baseline.md"

# 等价完成度里程碑配置（v0.2）。
# 标签按"完成度水位"对齐两库，commit hash 不可变（重写历史会断）。
# 顺序代表水位递进（init → design 完成 → 业务实装完成 → 测试通过/可上线）。
MILESTONES = {
    "prism-0420": [
        ("init", "4ec1b1f"),  # 2026-04-20
        ("design 完成", "8d14e46"),  # 2026-04-27 Phase 1 全 20 模块 accepted
        ("业务实装完成", "b36d4d0"),  # 2026-05-09 Phase 2.1 100% / M01-M20
        ("前端继承完成", "597b885"),  # 2026-05-09 Phase 2.2 100%
        # 注: "测试通过 / 可上线" 等价点未到（Phase 2.3 集成验证未做）
    ],
    "prism v1": [
        ("init", "bd5c2d6"),  # 2026-04-03
        ("design 完成 (PRD/ADR)", "426455b"),  # 2026-04-12 PRD F6-F20 + 3 ADR
        ("业务实装完成", "affa2da"),  # 2026-04-14 F1-F20 + 134 测试 100%
        ("测试通过 / 可上线", "f1bf4df"),  # 2026-04-15 155 测试 100% + RCA
    ],
}

# commit msg 分类规则。优先级从上到下，首匹配生效。
# 两库共用，新增 pattern 仅在本字典加行即可（开放扩展，无散布逻辑）。
PATTERNS = [
    ("Sprint", re.compile(r"^Sprint\s+\d", re.I)),  # prism-0420 Sprint X.Y
    ("Phase", re.compile(r"Phase\s+\d", re.I)),  # prism-0420 Phase 2.X
    ("M-module", re.compile(r"\bM\d{1,2}\b")),  # prism-0420 M01-M20
    ("fix-bug-id", re.compile(r"^fix\(BUG-\d", re.I)),  # prism v1 fix(BUG-xxx)
    ("fix-generic", re.compile(r"^fix[:\(]", re.I)),  # generic fix
    ("feat", re.compile(r"^feat[:\(]", re.I)),
    ("docs", re.compile(r"^docs[:\(]", re.I)),
    ("refactor", re.compile(r"^refactor[:\(]", re.I)),
    ("test", re.compile(r"^test[:\(]", re.I)),
    ("chore", re.compile(r"^chore[:\(]", re.I)),
    ("cleanup", re.compile(r"cleanup|CLEANUP", re.I)),
    ("other", re.compile(r".")),  # catch-all
]


@dataclass
class RepoStats:
    name: str
    path: Path
    first_commit_date: str = ""
    last_commit_date: str = ""
    total_commits: int = 0
    days_span: int = 0
    pattern_counts: Counter = field(default_factory=Counter)
    bug_fix_commits: int = 0


def git_log_subjects(repo: Path) -> list[tuple[str, str, str]]:
    """Return [(date_iso, hash, subject)] for all commits, oldest→newest."""
    out = subprocess.run(
        ["git", "log", "--reverse", "--format=%ad\t%h\t%s", "--date=short"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    rows = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 2)
        if len(parts) == 3:
            rows.append(tuple(parts))  # type: ignore
    return rows


def classify(subject: str) -> str:
    for name, regex in PATTERNS:
        if regex.search(subject):
            return name
    return "other"


def is_bug_fix(subject: str) -> bool:
    """Bug fix commit 判定（两库共用启发式）。"""
    s = subject.lower()
    return any(
        kw in s
        for kw in (
            "fix(bug",
            "fix:",
            "fix —",
            "fix --",
            "bug-",
            "fix#",
            "修复",
            "bugfix",
        )
    )


def collect_from_rows(name: str, path: Path, rows: list[tuple[str, str, str]]) -> RepoStats:
    """计算 stats from given rows（oldest→newest）。供 collect 和 milestone 共用。"""
    stats = RepoStats(name=name, path=path, total_commits=len(rows))
    if rows:
        stats.first_commit_date = rows[0][0]
        stats.last_commit_date = rows[-1][0]
        d0 = datetime.fromisoformat(stats.first_commit_date)
        d1 = datetime.fromisoformat(stats.last_commit_date)
        stats.days_span = (d1 - d0).days + 1
    for _, _, subject in rows:
        stats.pattern_counts[classify(subject)] += 1
        if is_bug_fix(subject):
            stats.bug_fix_commits += 1
    return stats


def collect(name: str, path: Path) -> RepoStats:
    return collect_from_rows(name, path, git_log_subjects(path))


def collect_at_milestones(
    name: str, path: Path, milestones: list[tuple[str, str]]
) -> list[tuple[str, RepoStats]]:
    """对每个里程碑算从 init 到该 hash 的累计 stats。hash 不存在则跳过。"""
    rows = git_log_subjects(path)
    results: list[tuple[str, RepoStats]] = []
    for label, hash_prefix in milestones:
        sub: list[tuple[str, str, str]] = []
        found = False
        for r in rows:
            sub.append(r)
            if r[1].startswith(hash_prefix) or hash_prefix.startswith(r[1]):
                found = True
                break
        if found:
            results.append((label, collect_from_rows(name, path, sub)))
    return results


def count_punt_pool_real_holes(repo: Path) -> int:
    """prism-0420: cross-sprint-punt-pool.md "真漏洞" 段计数。"""
    pool = repo / "_handoff/cross-sprint-punt-pool.md"
    if not pool.exists():
        return 0
    text = pool.read_text(encoding="utf-8")
    # 真漏洞表条目：行起以 `| **<num>**` 或 `| <num>` 跟 punt 描述。粗略 grep。
    rows = re.findall(r"^\|\s*\*?\*?\d+\*?\*?\s*\|", text, re.M)
    return len(rows)


def count_v1_bug_ids(repo: Path) -> int:
    """prism v1: bug-log.md BUG-xxx 计数。"""
    log = repo / "docs/testing/bugs/bug-log.md"
    if not log.exists():
        return 0
    ids = set(re.findall(r"BUG-\d{3}", log.read_text(encoding="utf-8")))
    return len(ids)


def render_table(s0: RepoStats, s1: RepoStats, p0_extra: dict, v1_extra: dict) -> str:
    """Render 对照表 markdown。"""
    lines = []
    lines.append("## 维度 1: 开发速度（v0.1 基线）\n")
    lines.append("| 指标 | prism-0420 | prism v1 | ratio (0420/v1) |")
    lines.append("|---|---|---|---|")
    lines.append(
        f"| 总 commit 数 | {s0.total_commits} | {s1.total_commits} | {s0.total_commits / max(s1.total_commits, 1):.2f}x |"
    )
    lines.append(
        f"| 时间跨度（天）| {s0.days_span} | {s1.days_span} | {s0.days_span / max(s1.days_span, 1):.2f}x |"
    )
    lines.append(f"| 起始 commit | {s0.first_commit_date} | {s1.first_commit_date} | — |")
    lines.append(f"| 最近 commit | {s0.last_commit_date} | {s1.last_commit_date} | — |")
    lines.append(
        f"| commit/day | {s0.total_commits / max(s0.days_span, 1):.2f} | {s1.total_commits / max(s1.days_span, 1):.2f} | {(s0.total_commits / max(s0.days_span, 1)) / max(s1.total_commits / max(s1.days_span, 1), 0.01):.2f}x |"
    )
    lines.append("")

    lines.append("### commit 类型分布（按 msg pattern）\n")
    lines.append("| Pattern | prism-0420 | prism v1 |")
    lines.append("|---|---|---|")
    all_keys = sorted(
        set(s0.pattern_counts) | set(s1.pattern_counts),
        key=lambda k: -(s0.pattern_counts[k] + s1.pattern_counts[k]),
    )
    for k in all_keys:
        lines.append(f"| {k} | {s0.pattern_counts.get(k, 0)} | {s1.pattern_counts.get(k, 0)} |")
    lines.append("")

    lines.append("## 维度 2: Bug 数（v0.1 基线）\n")
    lines.append("| 指标 | prism-0420 | prism v1 | 备注 |")
    lines.append("|---|---|---|---|")
    lines.append(
        f"| Bug fix commit 数 | {s0.bug_fix_commits} | {s1.bug_fix_commits} | 启发式: msg 含 fix/修复/BUG- |"
    )
    lines.append(
        f"| 真漏 / BUG ID 计数 | {p0_extra['punt_pool_real_holes']}（punt pool 真漏）| {v1_extra['bug_ids']}（bug-log.md BUG-xxx）| 不同口径，仅作量级参考 |"
    )
    lines.append("")
    return "\n".join(lines)


def render_milestone_section(
    p0_ms: list[tuple[str, RepoStats]], v1_ms: list[tuple[str, RepoStats]]
) -> str:
    """v0.2 维度 3: 等价完成度对齐。"""
    lines = []
    lines.append("## 维度 3: 等价完成度对齐（v0.2 / 解决 v0.1 时间窗口不可比）\n")
    lines.append(
        "> 用里程碑切分累计 stats（init → design 完成 → 业务实装完成 → 测试通过）。"
        "同水位下对比才有意义。\n"
    )

    def _milestone_table(repo_label: str, ms: list[tuple[str, RepoStats]]) -> list[str]:
        rows = [
            f"### {repo_label} 各里程碑累计\n",
            "| 里程碑 | 累计天数 | 累计 commits | 累计 fix | commit/day |",
            "|---|---|---|---|---|",
        ]
        for label, st in ms:
            cpd = st.total_commits / max(st.days_span, 1)
            rows.append(
                f"| {label} | {st.days_span} | {st.total_commits} | {st.bug_fix_commits} | {cpd:.2f} |"
            )
        rows.append("")
        return rows

    lines.extend(_milestone_table("prism-0420", p0_ms))
    lines.extend(_milestone_table("prism v1", v1_ms))

    # 等价对照：业务实装完成
    p0_impl = next((s for label, s in p0_ms if "业务实装完成" in label), None)
    v1_impl = next((s for label, s in v1_ms if "业务实装完成" in label), None)
    if p0_impl and v1_impl:
        lines.append("### 等价对照：业务实装完成水位\n")
        lines.append("| 指标 | prism-0420 | prism v1 | ratio (0420/v1) |")
        lines.append("|---|---|---|---|")
        lines.append(
            f"| 累计天数 | {p0_impl.days_span} | {v1_impl.days_span} | "
            f"{p0_impl.days_span / max(v1_impl.days_span, 1):.2f}x |"
        )
        lines.append(
            f"| 累计 commits | {p0_impl.total_commits} | {v1_impl.total_commits} | "
            f"{p0_impl.total_commits / max(v1_impl.total_commits, 1):.2f}x |"
        )
        lines.append(
            f"| 累计 fix commits | {p0_impl.bug_fix_commits} | {v1_impl.bug_fix_commits} | "
            f"{p0_impl.bug_fix_commits / max(v1_impl.bug_fix_commits, 1):.2f}x |"
        )
        cpd_0 = p0_impl.total_commits / max(p0_impl.days_span, 1)
        cpd_1 = v1_impl.total_commits / max(v1_impl.days_span, 1)
        lines.append(
            f"| commit/day | {cpd_0:.2f} | {cpd_1:.2f} | {cpd_0 / max(cpd_1, 0.01):.2f}x |"
        )
        lines.append("")

    lines.append("### 关键 insight 候选\n")
    lines.append(
        '- ⚠️ prism-0420 **未到"测试通过 / 可上线"水位**（Phase 2.3 集成验证未做）；'
        "完整对照需 Phase 2.3 完成后重跑\n"
    )
    if p0_impl and v1_impl:
        ratio = p0_impl.days_span / max(v1_impl.days_span, 1)
        lines.append(
            f"- 业务实装完成水位天数: prism-0420 {p0_impl.days_span} 天 vs v1 "
            f"{v1_impl.days_span} 天（**{ratio:.2f}x**）—— design-first 前置设计的时间代价\n"
        )
        fix_ratio = p0_impl.bug_fix_commits / max(v1_impl.bug_fix_commits, 1)
        lines.append(
            f"- 业务实装完成水位 fix commits: prism-0420 {p0_impl.bug_fix_commits} vs v1 "
            f"{v1_impl.bug_fix_commits}（**{fix_ratio:.2f}x**）—— design-first 是否减少 bug 的实证\n"
        )
    lines.append("")
    return "\n".join(lines)


BEGIN_MARK = "<!-- BEGIN: auto-generated by scripts/phase3_data_collector.py -->"
END_MARK = "<!-- END: auto-generated -->"


def write_output(table_md: str) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    auto_block = (
        f"{BEGIN_MARK}\n"
        f"\n> 自动生成于 {timestamp}（脚本: `scripts/phase3_data_collector.py`）。\n"
        f"> 手工 narrative 段写在 {END_MARK} 之后，不会被脚本覆盖。\n\n"
        f"{table_md}\n"
        f"{END_MARK}\n"
    )

    if OUTPUT.exists():
        old = OUTPUT.read_text(encoding="utf-8")
        if BEGIN_MARK in old and END_MARK in old:
            new = re.sub(
                rf"{re.escape(BEGIN_MARK)}.*?{re.escape(END_MARK)}\n?",
                auto_block,
                old,
                count=1,
                flags=re.S,
            )
            OUTPUT.write_text(new, encoding="utf-8")
            return
        OUTPUT.write_text(old + "\n\n" + auto_block, encoding="utf-8")
        return

    header = (
        "---\n"
        "title: Phase 3 数据对照 baseline（prism-0420 vs prism v1）\n"
        "status: living-doc\n"
        "owner: CY\n"
        "purpose: Shadow 项目 KPI 数据基线。脚本自动维护对照表段；手工写 narrative。\n"
        "---\n\n"
        "# Phase 3 数据对照 baseline\n\n"
        "> 来源: `scripts/phase3_data_collector.py`（可重跑 / v0.2+ 迭代扩维度）。\n"
        "> v0.1 范围: 维度 1 开发速度 + 维度 2 Bug 数。重工 / 可追溯 / 关闸盲区留 v0.2+。\n\n"
    )
    OUTPUT.write_text(header + auto_block, encoding="utf-8")


def main() -> None:
    s0 = collect("prism-0420", PRISM_0420)
    s1 = collect("prism v1", PRISM_V1)
    p0_extra = {"punt_pool_real_holes": count_punt_pool_real_holes(PRISM_0420)}
    v1_extra = {"bug_ids": count_v1_bug_ids(PRISM_V1)}
    table = render_table(s0, s1, p0_extra, v1_extra)

    # v0.2: 等价完成度
    p0_ms = collect_at_milestones("prism-0420", PRISM_0420, MILESTONES["prism-0420"])
    v1_ms = collect_at_milestones("prism v1", PRISM_V1, MILESTONES["prism v1"])
    milestone_section = render_milestone_section(p0_ms, v1_ms)

    output = table + "\n" + milestone_section
    print(output)
    write_output(output)
    print(f"\n→ written to {OUTPUT}")


if __name__ == "__main__":
    main()
