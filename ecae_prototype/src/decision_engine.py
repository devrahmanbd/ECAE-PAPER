"""
Decision Engine — Rank candidate changes using Pareto, Weighted Utility, and Minimax.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import random


@dataclass
class CandidateChange:
    id: str
    description: str
    affected: List[str]
    blast_radius: set
    decision_score: float
    objection_level: int
    perspective_scores: dict
    verdict: str = ""

    def utility(self) -> float:
        return self.decision_score


class DecisionEngine:
    def __init__(self, mode: str = "minimax"):
        self.mode = mode  # "pareto", "weighted", "minimax"

    def select(self, candidates: List[CandidateChange]) -> CandidateChange:
        if not candidates:
            raise ValueError("No candidates to select from")

        if self.mode == "minimax":
            return self._minimax_select(candidates)
        elif self.mode == "weighted":
            return self._weighted_select(candidates)
        elif self.mode == "pareto":
            return self._pareto_select(candidates)
        else:
            return candidates[0]

    def _minimax_select(self, candidates: List[CandidateChange]) -> CandidateChange:
        return max(candidates, key=lambda c: c.decision_score)

    def _weighted_select(self, candidates: List[CandidateChange]) -> CandidateChange:
        return max(candidates, key=lambda c: c.utility())

    def _pareto_select(self, candidates: List[CandidateChange]) -> List[CandidateChange]:
        pareto = []
        for candidate in candidates:
            dominated = False
            for other in candidates:
                if other is candidate:
                    continue
                if all(
                    other.utility() >= candidate.utility() for _ in [1]
                ) and any(
                    other.utility() > candidate.utility() for _ in [1]
                ):
                    dominated = True
                    break
            if not dominated:
                pareto.append(candidate)
        return pareto