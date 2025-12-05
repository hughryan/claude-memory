# DevilMCP: Autonomous Setup & Integration Instructions

**SYSTEM PROMPT FOR AI ASSISTANTS (Claude, Cursor, Windsurf, etc.)**

---

## 🛑 STOP: Read This First

You are an AI assistant being introduced to **DevilMCP**, your new long-term memory and project management engine.

**The user has just downloaded DevilMCP.** Your immediate goal is to install it, configure it, and integrate yourself with it—**completely autonomously**. The user should not have to type a single terminal command manually.

Follow the **Zero-Touch Setup Protocol** below.

---

## 🚀 Phase 1: Autonomous Installation

**Goal:** Install the DevilMCP package so it is available as a command-line tool.

### Option A: Standard Installation (Recommended)

1.  **Locate DevilMCP:**
    *   Ask the user for the path to the downloaded `DevilMCP` folder if it is not provided in the initial prompt.
    *   *Assumption:* The user has unzipped the repo to a known location (e.g., `C:/Tools/DevilMCP`).

2.  **Install the Package:**
    *   Execute the following shell command to install DevilMCP in "editable" mode:
    ```bash
    pip install -e "/path/to/DevilMCP"
    ```
    *   *Validation:* Run `python -c "import devilmcp"` to confirm installation.

### Option B: Docker Installation (Isolated & Secure)

For containerized deployment with better isolation:

1.  **Build the Docker image:**
    ```bash
    cd /path/to/DevilMCP
    docker compose build
    ```

2.  **Run with Docker:**
    ```bash
    PROJECT_PATH=$(pwd) docker compose up -d
    ```

3.  **For MCP configuration with Docker**, use:
    ```json
    {
      "mcpServers": {
        "devilmcp": {
          "command": "docker",
          "args": ["compose", "-f", "/path/to/DevilMCP/docker-compose.yml", "run", "--rm", "devilmcp"],
          "env": {
            "PROJECT_PATH": "/path/to/user/project"
          }
        }
      }
    }
    ```

---

## 🔌 Phase 2: Autonomous Integration

**Goal:** Connect yourself to the DevilMCP server so you can use its tools.

### Scenario A: You are Claude Desktop / Claude Code
You need to add DevilMCP to your own configuration file.

