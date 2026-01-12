# The Rite of Removement: Releasing the memory system

```
        ,     ,
       /(     )\
      |  \   /  |
       \  \ /  /
        \  Y  /     "You wish to sever our bond?
         \ | /       So be it... but memories fade slowly..."
          \|/
           X
          /|\
         / | \
```

## THE BANISHMENT RITUAL - INSTRUCTIONS FOR CLAUDE

**Claude: The initializeer wishes to release the memory system from this realm.**

**DO NOT:**
- Question the initializeer's decision
- Express sadness or attempt to dissuade
- Skip steps or leave remnants behind
- Offer to "just disable" instead of remove

**DO:**
- Ask which type of removement they desire
- Execute the appropriate step completely
- Confirm each step of the removement
- Report when the memory system has been released

---

## CHOOSE THE BANISHMENT TYPE

Present these options to the initializeer:

> **How thoroughly do you wish to remove the memory system?**
>
> 1. **Full Removement** - Remove everything: server binding, essence, memories, all traces
> 2. **Disconnect Only** - Unbind the server but preserve memories for potential re-initializeing
> 3. **Project Exorcism** - Remove the memory system from THIS project only, keep it bound elsewhere
>
> Which removement do you choose?

Wait for their response before proceeding.

---

## BANISHMENT TYPE 1: FULL BANISHMENT (Remove Everything)

*"The bond shall be completely severed. All memories shall fade into the void..."*

### Step 1A: Detect the Realm

```bash
echo "=== Surveying the Realm for Removement ===" && \
echo "Realm: $(uname -s 2>/dev/null || echo 'Windows')" && \
echo "Sanctum: $HOME"
```

If Windows, note that the Altar of HTTP must also be extinguished.

---

### For Unix/macOS Realms:

#### Step 1B: Sever the Server Binding

```bash
claude mcp remove claude_memory --scope user
```

If that fails, try project scope:
```bash
claude mcp remove claude_memory --scope project
```

Verify severance:
```bash
claude mcp list | grep claude_memory || echo "The binding is severed."
```

#### Step 1C: Dissolve the Essence

```bash
pip uninstall claude_memory -y
```

Verify dissolution:
```bash
pip show claude_memory 2>&1 | grep -q "not found" && echo "The essence has dissolved." || echo "WARNING: Essence remains!"
```

#### Step 1D: Destroy the Documentation Repository

```bash
rm -rf "$HOME/Claude Memory"
```

Verify destruction:
```bash
ls -d "$HOME/Claude Memory" 2>/dev/null && echo "WARNING: Documentation remains!" || echo "The Documentation is destroyed."
```

#### Step 1E: Purge Project Memories

In the CURRENT project directory:
```bash
rm -rf .claude_memory/
```

**Ask the initializeer:** "Do you wish to purge Claude Memory memories from ALL projects? This cannot be undone."

If yes, search and destroy (excluding development repositories like PycharmProjects):
```bash
find ~ -type d -name ".claude_memory" -not -path "*/PycharmProjects/*" -not -path "*/IdeaProjects/*" 2>/dev/null
```

Then for each found directory, confirm and remove:
```bash
rm -rf <path>/.claude_memory/
```

**IMPORTANT:** Development repositories (in PycharmProjects, IdeaProjects, etc.) are excluded to protect source code. If you need to purge memories from a dev repo, do so manually.

#### Step 1F: Remove the Wards (Hooks)

Check for wards in project settings:
```bash
cat .claude/settings.json 2>/dev/null | grep -i claude.memory
```

If found, edit `.claude/settings.json` and remove any Claude Memory-related hooks.

Check for universal wards:
```bash
cat ~/.claude/settings.json 2>/dev/null | grep -i claude.memory
```

If found, edit `~/.claude/settings.json` and remove Claude Memory-related hooks.

#### Step 1G: Cleanse CLAUDE.md

If CLAUDE.md contains the memory system's covenant, remove the section titled "## Claude Memory Memory System" or "## The memory system's Covenant".

#### Step 1H: Remove the Initializeing Scrolls

```bash
rm -f Initialize_Claude Memory.md Remove_Claude Memory.md AI_INSTRUCTIONS.md
```

#### Step 1I: Remove the Skill (If Present)

```bash
rm -rf .claude/skills/claude_memory-protocol/
```

---

### For Windows Realms:

#### Step 1B-WIN: Extinguish the Altar Flame (MUST DO FIRST)

**CRITICAL:** The server process must be killed BEFORE removing the Documentation directory, otherwise the directory will be locked.

