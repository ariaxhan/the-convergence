"""
Confidence Extraction Evaluator

Extracts confidence scores from LLM response text using multiple methods:
- Explicit markers (e.g., "Confidence: 85%")
- Hedging language detection (uncertainty indicators)
- Certainty language detection (confidence boosters)
- Auto mode combining all methods
"""
import re
from typing import Optional


# Hedging phrases that indicate uncertainty
HEDGING_PHRASES = [
    "i'm not entirely sure",
    "not entirely sure",
    "i'm not sure",
    "not sure",
    "not certain",
    "it seems like",
    "it appears",
    "could be",
    "i think",
    "i believe",
    "uncertain",
    "possibly",
    "probably",
    "perhaps",
    "maybe",
    "might",
]

# Certainty phrases that indicate high confidence
CERTAINTY_PHRASES = [
    "without a doubt",
    "definitely",
    "certainly",
    "absolutely",
    "guaranteed",
    "for sure",
    "obviously",
    "clearly",
    "always",
    "100%",
]

# Phrases that negate hedging (e.g., "I am sure" is NOT hedging)
NEGATION_PATTERNS = [
    r"\bi am sure\b",
    r"\bi'm sure\b",
    r"\bam certain\b",
    r"\bam confident\b",
]

VALID_METHODS = {"explicit", "hedging", "certainty", "auto"}


def extract_confidence(text: str, method: str = "auto") -> Optional[float]:
    """
    Extract confidence score from LLM response text.

    Args:
        text: The LLM response text to analyze
        method: Extraction method to use:
            - "explicit": Look for explicit confidence markers
            - "hedging": Detect hedging language (uncertainty)
            - "certainty": Detect certainty markers
            - "auto": Combine all methods (default)

    Returns:
        Confidence score between 0.0 and 1.0, or None if explicit method
        finds no marker.

    Raises:
        ValueError: If method is not one of the valid methods

    Example:
        >>> extract_confidence("The answer is X. Confidence: 85%")
        0.85
        >>> extract_confidence("I think maybe the answer is X.", method="hedging")
        0.4  # Approximate, varies based on hedging detection
    """
    if method not in VALID_METHODS:
        raise ValueError(
            f"Invalid method '{method}'. Must be one of: {', '.join(VALID_METHODS)}"
        )

    if method == "explicit":
        return _extract_explicit(text)
    elif method == "hedging":
        return _extract_hedging(text)
    elif method == "certainty":
        return _extract_certainty(text)
    else:  # auto
        return _extract_auto(text)


def _extract_explicit(text: str) -> Optional[float]:
    """Extract explicit confidence markers like 'Confidence: 85%' or 'Confidence: 0.92'."""
    if not text or not text.strip():
        return None

    # Pattern for "Confidence: X%" or "Confidence: 0.X"
    # Case insensitive, handles spacing variations
    pattern = r"confidence:\s*(-?\d+(?:\.\d+)?)\s*%?"

    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None

    value_str = match.group(1)
    value = float(value_str)

    # Check if it was a percentage (has % after the number)
    # Re-check the original match to see if % was present
    full_match = match.group(0)
    is_percentage = "%" in full_match

    if is_percentage:
        # Convert percentage to decimal
        value = value / 100.0
    elif value > 1.0:
        # If value > 1 and no %, assume it's a percentage anyway
        value = value / 100.0

    # Handle invalid values
    if value < 0.0:
        return None  # Reject negative values
    elif value > 1.0:
        return 1.0  # Clamp values over 100%

    return float(value)


def _extract_hedging(text: str) -> float:
    """Detect hedging language that indicates uncertainty."""
    if not text or not text.strip():
        return 0.3  # Empty text = uncertain

    text_lower = text.lower()

    # Check for negation patterns that cancel hedging
    # e.g., "I am sure" is NOT hedging
    negated_text = text_lower
    for pattern in NEGATION_PATTERNS:
        negated_text = re.sub(pattern, "", negated_text)

    # Count hedging phrases
    hedging_count = 0
    for phrase in HEDGING_PHRASES:
        # Use word boundary matching for single words
        if " " in phrase:
            # Multi-word phrase: direct substring match
            if phrase in negated_text:
                hedging_count += 1
        else:
            # Single word: use word boundary
            if re.search(rf"\b{re.escape(phrase)}\b", negated_text):
                hedging_count += 1

    # No hedging = high confidence
    if hedging_count == 0:
        return 0.9

    # More hedging = lower confidence
    # Scale: 1 hedge = 0.7, 2 = 0.55, 3 = 0.45, 4+ = 0.3
    if hedging_count == 1:
        return 0.7
    elif hedging_count == 2:
        return 0.55
    elif hedging_count == 3:
        return 0.45
    else:
        return 0.3


def _extract_certainty(text: str) -> float:
    """Detect certainty markers that indicate high confidence."""
    if not text or not text.strip():
        return 0.3  # Empty text = uncertain

    text_lower = text.lower()

    # Count certainty phrases
    certainty_count = 0
    for phrase in CERTAINTY_PHRASES:
        # For phrases with special characters (like "100%"), use direct match
        if any(c in phrase for c in "%"):
            if phrase in text_lower:
                certainty_count += 1
        elif " " in phrase:
            # Multi-word phrase: direct substring match
            if phrase in text_lower:
                certainty_count += 1
        else:
            # Single word: use word boundary
            if re.search(rf"\b{re.escape(phrase)}\b", text_lower):
                certainty_count += 1

    # No certainty markers = neutral confidence
    if certainty_count == 0:
        return 0.65  # In the 0.5-0.8 neutral range

    # More certainty = higher confidence
    # Scale: 1 = 0.8, 2 = 0.88, 3+ = 0.95
    if certainty_count == 1:
        return 0.8
    elif certainty_count == 2:
        return 0.88
    else:
        return 0.95


def _extract_auto(text: str) -> float:
    """Combine all methods, using explicit when present, otherwise linguistic analysis."""
    if not text or not text.strip():
        return 0.3  # Empty text = low confidence

    # Try explicit first - it takes precedence
    explicit_result = _extract_explicit(text)
    if explicit_result is not None:
        return explicit_result

    # Fall back to linguistic analysis
    hedging_score = _extract_hedging(text)
    certainty_score = _extract_certainty(text)

    # When methods potentially disagree, be conservative
    # Hedging pulls down, certainty pulls up
    # Conservative approach: weight hedging more when both are present

    # Check if there's hedging detected (score < 0.9 means hedging found)
    has_hedging = hedging_score < 0.85
    # Check if there's certainty detected (score > 0.7 means certainty found)
    has_certainty = certainty_score > 0.7

    if has_hedging and has_certainty:
        # Both present - be conservative, lean toward hedging
        # Average with hedging weighted more heavily
        combined = (hedging_score * 0.6 + certainty_score * 0.4)
        return round(combined, 2)
    elif has_hedging:
        # Only hedging - use hedging score
        return hedging_score
    elif has_certainty:
        # Only certainty - use certainty score
        return certainty_score
    else:
        # Neither - return neutral-ish confidence
        return 0.75
