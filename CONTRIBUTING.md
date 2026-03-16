# Contributing to Ada

Thank you for your interest in contributing to Ada! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/nebula/ada/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - System information (OS, Python version, etc.)
   - Logs or screenshots if applicable

### Suggesting Features

1. Check existing issues for similar suggestions
2. Create a new issue with the "enhancement" label
3. Describe the feature and its use case
4. Explain why it would benefit most users

### Submitting Code

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `make test`
5. Run linting: `make lint`
6. Commit with clear message: `git commit -m 'Add: feature description'`
7. Push: `git push origin feature/my-feature`
8. Open a Pull Request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/ada.git
cd ada

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: .\venv\Scripts\activate  # Windows

# Install development dependencies
pip install -e ".[dev]"

# Run tests
make test

# Run linting
make lint

# Format code
make format
```

## Code Style

- **Formatting**: Black (line length 100)
- **Linting**: Ruff
- **Type hints**: MyPy
- **Imports**: isort

```bash
# Format code
black src/ ada/ tests/

# Check linting
ruff check src/ ada/ tests/

# Type check
mypy src/ada
```

## Project Structure

```
Ada/
├── src/ada/          # Core source code
│   ├── core/         # Core components
│   ├── skill/        # Skill system
│   ├── memory/       # Memory system
│   ├── events/       # Event system
│   └── intent/       # Intent parsing
├── platform/ada/     # Platform adaptation
├── security/ada/     # Security modules
├── ui/gtk/           # GTK UI
├── cli/              # CLI tools
├── api/              # REST API
├── skills/           # Skill packages
└── tests/            # Test suite
```

## Creating Skills

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed instructions on creating custom skills.

## Commit Guidelines

Use clear commit messages following this format:

```
<type>: <subject>

<body>

<footer>
```

Types:
- `Add:` New feature
- `Fix:` Bug fix
- `Update:` Change to existing feature
- `Refactor:` Code cleanup
- `Docs:` Documentation changes
- `Test:` Adding/updating tests
- `Chore:` Maintenance tasks

Example:
```
Add: weather query skill

- Add WeatherCheckerSkill class
- Support Chinese city names
- Add unit tests

Closes #123
```

## Testing

- Write tests for new features
- Maintain test coverage above 80%
- Run tests before committing

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_skill.py -v

# Run with coverage
pytest --cov=ada tests/
```

## Documentation

- Update README.md for user-facing changes
- Update DEVELOPMENT.md for API changes
- Add docstrings to new functions/classes
- Update CHANGELOG.md for releases

## Review Process

1. All PRs require at least one review
2. CI tests must pass
3. Address all review comments
4. Squash commits before merge (if requested)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Ada! 🎉
