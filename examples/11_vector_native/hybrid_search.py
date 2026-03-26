"""
Hybrid Search — Semantic + Keyword Fusion

What this demonstrates:
- Weighted blend of semantic similarity and keyword (Jaccard) matching
- Negative keyword filtering to reject misleading matches
- Fallback logic when one scoring method fails
- Score explanations showing per-component breakdown
- Cases where hybrid outperforms pure semantic or pure keyword search

Prerequisites:
- pip install armature-ai

Suggested prompts / test inputs:
- "Adjust SEMANTIC_WEIGHT to see blend tradeoff"
- "Add negative keywords for your domain"
- "Try queries that are semantically similar but topically different"
"""

# --- Configuration ---
import hashlib
import math
import re
from typing import Dict, List, Optional, Set, Tuple

EMBEDDING_DIM: int = 64
SEMANTIC_WEIGHT: float = 0.7
KEYWORD_WEIGHT: float = 0.3
MATCH_THRESHOLD: float = 0.40
# Words that, if mismatched, should reject an otherwise-close match
NEGATIVE_KEYWORDS: Set[str] = {
    "python", "java", "javascript", "rust", "go", "ruby",
    "delete", "create", "cancel", "upgrade", "downgrade",
}


# --- Utilities ---

def _l2_normalize(vec: List[float]) -> List[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm < 1e-10:
        return [0.0] * len(vec)
    return [x / norm for x in vec]


def hash_embedding(text: str, dim: int = EMBEDDING_DIM) -> List[float]:
    """SHA-256 hash to fixed-dim float vector."""
    h = hashlib.sha256(text.lower().strip().encode()).digest()
    raw = [float(b) / 255.0 for b in h]
    while len(raw) < dim:
        h = hashlib.sha256(h).digest()
        raw.extend(float(b) / 255.0 for b in h)
    return _l2_normalize(raw[:dim])


def sentence_embedding(text: str, dim: int = EMBEDDING_DIM) -> List[float]:
    """Word-average embedding with positional weighting."""
    words = re.findall(r'\w+', text.lower())
    if not words:
        return _l2_normalize([0.0] * dim)
    vec = [0.0] * dim
    total_w = 0.0
    for pos, word in enumerate(words):
        w = 1.0 / (1.0 + 0.1 * pos)
        total_w += w
        wv = hash_embedding(word, dim)
        for i in range(dim):
            vec[i] += wv[i] * w
    if total_w > 0:
        vec = [v / total_w for v in vec]
    return _l2_normalize(vec)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if len(a) != len(b):
        raise ValueError(f"Vector length mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    return max(-1.0, min(1.0, dot))


def tokenize(text: str) -> Set[str]:
    """Lowercase word tokenization, stripping punctuation."""
    return set(re.findall(r'\w+', text.lower()))


def jaccard_similarity(a: Set[str], b: Set[str]) -> float:
    """Jaccard similarity between two token sets."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# --- Hybrid Searcher ---

class HybridSearcher:
    """Combines semantic and keyword scoring for robust search.

    Args:
        semantic_weight: Weight for semantic similarity (0-1).
        keyword_weight: Weight for keyword similarity (0-1).
        threshold: Minimum combined score for a match.
        negative_keywords: Set of words where mismatch rejects match.
    """

    def __init__(
        self,
        semantic_weight: float = SEMANTIC_WEIGHT,
        keyword_weight: float = KEYWORD_WEIGHT,
        threshold: float = MATCH_THRESHOLD,
        negative_keywords: Optional[Set[str]] = None,
    ) -> None:
        if not (0.0 <= semantic_weight <= 1.0):
            raise ValueError(f"semantic_weight must be in [0, 1], got {semantic_weight}")
        if not (0.0 <= keyword_weight <= 1.0):
            raise ValueError(f"keyword_weight must be in [0, 1], got {keyword_weight}")
        self._sw = semantic_weight
        self._kw = keyword_weight
        self._threshold = threshold
        self._negative_kw = negative_keywords or NEGATIVE_KEYWORDS
        self._index: List[Dict] = []

    def add(self, question: str, answer: str) -> None:
        """Add a Q&A pair to the search index."""
        self._index.append({
            "question": question,
            "answer": answer,
            "embedding": sentence_embedding(question),
            "tokens": tokenize(question),
        })

    def _check_negative_keywords(self, query_tokens: Set[str], doc_tokens: Set[str]) -> bool:
        """Return True if negative keyword mismatch detected (should reject)."""
        query_neg = query_tokens & self._negative_kw
        doc_neg = doc_tokens & self._negative_kw
        # Reject if both have negative keywords but they differ
        if query_neg and doc_neg and not (query_neg & doc_neg):
            return True
        return False

    def search(
        self, query: str, top_k: int = 3
    ) -> List[Dict]:
        """Search index with hybrid scoring.

        Args:
            query: Search query string.
            top_k: Maximum results to return.

        Returns:
            List of result dicts with scores and explanations.
        """
        if not self._index:
            return []
        if not query.strip():
            raise ValueError("Query cannot be empty")

        query_emb = sentence_embedding(query)
        query_tokens = tokenize(query)
        semantic_ok = True
        keyword_ok = True

        # Validate embedding worked
        if all(v == 0.0 for v in query_emb):
            semantic_ok = False

        results: List[Dict] = []
        for entry in self._index:
            # Semantic score (with fallback)
            if semantic_ok:
                try:
                    sem_score = cosine_similarity(query_emb, entry["embedding"])
                except (ValueError, ZeroDivisionError):
                    sem_score = 0.0
            else:
                sem_score = 0.0

            # Keyword score (with fallback)
            if keyword_ok:
                try:
                    kw_score = jaccard_similarity(query_tokens, entry["tokens"])
                except (TypeError, ZeroDivisionError):
                    kw_score = 0.0
            else:
                kw_score = 0.0

            # Weighted combination — rebalance if one method failed
            if semantic_ok and keyword_ok:
                combined = self._sw * sem_score + self._kw * kw_score
            elif semantic_ok:
                combined = sem_score
            else:
                combined = kw_score

            # Negative keyword check
            rejected = self._check_negative_keywords(query_tokens, entry["tokens"])
            matched_kw = query_tokens & entry["tokens"]

            results.append({
                "question": entry["question"],
                "answer": entry["answer"],
                "semantic_score": round(sem_score, 4),
                "keyword_score": round(kw_score, 4),
                "combined_score": round(combined, 4),
                "matched_keywords": sorted(matched_kw),
                "negative_reject": rejected,
                "decision": "REJECT" if rejected else (
                    "MATCH" if combined >= self._threshold else "MISS"
                ),
            })

        # Sort by combined score, filter rejects to bottom
        results.sort(key=lambda r: (not r["negative_reject"], r["combined_score"]), reverse=True)
        return results[:top_k]


# --- Execution ---

if __name__ == "__main__":
    searcher = HybridSearcher()

    # Build index of Q&A pairs
    qa_pairs: List[Tuple[str, str]] = [
        ("How to install Python packages?", "Use pip install <package_name>."),
        ("How to install Java dependencies?", "Use Maven or Gradle to manage deps."),
        ("Reset my password", "Go to Settings > Security > Reset Password."),
        ("Delete my account", "Contact support or go to Settings > Delete Account."),
        ("Track my order", "Check your email for tracking link or visit Orders page."),
        ("Cancel my subscription", "Go to Billing > Cancel Subscription."),
        ("Upgrade my plan", "Visit Billing > Plans > Upgrade."),
        ("Downgrade my plan", "Visit Billing > Plans > Downgrade."),
        ("How to use async in Python?", "Use async def and await keywords with asyncio."),
        ("How to use threads in Java?", "Use Thread class or ExecutorService."),
        ("Export my data", "Go to Settings > Privacy > Export Data."),
        ("Change notification settings", "Go to Settings > Notifications."),
        ("Two-factor authentication setup", "Go to Security > Enable 2FA."),
        ("Refund policy", "Refunds within 30 days. Contact support."),
        ("API rate limits", "Free tier: 100/min. Pro: 1000/min."),
    ]
    for q, a in qa_pairs:
        searcher.add(q, a)

    test_queries: List[Tuple[str, str]] = [
        ("install python libraries", "paraphrase — should match Python packages"),
        ("how to add java deps", "paraphrase — should match Java dependencies"),
        ("python threading tutorial", "keyword overlap python + semantic mismatch"),
        ("java async patterns", "keyword overlap java + semantic mismatch"),
        ("remove my account", "synonym for delete — hybrid advantage"),
        ("change my password", "synonym for reset password"),
        ("stop my subscription", "synonym for cancel subscription"),
        ("upgrade my subscription to pro", "mixed: upgrade + subscription keywords"),
        ("billing information", "weak semantic match to billing entries"),
        ("how do I get a refund?", "paraphrase of refund policy"),
    ]

    print("=" * 90)
    print("HYBRID SEARCH RESULTS — Semantic + Keyword Fusion")
    print(f"Weights: semantic={SEMANTIC_WEIGHT}, keyword={KEYWORD_WEIGHT}, "
          f"threshold={MATCH_THRESHOLD}")
    print("=" * 90)

    for query, note in test_queries:
        results = searcher.search(query, top_k=2)
        print(f"\nQuery: \"{query}\"")
        print(f"  Note: {note}")
        for i, r in enumerate(results):
            flag = " ** NEGATIVE REJECT **" if r["negative_reject"] else ""
            print(f"  [{i+1}] {r['decision']:<6} combined={r['combined_score']:.3f} "
                  f"(sem={r['semantic_score']:.3f} kw={r['keyword_score']:.3f}){flag}")
            print(f"       -> \"{r['question']}\"")
            if r["matched_keywords"]:
                print(f"       keywords: {', '.join(r['matched_keywords'])}")
