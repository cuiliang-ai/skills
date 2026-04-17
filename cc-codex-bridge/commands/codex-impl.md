---
description: Hand off an implementation task to Codex CLI — via a plan file OR an inline prompt
argument-hint: <path-to-plan.md | inline task description>
allowed-tools: Bash, Read, Glob
---

# Codex Implementation Handoff

Hand off an implementation task to the Codex CLI. Works in two modes:

- **File mode**: `$ARGUMENTS` points to an existing plan document (`.md`, `.txt`, etc.)
- **Inline mode**: `$ARGUMENTS` is a free-form task description

Your job: detect the mode, invoke `codex exec` with a self-contained prompt, relay results.

## Arguments

`$ARGUMENTS`

## Mode detection

1. Take the **first whitespace-separated token** of `$ARGUMENTS`.
2. If that token looks like a path (contains `/`, `\`, or a file extension like `.md`/`.txt`/`.plan`) AND the file exists on disk → **File mode**.
3. Otherwise → **Inline mode** (treat the entire `$ARGUMENTS` as the task prompt).
4. If ambiguous (looks like a path but file doesn't exist), STOP and ask the user whether they meant a file path or an inline prompt.

## File mode

1. Resolve the path to an **absolute path**.
2. Use `Read` to skim the plan (first ~100 lines) so you understand scope.
3. Build the Codex prompt:

   ```
   Read the plan document at <ABSOLUTE_PLAN_PATH> and implement it end-to-end.

   Requirements:
   - Follow the plan's steps in order.
   - Make all necessary file edits; do not just describe changes.
   - If the plan is ambiguous, make the most reasonable choice and note it.
   - After implementing, print a summary of: files changed, key decisions made, and anything left incomplete or blocked.
   - Do NOT commit or push unless the plan explicitly says to.

   <EXTRA_TOKENS_AFTER_THE_PATH_IF_ANY>
   ```

## Inline mode

1. Use `$ARGUMENTS` verbatim as the core task.
2. Build the Codex prompt:

   ```
   Task: <$ARGUMENTS>

   Requirements:
   - Make all necessary file edits; do not just describe changes.
   - If requirements are ambiguous, make the most reasonable choice and note it.
   - After implementing, print a summary of: files changed, key decisions made, and anything left incomplete or blocked.
   - Do NOT commit or push.
   ```

## Invoke Codex

Run via Bash:

```
codex exec "<prompt>"
```

Notes:
- Windows shell quoting is fragile for long multi-line prompts. If the prompt contains double quotes or spans many lines, write it to a temp file first (e.g. `%TEMP%\codex-prompt.txt` or `$env:TEMP\codex-prompt.txt`) and pass it in via whatever stdin/file flag `codex exec` supports, or `codex exec "$(Get-Content -Raw tmpfile)"` equivalent.
- Set Bash `timeout` to `600000` ms (10 min) — Codex runs can be long.
- If `codex exec` offers `--cd <dir>`, prefer running it in the relevant repo root.

## Report back

- Summarize Codex's changes (files + what changed) in <200 words.
- Surface anything Codex flagged as incomplete, ambiguous, or risky.
- Suggest running `/deep-review` or `/review` on the diff as the next step.

## Safety

- File mode: never run `codex exec` on a plan you haven't read. If the file is missing or empty, stop and ask.
- Never create commits yourself — let the user decide after reviewing Codex's output.
- If `codex exec` exits non-zero, surface the error verbatim and stop.
