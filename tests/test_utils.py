from src.reflexion_lab.utils import normalize_answer
from src.reflexion_lab.schemas import ReflectionEntry


def test_normalize_answer_punctuation_case():
    assert normalize_answer("Oxford University!") == "oxford university"
    assert normalize_answer("  The BIG Apple.  ") == "big apple"


def test_normalize_answer_articles():
    assert normalize_answer("A dog") == "dog"
    assert normalize_answer("an Apple") == "apple"
    assert normalize_answer("The Matrix") == "matrix"


def test_reflection_entry_schema():
    entry = ReflectionEntry(
        attempt_id=1,
        failure_reason="Failed to find entity",
        lesson="Look harder",
        next_strategy="Use index",
    )
    assert entry.attempt_id == 1
    assert "Failed" in entry.failure_reason
