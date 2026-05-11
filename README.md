# 🚀 EveryCli

**Don't look for your commands, describe them.**

EveryCli is an intelligent command-line assistant that uses AI to instantly find the exact command you need, even if you don't know its syntax.

![License](https://img.shields.io/github/license/HE11032006/EveryCli)
![Build Status](https://img.shields.io/github/actions/workflow/status/HE11032006/EveryCli/build.yml)

## Contents

- [Getting started](#-getting-started)
- [Overview](#-overview)
- [Directory Structure](#directory-structure)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✈️ Getting started

### 🚀 Download & Install (Recommended)

Two versions are available for each operating system on the [Releases](https://github.com/HE11032006/EveryCli/releases) page:

- **Full Version** (~300MB): **Ready to use.** Includes the AI model. Perfect for offline use or fast first-run experience.
- **Lite Version** (~50MB): **Lightweight.** Will automatically download the AI model (~400MB) on the first search. Recommended if you have a good internet connection.

1. Download the version that fits your needs.
2. (Optional) Add the binary to your system PATH to run it from anywhere.

### 🛠️ Installation (Source)

If you want to contribute or build from source:

1. Clone the repo: `git clone https://github.com/HE11032006/EveryCli.git`.
2. Go to the root: `cd EveryCli`.
3. Install dependencies: `pip install -r requirements.txt`.

### Running locally

Run a search directly:
```bash
python -m everycli.everycli search "how to undo my last commit"
```

> [!TIP]
> To enjoy sub-50ms response times, EveryCli uses a background Daemon. The first search will automatically start it.

---

## 📖 Overview

EveryCli is built for speed and intelligence. Almost all our content is generated from YAML files you can find in the `everycli/data/commands/` directory.

If you would like to contribute an edit or addition to the docs, read through our [Contributing Guide](CONTRIBUTING.md).

### Documentation Sources

For deep dives, check our dedicated documentation files:
- 📖 [Tutorial: Installation](docs/tutorial_installation.md)
- 🛠️ [How to Build & Test](docs/how_to_build.md)
- 🏗️ [Architecture Explanation](docs/explanation_architecture.md)
- ⚙️ [Reference Configuration](docs/reference_config.md)

### Directory Structure

The following is a high-level overview of relevant files and folders.

```text
EveryCli/
├── .github/             # CI/CD Workflows (Auto-build binaries)
├── docs/                # Detailed Diátaxis documentation
├── everycli/
│   ├── core/            # Domain logic (Models, Search Engine, Coordinator)
│   ├── data/
│   │   └── commands/    # YAML scenarios database
│   └── infra/           # Infrastructure (AI Matchers, TCP Daemon, YAML loaders)
├── everycli.ps1         # Windows PowerShell wrapper
├── requirements.txt     # Python dependencies
└── README.md            # You are here
```

---

## 👏 Contributing

We welcome all contributions! Whether it's adding a new command or improving the AI matcher.
Please see our [Contributing Guide](CONTRIBUTING.md) for more details.

---

## 📄 License

EveryCli is **MIT licensed**.
Documentation is Creative Commons licensed.

---
*Made with ❤️ for developers who hate memorizing flags.*
