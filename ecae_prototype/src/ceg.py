"""
Causal Experience Graph (CEG) — Long-term engineering memory.
Stores failure records, fix patterns, and reusable engineering knowledge.
Uses an in-memory store (swap with Qdrant in production).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import hashlib


@dataclass
class FailureRecord:
    cause: str
    effect: str
    entities_involved: List[str]
    symptoms: List[str]
    fix: str
    outcome: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    occurrence_count: int = 1

    def signature(self) -> str:
        data = f"{self.cause}:{':'.join(sorted(self.entities_involved))}"
        return hashlib.md5(data.encode()).hexdigest()[:8]


@dataclass
class FixPattern:
    failure_sig: str
    fix_strategy: str
    entities_modified: List[str]
    outcome: str
    reuse_count: int = 0

    def apply(self) -> dict:
        return {
            "strategy": self.fix_strategy,
            "modified_entities": self.entities_modified,
        }


@dataclass
class CEGRecord:
    id: str
    type: str  # "failure", "fix", "pattern"
    cause_entities: List[str] = field(default_factory=list)
    effect_entities: List[str] = field(default_factory=list)
    symptoms: List[str] = field(default_factory=list)
    fix: str = ""
    outcome: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    reuse_count: int = 0
    pattern_score: float = 0.0


class CausalExperienceGraph:
    def __init__(self):
        self.records: List[CEGRecord] = []
        self.failure_index: Dict[str, List[CEGRecord]] = {}
        self.entity_index: Dict[str, List[CEGRecord]] = {}
        self.pattern_cache: Dict[str, FixPattern] = {}

    def store_failure(self, cause: str, effect: str, entities: List[str],
                     symptoms: List[str], fix: str, outcome: str):
        sig = hashlib.md5(f"{cause}:{':'.join(sorted(entities))}".encode()).hexdigest()[:8]

        for rec in self.records:
            if rec.id == sig and rec.type == "failure":
                rec.reuse_count += 1
                return rec

        record = CEGRecord(
            id=sig,
            type="failure",
            cause_entities=[cause] + entities,
            effect_entities=[effect] + entities,
            symptoms=symptoms,
            fix=fix,
            outcome=outcome,
        )
        self.records.append(record)

        for entity in [cause] + entities:
            self.entity_index.setdefault(entity, []).append(record)

        return record

    def store_fix(self, failure_id: str, fix_strategy: str,
                  entities_modified: List[str], outcome: str):
        pattern = FixPattern(
            failure_sig=failure_id,
            fix_strategy=fix_strategy,
            entities_modified=entities_modified,
            outcome=outcome,
        )
        self.pattern_cache[failure_id] = pattern
        return pattern

    def query_by_entity(self, entity: str) -> List[CEGRecord]:
        return self.entity_index.get(entity, [])

    def query_by_type(self, entity_type: str, graph: Any) -> List[CEGRecord]:
        results = []
        for rec in self.records:
            if any(graph.get_entity(e).type == entity_type for e in rec.cause_entities if graph.get_entity(e)):
                results.append(rec)
        return results

    def check_known_failure(self, entities: List[str], theta: float = 0.6) -> tuple[bool, Optional[CEGRecord]]:
        max_score = 0.0
        best_match = None

        for entity in entities:
            for rec in self.entity_index.get(entity, []):
                overlap = len(set(entities) & set(rec.cause_entities)) / max(len(set(entities)), 1)
                if overlap > max_score:
                    max_score = overlap
                    best_match = rec

        return max_score >= theta, best_match

    def get_repeated_failure_count(self) -> int:
        return sum(1 for r in self.records if r.reuse_count > 1)

    def summary(self) -> dict:
        return {
            "total_records": len(self.records),
            "repeated_failures": self.get_repeated_failure_count(),
            "cached_patterns": len(self.pattern_cache),
            "entities_indexed": len(self.entity_index),
        }

    def __repr__(self):
        return json.dumps({
            "records": len(self.records),
            "repeated": self.get_repeated_failure_count(),
            "patterns": len(self.pattern_cache),
        }, indent=2)