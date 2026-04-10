---
name: blog-publisher
description: "End-to-end blog publishing workflow for cuiliang.ai. Covers environment setup, article creation, review, and publishing. Use when user mentions: 发blog, 发表文章, publish article, 写文章, 新建文章, create post, 环境搭建, setup environment, 准备环境, 发布, deploy blog, Hugo, page bundle, 检查环境. Also triggers on: blog workflow, blog pipeline, 博客工作流."
---

# Blog Publisher Skill — cuiliang.ai

End-to-end workflow for the **cuiliang.ai** Hugo blog: environment setup, article creation, review, and publishing.

## Blog Identity

- **Site**: https://cuiliang.ai/
- **Engine**: Hugo Extended + PaperMod theme (git submodule)
- **Repo**: `https://github.com/cuiliang-ai/cuiliang.ai.git`
- **Deploy**: Push to `main` → GitHub Actions → GitHub Pages
- **Language**: Chinese with English technical terms
- **Topics**: AI Agent, CUA, MCP, LLM, Harness Engineering, Code Agent

## Quality Gate

Every article MUST pass this test before publishing:

> **读者花 10-15 分钟读完这一篇后，能说出一个他之前不知道的、能改变他下一步行动的东西吗？**

If the answer is no, the article should NOT be published. Use the **blog-review** skill for formal scoring.

---

## Task 1: Environment Check（检查环境）

When user asks to check or verify the blog environment, run these checks:

```bash
# 1. Core tools
node -v          # Need: v20.x+
npm -v           # Need: 11.x+
git --version    # Need: 2.50+
gh --version     # Need: installed
hugo version     # Need: v0.147.0+extended (MUST match CI)
python --version # Need: 3.12.x

# 2. Claude Code
claude --version # Need: 2.1+

# 3. Blog repo
cd <repo-path>
git remote -v              # Should show cuiliang-ai/cuiliang.ai.git
git submodule status       # themes/PaperMod must exist

# 4. Hugo build test
hugo server --port 1314    # Quick smoke test, Ctrl+C after confirming it works

# 5. Optional: Obsidian CLI (requires Obsidian running)
obsidian version           # 1.12+
```

Report results as a checklist table. Flag any missing/mismatched versions.

---

## Task 2: Environment Setup（环境搭建）

When user asks to set up the blog environment on a new machine, follow these steps IN ORDER:

### Step 1: Install base tools (Windows)

```powershell
# Package manager
winget --version  # Pre-installed on Windows 11

# Core tools
winget install OpenJS.NodeJS.LTS      # Node.js 20.x
winget install Git.Git                # Git
winget install GitHub.cli             # GitHub CLI
winget install Hugo.Hugo.Extended     # Hugo Extended (MUST be Extended edition)
winget install Python.Python.3.12     # Python 3.12

# Git config
git config --global user.name "Liang Cui"
git config --global user.email "cuiliang@microsoft.com"

# GitHub auth
gh auth login
```

### Step 2: Clone blog repo

```powershell
git clone --recurse-submodules https://github.com/cuiliang-ai/cuiliang.ai.git
cd cuiliang.ai
hugo server  # Verify: http://localhost:1313 works
```

### Step 3: Install Claude Code

```powershell
npm install -g @anthropic-ai/claude-code
```

### Step 4: Configure Claude Code

Create `~/.claude/settings.json`:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://localhost:4141",
    "ANTHROPIC_AUTH_TOKEN": "dummy",
    "ANTHROPIC_MODEL": "claude-opus-4.6-1m",
    "ANTHROPIC_SMALL_FAST_MODEL": "claude-sonnet-4.6",
    "DISABLE_NON_ESSENTIAL_MODEL_CALLS": "1",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

> If using Anthropic API directly instead of local proxy:
> - Set `ANTHROPIC_BASE_URL` to `https://api.anthropic.com`
> - Set `ANTHROPIC_AUTH_TOKEN` to your actual API key

