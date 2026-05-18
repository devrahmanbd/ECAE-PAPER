"""
Sandbox Execution — Deterministic simulation of code execution.
Models the reactive generate-fail-fix loop vs ECAE-PREDICTIVE pre-execution filtering.

REACTIVE mode:
  - No pre-execution analysis
  - Bug trigger probability grows with each iteration (fail → fix → fail → fix...)
  - Iterations simulate: generation attempt, first fix, second fix, etc.

ECAE-PREDICTIVE mode:
  - Pre-execution filtering has already approved the change
  - Multi-perspective meeting may have REJECTED dangerous changes
  - If blocked: zero iterations (prevention is better than cure)
  - If approved: limited iterations since pre-analysis caught most issues
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import random


@dataclass
class ExecutionResult:
    success: bool
    iterations: int
    failed_entities: List[str]
    bugs_triggered: List[str]
    regression_detected: bool
    reason: str


class Sandbox:
    def __init__(self, entity_graph, seed: int = 42):
        self.graph = entity_graph
        self.rng = random.Random(seed)

    def execute(self, change: dict, iterations: int = 10,
                bug_trigger_override: Optional[float] = None,
                pre_execution_blocked: bool = False) -> ExecutionResult:
        """
        ECAE-PREDICTIVE execution.
        If pre_execution_blocked=True, the change is never executed — no regression possible.
        """
        introduces_bug = change.get("introduces_bug")
        expected_impact = set(change.get("expected_impact", []))

        if pre_execution_blocked:
            return ExecutionResult(
                success=False,
                iterations=0,
                failed_entities=change.get("affected", []),
                bugs_triggered=[],
                regression_detected=False,
                reason="REJECTED pre-execution by multi-perspective meeting",
            )

        bugs_triggered = []
        failed_entities = []
        regression_detected = False
        success = True
        reason = "Change executed successfully."
        iteration = 0

        if introduces_bug and introduces_bug in expected_impact:
            bug_entity = self.graph.get_entity(introduces_bug)
            trigger_prob = (bug_trigger_override if bug_trigger_override is not None
                            else self.rng.random())

            for i in range(1, iterations + 1):
                iteration = i
                progressive_prob = min(0.10 + (i - 1) * 0.25, 0.85)
                if trigger_prob < progressive_prob:
                    bugs_triggered.append(introduces_bug)
                    failed_entities.append(introduces_bug)
                    regression_detected = True
                    success = False
                    reason = (f"Bug '{introduces_bug}' triggered at iteration {i}. "
                              f"Symptom: {bug_entity.symptom}. "
                              f"Root cause: {bug_entity.root_cause}")
                    break
            else:
                success = True
                reason = f"Change executed. Bug '{introduces_bug}' was in blast radius but not triggered."
        elif introduces_bug:
            success = True
            reason = f"Bug '{introduces_bug}' not in expected impact scope — no regression."
        else:
            success = True
            reason = "Change executed successfully (no seeded bug in this change)."
            iteration = 1

        return ExecutionResult(
            success=success,
            iterations=max(iteration, 1),
            failed_entities=failed_entities,
            bugs_triggered=bugs_triggered,
            regression_detected=regression_detected,
            reason=reason,
        )

    def execute_reactive(self, change: dict, max_iterations: int = 10) -> ExecutionResult:
        """
        REACTIVE baseline: Generate → Execute → Fail → Fix → (repeat).

        Behavior:
        - Bug-carrying changes: fails after a few iterations as trigger prob grows
        - Non-bug changes: usually succeeds in 1 iteration, but may still fail due to
          structural blindness (API renames cascade without understanding dependencies)
        """
        introduces_bug = change.get("introduces_bug")

        iteration = 0
        bugs_triggered = []
        failed_entities = []
        regression_detected = False
        success = False
        reason = ""

        if introduces_bug:
            bug_entity = self.graph.get_entity(introduces_bug)

            for i in range(1, max_iterations + 1):
                iteration = i
                trigger_prob = min(0.30 + (i - 1) * 0.10, 0.90)
                roll = self.rng.random()

                if roll < trigger_prob:
                    bugs_triggered.append(introduces_bug)
                    failed_entities.append(introduces_bug)
                    regression_detected = True
                    success = False
                    reason = (f"REACTIVE FAIL at iteration {i}: Bug '{introduces_bug}' "
                              f"triggered (trigger prob={trigger_prob:.0%}). "
                              f"Symptom: {bug_entity.symptom}")
                    break

            if iteration == max_iterations and not bugs_triggered:
                success = False
                reason = (f"REACTIVE FAIL: Bug '{introduces_bug}' not resolved after "
                          f"{max_iterations} generate-fix iterations. "
                          f"Root cause: {bug_entity.root_cause}")
                regression_detected = True
        else:
            for i in range(1, max_iterations + 1):
                iteration = i
                structural_fail_prob = min(0.15 + (i - 1) * 0.05, 0.50)
                roll = self.rng.random()
                if roll < structural_fail_prob:
                    success = False
                    reason = (f"REACTIVE FAIL at iteration {i}: Structural blindness — "
                              f"change cascaded unexpectedly through dependency graph. "
                              f"No seeded bug but change broke an implicit dependency.")
                    break
            else:
                success = False
                reason = (f"REACTIVE FAIL: Structural blindness persisted across "
                          f"{max_iterations} iterations.")

            if iteration == 1 and success:
                success = True
                regression_detected = False
                reason = "Reactive success (no seeded bug, structural checks passed)."

        if iteration == 0:
            iteration = 1

        return ExecutionResult(
            success=success,
            iterations=iteration,
            failed_entities=failed_entities,
            bugs_triggered=bugs_triggered,
            regression_detected=regression_detected,
            reason=reason,
        )