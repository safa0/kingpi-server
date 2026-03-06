#!/usr/bin/env bash
set -euo pipefail

# Install tmux for persistent sessions
sudo apt-get update && sudo apt-get install -y --no-install-recommends tmux \
  && sudo rm -rf /var/lib/apt/lists/*

# Install Python project dependencies
pip install -e ".[dev]"

# Install Claude Code CLI
npm install -g @anthropic-ai/claude-code