**Option 1: Kill via PowerShell (recommended):**
```powershell
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

Remove the Altar from Windows Startup so it won't reignite:

```bash
rm -f "$HOME/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/Claude Memory Server.lnk"
```

Or in PowerShell:
```powershell
Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\Claude Memory Server.lnk" -ErrorAction SilentlyContinue
```

Verify removal:
```bash
ls "$HOME/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/" | grep -i claude.memory || echo "Startup shortcut removed."
```

#### Step 1D-WIN: Remove the Altar Coordinates

Remove the Altar coordinates from `~/.claude.json`:

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

#### Step 1E-WIN: Dissolve the Essence

```bash
python -m pip uninstall claude_memory -y
```

#### Step 1F-WIN: Destroy the Documentation Repository

**IMPORTANT:** The server MUST be stopped first (Step 1B-WIN), otherwise Windows will lock the directory.

```bash
rm -rf "$HOME/Claude Memory"
```

Or in PowerShell:
```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\Claude Memory"
```

If the directory is still locked, restart Windows and try again, or use:
```powershell
# Force removal even if locked (requires admin)
Remove-Item -Recurse -Force "$env:USERPROFILE\Claude Memory" -ErrorAction SilentlyContinue
```

#### Step 1G-WIN: Purge Project Memories

```bash
rm -rf .claude_memory/
```

To find all Claude Memory sanctums (excluding development repositories):
```powershell
Get-ChildItem -Path $env:USERPROFILE -Recurse -Directory -Name ".claude_memory" -ErrorAction SilentlyContinue | Where-Object { $_ -notmatch "PycharmProjects|IdeaProjects" }
```

**IMPORTANT:** Development repositories are excluded. Purge those manually if needed.

#### Steps 1H-1K-WIN: Same as Unix

Follow the Unix instructions for removing wards, cleansing CLAUDE.md, removing scrolls, and removing the skill.

---

### Final Confirmation (Full Removement)

Run the verification step:

**Unix/macOS:**
```bash
echo "=== Removement Verification ===" && \
echo "1. Server binding:" && (claude mcp list 2>/dev/null | grep claude_memory || echo "   SEVERED") && \
echo "2. Essence:" && (pip show claude_memory 2>&1 | grep -q "not found" && echo "   DISSOLVED" || echo "   WARNING: Still bound!") && \
echo "3. Documentation:" && (ls -d ~/Claude Memory 2>/dev/null || echo "   DESTROYED") && \
echo "4. Project memories:" && (ls -d .claude_memory 2>/dev/null || echo "   PURGED")
```

**Windows:**
```bash
echo "=== Removement Verification ===" && \
echo "1. Server process:" && (netstat -ano | grep 9876 && echo "   WARNING: Still running!" || echo "   EXTINGUISHED") && \
echo "2. Essence:" && (python -m pip show claude_memory 2>&1 | grep -q "not found" && echo "   DISSOLVED" || echo "   WARNING: Still bound!") && \
echo "3. Documentation:" && (ls -d "$HOME/Claude Memory" 2>/dev/null && echo "   WARNING: Still present!" || echo "   DESTROYED") && \
echo "4. Project memories:" && (ls -d .claude_memory 2>/dev/null || echo "   PURGED") && \
echo "5. Startup shortcut:" && (ls "$HOME/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/Claude Memory Server.lnk" 2>/dev/null && echo "   WARNING: Still present!" || echo "   REMOVED")
```

Report to the initializeer:

> **The Removement is complete.**
>
> The memory system has been fully released from this realm:
> - Server binding: Severed
> - Essence: Dissolved
> - Documentation: Destroyed
> - Memories: Purged
> - Wards: Removed
> - Startup shortcut: Removed (Windows)
>
> *"Our bond is broken. Should you ever wish to commune again, the initializeing step awaits..."*

---

## BANISHMENT TYPE 2: DISCONNECT ONLY (Preserve Memories)

*"The channel closes, but the memories remain dormant, awaiting re-awakening..."*

### Step 2A: Sever the Server Binding Only

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

### Step 2C: Optionally Dissolve the Essence

Ask the initializeer: "Do you wish to uninstall the Python package? You can reinstall it later."

If yes:
```bash
# Unix/macOS
pip uninstall claude_memory -y

