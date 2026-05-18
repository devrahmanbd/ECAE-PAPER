"""
Multi-Perspective Agent Simulation — Each engineering perspective evaluates
a proposed change and returns a score + optional hard objection.

Perspectives:
  PRODUCT     — Goal alignment, feature coherence
  UI          — Visual consistency
  UX          — Cognitive load, interaction flow
  ARCHITECT   — Modularity, boundary integrity
  FRONTEND    — Component state, rendering
  BACKEND     — API contracts, data integrity
  QA          — Test coverage, edge cases
  RED_TEAM    — Attack surface, input validation
  BLUE_TEAM   — Observability, logging
  DECISION    — Synthesizes all scores
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum
import random


class PerspectiveType(Enum):
    PRODUCT = "PRODUCT"
    UI = "UI"
    UX = "UX"
    ARCHITECT = "ARCHITECT"
    FRONTEND = "FRONTEND"
    BACKEND = "BACKEND"
    QA = "QA"
    RED_TEAM = "RED_TEAM"
    BLUE_TEAM = "BLUE_TEAM"
    DECISION = "DECISION"


@dataclass
class PerspectiveResponse:
    perspective: str
    score: float          # -1.0 (strong objection) to +1.0 (strong endorsement)
    objection_level: int # 0 = none, 1 = soft, 2 = hard
    reason: str
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class PerspectiveAgent:
    def __init__(self, perspective: PerspectiveType, ceg=None, graph=None):
        self.perspective = perspective
        self.ceg = ceg
        self.graph = graph

    def evaluate(self, change: dict, blast_radius: set, entity_graph) -> PerspectiveResponse:
        method_name = f"_eval_{self.perspective.value.lower()}"
        method = getattr(self, method_name, self._eval_default)
        return method(change, blast_radius, entity_graph)

    def _eval_default(self, change: dict, blast_radius: set, graph) -> PerspectiveResponse:
        return PerspectiveResponse(
            perspective=self.perspective.value,
            score=0.0,
            objection_level=0,
            reason="No specific evaluation criteria defined.",
        )

    def _eval_product(self, change: dict, blast_radius: set, graph) -> PerspectiveResponse:
        affected = change.get("affected", [])
        impacting_features = any(
            graph.get_entity(e).type == "FEATURE"
            for e in affected + list(blast_radius) if graph.get_entity(e)
        )
        if impacting_features:
            return PerspectiveResponse(
                perspective=self.perspective.value,
                score=0.7,
                objection_level=0,
                reason="Change touches feature entities — verify alignment with product goals.",
            )
        return PerspectiveResponse(
            perspective=self.perspective.value, score=0.9, objection_level=0,
            reason="No feature impact detected.", warnings=["Verify goal alignment."],
        )

    def _eval_architect(self, change: dict, blast_radius: set, graph) -> PerspectiveResponse:
        affected = change.get("affected", [])
        for e in affected + list(blast_radius):
            entity = graph.get_entity(e)
            if entity and entity.type == "MODULE":
                downstream = list(blast_radius)
                if len(downstream) > 3:
                    return PerspectiveResponse(
                        perspective=self.perspective.value, score=-0.5, objection_level=2,
                        reason=f"Modular boundary violation: {e} affects {len(downstream)} downstream entities.",
                        warnings=["HIGH RISK: Architectural boundary crossing detected."],
                    )
        return PerspectiveResponse(
            perspective=self.perspective.value, score=0.6, objection_level=0,
            reason="Architectural impact within acceptable bounds.",
        )

    def _eval_backend(self, change: dict, blast_radius: set, graph) -> PerspectiveResponse:
        affected = change.get("affected", [])
        api_touched = any(
            graph.get_entity(e).type == "API"
            for e in affected + list(blast_radius) if graph.get_entity(e)
        )
        bug_touched = any(
            graph.get_entity(e).type == "BUG"
            for e in blast_radius if graph.get_entity(e)
        )
        if bug_touched:
            return PerspectiveResponse(
                perspective=self.perspective.value, score=-0.8, objection_level=2,
                reason="Change propagates to known bug entity — risk of triggering failure.",
                warnings=["BUG CASCADE RISK: Known bug in blast radius."],
            )
        if api_touched:
            return PerspectiveResponse(
                perspective=self.perspective.value, score=0.3, objection_level=1,
                reason="API contract changes detected — ensure backward compatibility.",
                warnings=["API contract change — coordinate with consumers."],
            )
        return PerspectiveResponse(
            perspective=self.perspective.value, score=0.8, objection_level=0,
            reason="Backend impact minimal.",
        )

    def _eval_qa(self, change: dict, blast_radius: set, graph) -> PerspectiveResponse:
        blast_size = len(blast_radius)
        if blast_size > 5:
            return PerspectiveResponse(
                perspective=self.perspective.value, score=-0.6, objection_level=2,
                reason=f"Large blast radius ({blast_size} entities) — extensive testing required.",
                warnings=["TEST COVERAGE GAP: Wide blast radius needs full regression."],
            )
        if blast_size > 2:
            return PerspectiveResponse(
                perspective=self.perspective.value, score=0.0, objection_level=1,
                reason=f"Moderate blast radius ({blast_size}) — expand test suite.",
                warnings=["Expand test coverage for affected entities."],
            )
        return PerspectiveResponse(
            perspective=self.perspective.value, score=0.7, objection_level=0,
            reason="Blast radius manageable with existing tests.",
        )

    def _eval_red_team(self, change: dict, blast_radius: set, graph) -> PerspectiveResponse:
        affected = change.get("affected", [])
        auth_touched = any(
            "auth" in e.lower() for e in affected + list(blast_radius)
        )
        api_touched = any(
            graph.get_entity(e).type == "API"
            for e in affected + list(blast_radius) if graph.get_entity(e)
        )
        if auth_touched:
            return PerspectiveResponse(
                perspective=self.perspective.value, score=-0.9, objection_level=2,
                reason="Auth-related change — verify token handling, session management, and access control.",
                warnings=["SECURITY: Auth change requires pentest review."],
            )
        if api_touched:
            return PerspectiveResponse(
                perspective=self.perspective.value, score=0.2, objection_level=1,
                reason="API change — validate input sanitization and authentication.",
                warnings=["SECURITY: Input validation review required."],
            )
        return PerspectiveResponse(
            perspective=self.perspective.value, score=0.8, objection_level=0,
            reason="No immediate security concerns.",
        )

    def _eval_blue_team(self, change: dict, blast_radius: set, graph) -> PerspectiveResponse:
        affected = change.get("affected", [])
        no_logging = graph.get_entity("no_logging")
        for e in affected + list(blast_radius):
            if no_logging and e in no_logging.connects:
                return PerspectiveResponse(
                    perspective=self.perspective.value, score=-0.5, objection_level=1,
                    reason="Change affects entity in no_logging achievement — add observability.",
                    warnings=["OBSERVABILITY: no_logging achievement active — add logging."],
                )
        return PerspectiveResponse(
            perspective=self.perspective.value, score=0.7, objection_level=0,
            reason="Observability coverage acceptable.",
        )

    def _eval_frontend(self, change: dict, blast_radius: set, graph) -> PerspectiveResponse:
        affected = change.get("affected", [])
        fe_touched = any(
            "frontend" in e.lower() for e in affected + list(blast_radius)
        )
        if fe_touched:
            return PerspectiveResponse(
                perspective=self.perspective.value, score=0.4, objection_level=1,
                reason="Frontend entity affected — verify component rendering and state.",
                warnings=["Verify UI state after change."],
            )
        return PerspectiveResponse(
            perspective=self.perspective.value, score=0.8, objection_level=0,
            reason="Frontend impact minimal.",
        )

    def _eval_ux(self, change: dict, blast_radius: set, graph) -> PerspectiveResponse:
        return PerspectiveResponse(
            perspective=self.perspective.value, score=0.5, objection_level=0,
            reason="UX evaluation: standard review — no major friction anticipated.",
        )

    def _eval_ui(self, change: dict, blast_radius: set, graph) -> PerspectiveResponse:
        return PerspectiveResponse(
            perspective=self.perspective.value, score=0.6, objection_level=0,
            reason="UI evaluation: visual consistency check — no issues detected.",
        )


class DecisionTaker:
    def __init__(self, weights: dict = None):
        self.weights = weights or {
            "PRODUCT": 0.05, "UI": 0.05, "UX": 0.05,
            "ARCHITECT": 0.15, "FRONTEND": 0.10, "BACKEND": 0.20,
            "QA": 0.15, "RED_TEAM": 0.15, "BLUE_TEAM": 0.10,
        }

    def synthesize(self, responses: List[PerspectiveResponse]) -> PerspectiveResponse:
        hard_objections = [r for r in responses if r.objection_level == 2]
        if hard_objections:
            worst_score = min(r.score for r in hard_objections)
            worst_reason = "; ".join(r.reason for r in hard_objections)
            return PerspectiveResponse(
                perspective="DECISION", score=worst_score, objection_level=2,
                reason=f"REJECTED by Decision Taker: {worst_reason}",
                warnings=[r.reason for r in hard_objections],
            )

        soft_objections = [r for r in responses if r.objection_level == 1]
        if soft_objections:
            warnings = [r.reason for r in soft_objections]
        else:
            warnings = []

        total_weight = 0.0
        weighted_score = 0.0
        for r in responses:
            if r.perspective in self.weights:
                w = self.weights[r.perspective]
                weighted_score += w * r.score
                total_weight += w

        normalized_score = weighted_score / total_weight if total_weight > 0 else 0.0

        return PerspectiveResponse(
            perspective="DECISION",
            score=normalized_score,
            objection_level=1 if soft_objections else 0,
            reason=f"Decision Taker: score={normalized_score:.2f} — {'proceed with caution' if soft_objections else 'approved'}",
            warnings=warnings,
        )


class MultiPerspectiveOrchestrator:
    def __init__(self, entity_graph, ceg):
        self.graph = entity_graph
        self.ceg = ceg
        self.perspectives = [
            PerspectiveType.PRODUCT,
            PerspectiveType.UI,
            PerspectiveType.UX,
            PerspectiveType.ARCHITECT,
            PerspectiveType.FRONTEND,
            PerspectiveType.BACKEND,
            PerspectiveType.QA,
            PerspectiveType.RED_TEAM,
            PerspectiveType.BLUE_TEAM,
        ]
        self.decision_taker = DecisionTaker()

    def conduct_meeting(self, change: dict, tau: float = 0.5) -> tuple[str, PerspectiveResponse, set]:
        blast_radius = self.graph.predict_blast_radius(
            change["affected"][0], tau=tau
        )

        responses = []
        for ptype in self.perspectives:
            agent = PerspectiveAgent(ptype, self.ceg, self.graph)
            response = agent.evaluate(change, blast_radius, self.graph)
            responses.append(response)

        decision = self.decision_taker.synthesize(responses)

        if decision.objection_level == 2:
            verdict = "REJECTED"
        elif decision.objection_level == 1:
            verdict = "CAUTION"
        else:
            verdict = "APPROVED"

        return verdict, decision, blast_radius