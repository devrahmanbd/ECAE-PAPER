"""
Entity Graph Builder — Builds a directed attributed graph from the sample codebase.
Each entity is a node; connections become directed edges with typed attributes.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from enum import Enum
import json


class EntityType(Enum):
    FEATURE = "FEATURE"
    MODULE = "MODULE"
    API = "API"
    BUG = "BUG"
    ACHIEVEMENT = "ACHIEVEMENT"
    PERSPECTIVE = "PERSPECTIVE"


@dataclass
class Entity:
    name: str
    type: str
    connects: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    calls: List[str] = field(default_factory=list)
    symptom: str = ""
    root_cause: str = ""
    description: str = ""
    severity: float = 0.0

    def __hash__(self):
        return hash(self.name)


@dataclass
class Edge:
    source: str
    target: str
    edge_type: str  # "depends_on", "calls", "connects"
    risk_weight: float = 1.0
    test_coverage: float = 1.0
    failure_history: float = 0.0


class EntityGraph:
    def __init__(self):
        self.nodes: Dict[str, Entity] = {}
        self.edges: List[Edge] = []
        self.adjacency: Dict[str, List[str]] = {}
        self.reverse_adj: Dict[str, List[str]] = {}

    def add_entity(self, entity: Entity):
        self.nodes[entity.name] = entity
        if entity.name not in self.adjacency:
            self.adjacency[entity.name] = []
        if entity.name not in self.reverse_adj:
            self.reverse_adj[entity.name] = []

    def add_edge(self, source: str, target: str, edge_type: str = "connects", risk_weight: float = 1.0):
        if source not in self.nodes or target not in self.nodes:
            return
        edge = Edge(source=source, target=target, edge_type=edge_type, risk_weight=risk_weight)
        self.edges.append(edge)
        self.adjacency.setdefault(source, []).append(target)
        self.reverse_adj.setdefault(target, []).append(source)

    def build_from_entities(self, entity_list: List[dict]):
        for e in entity_list:
            entity = Entity(
                name=e["name"],
                type=e["type"],
                connects=e.get("connects", []),
                depends_on=e.get("depends_on", []),
                calls=e.get("calls", []),
                symptom=e.get("symptom", ""),
                root_cause=e.get("root_cause", ""),
                description=e.get("description", ""),
                severity=e.get("severity", 0.0),
            )
            self.add_entity(entity)

        for name, entity in self.nodes.items():
            for conn in entity.connects:
                if conn in self.nodes:
                    base_risk = entity.severity if entity.type == "BUG" else 0.3
                    self.add_edge(name, conn, "connects", risk_weight=base_risk)
            for dep in entity.depends_on:
                if dep in self.nodes:
                    self.add_edge(name, dep, "depends_on", risk_weight=0.5)
            for call in entity.calls:
                if call in self.nodes:
                    self.add_edge(name, call, "calls", risk_weight=0.4)

    def predict_blast_radius(self, source: str, tau: float = 0.5) -> Set[str]:
        affected: Set[str] = {source}
        visited: Set[str] = set()
        queue = [(source, 0.0)]

        while queue:
            current, acc_risk = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            for edge in self.edges:
                if edge.source == current:
                    new_risk = acc_risk + edge.risk_weight
                    if new_risk <= tau:
                        continue
                    if edge.target not in affected:
                        affected.add(edge.target)
                        queue.append((edge.target, new_risk))

        return affected - {source}

    def get_entity(self, name: str) -> Optional[Entity]:
        return self.nodes.get(name)

    def dump(self) -> dict:
        return {
            "nodes": {name: {"type": e.type, "connects": e.connects}
                      for name, e in self.nodes.items()},
            "edges": [{"source": e.source, "target": e.target, "type": e.edge_type, "risk": e.risk_weight}
                      for e in self.edges],
        }

    def __repr__(self):
        return json.dumps(self.dump(), indent=2)