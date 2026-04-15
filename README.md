# Claude Code Skills

Reusable [Claude Code](https://claude.ai/code) skill definitions by [Cui Liang](https://cuiliang.ai).

Follow the [Agent Skills](https://agentskills.io) open standard — works across Claude Code, Cursor, Gemini CLI, VS Code Copilot, and other compatible agents.

## Available Skills

| Skill | Description | Invoke |
|-------|-------------|--------|
| **[blog-review](blog-review/)** | 8 维度结构化评分体系审查博客文章质量 | `/blog-review` |
| **[blog-publisher](blog-publisher/)** | 端到端博客发布工作流（Hugo + PaperMod） | `/blog-publisher` |
| **[interactive-diagram](interactive-diagram/)** | 为 mdBook 生成 8 种交互式图表（纯 HTML/CSS/JS，零依赖） | `/interactive-diagram` |
| **[token-usage](token-usage/)** | Claude Code Token 用量分析与可视化报告生成 | `/token-usage` |

## Install

### Method 1: Copy to personal skills directory（推荐）

Personal skills are available across **all** your projects:

```bash
git clone https://github.com/cuiliang-ai/skills.git /tmp/cuiliang-skills

# Install one skill
cp -r /tmp/cuiliang-skills/interactive-diagram ~/.claude/skills/interactive-diagram

# Or install all
cp -r /tmp/cuiliang-skills/*/ ~/.claude/skills/
```

After copying, the skill is immediately available — type `/interactive-diagram` in Claude Code.

### Method 2: Copy to project skills directory

Project-scoped skills only apply to one project and can be committed to version control:

```bash
cp -r /tmp/cuiliang-skills/interactive-diagram .claude/skills/interactive-diagram
```

### Method 3: Add as additional directory（零安装）

Read-only, session-scoped — no files are copied:

```bash
claude --add-dir /path/to/cuiliang-skills
```

All skills from the directory become available in that session.

### Method 4: Git submodule（团队共享）

Add as a submodule for team-wide access:

```bash
git submodule add https://github.com/cuiliang-ai/skills.git .claude/skills/cuiliang-skills
```

## Skill Structure

```
<skill-name>/
├── SKILL.md           # Entry point with YAML frontmatter (required)
├── reference/         # Reference docs (loaded on demand)
├── templates/         # Templates for Claude to fill in
├── scripts/           # Scripts Claude can execute
└── examples/          # Example outputs
```

## Compatibility

Skills follow the [Agent Skills](https://agentskills.io) open standard. Compatible with:

- [Claude Code](https://claude.ai/code)
- [Cursor](https://cursor.com)
- [VS Code Copilot](https://code.visualstudio.com)
- [Gemini CLI](https://geminicli.com)
- [Roo Code](https://roocode.com)
- [OpenHands](https://openhands.dev)
- And [many more](https://agentskills.io)

## License

MIT
