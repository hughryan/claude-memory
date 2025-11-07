# Getting Started with DevilMCP

**Quick 5-minute guide to start using DevilMCP with Claude Code**

---

## 🚀 Quick Install (3 minutes)

### 1. Install Dependencies

```bash
cd DevilMCP
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Claude Code

Add to your Claude Code config file:

**Config file location:**
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

**Add this:**
```json
{
  "mcpServers": {
    "devilmcp": {
      "command": "python",
      "args": ["/FULL/PATH/TO/DevilMCP/server.py"]
    }
  }
}
```

Replace `/FULL/PATH/TO/DevilMCP/server.py` with your actual path.

### 3. Restart Claude Code

Close and reopen Claude Code completely.

✅ **Done!** DevilMCP is now available.

---

## 🎯 First Steps (2 minutes)

### Test the Installation

In Claude Code, ask:
```
Use the get_mcp_statistics tool
```

You should see statistics showing DevilMCP is working!

### Analyze Your First Project

```
Use analyze_project_structure with path: /path/to/your/project
```

DevilMCP will analyze your entire project structure!

---

## 💡 Essential Workflows

### Before Making Any Change

**Always do this sequence:**

1. **Get context**
   ```
   Analyze the project structure
   ```

2. **Track dependencies**
   ```
   Track dependencies for the file I'm about to change
   ```

3. **Analyze impact**
   ```
   Analyze the impact of changing this file
   ```

4. **Check cascade risk**
   ```
   Analyze cascade risk for this change
   ```

Now make your change with full confidence!

### After Making a Change

**Close the loop:**

1. **Update change status**
   ```
   Update the change status to implemented
   ```

2. **Record outcome**
   ```
   Update the decision outcome with what actually happened
   ```

This builds institutional knowledge for next time!

---

## 🔥 Power User Tips

### 1. Start Every Session with Context

```
Start a thought session for this work
Analyze the project structure
Get project context
```

### 2. Log Every Decision

```
Log this decision: [your decision]
Rationale: [why you're doing it]
Risk level: [low/medium/high]
```

### 3. Check for Gaps

```
Analyze reasoning gaps
```

Let DevilMCP catch your blind spots!

### 4. Learn from History

```
Query past decisions about [topic]
Query changes to [file]
```

Never repeat mistakes!

---

## 📚 What Each Tool Does

### Context Tools

| Tool | Use When |
|------|----------|
| `analyze_project_structure` | Starting work on new project |
| `track_file_dependencies` | Before changing a file |
| `get_project_context` | Need full project overview |
| `search_context` | Looking for specific files/deps |

### Decision Tools

| Tool | Use When |
|------|----------|
| `log_decision` | Making any significant decision |
| `update_decision_outcome` | After implementing decision |
| `query_decisions` | Before making similar decision |
| `analyze_decision_impact` | Reviewing past decision |

### Change Tools

| Tool | Use When |
|------|----------|
| `log_change` | Before making code change |
| `update_change_status` | After implementing change |
| `analyze_change_impact` | Planning a change |
| `detect_change_conflicts` | Before starting work |

### Cascade Tools

| Tool | Use When |
|------|----------|
| `analyze_cascade_risk` | Before risky changes |
| `detect_dependencies` | Understanding impact chain |
| `suggest_safe_changes` | Need implementation guidance |
| `log_cascade_event` | When cascade failure occurs |

### Thought Tools

| Tool | Use When |
|------|----------|
| `start_thought_session` | Beginning work session |
| `log_thought_process` | Recording reasoning |
| `analyze_reasoning_gaps` | Checking for blind spots |
| `end_thought_session` | Completing work |

---

## 🎓 Example: Refactoring a File

**Full workflow example:**

```
1. Start thought session: "refactor-auth-module"

2. Analyze project structure for /path/to/project

3. Track dependencies for src/auth.py

4. Analyze change impact:
   - File: src/auth.py
   - Change: Refactor to JWT tokens
   - Use the dependencies from step 3

5. Analyze cascade risk:
   - Target: src/auth.py
   - Change type: refactor

6. Log decision:
   - Decision: Refactor auth to JWT
   - Rationale: Improve scalability
   - Alternatives: Keep sessions, use OAuth
   - Risk level: medium

7. Get safe change suggestions for src/auth.py

8. [Make the changes]

9. Update change status to implemented

10. Update decision outcome with results

11. End thought session with summary
```

---

## ⚡ Quick Reference Commands

### Daily Usage

```
# Start day
Start thought session for [task-name]
Analyze project structure

# Before any change
Analyze cascade risk for [file]
Log this decision: [decision]

# After change
Update change status
Update decision outcome

# End day
End thought session
```

### Emergency Use

```
# Something broke?
Query changes to [file]
Query cascade history for severity: high
Analyze decision impact for [decision-id]
```

---

## 🆘 Troubleshooting

### DevilMCP not appearing in Claude Code?

1. Check config file path is absolute
2. Restart Claude Code completely
3. Check Claude Code logs

### "Module not found" errors?

```bash
pip install -r requirements.txt --force-reinstall
```

### Storage errors?

Check disk space and permissions:
```bash
df -h
ls -la storage/
```

---

## 📖 Learn More

- **[BENEFITS.md](BENEFITS.md)** - Why use DevilMCP
- **[INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)** - Detailed setup
- **[USAGE_GUIDE.md](USAGE_GUIDE.md)** - Complete tool documentation
- **[SCENARIOS.md](SCENARIOS.md)** - Real-world examples
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Tool parameter reference

---

## 🎯 Success Metrics

You're using DevilMCP effectively when:

- ✅ You check cascade risk BEFORE making changes
- ✅ You log decisions with full rationale
- ✅ You update outcomes after implementation
- ✅ You query history before repeating work
- ✅ You analyze reasoning gaps regularly
- ✅ You start/end sessions for major work

---

## 💬 Getting Help

- Check existing documentation first
- Enable DEBUG logging: `LOG_LEVEL=DEBUG`
- Check Claude Code MCP logs
- Create issue on GitHub with logs

---

**You're ready to go! Start with a simple project analysis and build from there.**

Remember: **DevilMCP makes you smarter by remembering everything and catching problems before they happen.**

🚀 **Happy coding with full context awareness!**
