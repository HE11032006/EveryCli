# Contributing to EveryCli

Thank you for your interest in contributing to EveryCli! Whether you're fixing bugs, improving documentation, or adding new CLI scenarios, your help is welcome.

## 📖 Documentation First

Before you start, please take a look at our detailed documentation:
- [Tutorial: Installation](docs/tutorial_installation.md)
- [How to Build & Test](docs/how_to_build.md)
- [Architecture Explanation](docs/explanation_architecture.md)
- [Reference Configuration](docs/reference_config.md)

## 🚀 Ways to Contribute

### 1. Adding New Scenarios
The easiest way to contribute is by adding new command scenarios to the `everycli/data/commands/` directory. 
- Scenarios are stored in YAML files.
- You can use the command `everycli add` to generate a new entry interactively.

### 2. Improving the AI Matcher
If you find that some searches don't return the expected results, you can help us improve the `HybridMatcher` or the `SemanticMatcher` in `everycli/infra/`.

### 3. Reporting Bugs
Please use GitHub Issues to report any bugs or suggest new features.

## 🛠️ Development Setup

1. Fork and clone the repository.
2. Install dependencies: `pip install -r requirements.txt`.
3. Run the daemon in debug mode: `python -m everycli.everycli daemon --start --debug`.
4. Test your changes: `python -m everycli.everycli search "your query"`.

## 📜 Code of Conduct

All contributors are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md).

---
*Thank you for making EveryCli better for everyone!*
