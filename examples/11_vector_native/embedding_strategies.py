"""
Embedding Strategies — Production Quality Comparison

What this demonstrates:
- 4 embedding strategies ranked by quality: hash, n-gram, TF-IDF, sentence-level
- Batch embedding with memoization for efficiency
- L2 normalization and NaN/Inf guards on all outputs
- Benchmarking with precision/recall/F1 at configurable threshold

Prerequisites:
- pip install armature-ai

Suggested prompts / test inputs:
- "Adjust EMBEDDING_DIM to see quality vs dimensionality tradeoff"
- "Add your own test pairs to SIMILAR_PAIRS / DIFFERENT_PAIRS"
- "Try threshold values between 0.7 and 0.95"
"""

# --- Configuration ---
import hashlib
import math
import re
from collections import Counter
from typing import Callable, Dict, List, Tuple

EMBEDDING_DIM: int = 64
NGRAM_DIM: int = 128
BENCHMARK_THRESHOLD: float = 0.5


# --- Utilities ---

def _l2_normalize(vec: List[float]) -> List[float]:
    """L2-normalize a vector to unit length. Returns zero vector if norm is zero."""
    norm = math.sqrt(sum(x * x for x in vec))
    if norm < 1e-10:
        return [0.0] * len(vec)
    return [x / norm for x in vec]