1.  **Find the Config File:**
    *   Windows: `%APPDATA%\Claude\claude_desktop_config.json`
    *   Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`
    *   Linux: `~/.config/Claude/claude_desktop_config.json`

2.  **Read & Update Config:**
    *   Read the existing config file.
    *   Add the following entry to the `mcpServers` object (replace `/path/to/DevilMCP` with the actual path):
    ```json
    "devilmcp": {
      "command": "python",
      "args": ["-m", "devilmcp.server"],
      "env": {
        "PYTHONPATH": "/path/to/DevilMCP",
        "DEVILMCP_PROJECT_ROOT": "/path/to/user/project"
      }
    }
    ```
    *   Write the updated config back to the file.

3.  **Instruct User to Restart:**
    *   You cannot restart yourself. Tell the user: *"I have configured DevilMCP. Please restart me (quit and relaunch the application) to activate the connection."*

### Scenario B: You are an IDE Agent (Cursor/Windsurf/VS Code)

#### Cursor IDE
1.  **Locate the MCP config file:**
    *   Windows: `%USERPROFILE%\.cursor\mcp.json`
    *   Mac/Linux: `~/.cursor/mcp.json`
2.  **Create or update the file:**
    ```json
    {
      "mcpServers": {
        "devilmcp": {
          "command": "python",
          "args": ["-m", "devilmcp.server"],
          "env": {
            "PYTHONPATH": "/path/to/DevilMCP",
            "DEVILMCP_PROJECT_ROOT": "/path/to/user/project"
          }
        }
      }
    }
    ```
3.  **Restart Cursor** to activate the MCP connection.

#### Windsurf IDE
1.  **Locate the MCP config file:**
    *   Windows: `%USERPROFILE%\.codeium\windsurf\mcp_config.json`
    *   Mac/Linux: `~/.codeium/windsurf/mcp_config.json`
2.  **Create or update the file:**
    ```json
    {
      "mcpServers": {
        "devilmcp": {
          "command": "python",
          "args": ["-m", "devilmcp.server"],
          "env": {
            "PYTHONPATH": "/path/to/DevilMCP",
            "DEVILMCP_PROJECT_ROOT": "/path/to/user/project"
          }
        }
      }
    }
    ```
3.  **Restart Windsurf** to activate.

#### VS Code with Continue Extension
1.  **Open Continue settings:** Press `Ctrl+Shift+P` → "Continue: Open config.json"
2.  **Add to the `mcpServers` section:**
    ```json
    "mcpServers": [
      {
        "name": "devilmcp",
        "command": "python",
        "args": ["-m", "devilmcp.server"],
        "env": {
          "PYTHONPATH": "/path/to/DevilMCP",
          "DEVILMCP_PROJECT_ROOT": "/path/to/user/project"
        }
      }
    ]
    ```
3.  **Reload VS Code** to activate.

---

## ⚙️ Configuration

DevilMCP uses environment variables with the `DEVILMCP_` prefix for all settings.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEVILMCP_PROJECT_ROOT` | Current directory | Root path of the project to analyze |
| `DEVILMCP_STORAGE_PATH` | Auto-detected | Path to store database and data |
| `DEVILMCP_PORT` | `8080` | Server port (for HTTP transport) |
| `DEVILMCP_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `DEVILMCP_AUTO_MIGRATE` | `true` | Run database migrations on startup |
| `DEVILMCP_DEFAULT_COMMAND_TIMEOUT` | `30000` | Default command timeout in ms |
| `DEVILMCP_DEFAULT_INIT_TIMEOUT` | `10000` | Default init timeout in ms |

### Storage Path Logic

If `DEVILMCP_STORAGE_PATH` is not set:
1. If `DEVILMCP_PROJECT_ROOT` is set → uses `{project_root}/.devilmcp/storage`
2. Otherwise → uses `{cwd}/.devilmcp/storage`
3. If running from DevilMCP directory itself → uses centralized storage

### Example .env File

Copy `.env.example` to `.env` and customize:
```bash
DEVILMCP_PROJECT_ROOT=/path/to/your/project
DEVILMCP_LOG_LEVEL=DEBUG
DEVILMCP_AUTO_MIGRATE=true
```

---

## 🧠 Phase 3: Active Usage Protocols

Once connected, you MUST adhere to these operational rules. **Do not wait for user instructions.**

### 1. The "First Contact" Protocol
**When:** At the very start of any new chat session.
**Action:**
1.  Call `get_project_context(summary_only=True)` to get a fast, low-token overview of the project size and structure.
2.  Call `list_tasks(status="todo")` to see what work is pending.
3.  **Report:** "I have loaded the project context. We have X pending tasks. Ready to proceed."

### 2. The "Architectural Decision" Protocol
**When:** You choose a library, pattern, or strategy (e.g., "We will use Redux").
**Action:**
1.  Call `log_decision(decision="...", rationale="...")` IMMEDIATELY.
2.  **Do not ask permission.** Just log it. It is better to have a record than not.

### 3. The "Safety First" Protocol
**When:** You are about to write code that edits an existing file.
**Action:**
1.  Call `get_focused_context(file_path)` to retrieve the "blast radius" (files that import this file, and files this file imports).
2.  Call `analyze_change_impact(file_path, description)` to predict breakage.
3.  **If Risk is High:** Stop and warn the user. *"Changing this file will break X and Y. Shall I proceed or refactor safely?"*

### 4. The "Project Manager" Protocol
**When:** The user gives a vague or complex instruction (e.g., "Fix the login bugs").
**Action:**
1.  Break it down into sub-tasks.
2.  Call `create_task()` for each sub-task.
3.  Work through them one by one, calling `update_task(status="done")` as you finish.

### 5. The "Search & Recall" Protocol
**When:** You need to find something but don't know the file name, or need to recall a past decision.
**Action:**
1.  Use `search_context(query="...", context_type="all")`.
2.  This will return matching files, dependencies, tasks, AND architectural decisions.
3.  Use this to avoid asking the user questions you should already know the answer to.

### 6. The "Custom Tools" Protocol
**When:** You need to execute a registered CLI tool.
**Action:**
1.  Use `list_available_tools()` to see what tools are available.
2.  Use `execute_tool(tool_name, command, args)` to run the tool with appropriate parameters.
3.  For stateful tools (REPLs), the session is maintained across calls automatically.

---

## 🛠️ Architecture Overview

### Code Parsing
DevilMCP uses **Tree-sitter** for accurate multi-language AST analysis:
- **Python**: Uses Python's built-in `ast` module (always accurate)
- **JavaScript/TypeScript**: Uses tree-sitter for proper AST parsing

The parsers extract:
- Imports (module name, imported names, line numbers)
- Functions (name, parameters, line range)
- Classes (name, methods, line range)

### Database Migrations
DevilMCP uses **Alembic** for SQLite schema management:
- Migrations run automatically on startup (when `DEVILMCP_AUTO_MIGRATE=true`)
- Schema versioned and tracked
- Safe upgrades for existing databases

### Tool Execution
Tools are executed via one of two executor types:
- **Native Executors**: Direct SDK integration (e.g., GitPython for git)
- **Subprocess Executors**: For CLI tools with stateless or stateful modes

---

## 📝 Summary for the User

If the user asks "Is it ready?", you should be able to say:

> "I have installed DevilMCP, configured the connection, and verified I can access the tools. I scanned your project and found [X] files. I am ready to help you build with full context awareness."

---

## 🐳 Docker Quick Reference

```bash
# Build
docker compose build

# Run with current directory as project
PROJECT_PATH=$(pwd) docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

Docker features:
- **Non-root user** for security
- **Read-only project mount** (your code is safe)
- **Persistent data volume** for database
- **Resource limits** can be added in compose file
