---
name: obsidian-cli
description: "Manage Obsidian vault via CLI. Use when user wants to create/read/search/edit notes, write daily journal, manage tasks, organize vault, work with tags/links/properties, or any note-taking related request. Triggers on keywords like: vault, obsidian, daily note, note, journal, search notes, tag, backlink, 笔记, 日记, 记录, 搜索笔记."
---

# Obsidian CLI Integration

Operate the user's Obsidian vault via the built-in `obsidian` CLI (v1.12+). Run all commands via the **Bash tool**.

## Prerequisites

- **Obsidian** desktop app v1.12+ installed and running
- **Obsidian CLI** available in PATH (bundled with Obsidian 1.12+)
- At least one vault open in Obsidian

## First-Time Setup

On the **first use** of this skill, you MUST auto-detect the user's environment before proceeding:

1. Run `obsidian vaults verbose` to list available vaults (names and paths)
2. If **multiple vaults** found → use `AskUserQuestion` to let the user pick which vault to use
3. If **only one vault** → use it directly, confirm with user
4. Run `obsidian daily:path` to detect the daily note format/path pattern
5. Run `obsidian sync:status` to check if sync is enabled
6. Present the detected configuration to the user for confirmation
7. Suggest the user add the following block to their `~/.claude/CLAUDE.md` (global) or project-level `CLAUDE.md` for future sessions:

```markdown
# Obsidian Notes
- Vault: `<vault_name>` at `<vault_path>`
- Obsidian CLI (v1.12+) is available in PATH. Use the `obsidian-cli` skill for note operations.
- Daily Note Format: `<detected_format>`
- When user mentions notes, journal, vault, obsidian, invoke the `obsidian-cli` skill.
```

> **Note**: If the user's `CLAUDE.md` already contains vault info (vault name + path), skip the setup and use that configuration directly.

## Syntax Rules

- `file=` resolves by name like wikilinks; `path=` is exact path including folder
- Quote values with spaces: `file="My Note"`
- Use `\n` for newline, `\t` for tab in content values
- Most commands default to the active file when file/path is omitted
- Output formats: `format=json|tsv|csv|text|yaml` (varies by command)

## Commands

### Read & Search

```bash
obsidian read file="Name"                          # Read by name
obsidian read path="folder/note.md"                # Read by exact path
obsidian search query="keyword"                    # Search file list
obsidian search:context query="keyword"            # Search with line context
obsidian search query="keyword" path="folder" limit=10 format=json
```

### Create & Edit

```bash
obsidian create name="Note.md" content="# Title\nBody"
obsidian create name="Note.md" template="TplName"
obsidian append file="Note" content="text"         # Append
obsidian prepend file="Note" content="text"        # Prepend
obsidian open file="Note"                          # Open in GUI
```

### Daily Notes

```bash
obsidian daily                                     # Open today
obsidian daily:path                                # Get path
obsidian daily:read                                # Read content
obsidian daily:append content="- Done something"   # Append
obsidian daily:prepend content="## Section"        # Prepend
```

### File Management

```bash
obsidian rename file="Old" name="New"
obsidian move file="Note" to="folder"
obsidian delete file="Note"                        # To trash
obsidian files                                     # List all
obsidian files folder="sub" ext=md total           # Count filtered
obsidian folders
```

### Properties (Frontmatter)

```bash
obsidian property:read name="key" file="Note"
obsidian property:set name="key" value="val" file="Note"
obsidian property:set name="tags" value="a,b" type=list file="Note"
obsidian property:remove name="key" file="Note"
obsidian properties file="Note"                    # All props of a note
obsidian properties counts sort=count              # Vault-wide stats
```

### Tasks

```bash
obsidian tasks                                     # All tasks
obsidian tasks todo                                # Incomplete
obsidian tasks done                                # Completed
obsidian tasks daily                               # Today's tasks
obsidian tasks file="Note" verbose                 # With line numbers
obsidian task file="Note" line=5 toggle            # Toggle
obsidian task file="Note" line=5 done              # Mark done
```

### Tags & Links

```bash
obsidian tags counts sort=count                    # All tags
obsidian tags file="Note"                          # Note's tags
obsidian links file="Note"                         # Outgoing
obsidian backlinks file="Note"                     # Incoming
obsidian orphans                                   # No incoming links
obsidian deadends                                  # No outgoing links
obsidian unresolved                                # Broken links
```

### Bookmarks

```bash
obsidian bookmarks
obsidian bookmark file="Note"
obsidian bookmark search="query" title="Title"
```

### Plugins

```bash
obsidian plugins                                   # Installed
obsidian plugins:enabled                           # Active
obsidian plugin:enable id="plugin-id"
obsidian plugin:disable id="plugin-id"
obsidian plugin:install id="plugin-id" enable
```

### Vault & System

```bash
obsidian vault                                     # Info
obsidian vaults verbose                            # All vaults
obsidian version
obsidian command id="command-id"                   # Run any command
obsidian commands filter="prefix"                  # List commands
obsidian eval code="app.vault.getName()"           # Run JS
```

### Bases (Database)

```bash
obsidian bases                                     # List bases
obsidian base:views                                # Views in base
obsidian base:query file="Base" format=json        # Query base
obsidian base:create file="Base" name="Item" content="text"
```

### History & Sync

```bash
obsidian history file="Note"                       # Version history
obsidian history:read file="Note" version=1        # Read version
obsidian history:restore file="Note" version=2     # Restore
obsidian sync:status                               # Sync status
obsidian diff file="Note"                          # Local/sync diff
```

## Workflow Guidelines

1. **Take notes / journal / add to today**: Use `daily:append` or `daily:prepend`
2. **Find notes / search**: Use `search` or `search:context`
3. **Organize vault**: Combine `orphans`, `deadends`, `unresolved`, `tags counts` to analyze vault health
4. **Before editing a note**: Always `read` first to understand existing content
5. **Batch operations**: Use `format=json` for structured output, then process programmatically
6. **Create from template**: Use `create name="Note.md" template="TemplateName"`
