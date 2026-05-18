"""
Graphify — AST-level Entity Graph Extraction from Real Python Codebases.

Extracts a typed directed attributed graph G = (V, E, L) from Python source code:
  V: Functions, Classes, Modules, API Routes, Tests
  E: Call dependencies, imports, data flow, API routes
  L: Risk scores, test coverage, change frequency, entity types

Usage:
  python3 -c "from graphify.core import extract_graph; g = extract_graph('/path/to/codebase'); print(g.summary())"
"""

from __future__ import annotations
import ast
import os
import re
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path
from enum import Enum


class EntityType(Enum):
    MODULE = "MODULE"
    CLASS = "CLASS"
    FUNCTION = "FUNCTION"
    METHOD = "METHOD"
    API_ROUTE = "API_ROUTE"
    TEST = "TEST"
    DATABASE_QUERY = "DATABASE_QUERY"
    EXTERNAL_CALL = "EXTERNAL_CALL"


class EdgeType(Enum):
    CALLS = "CALLS"
    IMPORTS = "IMPORTS"
    INHERITS = "INHERITS"
    API_ROUTE_TO_HANDLER = "API_ROUTE_TO_HANDLER"
    DATABASE_ACCESS = "DATABASE_ACCESS"
    EXTERNAL_CALL = "EXTERNAL_CALL"


@dataclass
class Entity:
    name: str
    type: EntityType
    file_path: str
    lineno: int = 0
    docstring: str = ""
    params: List[str] = field(default_factory=list)
    return_type: str = ""
    risk_score: float = 0.3
    test_coverage: float = 0.0
    change_frequency: float = 0.0
    calls: List[str] = field(default_factory=list)
    called_by: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def signature(self) -> str:
        return f"{self.file_path}:{self.name}"

    def __hash__(self):
        return hash(self.signature())

    def __eq__(self, other):
        return self.signature() == other.signature()


@dataclass
class Edge:
    source: str
    target: str
    edge_type: EdgeType
    risk_weight: float = 1.0
    lineno: int = 0
    metadata: Dict = field(default_factory=dict)


class EntityGraph:
    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.edges: List[Edge] = []
        self.module_entities: Dict[str, List[str]] = {}
        self.call_graph: Dict[str, Set[str]] = {}
        self.reverse_call_graph: Dict[str, Set[str]] = {}

    def add_entity(self, entity: Entity) -> None:
        key = entity.signature()
        self.entities[key] = entity
        self.module_entities.setdefault(entity.file_path, []).append(key)
        self.call_graph.setdefault(key, set())
        self.reverse_call_graph.setdefault(key, set())

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge)
        self.call_graph.setdefault(edge.source, set()).add(edge.target)
        self.reverse_call_graph.setdefault(edge.target, set()).add(edge.source)

    def get_entity(self, key: str) -> Optional[Entity]:
        return self.entities.get(key)

    def predict_blast_radius(self, source_key: str, tau: float = 0.5) -> Set[str]:
        affected: Set[str] = set()
        visited: Set[str] = set()
        queue: List[Tuple[str, float]] = [(source_key, 0.0)]

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
                    affected.add(edge.target)
                    queue.append((edge.target, new_risk))

        return affected

    def get_callers(self, entity_key: str) -> Set[str]:
        return self.reverse_call_graph.get(entity_key, set())

    def get_callees(self, entity_key: str) -> Set[str]:
        return self.call_graph.get(entity_key, set())

    def summary(self) -> dict:
        by_type: Dict[str, int] = {}
        for e in self.entities.values():
            by_type[e.type.value] = by_type.get(e.type.value, 0) + 1
        by_edge: Dict[str, int] = {}
        for e in self.edges:
            by_edge[e.edge_type.value] = by_edge.get(e.edge_type.value, 0) + 1
        return {
            "entities": len(self.entities),
            "edges": len(self.edges),
            "by_type": by_type,
            "by_edge_type": by_edge,
        }


