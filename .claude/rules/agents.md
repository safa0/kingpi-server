# Agent Orchestration

## Model Override (CRITICAL)

ALL agents MUST use Opus 4.6 (`claude-opus-4-6`), regardless of what the agent's own settings specify. This applies to:
- All `everything-claude-code:*` agents
- All custom agents in `~/.claude/agents/`
- All built-in agent types (Explore, Plan, general-purpose, etc.)

When spawning any agent, always set the model to `claude-opus-4-6`. Never use Haiku or Sonnet for agents in this project.

## Spawning Mode (CRITICAL)

ALWAYS use team mode (tmux panes) over subprocess:

1. Create a team with TeamCreate first
2. Spawn teammates using the Agent tool with `team_name` parameter
3. Use SendMessage for communication between agents
4. Shut down teammates with shutdown_request when done

Do NOT use the Agent tool without `team_name` — always use team mode so agents run in separate tmux panes for visibility.

## Available Agents

Located in `~/.claude/agents/`:

| Agent | Purpose | When to Use |
|-------|---------|-------------|
| planner | Implementation planning | Complex features, refactoring |
| architect | System design | Architectural decisions |
| tdd-guide | Test-driven development | New features, bug fixes |
| code-reviewer | Code review | After writing code |
| security-reviewer | Security analysis | Before commits |
| build-error-resolver | Fix build errors | When build fails |
| e2e-runner | E2E testing | Critical user flows |
| refactor-cleaner | Dead code cleanup | Code maintenance |
| doc-updater | Documentation | Updating docs |

## Immediate Agent Usage

No user prompt needed:
1. Complex feature requests - Use **planner** agent
2. Code just written/modified - Use **code-reviewer** agent
3. Bug fix or new feature - Use **tdd-guide** agent
4. Architectural decision - Use **architect** agent

## Parallel Task Execution

ALWAYS use parallel Task execution for independent operations:

```markdown
# GOOD: Parallel execution
Launch 3 agents in parallel:
1. Agent 1: Security analysis of auth module
2. Agent 2: Performance review of cache system
3. Agent 3: Type checking of utilities

# BAD: Sequential when unnecessary
First agent 1, then agent 2, then agent 3
```

## Multi-Perspective Analysis

For complex problems, use split role sub-agents:
- Factual reviewer
- Senior engineer
- Security expert
- Consistency reviewer
- Redundancy checker
