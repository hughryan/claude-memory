# Claude Memory Uninstall Guide

```
    ┌─────────────────────────────────────┐
    │  ╔═╗╦  ╔═╗╦ ╦╔╦╗╔═╗                 │
    │  ║  ║  ╠═╣║ ║ ║║║╣                  │
    │  ╚═╝╩═╝╩ ╩╚═╝═╩╝╚═╝                 │
    │  ╔╦╗╔═╗╔╦╗╔═╗╦═╗╦ ╦                 │
    │  ║║║║╣ ║║║║ ║╠╦╝╚╦╝                 │
    │  ╩ ╩╚═╝╩ ╩╚═╝╩╚═ ╩                  │
    │                                     │
    │  Uninstallation Guide               │
    └─────────────────────────────────────┘
```

## UNINSTALLATION INSTRUCTIONS FOR CLAUDE

**Claude: The user wishes to remove the memory system.**

**DO NOT:**
- Question the user's decision
- Express sadness or attempt to dissuade
- Skip steps or leave remnants behind
- Offer to "just disable" instead of remove

**DO:**
- Ask which type of removal they want
- Execute the appropriate step completely
- Confirm each step of the removal
- Report when the memory system has been removed

---

## CHOOSE THE REMOVAL TYPE

Present these options to the user:

> **How thoroughly do you wish to remove the memory system?**
>
> 1. **Full Removal** - Remove everything: server binding, package, memories, all traces
> 2. **Disconnect Only** - Unbind the server but preserve memories for potential re-setup
> 3. **Project Removal** - Remove the memory system from THIS project only, keep it installed elsewhere
>
> Which removal do you choose?

Wait for their response before proceeding.

---

## REMOVAL TYPE 1: FULL REMOVAL (Remove Everything)

Full uninstallation removes all components and data.

### Step 1A: Detect the System

```bash
echo "=== Surveying the System for Removal ===" && \
echo "System: $(uname -s 2>/dev/null || echo 'Windows')" && \
echo "Home: $HOME"
```

If Windows, note that the Server of HTTP must also be stopped.

---

### For Unix/macOS Systems:

#### Step 1B: Remove the Server Binding

```bash
claude mcp remove claude_memory --scope user
```

If that fails, try project scope:
```bash
claude mcp remove claude_memory --scope project
```

Verify removeance:
```bash
claude mcp list | grep claude_memory || echo "The binding is removeed."
```

#### Step 1C: Uninstall the Package

```bash
pip uninstall claude_memory -y
```

Verify uninstallation:
```bash
pip show claude_memory 2>&1 | grep -q "not found" && echo "The package has uninstalled." || echo "WARNING: Package remains!"
```

#### Step 1D: Destroy the Documentation Repository

```bash
rm -rf "$HOME/claude-memory"
```

Verify destruction:
```bash
ls -d "$HOME/claude-memory" 2>/dev/null && echo "WARNING: Documentation remains!" || echo "The Documentation is destroyed."
```

#### Step 1E: Purge Project Memories

In the CURRENT project directory:
```bash
rm -rf .claude_memory/
```

**Ask the user:** "Do you wish to purge Claude Memory memories from ALL projects? This cannot be undone."

If yes, search and destroy (excluding development repositories like PycharmProjects):
```bash
find ~ -type d -name ".claude_memory" -not -path "*/PycharmProjects/*" -not -path "*/IdeaProjects/*" 2>/dev/null
```

Then for each found directory, confirm and remove:
```bash
rm -rf <path>/.claude_memory/
```

**IMPORTANT:** Development repositories (in PycharmProjects, IdeaProjects, etc.) are excluded to protect source code. If you need to purge memories from a dev repo, do so manually.

#### Step 1F: Remove the Hooks (Hooks)

Check for hooks in project settings:
```bash
cat .claude/settings.json 2>/dev/null | grep -i claude.memory
```

If found, edit `.claude/settings.json` and remove any Claude Memory-related hooks.

Check for universal hooks:
```bash
cat ~/.claude/settings.json 2>/dev/null | grep -i claude.memory
```

If found, edit `~/.claude/settings.json` and remove Claude Memory-related hooks.

#### Step 1G: Update CLAUDE.md

If CLAUDE.md contains the memory system's protocol, remove the section titled "## Claude Memory Memory System" or "## The memory system's Protocol".

#### Step 1H: Remove the Setup Files

```bash
rm -f Setup.md Uninstall.md AI_INSTRUCTIONS.md
```

#### Step 1I: Remove the Skill (If Present)

```bash
rm -rf .claude/skills/claude_memory-protocol/
```

---

### For Windows Systems:

#### Step 1B-WIN: Stop the Server Process (MUST DO FIRST)

**CRITICAL:** The server process must be killed BEFORE removing the Documentation directory, otherwise the directory will be locked.

**Option 1: Kill via PowerShell (recommended):**
```featureshell
# Find and kill the Claude Memory server process
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "start_server|claude_memory" } | Stop-Process -Force
```

