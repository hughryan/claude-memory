# Upstream Mapping: DasBluEyedDevil/Daem0n-MCP → hughryan/claude-memory

This file documents all naming changes to facilitate merging upstream changes from the original repository.

## Quick Reference

| Element | Upstream (Daem0n-MCP) | Fork (claude-memory) |
|---------|----------------------|----------------------|
| Python package | `daem0nmcp` | `claude_memory` |
| Package directory | `daem0nmcp/` | `claude_memory/` |
| CLI command | `daem0nmcp` | `claude-memory` |
| Env var prefix | `DAEM0NMCP_` | `CLAUDE_MEMORY_` |
| Storage directory | `.daem0nmcp/` | `.claude-memory/` |
| Database file | `daem0nmcp.db` | `claude_memory.db` |
| MCP resource URIs | `daem0n://` | `memory://` |
| Qdrant collection (memories) | `daem0n_memories` | `cm_memories` |
| Qdrant collection (code) | `daem0n_code_entities` | `cm_code_entities` |
| MCP server name | `Daem0nMCP` | `ClaudeMemory` |

## File Renames

| Upstream | Fork |
|----------|------|
| `daem0nmcp/` | `claude_memory/` |
| `hooks/daem0n_pre_edit_hook.py` | `hooks/claude_memory_pre_edit_hook.py` |
| `hooks/daem0n_post_edit_hook.py` | `hooks/claude_memory_post_edit_hook.py` |
| `hooks/daem0n_prompt_hook.py` | `hooks/claude_memory_prompt_hook.py` |
| `hooks/daem0n_stop_hook.py` | `hooks/claude_memory_stop_hook.py` |
| `.claude/skills/daem0nmcp-protocol/` | `.claude/skills/claude-memory-protocol/` |
| `.claude/skills/summon_daem0n/` | `.claude/skills/setup-guide/` |
| `.claude/skills/openspec-daem0n-bridge/` | `.claude/skills/openspec-memory-bridge/` |
| `Summon_Daem0n.md` | `Setup.md` |
| `Banish_Daem0n.md` | `Uninstall.md` |
| `docs/openspec-daem0n-integration.md` | `docs/openspec-integration.md` |
| `start_daem0nmcp_server.bat` | `start_claude_memory_server.bat` |

## Themed Language Replacements

| Upstream | Fork |
|----------|------|
| Daem0nMCP | Claude Memory |
| Daem0n-MCP | Claude Memory |
| The Daem0n | the memory system |
| Sacred Covenant | Protocol |
| communion | initialization |
| Commune | Initialize |
| inscribe | record |
| grimoire | documentation/reference |
| ritual | step |
| summon | initialize |
| banish | remove |
| incantation | step/instruction |
| covenant | protocol |
| counsel | context |
| COUNSEL_REQUIRED | CONTEXT_CHECK_REQUIRED |
| COMMUNION_REQUIRED | INIT_REQUIRED |
| requires_counsel | requires_context_check |
| seek counsel | check context |
| wards | hooks |
| altar | server |
| realm | environment/project/system |
| sanctum | storage |
| essence | package |
| portal | session |
| divination | diagnostics |
| afflictions | issues |
| awakens/awaken | starts/start |
| slumber | pause/sleep |
| scrolls | files |
| runes | configuration |
| visions | results |
| powers | tools |
| whispers | messages/hints |
| wisdom | knowledge |
| bound | installed |
| vessel | executable |
| stirs | is active |
| manifest | work |
| transcribed | cloned |
| enchanted | configured |
| laws | rules |
| blessing | approval |
| sacred | core |
| divine | determine |
| Silent Scribe | Auto-Capture |
| Ascension | Upgrade |
| flame | process |
| ignite/light | start |
| Nuclear Option | Quick Removal |
| eternal | permanent |
| fading | decaying |
| burden | context |
| weighty | significant |
| dawn | start |
| meditation | search |
| unbidden | automatically |
| ancient | existing |
| void | database |
| witness | see |
| Sever/sever | Remove/remove |
| Dissolve | Uninstall |
| Exorcism | Removal |
| dormant | inactive |
| initializeer | user |
| Initializeing | Setup |

