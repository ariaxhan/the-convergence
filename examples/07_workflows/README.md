# 07 - Workflow and Pipeline Patterns

Multi-step pipelines where each step has its own Thompson Sampling instance.
The runtime learns independently at each stage, optimizing the full pipeline over time.

## Examples

| File | Pattern | Key Concept |
|------|---------|-------------|
| `sequential_pipeline.py` | 3-step classify->generate->validate | Per-step convergence in a serial pipeline |
| `branching_workflow.py` | Confidence-based routing | Route to different branches based on confidence |
| `retry_with_learning.py` | Retry with arm switching | Thompson Sampling naturally tries alternatives |
| `human_in_the_loop.py` | Escalation workflow | Auto-respond vs flag for human review |

## Running

```bash
pip install the-convergence

python sequential_pipeline.py
python branching_workflow.py
python retry_with_learning.py
python human_in_the_loop.py
```

No API keys required. All examples use simulated LLM responses.

## Concepts

**Per-step runtime:** Each pipeline step gets its own `configure_runtime` call with its own arms.
Thompson Sampling converges independently at each stage, so one step can learn "concise is better"
while another learns "strict validation wins."

**Confidence routing:** Use `extract_confidence` to score responses, then route to different
code paths. High confidence goes fast-path, low confidence gets retried or escalated.

**Learning from retries:** When a first attempt scores low, selecting again from Thompson Sampling
naturally explores alternatives. Over time, bad arms get fewer first-attempt selections.