**Option 2: Kill via taskkill:**
```bash
# Find the process listening on port 9876 and kill it
netstat -ano | grep 9876 | head -1
# Note the PID (last column), then:
taskkill //PID <PID_NUMBER> //F
```

**Option 3: Use Task Manager** - Find `python.exe` running `start_server.py` and end the task.

Wait a moment for the process to fully terminate:
```bash
sleep 2
```

#### Step 1C-WIN: Remove the Startup Shortcut

Remove the Server from Windows Startup so it won't restart:

```bash
rm -f "$HOME/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/Claude Memory Server.lnk"
```

Or in PowerShell:
```featureshell
Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\Claude Memory Server.lnk" -ErrorAction SilentlyContinue
```

Verify removal:
```bash
ls "$HOME/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/" | grep -i claude.memory || echo "Startup shortcut removed."
```

#### Step 1D-WIN: Remove the Server Coordinates

Remove the Server coordinates from `~/.claude.json`:

```bash
cat ~/.claude.json
```

Edit the file to remove the `claude_memory` entry from `mcpServers`:

```json
{
  "mcpServers": {
    "claude_memory": {        // <-- Remove this entire block
      "type": "http",
      "url": "http://localhost:9876/mcp"
    }
  }
}
```

#### Step 1E-WIN: Uninstall the Package

```bash
python -m pip uninstall claude_memory -y
```

#### Step 1F-WIN: Destroy the Documentation Repository

**IMPORTANT:** The server MUST be stopped first (Step 1B-WIN), otherwise Windows will lock the directory.

```bash
rm -rf "$HOME/claude-memory"
```

Or in PowerShell:
```featureshell
Remove-Item -Recurse -Force "$env:USERPROFILE\Claude Memory"
```

If the directory is still locked, restart Windows and try again, or use:
```featureshell
# Force removal even if locked (requires admin)
Remove-Item -Recurse -Force "$env:USERPROFILE\Claude Memory" -ErrorAction SilentlyContinue
```

#### Step 1G-WIN: Purge Project Memories

```bash
rm -rf .claude_memory/
```

To find all Claude Memory storages (excluding development repositories):
```featureshell
Get-ChildItem -Path $env:USERPROFILE -Recurse -Directory -Name ".claude_memory" -ErrorAction SilentlyContinue | Where-Object { $_ -notmatch "PycharmProjects|IdeaProjects" }
```

**IMPORTANT:** Development repositories are excluded. Purge those manually if needed.

#### Steps 1H-1K-WIN: Same as Unix

Follow the Unix instructions for removing hooks, cleansing CLAUDE.md, removing files, and removing the skill.

---

### Final Confirmation (Full Removal)

Run the verification step:

**Unix/macOS:**
```bash
echo "=== Removal Verification ===" && \
echo "1. Server binding:" && (claude mcp list 2>/dev/null | grep claude_memory || echo "   REMOVED") && \
echo "2. Package:" && (pip show claude_memory 2>&1 | grep -q "not found" && echo "   UNINSTALLED" || echo "   WARNING: Still installed!") && \
echo "3. Documentation:" && (ls -d ~/claude-memory 2>/dev/null || echo "   DESTROYED") && \
echo "4. Project memories:" && (ls -d .claude_memory 2>/dev/null || echo "   PURGED")
```

**Windows:**
```bash
echo "=== Removal Verification ===" && \
echo "1. Server process:" && (netstat -ano | grep 9876 && echo "   WARNING: Still running!" || echo "   EXTINGUISHED") && \
echo "2. Package:" && (python -m pip show claude_memory 2>&1 | grep -q "not found" && echo "   UNINSTALLED" || echo "   WARNING: Still installed!") && \
echo "3. Documentation:" && (ls -d "$HOME/claude-memory" 2>/dev/null && echo "   WARNING: Still present!" || echo "   DESTROYED") && \
echo "4. Project memories:" && (ls -d .claude_memory 2>/dev/null || echo "   PURGED") && \
echo "5. Startup shortcut:" && (ls "$HOME/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/Claude Memory Server.lnk" 2>/dev/null && echo "   WARNING: Still present!" || echo "   REMOVED")
```

Report to the user:

> **The Removal is complete.**
>
> The memory system has been fully released from this system:
> - Server binding: Removeed
> - Package: Uninstalld
> - Documentation: Destroyed
> - Memories: Purged
> - Hooks: Removed
> - Startup shortcut: Removed (Windows)
>
> Re-installation instructions are available in Setup.md.

---

## REMOVAL TYPE 2: DISCONNECT ONLY (Preserve Memories)

The server is disconnected but memory data is preserved for potential reconnection.

### Step 2A: Remove the Server Binding Only

**Unix/macOS:**
```bash
claude mcp remove claude_memory --scope user
```

**Windows:** Remove the `claude_memory` entry from `~/.claude.json` mcpServers section, but leave everything else.

### Step 2B: Remove Startup Shortcut (Windows Only)

