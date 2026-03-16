# Changelog

All notable changes to Ada will be documented in this file.

## [0.1.0] - 2024-03-16

### Added

#### Core
- Initial release of Ada AI Assistant
- StateGraph state machine engine for workflow management
- Hybrid execution engine with priority-based backend selection
- Task planner with dependency resolution
- Unified LLM interface supporting Ollama and OpenAI-compatible APIs
- Agent context and configuration management

#### Skill System
- Modular skill architecture with dynamic loading
- Built-in skills:
  - File Organizer - Organize files by type, date, or size
  - App Launcher - Launch, switch, and close applications
  - System Control - Power management, volume, brightness
  - Web Search - Search and fetch web content
  - Calendar Reminder - Schedule reminders
  - Clipboard Manager - Clipboard operations and history
- Support for Python class-based and declarative YAML skills

#### Memory System
- SQLite-based persistent memory storage
- Vector similarity search (ChromaDB/sqlite-vec)
- Multiple memory types: episodic, semantic, procedural, working

#### Event System
- Event bus for publish/subscribe messaging
- Built-in event handlers for focus, clipboard, shortcuts
- Event recording and playback

#### Platform Integration
- AT-SPI based UI perception
- D-Bus service (org.nebula.Ada)
- Systemd user service integration
- Execution backends: API, D-Bus, CLI, GUI

#### Security
- Bubblewrap-based sandboxing
- Permission management system
- Confirmation for destructive actions

#### User Interfaces
- GTK4/libadwaita GUI application
- GNOME Shell extension with panel indicator
- Command-line interface with full command set
- REST API with WebSocket support

#### Developer Tools
- Complete test suite with pytest
- Example custom skills (weather, notes)
- Development documentation

### Technical Details

- 61 Python modules
- ~12,000 lines of code
- 85% test coverage target
- Python 3.10+ support
- GTK4/libadwaita for UI

[0.1.0]: https://github.com/nebula/ada/releases/tag/v0.1.0