### Step 5: Configure MCP Servers

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "memory": {
      "type": "stdio",
      "command": "cmd",
      "args": ["/c", "npx", "-y", "@modelcontextprotocol/server-memory"],
      "env": {
        "MEMORY_FILE_PATH": "C:\\Users\\<username>\\.shared-ai-memory\\memory.jsonl"
      }
    }
  }
}
```

```powershell
mkdir "$env:USERPROFILE\.shared-ai-memory"
```

Notion MCP is project-level (already in `<repo>/.claude/settings.json`), first use triggers OAuth.

### Step 6: Copy Skills

Copy the `~/.claude/skills/` directory from source machine. **Minimum required**:
- `blog-review/` — 8-dimension article scoring
- `obsidian-cli/` — Obsidian vault management
- `blog-publisher/` — this skill

### Step 7: Copy global CLAUDE.md

Copy `~/.claude/CLAUDE.md` from source machine. Update vault paths if different.

### Step 8: Optional — Obsidian

```powershell
winget install Obsidian.Obsidian  # v1.12.4+
# Open Obsidian → "Open folder as vault" → choose vault directory
# Login to Obsidian Sync if using sync
```

### Step 9: Verify

Run Task 1 (Environment Check) to confirm everything works.

---

## Task 3: Create New Article（新建文章）

When user asks to create a new blog post:

### Step 1: Create page bundle

```bash
# Slug should be lowercase English with hyphens
mkdir -p content/posts/<slug>
```

### Step 2: Create index.md with front matter

```markdown
---
title: "文章标题"
date: YYYY-MM-DD
draft: true
summary: "一句话概要"
description: "一句话概要"
tags:
  - Tag1
  - Tag2
categories:
  - AI Agent Engineering
ShowToc: true
TocOpen: true
---

文章内容...
```

### Rules

- **Page bundle format**: `content/posts/<slug>/index.md` — NOT loose files in posts/
- **Front matter**: YAML delimiters (`---`), NOT TOML (`+++`)
- **Draft**: Always start as `draft: true`
- **Images**: Place in the same directory as `index.md`
- **Date**: Use the actual publish date, format `YYYY-MM-DD`

---

## Task 4: Publish Article（发表文章）

When user asks to publish an article:

### Pre-flight checklist

1. **Quality gate**: Has the article been reviewed with `blog-review` skill? Score should be ≥ 8.5
2. **Draft flag**: Change `draft: true` → `draft: false`
3. **Date**: Confirm date is correct (should be today's date or intended publish date)
4. **Format**: File is at `content/posts/<slug>/index.md` (page bundle)
5. **Front matter**: title, summary, description, tags, categories all present

### Publish steps

```bash
# 1. Set draft to false
# Edit index.md: draft: false

# 2. Stage the article
git add content/posts/<slug>/

# 3. Commit
git commit -m "publish: 文章标题"

# 4. Push to trigger deployment
git push origin main

# 5. Verify deployment
# GitHub Actions will build and deploy
# Article will be live at https://cuiliang.ai/posts/<slug>/
```

### Commit message convention

Follow the repo's existing style:
- `publish: 文章标题` — new article
- `enhance: description of change` — improve existing article
- `fix: description of fix` — fix errors in article

**IMPORTANT**: Use native git commands. Do NOT use coding-flow MCP tools for commits.

---

## Task 5: Review Article（评审文章）

Delegate to the **blog-review** skill. Invoke it with the article file path.

The review produces an 8-dimension score:
1. 命题价值 (Thesis Value)
2. 结构设计 (Structure Design)
3. 论证质量 (Argumentation Quality)
4. 信息密度 (Information Density)
5. 可操作性 (Actionability)
6. 引用与可信度 (Citations & Credibility)
7. 原创洞察 (Original Insight)
8. 文字质量 (Writing Quality)

Publishing threshold: composite score ≥ 8.5, no dimension below 8.0.

---

## Directory Structure Reference

```
~/.claude/
├── CLAUDE.md              # Global instructions (Memory + Obsidian rules)
├── settings.json          # API config, env vars
├── skills/                # Skills (including this one)
│   ├── blog-publisher/
│   ├── blog-review/
│   ├── obsidian-cli/
│   └── ...
~/.claude.json             # Global MCP servers (memory, etc.)
~/.shared-ai-memory/
└── memory.jsonl           # Knowledge graph data

<repo>/cuiliang.ai/
├── CLAUDE.md              # Project instructions (Hugo workflow)
├── .claude/settings.json  # Project MCP (Notion)
├── hugo.yaml              # Hugo config
├── content/posts/         # Articles (page bundles)
│   └── <slug>/index.md
├── themes/PaperMod/       # Theme submodule
└── .github/workflows/     # CI/CD (deploy.yml)
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Hugo version mismatch | CI uses `v0.147.0`. Install exact version: `winget install Hugo.Hugo.Extended --version 0.147.0` |
| PaperMod submodule empty | `git submodule update --init --recursive` |
| Obsidian CLI unavailable | Obsidian desktop app must be running |
| Claude Code connection failed | Check `ANTHROPIC_BASE_URL` reachability; ensure proxy is running |
| Notion MCP auth expired | Run any Notion operation in Claude Code to re-authenticate |
| Memory MCP migration | Copy `memory.jsonl` to new machine's `~/.shared-ai-memory/` |
| Article not appearing after push | Wait 2-3 min for GitHub Actions; check `draft: false` is set |