## Sed Patterns for Merging

Use these patterns to transform upstream changes to match fork naming:

```bash
#!/bin/bash
# transform_upstream.sh - Apply to files after git merge

file="$1"

# Package/module names
sed -i '' 's/from daem0nmcp/from claude_memory/g' "$file"
sed -i '' 's/import daem0nmcp/import claude_memory/g' "$file"
sed -i '' 's/"daem0nmcp"/"claude_memory"/g' "$file"
sed -i '' "s/'daem0nmcp'/'claude_memory'/g" "$file"

# Environment variables
sed -i '' 's/DAEM0NMCP_/CLAUDE_MEMORY_/g' "$file"

# Storage paths
sed -i '' 's/\.daem0nmcp/\.claude-memory/g' "$file"
sed -i '' 's/daem0nmcp\.db/claude_memory.db/g' "$file"

# MCP resources
sed -i '' 's|daem0n://|memory://|g' "$file"

# Qdrant collections
sed -i '' 's/daem0n_memories/cm_memories/g' "$file"
sed -i '' 's/daem0n_code_entities/cm_code_entities/g' "$file"

# Project name
sed -i '' 's/Daem0nMCP/ClaudeMemory/g' "$file"
sed -i '' 's/Daem0n-MCP/Claude Memory/g' "$file"

# Hook filenames (in docs/configs)
sed -i '' 's/daem0n_pre_edit_hook/claude_memory_pre_edit_hook/g' "$file"
sed -i '' 's/daem0n_post_edit_hook/claude_memory_post_edit_hook/g' "$file"
sed -i '' 's/daem0n_prompt_hook/claude_memory_prompt_hook/g' "$file"
sed -i '' 's/daem0n_stop_hook/claude_memory_stop_hook/g' "$file"

# Themed language (for docs)
sed -i '' 's/Sacred Covenant/Protocol/g' "$file"
sed -i '' 's/sacred covenant/protocol/g' "$file"
sed -i '' 's/communion/initialization/g' "$file"
sed -i '' 's/The Daem0n/the memory system/g' "$file"
sed -i '' 's/the Daem0n/the memory system/g' "$file"

# Additional themed language (comprehensive list)
sed -i '' 's/incantation/step/g' "$file"
sed -i '' 's/Incantation/Step/g' "$file"
sed -i '' 's/covenant/protocol/g' "$file"
sed -i '' 's/Covenant/Protocol/g' "$file"
sed -i '' 's/counsel/context/g' "$file"
sed -i '' 's/COUNSEL_REQUIRED/CONTEXT_CHECK_REQUIRED/g' "$file"
sed -i '' 's/COMMUNION_REQUIRED/INIT_REQUIRED/g' "$file"
sed -i '' 's/requires_counsel/requires_context_check/g' "$file"
sed -i '' 's/wards/hooks/g' "$file"
sed -i '' 's/Wards/Hooks/g' "$file"
sed -i '' 's/altar/server/g' "$file"
sed -i '' 's/Altar/Server/g' "$file"
sed -i '' 's/realm/environment/g' "$file"
sed -i '' 's/Realm/Environment/g' "$file"
sed -i '' 's/sanctum/storage/g' "$file"
sed -i '' 's/Sanctum/Storage/g' "$file"
sed -i '' 's/essence/package/g' "$file"
sed -i '' 's/Essence/Package/g' "$file"
sed -i '' 's/portal/session/g' "$file"
sed -i '' 's/divination/diagnostics/g' "$file"
sed -i '' 's/afflictions/issues/g' "$file"
sed -i '' 's/awakens/starts/g' "$file"
sed -i '' 's/scrolls/files/g' "$file"
sed -i '' 's/Scrolls/Files/g' "$file"
sed -i '' 's/runes/configuration/g' "$file"
sed -i '' 's/visions/results/g' "$file"
sed -i '' 's/powers/tools/g' "$file"
sed -i '' 's/Powers/Tools/g' "$file"
sed -i '' 's/whispers/messages/g' "$file"
sed -i '' 's/wisdom/knowledge/g' "$file"
sed -i '' 's/vessel/executable/g' "$file"
sed -i '' 's/Vessel/Executable/g' "$file"
sed -i '' 's/manifest/work/g' "$file"
sed -i '' 's/transcribed/cloned/g' "$file"
sed -i '' 's/enchanted/configured/g' "$file"
sed -i '' 's/laws/rules/g' "$file"
sed -i '' 's/blessing/approval/g' "$file"
sed -i '' 's/sacred/core/g' "$file"
sed -i '' 's/Sacred/Core/g' "$file"
sed -i '' 's/Silent Scribe/Auto-Capture/g' "$file"
sed -i '' 's/Ascension/Upgrade/g' "$file"
sed -i '' 's/flame/process/g' "$file"
sed -i '' 's/ignite/start/g' "$file"
sed -i '' 's/eternal/permanent/g' "$file"
sed -i '' 's/Eternal/Permanent/g' "$file"
sed -i '' 's/fading/decaying/g' "$file"
sed -i '' 's/unbidden/automatically/g' "$file"
sed -i '' 's/ancient/existing/g' "$file"
sed -i '' 's/void/database/g' "$file"
sed -i '' 's/witness/see/g' "$file"
sed -i '' 's/initializeer/user/g' "$file"
sed -i '' 's/Initializeer/User/g' "$file"
sed -i '' 's/Initializeing/Setup/g' "$file"
sed -i '' 's/initializeing/setup/g' "$file"
```