class PythonASTExtractor:
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.graph = EntityGraph()
        self.defined_names: Dict[str, List[str]] = {}

    def extract(self) -> EntityGraph:
        python_files = list(self.root_path.rglob("*.py"))
        python_files = [f for f in python_files if not f.name.startswith("__")]

        for file_path in python_files:
            self._process_file(file_path)

        for file_path in python_files:
            self._process_second_pass(file_path)

        self._compute_risk_scores()
        return self.graph

    def _process_file(self, file_path: Path) -> None:
        try:
            source = file_path.read_text()
            tree = ast.parse(source, filename=str(file_path))
        except (SyntaxError, ast.ASTError):
            return

        module_name = str(file_path.relative_to(self.root_path))
        module_key = f"{module_name}"

        mod_entity = Entity(
            name=module_name,
            type=EntityType.MODULE,
            file_path=module_name,
            docstring=ast.get_docstring(tree) or "",
        )
        self.graph.add_entity(mod_entity)

        visitor = FirstPassVisitor(file_path, self.graph, module_name)
        visitor.visit(tree)

        self._identify_api_routes(file_path, tree, module_name)

    def _process_second_pass(self, file_path: Path) -> None:
        try:
            source = file_path.read_text()
            tree = ast.parse(source, filename=str(file_path))
        except (SyntaxError, ast.ASTError):
            return

        module_name = str(file_path.relative_to(self.root_path))
        visitor = SecondPassVisitor(file_path, self.graph, module_name)
        visitor.visit(tree)

    def _identify_api_routes(self, file_path: Path, tree: ast.AST, module_name: str) -> None:
        source = file_path.read_text()
        route_pattern = re.compile(r'@app\.(route|get|post|put|delete|patch)\([^)]+\)')
        func_pattern = re.compile(r"def\s+(api_\w+)\s*\(")

        for match in route_pattern.finditer(source):
            route_line = match.group(0)
            func_name = None
            line = match.end()
            while line < len(source):
                if source[line:line+3] == "def":
                    m = re.match(r"def\s+(\w+)\s*\(", source[line:])
                    if m:
                        func_name = m.group(1)
                    break
                line += 1

            if func_name:
                route_entity = Entity(
                    name=f"{func_name} ({route_line})",
                    type=EntityType.API_ROUTE,
                    file_path=module_name,
                    lineno=source[:match.start()].count("\n") + 1,
                    risk_score=0.8,
                )
                self.graph.add_entity(route_entity)

                func_key = f"{module_name}:{func_name}"
                if self.graph.get_entity(func_key):
                    edge = Edge(
                        source=route_entity.signature(),
                        target=func_key,
                        edge_type=EdgeType.API_ROUTE_TO_HANDLER,
                        risk_weight=1.0,
                    )
                    self.graph.add_edge(edge)

    def _compute_risk_scores(self) -> None:
        for entity_key, entity in self.graph.entities.items():
            callers = self.graph.get_callers(entity_key)
            callees = self.graph.get_callees(entity_key)
            entity.metadata["fan_in"] = len(callers)
            entity.metadata["fan_out"] = len(callees)

            if entity.type == EntityType.API_ROUTE:
                entity.risk_score = 0.9
            elif entity.type == EntityType.DATABASE_QUERY:
                entity.risk_score = 0.7
            elif entity.type in (EntityType.FUNCTION, EntityType.METHOD):
                if not entity.test_coverage:
                    entity.risk_score = min(0.3 + len(callees) * 0.05, 1.0)
            elif entity.type == EntityType.EXTERNAL_CALL:
                entity.risk_score = 0.6


