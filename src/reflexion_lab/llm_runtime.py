import json
from typing import Optional
from .schemas import QAExample, JudgeResult, ReflectionEntry
from .prompts import ACTOR_SYSTEM, EVALUATOR_SYSTEM, REFLECTOR_SYSTEM
from .providers import get_provider, LLMProvider

_provider: Optional[LLMProvider] = None


def init_runtime(provider_name: str, model_name: Optional[str] = None):
    global _provider
    _provider = get_provider(provider_name, model_name)


def get_active_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        # Default fallback
        init_runtime("gemini")
    return _provider


def actor_answer(
    example: QAExample, attempt_id: int, agent_type: str, reflection_memory: list[str]
) -> tuple[str, int, float]:
    context_str = "\n\n".join([f"Source: {c.title}\n{c.text}" for c in example.context])
    reflection_str = "\n".join(reflection_memory) if reflection_memory else "None"
    user_prompt = f"Question: {example.question}\n\nContext:\n{context_str}\n\nReflection Memory:\n{reflection_str}"

    return get_active_provider().call(ACTOR_SYSTEM, user_prompt)


def evaluator(example: QAExample, answer: str) -> tuple[JudgeResult, int, float]:
    user_prompt = f"Question: {example.question}\nPredicted Answer: {answer}\nGold Standard Answer: {example.gold_answer}"
    text, tokens, latency = get_active_provider().call(
        EVALUATOR_SYSTEM, user_prompt, json_mode=True
    )

    try:
        data = json.loads(text)
        return JudgeResult(**data), tokens, latency
    except Exception as e:
        print(f"Error parsing evaluator JSON: {e}\nRaw text: {text}")
        return (
            JudgeResult(
                score=0, reason=f"Failed to parse evaluator response: {str(e)}"
            ),
            tokens,
            latency,
        )


def reflector(
    example: QAExample, attempt_id: int, judge: JudgeResult
) -> tuple[ReflectionEntry, int, float]:
    user_prompt = f"Question: {example.question}\nFailed Answer: (see previous attempt)\nEvaluation Feedback:\nReason: {judge.reason}\nMissing Evidence: {judge.missing_evidence}\nSpurious Claims: {judge.spurious_claims}\n\nPlease provide reflection for attempt_id: {attempt_id}"
    text, tokens, latency = get_active_provider().call(
        REFLECTOR_SYSTEM, user_prompt, json_mode=True
    )

    try:
        data = json.loads(text)
        data["attempt_id"] = attempt_id
        return ReflectionEntry(**data), tokens, latency
    except Exception as e:
        print(f"Error parsing reflector JSON: {e}\nRaw text: {text}")
        return (
            ReflectionEntry(
                attempt_id=attempt_id,
                failure_reason="Parsing error",
                lesson="N/A",
                next_strategy="Try again",
            ),
            tokens,
            latency,
        )


def compress_memory(reflection_memory: list[str]) -> tuple[str, int, float]:
    system_prompt = "You are an expert at distilling technical feedback. Summarize the following failed attempts into a concise set of 'Lessons Learned' and a unified 'Consolidated Strategy'."
    user_prompt = "Previous attempts feedback:\n" + "\n---\n".join(reflection_memory)
    return get_active_provider().call(system_prompt, user_prompt)


def classify_failure(
    question: str, answer: str, gold_answer: str, reason: str
) -> tuple[str, int, float]:
    system_prompt = """
    Classify the following QA failure into one of these categories:
    - entity_drift
    - incomplete_multi_hop
    - wrong_final_answer
    - looping
    - reflection_overfit
    Output ONLY the category name.
    """
    user_prompt = f"Question: {question}\nPredicted: {answer}\nGold: {gold_answer}\nFailure Reason: {reason}"
    text, tokens, latency = get_active_provider().call(system_prompt, user_prompt)

    category = text.strip().lower()
    valid = {
        "entity_drift",
        "incomplete_multi_hop",
        "wrong_final_answer",
        "looping",
        "reflection_overfit",
    }
    for v in valid:
        if v in category:
            return v, tokens, latency
    return "wrong_final_answer", tokens, latency