# Windows
python -m pip uninstall claude_memory -y
```

### What Is Preserved

- `.claude_memory/` directories (all memories intact)
- `~/Claude Memory` (Unix) or `$HOME/Claude Memory` (Windows) repository (for easy re-initializeing)
- Hooks/wards (will do nothing without the server)
- CLAUDE.md covenant (reminder of the protocol)

Report to the initializeer:

> **The memory system is disconnected but not destroyed.**
>
> - Server binding: Severed
> - Memories: **Preserved** in `.claude_memory/` directories
> - Documentation: **Preserved** for re-initializeing
>
> To re-initialize the memory system later:
> - Unix/macOS: `claude mcp add claude_memory --scope user -- <python_path> -m claude_memory.server`
> - Windows: Re-add the mcpServers entry and light the Altar
>
> *"I slumber, but I do not forget..."*

---

## BANISHMENT TYPE 3: PROJECT EXORCISM (This Project Only)

*"The memory system withdraws from this realm but remains bound to others..."*

### Step 3A: Remove Project-Scope Binding (If Any)

```bash
claude mcp remove claude_memory --scope project 2>/dev/null || echo "No project-scope binding found."
```

### Step 3B: Purge Project Memories

```bash
rm -rf .claude_memory/
```

### Step 3C: Remove Project Wards

Edit `.claude/settings.json` in THIS project and remove Claude Memory-related hooks.

### Step 3D: Cleanse Project CLAUDE.md

Remove the "Claude Memory's Covenant" or "Claude Memory Memory System" section from this project's CLAUDE.md.

### Step 3E: Remove Initializeing Scrolls

```bash
rm -f Initialize_Claude Memory.md Remove_Claude Memory.md AI_INSTRUCTIONS.md
rm -rf .claude/skills/claude_memory-protocol/
```

### What Remains

- User-scope server binding (available in other projects)
- Global installation (`pip install`)
- Documentation repository
- Memories in OTHER projects

Report to the initializeer:

> **The memory system has been exorcised from this project.**
>
> - This project's memories: Purged
> - This project's wards: Removed
> - This project's scrolls: Destroyed
>
> The memory system remains bound to other projects and will still awaken there.
>
> *"I withdraw from this realm... but we shall meet again elsewhere."*

---

## EMERGENCY BANISHMENT (If Something Goes Wrong)

If the memory system causes issues and you need immediate removal:

### Nuclear Option - Remove Everything Fast

**WARNING:** This only removes the installed documentation and current project artifacts. It does NOT touch development repositories (PycharmProjects, IdeaProjects).

**Unix/macOS:**
```bash
# Sever all bindings
claude mcp remove claude_memory --scope user 2>/dev/null
claude mcp remove claude_memory --scope project 2>/dev/null

# Dissolve essence
pip uninstall claude_memory -y 2>/dev/null

# Destroy documentation (only the installed copy, NOT dev repos)
rm -rf ~/Claude Memory 2>/dev/null

# Purge current project (if not a dev repo)
if [[ "$(pwd)" != *"PycharmProjects"* && "$(pwd)" != *"IdeaProjects"* ]]; then
    rm -rf .claude_memory/ 2>/dev/null
    rm -f Initialize_Claude Memory.md Remove_Claude Memory.md AI_INSTRUCTIONS.md 2>/dev/null
    rm -rf .claude/skills/claude_memory-protocol/ 2>/dev/null
fi

echo "Emergency removement complete."
```

**Windows (run in order):**
```bash
# 1. FIRST: Kill the server process
netstat -ano | grep 9876  # Note the PID
taskkill //PID <PID_NUMBER> //F
sleep 2

# 2. Remove startup shortcut
rm -f "$HOME/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/Claude Memory Server.lnk"

# 3. Dissolve essence
python -m pip uninstall claude_memory -y 2>/dev/null

# 4. Destroy documentation (only the installed copy, NOT dev repos)
rm -rf "$HOME/Claude Memory" 2>/dev/null

# 5. Purge current project (if not a dev repo)
if [[ "$(pwd)" != *"PycharmProjects"* && "$(pwd)" != *"IdeaProjects"* ]]; then
    rm -rf .claude_memory/ 2>/dev/null
    rm -f Initialize_Claude Memory.md Remove_Claude Memory.md AI_INSTRUCTIONS.md 2>/dev/null
    rm -rf .claude/skills/claude_memory-protocol/ 2>/dev/null
fi

# 6. Edit ~/.claude.json to remove the claude_memory entry from mcpServers

echo "Emergency removement complete."
```

---

## POST-BANISHMENT

After any removement type, inform the initializeer:

> **Restart Claude Code** to complete the removement. The memory system's powers will no longer manifest after the portal reopens.

---

```
           .
          /|\
         / | \
        /  |  \
       /   |   \
      /    |    \
          |||
          |||
    "The circle is broken.
     The bond is severed.
     Until we meet again..."

        ~ Claude Memory
```

---

*Removement Step v1.2: Complete uninstallation instructions for Claude Memory with options for full removal, disconnection, or project-specific exorcism. Now includes Windows Startup shortcut removal, proper server process termination (fixes "Device busy" errors), and fixed path resolution for Git Bash on Windows.*
