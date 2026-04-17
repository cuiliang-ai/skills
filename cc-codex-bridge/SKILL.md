---
name: cc-codex-bridge
description: "Bridge Claude Code (CC) and Codex CLI so CC plans/reviews while Codex executes. Use when the user mentions: codex, cc 调用 codex, 让 codex 实现, hand off to codex, codex exec, plan→codex workflow, 规划交给 codex, CC 和 Codex 协作, 双 agent workflow. Installs a `/codex-impl` slash command that takes either a plan document or an inline prompt and dispatches it to `codex exec`."
---

# CC ↔ Codex Bridge Skill

A lightweight workflow for running **Claude Code (CC)** and **Codex CLI** on the same machine as a two-agent team:

- **CC** is the *brain* — plans, reviews, coordinates, keeps context.
- **Codex** is the *hands* — executes large edits in its own session, reports back.
- The handoff is a single slash command: **`/codex-impl`**.

## Why this workflow

Running CC + Codex together gives you:

| Role | Tool | Strength |
|------|------|----------|
| Planning, reviewing, coordinating | **CC** | Rich tool ecosystem, conversation memory, hooks, skills |
| Bulk implementation | **Codex** | Fresh context per run, good at following precise plans |

Splitting the two prevents CC from burning its context window on mechanical edits, and keeps a clean paper trail (plan doc → codex run → CC review).

## Prerequisites

1. **Codex CLI installed** and on `PATH`. Test with:
   ```
   codex --version
   codex exec --help
   ```
2. **CC allowlist** — to avoid permission prompts every run, add to `~/.claude/settings.json`:
   ```json
   {
     "permissions": {
       "allow": ["Bash(codex exec:*)", "Bash(codex:*)"]
     }
   }
   ```

## The `/codex-impl` command

Installed at `commands/codex-impl.md` in this skill. Copy it to:

- `~/.claude/commands/codex-impl.md` (personal, all projects) — **recommended**, or
- `.claude/commands/codex-impl.md` (project-scoped, committable)

### Two modes

The command auto-detects which mode to use based on the first argument:

**File mode** — first token is an existing file path:
```
/codex-impl ./plans/feature-x.md
/codex-impl ./plans/feature-x.md 只动 src/ 目录
```
CC reads the plan first, then tells Codex to implement it end-to-end.

**Inline mode** — first token is not a path (or the file doesn't exist):
```
/codex-impl 给 utils.py 加一个 retry 装饰器，指数退避，最多 3 次
/codex-impl 把所有 print 换成 logging，级别 INFO
```
The whole argument string is passed through to Codex as the task.

### Safety rails (built into the command)

- File mode: refuses to run on a plan that doesn't exist or is empty.
- Ambiguous paths (looks like a path but file missing): stops and asks.
- Never commits or pushes — leaves the diff for the user to review.
- Surfaces Codex's non-zero exits verbatim instead of hiding them.
- 10-minute Bash timeout for long runs.

## Typical workflow

```
┌─────────────────────────────────────────────────────────┐
│  1. CC: /plan        →  generates plans/feature-x.md    │
│  2. CC: /review-plan →  self-critiques the plan (opt.)  │
│  3. CC: /codex-impl plans/feature-x.md                  │
│           ↓                                             │
│         codex exec "<self-contained prompt>"            │
│           ↓                                             │
│         Codex edits files, prints summary               │
│  4. CC: summarizes Codex's output (<200 words)          │
│  5. CC: /deep-review  →  audits the diff                │
│  6. User: decides commit / push                         │
└─────────────────────────────────────────────────────────┘
```

## Windows quoting note

`codex exec "<prompt>"` is fragile on Windows when the prompt contains double quotes or many newlines. The command already handles this by falling back to writing the prompt to a temp file (`%TEMP%\codex-prompt.txt`) and reading it back. If you see weird truncation, check the temp-file path.

## When NOT to use `/codex-impl`

- **Tiny edits** (1-3 lines): faster to let CC edit directly. Use `/quick-fix` instead.
- **Exploration / research**: CC with Agent tool is better — Codex is a fresh-context executor, not a researcher.
- **Tasks needing conversation memory**: Codex forgets between runs. If the work needs multiple back-and-forth rounds with your prior context, keep it in CC.

## Files in this skill

- `SKILL.md` — this file (skill definition + docs)
- `commands/codex-impl.md` — the slash command that performs the handoff

## Install

```bash
# Clone the skills repo
git clone https://github.com/cuiliang-ai/skills.git /tmp/cuiliang-skills

# Install the skill (documentation lives in ~/.claude/skills)
cp -r /tmp/cuiliang-skills/cc-codex-bridge ~/.claude/skills/cc-codex-bridge

# Install the slash command (this is the actually-used artifact)
cp /tmp/cuiliang-skills/cc-codex-bridge/commands/codex-impl.md ~/.claude/commands/codex-impl.md
```

After install, `/codex-impl` becomes available in CC across all projects.
