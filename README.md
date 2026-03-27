# Ada - OS-Integrated AI Assistant

<div align="center">

![Ada Logo](data/icons/hicolor/scalable/apps/ada.svg)

**An intelligent AI assistant for NebulaOS**

[Features](#features) • [Installation](#installation) • [Usage](#usage) • [Development](#development) • [Architecture](#architecture)

</div>

---

## Overview

Ada (named after Ada Lovelace, the first programmer) is an OS-integrated AI assistant designed for NebulaOS, a GTK4-based Linux/BSD desktop system. Unlike traditional AI chatbots, Ada can perceive and interact with your desktop environment.

## Features

### 🖥️ Desktop Integration
- **AT-SPI Based UI Perception**: Understands application interfaces through accessibility APIs
- **D-Bus Integration**: Communicates with system services and applications
- **Native GTK4/libadwaita UI**: Seamless integration with GNOME desktop

### 🧠 Hybrid Execution
Intelligent action execution with fallback paths:
1. **API** - Direct function calls (fastest)
2. **D-Bus** - System service calls
3. **CLI** - Command-line tools
4. **GUI** - UI automation via AT-SPI (fallback)

### 🔧 Skill System
Modular, extensible skill system:
- **File Organizer**: Organize files by type, date, or size
- **App Launcher**: Launch, switch, and manage applications
- **Custom Skills**: Create your own skills with Python or declarative YAML

### 💾 Memory System
Persistent context and learning:
- **Episodic Memory**: Conversation history
- **Semantic Memory**: Facts and knowledge
- **Vector Search**: Semantic similarity search

### 🔒 Security
Privacy-first design:
- **Sandboxed Execution**: Run untrusted code safely with bubblewrap
- **Permission System**: Fine-grained control over capabilities
- **Local-First**: Works offline with Ollama

## Installation

### Requirements

- Python 3.10+
- GTK4 and libadwaita
- AT-SPI2 (for UI perception)
- Ollama (for local LLM)

### From Source

```bash
# Clone the repository
git clone https://github.com/nebula/ada.git
cd ada

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Install as user service
ada install
```

### Flatpak (Coming Soon)

```bash
flatpak install flathub org.nebula.Ada
```

## Usage

### Interactive Chat

```bash
# Start interactive chat
ada chat

# Or just run without arguments
ada
```

### Single Query

```bash
# Ask a quick question
ada ask "What's the weather today?"
```

### Daemon Mode

```bash
# Run as background service
ada daemon
```

### Manage Skills

```bash
# List available skills
ada skills

# Execute a skill directly
ada skill file.organizer "organize downloads"
```

### GTK Application

```bash
# Launch the GUI
ada-gui
```

### 开发模式启动

在开发过程中，可以直接从源码启动 GTK 界面：

```bash
# 进入 UI 目录
cd Ada/ui/gtk

# 设置 PYTHONPATH 并启动应用
PYTHONPATH=. python3 -m ada.ui.app
```

## Development

### Project Structure

```
Ada/
├── src/ada/                 # Main Python package
│   ├── core/                # Core agent components
│   │   ├── graph.py         # State machine (StateGraph)
│   │   ├── executor.py      # Hybrid execution engine
│   │   ├── planner.py       # Task decomposition
│   │   ├── llm.py           # LLM abstraction
│   │   └── context.py       # Agent state and config
│   ├── skill/               # Skill system
│   │   ├── base.py          # Base classes
│   │   ├── registry.py      # Skill discovery
│   │   ├── loader.py        # Dynamic loading
│   │   └── builtin/         # Built-in skills
│   ├── memory/              # Memory system
│   ├── intent/              # Intent parsing
│   └── events/              # Event handling
├── platform/ada/            # Platform adaptation layer
│   ├── perception/          # AT-SPI, screen capture
│   ├── execution/backends/  # API, D-Bus, CLI, GUI
│   └── adapters/            # D-Bus service, systemd
├── security/ada/            # Security components
│   ├── sandbox.py           # Bubblewrap sandboxing
│   └── permissions.py       # Permission management
├── ui/gtk/ada/ui/           # GTK4/libadwaita UI
├── api/ada/                 # REST API
├── cli/ada/                 # Command-line interface
├── config/                  # Configuration files
├── data/                    # Desktop files, icons
└── tests/                   # Test suite
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ada

# Run specific test file
pytest tests/test_executor.py
```

### Code Style

```bash
# Format code
black src/ ada/

# Lint
ruff check src/ ada/

# Type check
mypy src/ada
```

## Architecture

### Hybrid Execution Flow

```
User Request → Intent Parser → Skill Registry → Skill Selection
                                                    ↓
                                              Execution
                                                    ↓
                    ┌─────────────────────────────────────────────────┐
                    │                 Execution Backends               │
                    ├─────────┬─────────┬─────────┬───────────────────┤
                    │   API   │  D-Bus  │   CLI   │       GUI         │
                    │ Priority│Priority │Priority │     Priority      │
                    │    10   │   20    │   30    │        40         │
                    └─────────┴─────────┴─────────┴───────────────────┘
                                    ↓
                              Result → Response
```

### State Machine

```
                    ┌─────────┐
                    │  Start  │
                    └────┬────┘
                         │
                    ┌────▼────┐
              ┌────►│ Analyze │
              │     └────┬────┘
              │          │
              │     ┌────▼────┐
              │     │  Plan   │
              │     └────┬────┘
              │          │
              │     ┌────▼────┐
              │     │Execute  │
              │     └────┬────┘
              │          │
              │     ┌────▼────┐
              ├─────┤  Verify │
              │     └────┬────┘
              │          │
              │     ┌────▼────┐
              │     │Complete │
              │     └────┬────┘
              │          │
              │     ┌────▼────┐
              └─────┤  Error  │──────►
                    └─────────┘
```

## Configuration

Configuration file: `~/.config/ada/ada.yaml`

```yaml
# Agent settings
agent:
  name: "Ada"
  mode: normal
  language: zh-CN

# LLM settings
llm:
  backend: ollama
  model: llama3.2
  ollama:
    base_url: http://localhost:11434

# Memory settings
memory:
  backend: sqlite
  database_path: ~/.local/share/ada/memory.db

# Security settings
security:
  mode: balanced
  sandbox:
    enabled: true
```

## D-Bus Interface

Ada exposes a D-Bus service at `org.nebula.Ada`:

```python
import dbus

# Connect to Ada
bus = dbus.SessionBus()
ada = bus.get_object('org.nebula.Ada', '/org/nebula/Ada')

# Process input
response = ada.ProcessInput('打开 Firefox')
print(response)
```

## Contributing

Contributions are welcome! Please read our contributing guidelines.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Named after [Ada Lovelace](https://en.wikipedia.org/wiki/Ada_Lovelace)
- Built with GTK4/libadwaita for GNOME
- Powered by local LLMs via Ollama

---

<div align="center">

Made with ❤️ for NebulaOS

</div>