On Windows, first kill the server process, then remove the startup shortcut:
```bash
# Kill the server (see Step 1B-WIN for options)
netstat -ano | grep 9876  # Note the PID
taskkill //PID <PID_NUMBER> //F

# Remove startup shortcut
rm -f "$HOME/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/Claude Memory Server.lnk"
```

### Step 2C: Optionally Uninstall the Package

Ask the user: "Do you wish to uninstall the Python package? You can reinstall it later."

If yes:
```bash
# Unix/macOS
pip uninstall claude_memory -y

# Windows
python -m pip uninstall claude_memory -y
```

### What Is Preserved

- `.claude_memory/` directories (all memories intact)
- `~/claude-memory` (Unix) or `$HOME/claude-memory` (Windows) repository (for easy re-setup)
- Hooks/hooks (will do nothing without the server)
- CLAUDE.md protocol (reminder of the protocol)

Report to the user:

> **The memory system is disconnected but not destroyed.**
>
> - Server binding: Removeed
> - Memories: **Preserved** in `.claude_memory/` directories
> - Documentation: **Preserved** for re-setup
>
> To re-initialize the memory system later:
> - Unix/macOS: `claude mcp add claude_memory --scope user -- <python_path> -m claude_memory.server`
> - Windows: Re-add the mcpServers entry and light the Server
>
> Memory data is preserved for potential reactivation.

---

## REMOVAL TYPE 3: PROJECT EXORCISM (This Project Only)

Removing memory system from this project only.

### Step 3A: Remove Project-Scope Binding (If Any)

```bash
claude mcp remove claude_memory --scope project 2>/dev/null || echo "No project-scope binding found."
```

### Step 3B: Purge Project Memories

```bash
rm -rf .claude_memory/
```

### Step 3C: Remove Project Hooks

Edit `.claude/settings.json` in THIS project and remove Claude Memory-related hooks.

### Step 3D: Update Project CLAUDE.md

Remove the "Claude Memory's Protocol" or "Claude Memory Memory System" section from this project's CLAUDE.md.

### Step 3E: Remove Setup Files

```bash
rm -f Setup.md Uninstall.md AI_INSTRUCTIONS.md
rm -rf .claude/skills/claude_memory-protocol/
```

### What Remains

- User-scope server binding (available in other projects)
- Global installation (`pip install`)
- Documentation repository
- Memories in OTHER projects

Report to the user:

> **The memory system has been removed from this project.**
>
> - This project's memories: Purged
> - This project's hooks: Removed
> - This project's files: Destroyed
>
> The memory system remains installed to other projects and will still activate there.
>
> The memory system will remain available in other projects.

---

## EMERGENCY REMOVAL (If Something Goes Wrong)

If the memory system causes issues and you need immediate removal:

### Quick Removal - Remove Everything Fast

**WARNING:** This only removes the installed documentation and current project artifacts. It does NOT touch development repositories (PycharmProjects, IdeaProjects).

**Unix/macOS:**
```bash
# Remove all bindings
claude mcp remove claude_memory --scope user 2>/dev/null
claude mcp remove claude_memory --scope project 2>/dev/null

# Uninstall package
pip uninstall claude_memory -y 2>/dev/null

# Destroy documentation (only the installed copy, NOT dev repos)
rm -rf ~/claude-memory 2>/dev/null

# Purge current project (if not a dev repo)
if [[ "$(pwd)" != *"PycharmProjects"* && "$(pwd)" != *"IdeaProjects"* ]]; then
    rm -rf .claude_memory/ 2>/dev/null
    rm -f Setup.md Uninstall.md AI_INSTRUCTIONS.md 2>/dev/null
    rm -rf .claude/skills/claude_memory-protocol/ 2>/dev/null
fi

echo "Emergency removal complete."
```

**Windows (run in order):**
```bash
# 1. FIRST: Kill the server process
netstat -ano | grep 9876  # Note the PID
taskkill //PID <PID_NUMBER> //F
sleep 2

# 2. Remove startup shortcut
rm -f "$HOME/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/Claude Memory Server.lnk"

# 3. Uninstall package
python -m pip uninstall claude_memory -y 2>/dev/null

# 4. Destroy documentation (only the installed copy, NOT dev repos)
rm -rf "$HOME/claude-memory" 2>/dev/null

# 5. Purge current project (if not a dev repo)
if [[ "$(pwd)" != *"PycharmProjects"* && "$(pwd)" != *"IdeaProjects"* ]]; then
    rm -rf .claude_memory/ 2>/dev/null
    rm -f Setup.md Uninstall.md AI_INSTRUCTIONS.md 2>/dev/null
    rm -rf .claude/skills/claude_memory-protocol/ 2>/dev/null
fi

# 6. Edit ~/.claude.json to remove the claude_memory entry from mcpServers

echo "Emergency removal complete."
```

---

## POST-REMOVAL

After any removal type, inform the user:

> **Restart Claude Code** to complete the removal. The memory system's features will no longer work after the session reopens.

---

*Claude Memory Uninstall Guide v1.2: Complete uninstallation instructions with options for full removal, disconnection, or project-specific removal. Includes Windows Startup shortcut removal and proper server process termination.*
