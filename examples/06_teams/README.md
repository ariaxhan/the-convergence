# 06 - Multi-Agent Teams

Patterns for multiple agents collaborating, competing, and evolving together.

## Examples

| File | What It Shows |
|------|---------------|
| `basic_team.py` | 3 agents with different strategies running in a civilization |
| `competitive_selection.py` | 5 agents competing with evolution-driven natural selection |
| `specialist_routing.py` | Thompson Sampling routes queries to specialist agents |
| `team_with_memory.py` | 2 agents sharing a ContextGraph for collective knowledge |

## Key Concepts

- **CivilizationRuntime** manages agent execution loops, learning, and evolution
- **Evolution** applies fitness-based selection pressure on agent populations
- **Thompson Sampling** routes work to the best-performing specialist
- **ContextGraph** enables shared memory between agents

## Running

```bash
pip install armature-ai

python basic_team.py
python competitive_selection.py
python specialist_routing.py
python team_with_memory.py
```

No API keys required. All examples use simulated agents.
