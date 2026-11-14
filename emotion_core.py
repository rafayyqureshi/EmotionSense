"""Deterministic score handling and explicit inference provenance."""
from dataclasses import dataclass
from math import isfinite
import re

EMOTIONS = ("happy", "sad", "angry", "fear", "neutral", "surprise")
LABEL_MAP = {
    "joy": "happy", "happiness": "happy", "happy": "happy", "love": "happy",
    "sadness": "sad", "sad": "sad", "anger": "angry", "angry": "angry",
    "disgust": "angry", "fear": "fear", "neutral": "neutral", "surprise": "surprise",
}
KEYWORDS = {
    "happy": {"happy", "joy", "glad", "excited", "wonderful", "amazing", "great", "love"},
    "sad": {"sad", "unhappy", "disappointed", "miserable", "upset", "crying", "sorry", "miss"},
    "angry": {"angry", "mad", "furious", "annoyed", "frustrated", "hate", "unfair"},
    "fear": {"afraid", "scared", "fear", "worried", "nervous", "terrified", "anxious"},
    "neutral": {"okay", "fine", "normal", "standard", "regular", "usual"},
    "surprise": {"wow", "surprised", "unexpected", "shocking", "amazed", "astonished"},
}


def normalize_scores(values):
    """Validate and normalize relative scores; these are not calibrated confidence."""
    result = {emotion: 0.0 for emotion in EMOTIONS}
    for emotion, score in values.items():
        if emotion not in result:
            raise ValueError("Unsupported emotion label")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise ValueError("Scores must be numbers")
        if not isfinite(score) or score < 0:
            raise ValueError("Scores must be finite and non-negative")
        result[emotion] += float(score)
    total = sum(result.values())
    if not isfinite(total) or total <= 0:
        raise ValueError("At least one positive score is required")
    return {emotion: score / total for emotion, score in result.items()}


@dataclass(frozen=True)
class InferenceResult:
    scores: dict
    method: str
    used_fallback: bool
    note: str
    components: tuple = ()

    def provenance(self):
        labels = {
            "remote_classifier": "Remote emotion classifier",
            "local_keywords": "Local keyword fallback",
            "generated_text_keywords": "Keywords in generated text",
            "weighted_ensemble": "Mixed experimental pipeline",
        }
        return {
            "method": self.method,
            "label": labels[self.method],
            "used_fallback": self.used_fallback,
            "is_model_prediction": self.method == "remote_classifier",
            "score_label": "Relative score; not calibrated confidence",
            "note": self.note,
            "components": list(self.components),
        }


def keyword_analysis(text, *, generated=False):
    """Use whole-word rules with no randomness or model-specific simulated bias."""
    words = set(re.findall(r"\b[\w']+\b", text.casefold()))
    scores = {emotion: float(len(words & keywords)) for emotion, keywords in KEYWORDS.items()}
    if not any(scores.values()):
        scores["neutral"] = 1.0
    if generated:
        return InferenceResult(
            normalize_scores(scores), "generated_text_keywords", False,
            "Keyword rules were applied to generated text. These are illustrative "
            "relative scores, not an emotion-classifier prediction.",
        )
    return InferenceResult(
        normalize_scores(scores), "local_keywords", True,
        "Remote inference was unavailable or not configured. Deterministic local "
        "keyword rules were used. Scores are illustrative and not calibrated confidence.",
    )


def classifier_analysis(payload):
    """Accept flat or single-batch Hugging Face classification responses."""
    if not isinstance(payload, list) or not payload:
        raise ValueError("Expected a classification list")
    rows = payload[0] if isinstance(payload[0], list) else payload
    if not rows:
        raise ValueError("Classification response is empty")
    values = {emotion: 0.0 for emotion in EMOTIONS}
    recognized = False
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("label"), str):
            raise ValueError("Invalid classification row")
        score = row.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise ValueError("Invalid classification score")
        if not isfinite(score) or score < 0:
            raise ValueError("Invalid classification score")
        emotion = LABEL_MAP.get(row["label"].casefold())
        if emotion:
            values[emotion] += float(score)
            recognized = True
    if not recognized:
        raise ValueError("No supported classification labels")
    return InferenceResult(
        normalize_scores(values), "remote_classifier", False,
        "Scores came from the configured remote classifier and were mapped to six "
        "display labels. They are relative scores, not independently calibrated confidence.",
    )


def combine_results(classifier, generated):
    values = {
        emotion: 0.6 * classifier.scores[emotion] + 0.4 * generated.scores[emotion]
        for emotion in EMOTIONS
    }
    fallback = classifier.used_fallback or generated.used_fallback
    return InferenceResult(
        normalize_scores(values), "weighted_ensemble", fallback,
        "This experimental result combines the classifier pipeline (60%) and "
        "generated-text rules (40%). Component methods are listed explicitly; "
        "the combined scores are not calibrated confidence.",
        (classifier.method, generated.method),
    )
