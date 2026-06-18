from __future__ import annotations
from .schemas import QAExample, JudgeResult, ReflectionEntry
from .utils import normalize_answer

FIRST_ATTEMPT_WRONG = {
    "hp2": "London",
    "hp4": "Atlantic Ocean",
    "hp6": "Red Sea",
    "hp8": "Andes",
    "5a8b57f25542995d1e6f1371": "no",  # Wrong final answer (actual is yes)
    "5a8c7595554299585d9e36b6": "Ambassador",  # Incomplete (actual is Chief of Protocol)
    "5a85ea095542994775f606a8": "Drifted Entity",  # Entity drift
}
FAILURE_MODE_BY_QID = {
    "hp2": "incomplete_multi_hop",
    "hp4": "wrong_final_answer",
    "hp6": "entity_drift",
    "hp8": "entity_drift",
    "5a8b57f25542995d1e6f1371": "wrong_final_answer",
    "5a8c7595554299585d9e36b6": "incomplete_multi_hop",
    "5a85ea095542994775f606a8": "entity_drift",
}


def get_mock_failure_mode(qid: str) -> str:
    base_qid = qid.split("_copy_")[0]
    if base_qid in FAILURE_MODE_BY_QID:
        return FAILURE_MODE_BY_QID[base_qid]

    # Deterministic assignment for other QIDs to ensure variety
    modes = ["wrong_final_answer", "incomplete_multi_hop", "entity_drift"]
    idx = sum(ord(c) for c in base_qid) % len(modes)
    return modes[idx]


def actor_answer(
    example: QAExample, attempt_id: int, agent_type: str, reflection_memory: list[str]
) -> tuple[str, int, float]:
    base_qid = example.qid.split("_copy_")[0]
    tokens = 320 + (attempt_id * 65) + (120 if agent_type == "reflexion" else 0)
    latency = 160 + (attempt_id * 40) + (90 if agent_type == "reflexion" else 0)

    # Only specific cases fail in mock to keep EM realistic
    FAIL_BASES = {
        "hp2",
        "hp4",
        "hp6",
        "hp8",
        "5a8b57f25542995d1e6f1371",
        "5a8c7595554299585d9e36b6",
        "5a85ea095542994775f606a8",
    }

    if base_qid not in FAIL_BASES:
        return example.gold_answer, tokens, latency

    if agent_type == "react":
        return FIRST_ATTEMPT_WRONG.get(base_qid, "Wrong Answer"), tokens, latency
    if attempt_id == 1 and not reflection_memory:
        return FIRST_ATTEMPT_WRONG.get(base_qid, "Wrong Answer"), tokens, latency

    return example.gold_answer, tokens, latency


def evaluator(example: QAExample, answer: str) -> tuple[JudgeResult, int, float]:
    tokens = 150
    latency = 50
    if normalize_answer(example.gold_answer) == normalize_answer(answer):
        return (
            JudgeResult(
                score=1,
                reason="Final answer matches the gold answer after normalization.",
            ),
            tokens,
            latency,
        )

    # Specific mock feedback for the real QIDs
    if example.qid.startswith("5a8c7595554299585d9e36b6"):
        return (
            JudgeResult(
                score=0,
                reason="The answer identified her as Ambassador but missed the specific Chief of Protocol role.",
                missing_evidence=["Chief of Protocol"],
                spurious_claims=[],
            ),
            tokens,
            latency,
        )

    if normalize_answer(answer) == "london":
        return (
            JudgeResult(
                score=0,
                reason="The answer stopped at the birthplace city and never completed the second hop to the river.",
                missing_evidence=[
                    "Need to identify the river that flows through London."
                ],
                spurious_claims=[],
            ),
            tokens,
            latency,
        )

    return (
        JudgeResult(
            score=0,
            reason="The final answer selected the wrong second-hop entity or fact.",
            missing_evidence=[
                "Need to ground the answer in the correct context paragraph."
            ],
            spurious_claims=[answer],
        ),
        tokens,
        latency,
    )


def reflector(
    example: QAExample, attempt_id: int, judge: JudgeResult
) -> tuple[ReflectionEntry, int, float]:
    base_qid = example.qid.split("_copy_")[0]
    tokens = 200
    latency = 100
    strategy = "Verify the final entity against the context carefully."
    if base_qid == "5a8c7595554299585d9e36b6":
        strategy = "Look for the specific government position held, not just the ambassadorial roles."
    elif base_qid == "hp2":
        strategy = (
            "Do the second hop explicitly: birthplace city -> river through that city."
        )

    return (
        ReflectionEntry(
            attempt_id=attempt_id,
            failure_reason=judge.reason,
            lesson="A partial or drifted answer is not enough.",
            next_strategy=strategy,
        ),
        tokens,
        latency,
    )
