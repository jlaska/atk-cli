# atk-cli

[![tests](https://github.com/jlaska/atk-cli/actions/workflows/test.yml/badge.svg)](https://github.com/jlaska/atk-cli/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/jlaska/atk-cli/graph/badge.svg)](https://codecov.io/gh/jlaska/atk-cli)

A `kubectl`-inspired CLI for [America's Test Kitchen](https://www.americastestkitchen.com). Browse
recipes, manage favorites, and export content — all from the terminal.

## Installation

```bash
pip install .
```

For PDF export support (requires [Playwright](https://playwright.dev/python/)):

```bash
pip install '.[pdf]'
playwright install chromium
```

## Quick Start

```bash
# Authenticate
atk login

# Search for recipes
atk search "chicken tikka masala"

# List your favorites
atk get favorites

# Describe a recipe
atk describe recipe 12345

# Export a recipe to PDF (saves to <slug>.pdf in current directory)
atk describe recipe 12345 -o pdf
```

## Commands

| Command | Description |
|---------|-------------|
| `atk login` | Authenticate with your ATK account |
| `atk logout` | Clear stored credentials |
| `atk search <query>` | Full-text search across recipes, articles, equipment |
| `atk get favorites` | List your saved favorites |
| `atk get trending` | Show trending recipes |
| `atk describe recipe <slug>` | Show full recipe details |
| `atk describe equipment <slug>` | Show equipment review details |
| `atk create favorite <id>` | Save an item to favorites |
| `atk delete favorite <id>` | Remove an item from favorites |
| `atk auth status` | Show authentication status |
| `atk config view` | Show current configuration |
| `atk config refresh-algolia` | Re-discover Algolia credentials from ATK |
| `atk version` | Show CLI version |

## Output Formats

All commands support `-o` / `--output`:

```bash
atk get favorites -o json
atk search "soup" -o yaml
atk search "soup" -o wide
atk search "soup" -o jsonpath=hits[*].title
```

## Configuration & Profiles

Configuration lives in `~/.atk/`:

```
~/.atk/
  config.json        # profiles and active profile
  tokens.json        # auth tokens (per-profile)
  algolia_index.json # cached Algolia credentials (auto-discovered)
```

### Multiple Profiles

```bash
# Create a profile
atk config set-profile work --email me@example.com

# Switch profiles
atk config use-profile work

# Use a profile for a single command
atk --profile work get favorites
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `ATK_PROFILE` | Override the active profile |
| `ATK_SITE` | Site key: `atk` (default), `cio`, `cco` |

## Shell Completions

```bash
# bash
atk --install-completion bash

# zsh
atk --install-completion zsh

# fish
atk --install-completion fish
```

## Algolia Discovery

Search credentials (App ID, API key, index name) are scraped from ATK's public
search page on first use and cached in `~/.atk/algolia_index.json`. To force
re-discovery:

```bash
atk config refresh-algolia
```
