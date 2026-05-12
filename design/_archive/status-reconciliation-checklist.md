# Status Reconciliation Checklist

## Goal

Align the project's status signals so that `frontmatter`, batch audit conclusions, and summary READMEs stop contradicting each other.

## Suggested Source Priority

Use the following order as the temporary single source of truth until the repo is cleaned up:

1. Module `00-design.md` frontmatter
2. Latest batch `verify` / audit conclusion for that module
3. `design/02-modules/README.md`
4. Planning documents such as PRD / module catalog / `design/README.md`

If two higher-priority sources conflict and there is no explicit supersede note, treat the module as **unresolved** and do not keep `accepted`.

## Current Reconciliation Items

| Scope | Conflicting signals | Current judgment | Action |
|------|------|------|------|
| Global planning state | `design/00-architecture/01-PRD.md` still says "A+B 完成后再选 1 个最小模块" while many modules are already documented as completed. `design/00-architecture/05-module-catalog.md` also still says "本期选定模块（待定）". | Planning documents are stale. | Rewrite these sections as historical context or current reality; they should no longer describe module selection as pending. |
| Design entry README | `design/README.md` still marks all B-dock docs unfinished and C-dock still not展开, while `design/02-modules/README.md` lists many completed modules. | Top-level progress view is stale. | Update `design/README.md` to reflect real progress, or add a clear "snapshot date / historical" note. |
| Engineering baseline vs accepted modules | `design/01-engineering/02-quality-spec.md`, `03-cicd-plan.md`, `04-observability-plan.md`, `05-security-baseline.md` are still mostly placeholders, but many modules are already marked `accepted`. | Acceptance gate is not consistent. | Stop creating new `accepted` states until B-dock decisions are complete, or explicitly weaken the acceptance definition. |
| M04 | `design/02-modules/M04-feature-archive/00-design.md` is `status: draft`, but `design/02-modules/README.md` lists M04 as accepted. | Unresolved. | Decide whether M04 is really accepted. Then change one side; do not leave `draft` and `accepted` side by side. |
| M02 / M03 / M11 / M12 | Module frontmatter and modules README say `accepted`, but `design/02-modules/audit-report-batch2-verify.md` still says all 4 cannot yet turn accepted. | Likely stale verify report or missing final re-verify note. | Either: 1) add a final accepted conclusion with date and resolved blockers, or 2) temporarily revert those modules to `draft`. |
| M08 / M09 / M10 / M15 | Module frontmatter and modules README say `accepted`, but `design/02-modules/audit-report-batch3.md` says all 4 are still `draft` and cannot turn accepted. | High-confidence status conflict. | Revert these 4 modules to `draft` unless there is a later verify file proving they passed. |
| M17 | `design/02-modules/M17-ai-import/00-design.md` and modules README say `accepted`, but `design/02-modules/M17-ai-import/audit-report.md` still contains a "不能转 accepted" conclusion. | Historical audit was not marked superseded. | Keep module status only if a later fix result exists; otherwise annotate the audit report as pre-fix / superseded. |
| Accepted modules with baseline patch debt | `design/adr/ADR-003-cross-module-read-strategy.md` requires changes in already accepted modules; `design/02-modules/README.md` also has a baseline patch TODO for accepted modules. | `accepted` does not mean frozen baseline. | Introduce `accepted-with-patch` policy or complete the baseline patch before keeping `accepted`. |
| Activity log ownership and enum evolution | Batch3 audit says M15's `action_type / target_type` cross-module alignment path is still incomplete. | Cross-module status is incomplete. | Add an ADR or README rule for `activity_log` ownership and enum update flow before further accept decisions. |

## Module-Level Decision Queue

### First priority

1. M08
2. M09
3. M10
4. M15

Reason: batch3 audit explicitly says these cannot turn accepted, but their frontmatter already says accepted.

### Second priority

1. M04
2. M02
3. M03
4. M11
5. M12
6. M17

Reason: these look more like stale summary / stale audit artifacts, but they still break trust in status.

## Recommended Cleanup Order

1. Define and document source priority in `design/README.md` or `design/02-modules/README.md`.
2. Reconcile frontmatter for M04, M08, M09, M10, M15 first.
3. Decide whether batch2 verify reports are stale or whether batch2 modules should be downgraded.
4. Mark historical audit reports as `superseded` or add a clear "pre-fix result" note.
5. Update PRD, module catalog, and top-level design README so they reflect the current phase.
6. Finish B-dock engineering decisions before issuing more `accepted` module states.
7. Execute the baseline patch TODO created by ADR-003 and batch3 rules.

## Minimum Repo Policy After Cleanup

Use this as the minimum rule going forward:

- A module cannot be `accepted` if the latest audit / verify still says "不能转 accepted".
- If a later fix changed the conclusion, the repo must contain a later verify artifact or an explicit supersede note.
- Summary READMEs must be regenerated or manually updated in the same change that modifies module frontmatter.
- Cross-module ADR-triggered baseline patches must either be finished before acceptance, or acceptance must explicitly carry patch debt status.

## Quick Verification Commands

```powershell
Get-ChildItem 'F:\prism-0420\design\02-modules' -Directory |
  Where-Object { $_.Name -like 'M*' } |
  ForEach-Object {
    $file = Join-Path $_.FullName '00-design.md'
    if (Test-Path $file) {
      Get-Content $file | Select-String '^status:|^accepted:'
    }
  }
```

```powershell
rg -n "不能转 accepted|status: accepted|status: draft" F:\prism-0420\design\02-modules
```

## Files To Update First

- `F:\prism-0420\design\02-modules\M04-feature-archive\00-design.md`
- `F:\prism-0420\design\02-modules\M08-module-relation\00-design.md`
- `F:\prism-0420\design\02-modules\M09-search\00-design.md`
- `F:\prism-0420\design\02-modules\M10-overview\00-design.md`
- `F:\prism-0420\design\02-modules\M15-activity-stream\00-design.md`
- `F:\prism-0420\design\02-modules\README.md`
- `F:\prism-0420\design\README.md`
- `F:\prism-0420\design\00-architecture\01-PRD.md`
- `F:\prism-0420\design\00-architecture\05-module-catalog.md`
