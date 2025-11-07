# DevilMCP Installation Guide

Complete step-by-step guide to installing and configuring DevilMCP for use with Claude Code and other MCP clients.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation Methods](#installation-methods)
3. [Configuration](#configuration)
4. [Testing the Installation](#testing-the-installation)
5. [Troubleshooting](#troubleshooting)
6. [Advanced Configuration](#advanced-configuration)

---

## Prerequisites

### Required

- **Python 3.8 or higher**
  ```bash
  python --version
  # Should show: Python 3.8.x or higher
  ```

- **pip** (Python package manager)
  ```bash
  pip --version
  # Should show pip version info
  ```

### Recommended

- **Virtual environment tool** (venv, virtualenv, or conda)
- **Git** (for cloning the repository)
- **Claude Code** or another MCP-compatible client

### System Requirements

- **OS**: Windows 10+, macOS 10.15+, or Linux (any modern distribution)
- **RAM**: Minimum 512MB available
- **Disk Space**: ~100MB for installation + storage for data
- **Network**: Not required (runs locally)

---

## Installation Methods

### Method 1: Standard Installation (Recommended)

#### Step 1: Clone or Download Repository

**Option A: Using Git**
```bash
git clone https://github.com/yourusername/DevilMCP.git
cd DevilMCP
```

**Option B: Manual Download**
1. Download the repository as ZIP
2. Extract to desired location
3. Open terminal/command prompt in the extracted directory

#### Step 2: Create Virtual Environment

**On Windows:**
```powershell
python -m venv venv
.\venv\Scripts\activate
```

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

#### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed fastmcp-0.2.0 requests-2.31.0 python-dotenv-1.0.0 networkx-3.2 ...
```

#### Step 4: Verify Installation

```bash
python server.py
```

You should see:
```
=================================================================
                     DevilMCP Server
=================================================================
  An extremely powerful MCP server for AI agents that:
  * Maintains full project context
  * Tracks decisions and their outcomes
  * Analyzes change impacts and cascade risks
  * Manages thought processes and reasoning
  * Prevents short-sighted development decisions
=================================================================

Starting DevilMCP server on port 8080
Storage path: /path/to/DevilMCP/storage/centralized
```

Press `Ctrl+C` to stop the server. Installation complete!

---

### Method 2: Development Installation

For developers who want to modify DevilMCP:

```bash
# Clone repository
git clone https://github.com/yourusername/DevilMCP.git
cd DevilMCP

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Now you can run from anywhere:
devilmcp
```

---

### Method 3: System-Wide Installation

**Not recommended** unless you understand Python package management:

```bash
cd DevilMCP
pip install .

# Run from anywhere:
devilmcp
```

---

## Configuration

### For Claude Code

DevilMCP works seamlessly with Claude Code. Follow these steps:

#### Step 1: Locate Your Claude Code Config File

**File locations:**
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

**To open:**

**Windows:**
```powershell
# Open in Notepad
notepad "%APPDATA%\Claude\claude_desktop_config.json"

# Or navigate there
explorer "%APPDATA%\Claude"
```

**macOS:**
```bash
# Open in default editor
open ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Or use TextEdit
open -a TextEdit ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Linux:**
```bash
# Open in default editor
xdg-open ~/.config/Claude/claude_desktop_config.json

# Or use nano
nano ~/.config/Claude/claude_desktop_config.json
```

#### Step 2: Add DevilMCP Configuration

**If file is empty or doesn't exist, add:**
```json
{
  "mcpServers": {
    "devilmcp": {
      "command": "python",
      "args": ["/absolute/path/to/DevilMCP/server.py"],
      "env": {
        "LOG_LEVEL": "INFO",
        "MAX_CONTEXT_DEPTH": "10"
      }
    }
  }
}
```

**If file already has mcpServers, add devilmcp to it:**
```json
{
  "mcpServers": {
    "existing-server": {
      ...
    },
    "devilmcp": {
      "command": "python",
      "args": ["/absolute/path/to/DevilMCP/server.py"],
      "env": {
        "LOG_LEVEL": "INFO",
        "MAX_CONTEXT_DEPTH": "10"
      }
    }
  }
}
```

#### Step 3: Get Absolute Path to server.py

**Windows:**
```powershell
cd C:\path\to\DevilMCP
echo %CD%\server.py
# Copy this path
```

**macOS/Linux:**
```bash
cd /path/to/DevilMCP
echo "$(pwd)/server.py"
# Copy this path
```

**Replace** `/absolute/path/to/DevilMCP/server.py` in the config with your actual path.

**Example paths:**
- Windows: `C:\\Users\\YourName\\DevilMCP\\server.py`
- macOS: `/Users/YourName/DevilMCP/server.py`
- Linux: `/home/username/DevilMCP/server.py`

⚠️ **Important**: On Windows, use double backslashes (`\\`) or forward slashes (`/`) in the path.

#### Step 4: Use Python from Virtual Environment (Recommended)

If you created a virtual environment, use the Python from there:

**Windows:**
```json
{
  "mcpServers": {
    "devilmcp": {
      "command": "C:\\path\\to\\DevilMCP\\venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\DevilMCP\\server.py"],
      "env": {
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**macOS/Linux:**
```json
{
  "mcpServers": {
    "devilmcp": {
      "command": "/path/to/DevilMCP/venv/bin/python",
      "args": ["/path/to/DevilMCP/server.py"],
      "env": {
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

#### Step 5: Restart Claude Code

Close and reopen Claude Code completely for the changes to take effect.

---

### Environment Variables Configuration

Create a `.env` file in the DevilMCP directory for custom configuration:

```bash
cp .env.example .env
```

Edit `.env`:
```bash
# Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Storage path (leave empty for auto-detection)
STORAGE_PATH=

# Maximum dependency traversal depth
MAX_CONTEXT_DEPTH=10

# Project root (optional - auto-detected)
# PROJECT_ROOT=/path/to/your/project
```

**Configuration options:**

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Controls logging verbosity |
| `STORAGE_PATH` | Auto | Where to store data files |
| `MAX_CONTEXT_DEPTH` | `10` | Max depth for dependency traversal |
| `PROJECT_ROOT` | Auto | Project root directory |

---

## Testing the Installation

### Test 1: Standalone Server

```bash
cd DevilMCP
source venv/bin/activate  # On Windows: venv\Scripts\activate
python server.py
```

Should show the banner and start successfully. Press `Ctrl+C` to stop.

### Test 2: Python Import Test

```bash
python -c "import server; print('Import successful')"
```

Should print: `Import successful`

### Test 3: Dependency Check

```bash
python -c "
import fastmcp
import networkx
import astroid
print('All dependencies installed correctly')
"
```

### Test 4: Claude Code Integration

1. Open Claude Code
2. Look for the MCP icon (hammer/wrench) in the UI
3. You should see "devilmcp" listed
4. Try using a DevilMCP tool:
   ```
   Use the get_mcp_statistics tool
   ```

Expected response: Statistics showing the server is working.

---

## Troubleshooting

### Issue: "Module not found" errors

**Problem:** Dependencies not installed correctly.

**Solution:**
```bash
# Activate virtual environment first
source venv/bin/activate  # Windows: venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

---

### Issue: "Permission denied" on Windows

**Problem:** Windows execution policy blocks Python scripts.

**Solution:**
```powershell
# Run as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Or use full Python path
python.exe server.py
```

---

### Issue: Claude Code doesn't see DevilMCP

**Checklist:**
1. ✅ Is the path in `claude_desktop_config.json` absolute?
2. ✅ Does the path use correct slashes (Windows: `\\` or `/`)?
3. ✅ Did you restart Claude Code completely?
4. ✅ Is Python accessible from that path?

**Test the command manually:**
```bash
# Copy the exact command and args from your config
python /absolute/path/to/server.py
```

If this doesn't work, the config won't work either.

---

### Issue: "NetworkX not available" warning

**Problem:** Optional dependency not installed.

**Impact:** Graph analysis features will be limited but server still works.

**Solution (optional):**
```bash
pip install networkx
```

---

### Issue: Server starts then immediately exits

**Problem:** Usually a configuration or import error.

**Solution:**
1. Check logs in the terminal
2. Try running with debug logging:
   ```bash
   LOG_LEVEL=DEBUG python server.py
   ```
3. Check for syntax errors:
   ```bash
   python -m py_compile server.py
   ```

---

### Issue: Storage path errors

**Problem:** Can't create or write to storage directory.

**Solution:**
1. Check disk space:
   ```bash
   df -h .  # Linux/Mac
   ```

2. Check permissions:
   ```bash
   ls -la storage/
   ```

3. Specify explicit storage path:
   ```bash
   # In .env file:
   STORAGE_PATH=/path/with/write/access
   ```

---

## Advanced Configuration

### Multi-Project Setup

DevilMCP automatically isolates data per project. Each project gets its own storage:

```
ProjectA/.devilmcp/storage/
ProjectB/.devilmcp/storage/
DevilMCP/storage/centralized/  # Fallback
```

**No configuration needed** - it just works!

### Custom Storage Location

Force all projects to use specific storage:

**In .env:**
```bash
STORAGE_PATH=/centralized/storage/location
```

**In Claude Code config:**
```json
{
  "mcpServers": {
    "devilmcp": {
      "command": "python",
      "args": ["/path/to/server.py"],
      "env": {
        "STORAGE_PATH": "/custom/storage/path"
      }
    }
  }
}
```

### Debug Mode

Enable maximum logging:

```json
{
  "mcpServers": {
    "devilmcp": {
      "command": "python",
      "args": ["/path/to/server.py"],
      "env": {
        "LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

Logs will show in Claude Code's MCP log viewer.

### Running Multiple Instances

You can run different DevilMCP instances for different projects:

```json
{
  "mcpServers": {
    "devilmcp-projectA": {
      "command": "python",
      "args": ["/path/to/server.py"],
      "env": {
        "PROJECT_ROOT": "/path/to/projectA",
        "LOG_LEVEL": "INFO"
      }
    },
    "devilmcp-projectB": {
      "command": "python",
      "args": ["/path/to/server.py"],
      "env": {
        "PROJECT_ROOT": "/path/to/projectB",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

---

## Next Steps

After installation:

1. **Read [USAGE_GUIDE.md](USAGE_GUIDE.md)** - Learn how to use all the tools
2. **Read [BENEFITS.md](BENEFITS.md)** - Understand the value proposition
3. **Read [SCENARIOS.md](SCENARIOS.md)** - See real-world usage examples
4. **Try the [QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Quick tool lookup

---

## Getting Help

### Common Resources

- **Issues**: Check existing issues or create new one on GitHub
- **Logs**: Check Claude Code's MCP logs for errors
- **Debug**: Run with `LOG_LEVEL=DEBUG` for verbose output

### Verification Checklist

Before asking for help, verify:

- [ ] Python 3.8+ installed (`python --version`)
- [ ] Dependencies installed (`pip list | grep fastmcp`)
- [ ] Server runs standalone (`python server.py`)
- [ ] Config file path is absolute
- [ ] Claude Code restarted after config changes
- [ ] Checked Claude Code MCP logs

---

## Uninstallation

To remove DevilMCP:

### 1. Remove from Claude Code

Delete the devilmcp section from `claude_desktop_config.json`

### 2. Delete Files

```bash
rm -rf /path/to/DevilMCP
```

### 3. Remove Project Storage (Optional)

```bash
# This deletes all DevilMCP data for your projects
find . -name ".devilmcp" -type d -exec rm -rf {} +
```

---

**Installation complete! You're ready to use DevilMCP.**

See [USAGE_GUIDE.md](USAGE_GUIDE.md) for how to use the tools.
