from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
from . import mock_runtime, llm_runtime
from .schemas import AttemptTrace, QAExample, ReflectionEntry, RunRecord


@dataclass
class BaseAgent:
    agent_type: Literal["react", "reflexion"]
    max_attempts: int = 1
    use_llm: bool = False

    def run(self, example: QAExample) -> RunRecord:
        reflection_memory: list[str] = []
        reflections: list[ReflectionEntry] = []
        traces: list[AttemptTrace] = []
        final_answer = ""
        final_score = 0

        runtime = llm_runtime if self.use_llm else mock_runtime

        previous_reason = ""
        for attempt_id in range(1, self.max_attempts + 1):
            # Actor call
            answer, actor_tokens, actor_latency = runtime.actor_answer(
                example, attempt_id, self.agent_type, reflection_memory
            )

            # Evaluator call
            judge, eval_tokens, eval_latency = runtime.evaluator(example, answer)

            token_estimate = actor_tokens + eval_tokens
            latency_ms = actor_latency + eval_latency

            trace = AttemptTrace(
                attempt_id=attempt_id,
                answer=answer,
                score=judge.score,
                reason=judge.reason,
                token_estimate=token_estimate,
                latency_ms=latency_ms,
            )
            final_answer = answer
            final_score = judge.score

            if judge.score == 1:
                traces.append(trace)
                break

            # Adaptive Stopping (Bonus)
            # If the reason is exactly the same as before, we are not making progress
            if self.agent_type == "reflexion" and judge.reason == previous_reason:
                traces.append(trace)
                break
            previous_reason = judge.reason

            if self.agent_type == "reflexion" and attempt_id < self.max_attempts:
                # Reflector call
                reflector_res = runtime.reflector(example, attempt_id, judge)
                if isinstance(reflector_res, tuple):
                    reflection, refl_tokens, refl_latency = reflector_res
                    trace.token_estimate += refl_tokens
                    trace.latency_ms += refl_latency
                else:
                    reflection = reflector_res

                reflections.append(reflection)
                reflection_memory.append(
                    f"Attempt {attempt_id} failed: {reflection.failure_reason}. Lesson: {reflection.lesson}. Strategy: {reflection.next_strategy}"
                )

                # Memory Compression (Bonus)
                if len(reflection_memory) >= 2 and self.use_llm:
                    summary, comp_tokens, comp_latency = runtime.compress_memory(
                        reflection_memory
                    )
                    reflection_memory = [
                        f"Summary of previous failures and consolidated strategy: {summary}"
                    ]
                    trace.token_estimate += comp_tokens
                    trace.latency_ms += comp_latency

                trace.reflection = reflection

            traces.append(trace)

        total_tokens = sum(t.token_estimate for t in traces)
        total_latency = sum(t.latency_ms for t in traces)

        # Failure mode analysis
        if final_score == 1:
            failure_mode = "none"
        else:
            if self.use_llm:
                # Actual LLM-based classification (Bonus)
                failure_mode, class_tokens, class_latency = runtime.classify_failure(
                    example.question,
                    final_answer,
                    example.gold_answer,
                    traces[-1].reason,
                )
                total_tokens += class_tokens
                total_latency += class_latency
            else:
                failure_mode = mock_runtime.get_mock_failure_mode(example.qid)

        return RunRecord(
            qid=example.qid,
            question=example.question,
            gold_answer=example.gold_answer,
            agent_type=self.agent_type,
            predicted_answer=final_answer,
            is_correct=bool(final_score),
            attempts=len(traces),
            token_estimate=total_tokens,
            latency_ms=total_latency,
            failure_mode=failure_mode,
            reflections=reflections,
            traces=traces,
        )


class ReActAgent(BaseAgent):
    def __init__(self, use_llm: bool = False) -> None:
        super().__init__(agent_type="react", max_attempts=1, use_llm=use_llm)


class ReflexionAgent(BaseAgent):
    def __init__(self, max_attempts: int = 3, use_llm: bool = False) -> None:
        super().__init__(
            agent_type="reflexion", max_attempts=max_attempts, use_llm=use_llm
        )
