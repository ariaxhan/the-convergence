"""
Budget Tracking

What this demonstrates:
- Tracking token usage across multiple interactions
- Setting and enforcing budget limits
- Alerting when approaching or exceeding budget
- Cost estimation from token counts

Prerequisites:
- pip install -e .

Suggested prompts / test inputs:
- Reduce BUDGET_LIMIT to 5000 to trigger earlier warnings
- Add different cost_per_token rates for different models
"""

# --- Configuration ---
BUDGET_LIMIT = 10000  # tokens
WARNING_THRESHOLD = 0.8  # warn at 80%
COST_PER_TOKEN = 0.00003  # $0.03 per 1K tokens

# --- Setup ---


class BudgetTracker:
    """Track token usage against a budget."""

    def __init__(self, limit: int, cost_per_token: float, warn_at: float = 0.8):
        self.limit = limit
        self.cost_per_token = cost_per_token
        self.warn_at = warn_at
        self.total_tokens = 0
        self.interactions: list[dict] = []

    def record(self, label: str, tokens: int) -> dict:
        """Record an interaction and return status."""
        self.total_tokens += tokens
        cost = tokens * self.cost_per_token
        total_cost = self.total_tokens * self.cost_per_token
        usage_pct = self.total_tokens / self.limit

        status = "OK"
        if self.total_tokens > self.limit:
            status = "EXCEEDED"
        elif usage_pct >= self.warn_at:
            status = "WARNING"

        entry = {
            "label": label,
            "tokens": tokens,
            "cost": cost,
            "total_tokens": self.total_tokens,
            "total_cost": total_cost,
            "usage_pct": usage_pct,
            "status": status,
        }
        self.interactions.append(entry)
        return entry

    def remaining(self) -> int:
        """Tokens remaining in budget."""
        return max(0, self.limit - self.total_tokens)

    def dashboard(self) -> str:
        """Print budget dashboard."""
        total_cost = self.total_tokens * self.cost_per_token
        pct = self.total_tokens / self.limit * 100
        bar_len = 30
        filled = min(bar_len, int(pct / 100 * bar_len))
        bar = "#" * filled + "." * (bar_len - filled)
        return (
            f"Budget: [{bar}] {pct:.0f}%\n"
            f"Tokens: {self.total_tokens:,} / {self.limit:,} "
            f"(remaining: {self.remaining():,})\n"
            f"Cost:   ${total_cost:.4f} / ${self.limit * self.cost_per_token:.4f}"
        )


INTERACTIONS = [
    ("Simple query", 150),
    ("Complex analysis", 2500),
    ("Code generation", 3200),
    ("Summarization", 800),
    ("Multi-turn chat", 1500),
    ("Document analysis", 2000),
    ("Final query", 1200),
]

# --- Execution ---
if __name__ == "__main__":
    tracker = BudgetTracker(BUDGET_LIMIT, COST_PER_TOKEN, WARNING_THRESHOLD)

    print(f"Budget: {BUDGET_LIMIT:,} tokens (${BUDGET_LIMIT * COST_PER_TOKEN:.2f})")
    print(f"Warning at: {WARNING_THRESHOLD * 100:.0f}%\n")

    header = f"{'Interaction':<20} | {'Tokens':>6} | {'Total':>7} | {'Used%':>5} | {'Status':<8} | {'Cost':>7}"
    print(header)
    print("-" * 70)

    for label, tokens in INTERACTIONS:
        result = tracker.record(label, tokens)
        print(f"{label:<20} | {tokens:>6} | {result['total_tokens']:>7} | "
              f"{result['usage_pct']:>4.0%} | {result['status']:<8} | "
              f"${result['cost']:>.4f}")

    print(f"\n{tracker.dashboard()}")
    print(f"\nInteractions: {len(tracker.interactions)}")
    exceeded = [i for i in tracker.interactions if i["status"] == "EXCEEDED"]
    if exceeded:
        print(f"Budget exceeded at: {exceeded[0]['label']}")
