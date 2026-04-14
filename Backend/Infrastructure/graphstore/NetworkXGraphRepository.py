import json
import logging
import threading
from pathlib import Path
import networkx as nx
from Backend.Domain.Entities.triple import Triple
from Backend.Application.Interfaces.IGraphRepository import IGraphRepository

logger = logging.getLogger(__name__)

MAX_EDGES_PER_NODE = 20


class NetworkXGraphRepository(IGraphRepository):
    def __init__(self, graph_path: str = "db/knowledge_graph.json"):
        self._graph_path = graph_path
        self._G = nx.DiGraph()
        self._lock = threading.Lock()
        self.load()

    def load(self) -> None:
        path = Path(self._graph_path)
        if not path.exists():
            logger.info("图文件不存在，初始化空图: %s", self._graph_path)
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            with self._lock:
                self._G.clear()
                for node in data.get("nodes", []):
                    self._G.add_node(node["id"], **node.get("attrs", {}))
                for edge in data.get("edges", []):
                    self._G.add_edge(
                        edge["src"], edge["dst"],
                        relation=edge["relation"],
                        source_file=edge.get("source_file", ""),
                    )
            logger.info(
                "图加载完成: %d 节点, %d 边",
                self._G.number_of_nodes(), self._G.number_of_edges(),
            )
        except Exception:
            logger.exception("图文件加载失败: %s", self._graph_path)

    def save(self) -> None:
        with self._lock:
            data = {
                "nodes": [
                    {"id": n, "attrs": dict(self._G.nodes[n])}
                    for n in self._G.nodes
                ],
                "edges": [
                    {
                        "src": u, "dst": v,
                        "relation": self._G[u][v].get("relation", ""),
                        "source_file": self._G[u][v].get("source_file", ""),
                    }
                    for u, v in self._G.edges
                ],
            }
        Path(self._graph_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self._graph_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("图已持久化: %s", self._graph_path)

    def add_triples(self, triples: list[Triple]) -> None:
        with self._lock:
            for t in triples:
                self._G.add_node(t.head, entity_type=t.head_type)
                self._G.add_node(t.tail, entity_type=t.tail_type)
                self._G.add_edge(
                    t.head, t.tail,
                    relation=t.relation,
                    source_file=t.source_file,
                )

    def remove_by_file(self, file_name: str) -> None:
        with self._lock:
            edges_to_remove = [
                (u, v) for u, v, d in self._G.edges(data=True)
                if d.get("source_file") == file_name
            ]
            self._G.remove_edges_from(edges_to_remove)
            # 移除孤立节点
            isolated = [n for n in self._G.nodes if self._G.degree(n) == 0]
            self._G.remove_nodes_from(isolated)
        if edges_to_remove:
            self.save()
            logger.info("已移除文件 %s 关联的 %d 条边", file_name, len(edges_to_remove))

    def expand_subgraph(self, seed_entities: list[str], hops: int = 2) -> list[dict]:
        paths = []
        with self._lock:
            visited = set(seed_entities)
            frontier = set()
            for seed in seed_entities:
                if seed in self._G:
                    frontier.add(seed)

            for _ in range(hops):
                next_frontier = set()
                for node in frontier:
                    for neighbor in list(self._G.successors(node)) + list(self._G.predecessors(node)):
                        if neighbor not in visited:
                            edge_data = (
                                self._G.get_edge_data(node, neighbor)
                                or self._G.get_edge_data(neighbor, node)
                            )
                            relation = edge_data.get("relation", "关联") if edge_data else "关联"
                            paths.append({
                                "from": node,
                                "relation": relation,
                                "to": neighbor,
                            })
                            visited.add(neighbor)
                            next_frontier.add(neighbor)
                frontier = next_frontier
        return paths

    def prune(self) -> None:
        with self._lock:
            for node in list(self._G.nodes):
                out_edges = list(self._G.out_edges(node, data=True))
                if len(out_edges) > MAX_EDGES_PER_NODE:
                    sorted_edges = sorted(
                        out_edges,
                        key=lambda e: e[2].get("weight", 1),
                        reverse=True,
                    )
                    for _, v, _ in sorted_edges[MAX_EDGES_PER_NODE:]:
                        self._G.remove_edge(node, v)

    def node_count(self) -> int:
        return self._G.number_of_nodes()

    def edge_count(self) -> int:
        return self._G.number_of_edges()
