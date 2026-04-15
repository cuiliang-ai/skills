# Claude Code Skills

Reusable [Claude Code](https://claude.com/claude-code) skill definitions by [Cui Liang](https://cuiliang.ai).

## Available Skills

| Skill | Description |
|-------|-------------|
| **[blog-review](blog-review/)** | 8 维度结构化评分体系审查博客文章质量 |
| **[blog-publisher](blog-publisher/)** | 端到端博客发布工作流（Hugo + PaperMod） |
| **[interactive-diagram](interactive-diagram/)** | 为 mdBook 生成 8 种交互式图表（纯 HTML/CSS/JS，零依赖） |
| **[token-usage](token-usage/)** | Claude Code Token 用量分析与可视化报告生成 |

## Install

Each skill is a directory with `SKILL.md` as the entry point, following the [Agent Skills](https://agentskills.io) open standard.

**Option 1 — Clone to personal skills directory** (all your projects can use it):

```bash
# Clone the repo
git clone https://github.com/cuiliang-ai/skills.git /tmp/cuiliang-skills

# Copy individual skills
cp -r /tmp/cuiliang-skills/blog-review ~/.claude/skills/blog-review
cp -r /tmp/cuiliang-skills/blog-publisher ~/.claude/skills/blog-publisher
cp -r /tmp/cuiliang-skills/interactive-diagram ~/.claude/skills/interactive-diagram
```

**Option 2 — Clone to project skills directory** (project-scoped):

```bash
cp -r /tmp/cuiliang-skills/interactive-diagram .claude/skills/interactive-diagram
```

**Option 3 — Use as additional directory** (read-only, session-scoped):

```bash
claude --add-dir /path/to/cuiliang-skills
```

## Skill Structure

```
<skill-name>/
├── SKILL.md           # Entry point (required)
├── reference/         # Reference docs (loaded on demand)
├── templates/         # Templates for Claude to fill in
├── scripts/           # Scripts Claude can execute
└── examples/          # Example outputs
```

## License

MIT
