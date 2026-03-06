# GitHub Codespaces

Run KingPi Server in a cloud dev environment with Claude Code for persistent AI-assisted development sessions.

## Launch a Codespace

1. Go to the [repository on GitHub](https://github.com/your-org/kingpi-server)
2. Click **Code > Codespaces > Create codespace on main**
3. Wait for the container to build (first launch takes a few minutes)

On launch, the environment automatically:
- Installs Python 3.12 and all project dependencies
- Starts PostgreSQL and Redis via Docker Compose
- Installs Claude Code CLI

## Set your API key

Claude Code needs an Anthropic API key. Set it as a [Codespaces secret](https://docs.github.com/en/codespaces/managing-your-codespaces/managing-encrypted-secrets-for-your-codespaces):

1. Go to **GitHub Settings > Codespaces > Secrets**
2. Add `ANTHROPIC_API_KEY` with your key
3. Grant access to the `kingpi-server` repository

The key will be available in all new codespaces automatically.

## Using Claude Code with tmux

tmux lets your session persist even if you close the browser tab or disconnect.

```bash
# Start a new tmux session
tmux new -s claude

# Launch Claude Code
claude

# Detach from the session (keeps it running)
# Press: Ctrl+B, then D

# Reattach later
tmux attach -t claude
```

### Useful tmux commands

| Action | Keys |
|---|---|
| Detach session | `Ctrl+B`, then `D` |
| List sessions | `tmux ls` |
| Attach to session | `tmux attach -t claude` |
| Kill session | `tmux kill-session -t claude` |
| Split pane horizontal | `Ctrl+B`, then `"` |
| Split pane vertical | `Ctrl+B`, then `%` |

## Quick start

```bash
# Start a tmux session
tmux new -s dev

# Run the app locally (services are already running)
uvicorn kingpi.app:app --reload

# In another pane (Ctrl+B, then %), start Claude Code
claude
```

## Troubleshooting

**Services not running?** Restart them manually:
```bash
docker compose up postgres redis -d
```

**Check service health:**
```bash
docker compose ps
```

**Rebuild the codespace** if the environment is broken:
- Click **Code > Codespaces > ... > Rebuild Container**