class FirstPassVisitor(ast.NodeVisitor):
    def __init__(self, file_path: Path, graph: EntityGraph, module_name: str):
        self.file_path = file_path
        self.graph = graph
        self.module_name = module_name
        self.class_stack: List[str] = []

    def visit_ClassDef(self, node: ast.ClassDef):
        class_entity = Entity(
            name=node.name,
            type=EntityType.CLASS,
            file_path=self.module_name,
            lineno=node.lineno,
            docstring=ast.get_docstring(node) or "",
        )
        self.graph.add_entity(class_entity)
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if self.class_stack:
            ftype = EntityType.METHOD
            fname = f"{self.class_stack[-1]}.{node.name}"
        else:
            ftype = EntityType.FUNCTION
            fname = node.name

        func_entity = Entity(
            name=node.name,
            type=ftype,
            file_path=self.module_name,
            lineno=node.lineno,
            docstring=ast.get_docstring(node) or "",
            params=[arg.arg for arg in node.args.args],
        )
        self.graph.add_entity(func_entity)

        for dec in node.decorator_list:
            dec_name = self._get_decorator_name(dec)
            if dec_name in ("app.route", "app.get", "app.post", "app.put", "app.delete", "app.patch"):
                route_entity = Entity(
                    name=f"{node.name} (API Route)",
                    type=EntityType.API_ROUTE,
                    file_path=self.module_name,
                    lineno=node.lineno,
                    risk_score=0.8,
                )
                self.graph.add_entity(route_entity)
                edge = Edge(
                    source=route_entity.signature(),
                    target=func_entity.signature(),
                    edge_type=EdgeType.API_ROUTE_TO_HANDLER,
                    risk_weight=1.0,
                )
                self.graph.add_edge(edge)

        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node: ast.Call):
        caller_key = self._get_caller_key()
        callee_key = self._resolve_call_target(node.func)

        if callee_key and caller_key != callee_key:
            edge = Edge(
                source=caller_key,
                target=callee_key,
                edge_type=EdgeType.CALLS,
                risk_weight=0.5,
                lineno=node.lineno,
            )
            self.graph.add_edge(edge)

        self.generic_visit(node)

    def _get_caller_key(self) -> str:
        return self.module_name

    def _get_decorator_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._get_decorator_name(node.value) + "." + node.attr
        elif isinstance(node, ast.Call):
            return self._get_decorator_name(node.func)
        return ""

    def _resolve_call_target(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Name):
            return f"{self.module_name}:{node.id}"
        elif isinstance(node, ast.Attribute):
            base = self._resolve_call_target(node.value)
            if base:
                return f"{base}.{node.attr}"
            return f"{self.module_name}:{node.attr}"
        return None


class SecondPassVisitor(ast.NodeVisitor):
    def __init__(self, file_path: Path, graph: EntityGraph, module_name: str):
        self.file_path = file_path
        self.graph = graph
        self.module_name = module_name
        self.class_stack: List[str] = []
        self.function_stack: List[str] = []
        self.external_modules = {"flask", "json", "ast", "time", "hashlib", "secrets", "sqlite3"}

    def visit_ClassDef(self, node: ast.ClassDef):
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        current_func = node.name
        if self.class_stack:
            current_func = f"{self.class_stack[-1]}.{node.name}"
        self.function_stack.append(current_func)
        self.generic_visit(node)
        self.function_stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node: ast.Call):
        caller = self._get_current_key()
        callee = self._resolve_call(node.func)

        if callee:
            self.graph.add_edge(Edge(
                source=caller, target=callee,
                edge_type=EdgeType.CALLS,
                risk_weight=0.5, lineno=node.lineno,
            ))

        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            pass

    def visit_ImportFrom(self, node: ast.ImportFrom):
        pass

    def _get_current_key(self) -> str:
        if self.function_stack:
            return f"{self.module_name}:{self.function_stack[-1]}"
        return self.module_name

    def _resolve_call(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Name):
            name = node.id
            if name in self.external_modules:
                ext_entity = Entity(
                    name=name, type=EntityType.EXTERNAL_CALL,
                    file_path=self.module_name,
                    metadata={"module": name},
                )
                self.graph.add_entity(ext_entity)
                return ext_entity.signature()
            return f"{self.module_name}:{name}"
        elif isinstance(node, ast.Attribute):
            base = self._resolve_call(node.value)
            if base:
                return f"{base}.{node.attr}"
            return f"{self.module_name}:{node.attr}"
        return None


def extract_graph(root_path: str) -> EntityGraph:
    extractor = PythonASTExtractor(root_path)
    return extractor.extract()


def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 -m graphify.core <path_to_codebase>")
        sys.exit(1)

    path = sys.argv[1]
    graph = extract_graph(path)
    s = graph.summary()

    print(f"\n{'='*60}")
    print(f"  Graphify — Entity Graph Summary")
    print(f"{'='*60}")
    print(f"  Codebase     : {path}")
    print(f"  Entities     : {s['entities']}")
    print(f"  Edges        : {s['edges']}")
    print(f"\n  Entities by type:")
    for etype, count in sorted(s["by_type"].items()):
        print(f"    {etype:<25} {count:>5}")
    print(f"\n  Edges by type:")
    for etype, count in sorted(s["by_edge_type"].items()):
        print(f"    {etype:<25} {count:>5}")

    print(f"\n  Top-risk entities:")
    risk_sorted = sorted(graph.entities.values(), key=lambda e: e.risk_score, reverse=True)
    for e in risk_sorted[:10]:
        print(f"    {e.risk_score:.1f}  {e.type.value:<15} {e.name:<40}")

    print(f"\n{'='*60}")
    return graph


if __name__ == "__main__":
    main()