## Merge Workflow

### Step 1: Add Upstream Remote (One-time)

```bash
git remote add upstream https://github.com/DasBluEyedDevil/Daem0n-MCP.git
```

### Step 2: Fetch Upstream Changes

```bash
git fetch upstream
```

### Step 3: Create Merge Branch

```bash
git checkout -b merge-upstream-YYYY-MM-DD
git merge upstream/main --no-commit
```

### Step 4: Handle File Renames

For each renamed file with conflicts:

```bash
# Example: If upstream changed daem0nmcp/server.py
git show upstream/main:daem0nmcp/server.py > /tmp/upstream_server.py
./transform_upstream.sh /tmp/upstream_server.py
# Manually merge /tmp/upstream_server.py changes into claude_memory/server.py
```

### Step 5: Apply Transform Script

For modified files that need name transformations:

```bash
# Apply to all Python files
find claude_memory tests -name "*.py" -exec ./transform_upstream.sh {} \;

# Apply to markdown files
find . -name "*.md" -not -path "./.git/*" -exec ./transform_upstream.sh {} \;
```

### Step 6: Test

```bash
# Verify no old naming
grep -r "daem0nmcp" claude_memory/ tests/ --include="*.py"
grep -r "DAEM0NMCP_" claude_memory/ tests/ --include="*.py"

# Run tests
pytest tests/ -v

# Test CLI
pip install -e .
claude-memory --help
```

### Step 7: Complete Merge

```bash
git add -A
git commit -m "Merge upstream changes from Daem0n-MCP"
git checkout main
git merge merge-upstream-YYYY-MM-DD
```

## Unchanged Elements

These elements have the same functionality, only naming differs:
- All Python logic and algorithms
- Database schema (table names unchanged)
- Test assertions and behavior
- MCP tool functionality
- API contracts

## Notes

- The fork preserves upstream functionality completely
- Only user-facing names and branding have changed
- When in doubt, prioritize upstream logic over fork conventions
- Document any divergences from upstream in this file