def _validate_embedding(vec: List[float], expected_dim: int, label: str = "") -> List[float]:
    """Guard against NaN, Inf, and wrong dimensionality."""
    if len(vec) != expected_dim:
        raise ValueError(
            f"Embedding dimension mismatch{' for ' + label if label else ''}: "
            f"expected {expected_dim}, got {len(vec)}"
        )
    for i, v in enumerate(vec):
        if math.isnan(v) or math.isinf(v):
            raise ValueError(
                f"Invalid float at index {i}{' for ' + label if label else ''}: {v}"
            )
    return vec


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two vectors. Assumes L2-normalized inputs."""
    if len(a) != len(b):
        raise ValueError(f"Vector length mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    # Clamp to [-1, 1] to handle floating point drift
    return max(-1.0, min(1.0, dot))


# --- Embedding Strategies ---

def hash_embedding(text: str, dim: int = EMBEDDING_DIM) -> List[float]:
    """SHA-256 hash to fixed-dim float vector. Deterministic and fast, poor similarity."""
    h = hashlib.sha256(text.lower().strip().encode()).digest()
    raw = [float(b) / 255.0 for b in h]
    while len(raw) < dim:
        h = hashlib.sha256(h).digest()
        raw.extend(float(b) / 255.0 for b in h)
    vec = raw[:dim]
    return _l2_normalize(_validate_embedding(vec, dim, "hash"))


def ngram_embedding(text: str, n: int = 3, dim: int = NGRAM_DIM) -> List[float]:
    """Character n-gram frequency vector hashed to fixed dimensions."""
    cleaned = text.lower().strip()
    if len(cleaned) < n:
        cleaned = cleaned.ljust(n)
    vec = [0.0] * dim
    for i in range(len(cleaned) - n + 1):
        gram = cleaned[i:i + n]
        # Hash each n-gram to a bucket
        bucket = int(hashlib.md5(gram.encode()).hexdigest(), 16) % dim
        vec[bucket] += 1.0
    return _l2_normalize(_validate_embedding(vec, dim, "ngram"))


def tfidf_embedding(text: str, vocab: Dict[str, int], idf: Dict[str, float]) -> List[float]:
    """TF-IDF embedding with pre-built vocabulary and IDF weights."""
    dim = len(vocab)
    if dim == 0:
        raise ValueError("Vocabulary is empty")
    words = re.findall(r'\w+', text.lower())
    if not words:
        return _l2_normalize([0.0] * dim)
    tf = Counter(words)
    total = len(words)
    vec = [0.0] * dim
    for word, count in tf.items():
        if word in vocab:
            tf_score = count / total
            idf_score = idf.get(word, 1.0)
            vec[vocab[word]] = tf_score * idf_score
    return _l2_normalize(_validate_embedding(vec, dim, "tfidf"))


def sentence_embedding(text: str, dim: int = EMBEDDING_DIM) -> List[float]:
    """Word averaging with positional weighting. Best quality among pure-computation methods."""
    words = re.findall(r'\w+', text.lower())
    if not words:
        return _l2_normalize([0.0] * dim)
    vec = [0.0] * dim
    total_weight = 0.0
    for pos, word in enumerate(words):
        # Positional weight: earlier words matter more (decaying)
        weight = 1.0 / (1.0 + 0.1 * pos)
        total_weight += weight
        word_vec = hash_embedding(word, dim)
        for i in range(dim):
            vec[i] += word_vec[i] * weight
    if total_weight > 0:
        vec = [v / total_weight for v in vec]
    return _l2_normalize(_validate_embedding(vec, dim, "sentence"))


# --- Embedding Manager ---

class EmbeddingManager:
    """Manages multiple embedding strategies with caching and benchmarking.

    Args:
        dim: Default embedding dimensionality.
    """

    def __init__(self, dim: int = EMBEDDING_DIM) -> None:
        if dim < 1:
            raise ValueError(f"Dimension must be positive, got {dim}")
        self.dim: int = dim
        self._cache: Dict[str, Dict[str, List[float]]] = {}
        self._vocab: Dict[str, int] = {}
        self._idf: Dict[str, float] = {}
        self._strategies: Dict[str, Callable[[str], List[float]]] = {
            "hash": lambda t: hash_embedding(t, self.dim),
            "ngram": lambda t: ngram_embedding(t, 3, NGRAM_DIM),
            "sentence": lambda t: sentence_embedding(t, self.dim),
        }

    def build_tfidf_vocab(self, corpus: List[str]) -> None:
        """Build TF-IDF vocabulary and IDF weights from a corpus."""
        if not corpus:
            raise ValueError("Corpus is empty")
        word_doc_count: Dict[str, int] = {}
        all_words: set = set()
        for doc in corpus:
            words = set(re.findall(r'\w+', doc.lower()))
            for w in words:
                word_doc_count[w] = word_doc_count.get(w, 0) + 1
                all_words.add(w)
        self._vocab = {w: i for i, w in enumerate(sorted(all_words))}
        n_docs = len(corpus)
        self._idf = {
            w: math.log((1 + n_docs) / (1 + count)) + 1.0
            for w, count in word_doc_count.items()
        }
        self._strategies["tfidf"] = lambda t: tfidf_embedding(t, self._vocab, self._idf)

    def embed(self, text: str, strategy: str) -> List[float]:
        """Embed text using named strategy, with memoization."""
        if strategy not in self._strategies:
            raise ValueError(f"Unknown strategy '{strategy}'. Available: {list(self._strategies)}")
        cache_key = f"{strategy}:{text}"
        if strategy not in self._cache:
            self._cache[strategy] = {}
        if cache_key not in self._cache[strategy]:
            self._cache[strategy][cache_key] = self._strategies[strategy](text)
        return self._cache[strategy][cache_key]

    def embed_batch(self, texts: List[str], strategy: str) -> List[List[float]]:
        """Embed multiple texts at once."""
        return [self.embed(t, strategy) for t in texts]

    def benchmark(
        self,
        similar_pairs: List[Tuple[str, str]],
        different_pairs: List[Tuple[str, str]],
        threshold: float = BENCHMARK_THRESHOLD,
    ) -> Dict[str, Dict[str, float]]:
        """Benchmark all strategies on labeled pairs. Returns metrics per strategy."""
        results: Dict[str, Dict[str, float]] = {}
        for name in self._strategies:
            sims_similar = []
            sims_different = []
            tp = fp = fn = tn = 0
            for a, b in similar_pairs:
                sim = cosine_similarity(self.embed(a, name), self.embed(b, name))
                sims_similar.append(sim)
                if sim >= threshold:
                    tp += 1
                else:
                    fn += 1
            for a, b in different_pairs:
                sim = cosine_similarity(self.embed(a, name), self.embed(b, name))
                sims_different.append(sim)
                if sim >= threshold:
                    fp += 1
                else:
                    tn += 1
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
            avg_sim = sum(sims_similar) / len(sims_similar) if sims_similar else 0.0
            avg_diff = sum(sims_different) / len(sims_different) if sims_different else 0.0
            separation = avg_sim - avg_diff if avg_diff > 0 else avg_sim
            results[name] = {
                "avg_similar_sim": round(avg_sim, 4),
                "avg_different_sim": round(avg_diff, 4),
                "separation_ratio": round(separation, 4),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
            }
        return results


# --- Execution ---

if __name__ == "__main__":
    similar_pairs: List[Tuple[str, str]] = [
        ("How do I reset my password?", "I need to change my password"),
        ("What is the return policy?", "How can I return an item?"),
        ("Track my order status", "Where is my package?"),
        ("Cancel my subscription", "I want to stop my subscription"),
        ("Contact customer support", "How do I reach support?"),
    ]
    different_pairs: List[Tuple[str, str]] = [
        ("How do I reset my password?", "What is the return policy?"),
        ("Track my order status", "Cancel my subscription"),
        ("Contact customer support", "How do I reset my password?"),
        ("What is the return policy?", "Track my order status"),
        ("Cancel my subscription", "Contact customer support"),
    ]

    mgr = EmbeddingManager(dim=EMBEDDING_DIM)

    # Build TF-IDF vocab from all texts in pairs
    all_texts = []
    for a, b in similar_pairs + different_pairs:
        all_texts.extend([a, b])
    mgr.build_tfidf_vocab(all_texts)

    results = mgr.benchmark(similar_pairs, different_pairs, threshold=BENCHMARK_THRESHOLD)

    print("=" * 78)
    print("EMBEDDING STRATEGY BENCHMARK")
    print("=" * 78)
    print(f"{'Strategy':<12} {'Avg Sim':>9} {'Avg Diff':>10} {'Separation':>11} "
          f"{'Prec':>6} {'Recall':>7} {'F1':>6}")
    print("-" * 78)
    for name, m in sorted(results.items(), key=lambda x: x[1]["f1"], reverse=True):
        print(f"{name:<12} {m['avg_similar_sim']:>9.4f} {m['avg_different_sim']:>10.4f} "
              f"{m['separation_ratio']:>11.4f} {m['precision']:>6.4f} "
              f"{m['recall']:>7.4f} {m['f1']:>6.4f}")
    print("-" * 78)
    best = max(results.items(), key=lambda x: x[1]["f1"])
    print(f"Best strategy: {best[0]} (F1={best[1]['f1']:.4f})")
