from typing import Dict, Tuple, List
import math

Graph = Dict[str, Dict[str, float]]

class DijkstraInputError(Exception):
    pass


def dijkstra(graph: Graph, start: str) -> Tuple[Dict[str, float], Dict[str, str | None]]:
    """Implementación clásica de Dijkstra para grafos con pesos no negativos.
    Devuelve (dist, prev) donde:
      - dist[nodo] = costo mínimo desde start
      - prev[nodo] = predecesor en el camino más corto (o None si es start)
    """
    if start not in graph:
        # Si el start no aparece como clave, aseguremos que exista
        graph = {**graph}
        graph.setdefault(start, {})

    # Inicializa distancias y predecesores
    dist: Dict[str, float] = {v: math.inf for v in graph}
    prev: Dict[str, str | None] = {v: None for v in graph}
    dist[start] = 0.0

    # Conjunto de nodos no visitados
    Q: List[str] = list(graph.keys())

    while Q:
        # Selecciona el no visitado con menor distancia
        u = min(Q, key=lambda x: dist.get(x, math.inf))
        Q.remove(u)

        # Si la distancia es infinita, el resto es inalcanzable
        if dist[u] is math.inf:
            break

        # Relajación de aristas salientes de u
        for v, w in graph.get(u, {}).items():
            if w < 0:
                raise DijkstraInputError("Dijkstra no admite pesos negativos")
            alt = dist[u] + float(w)
            if alt < dist.get(v, math.inf):
                dist[v] = alt
                prev[v] = u

    return dist, prev


def reconstruct_path(prev: Dict[str, str | None], start: str, target: str) -> List[str]:
    """Reconstruye el camino más corto start→target usando el mapa prev."""
    if start == target:
        return [start]
    path: List[str] = []
    cur: str | None = target
    while cur is not None:
        path.append(cur)
        if cur == start:
            break
        cur = prev.get(cur)
    path.reverse()
    if not path or path[0] != start:
        # Sin camino válido
        return []
    return path


def parse_edges_text(text: str, directed: bool) -> Graph:
    """Parses edge list text into adjacency dict.
    Line format: "u v w" (space or comma separated). Ignores lines starting with '#'.
    """
    graph: Graph = {}
    if not text:
        return graph

    errors: List[str] = []

    for i, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        line = line.replace(',', ' ')
        parts = [p for p in line.split() if p]
        if len(parts) != 3:
            errors.append(f"Línea {i}: formato inválido → '{raw}'")
            continue
        u, v, w = parts
        try:
            w_val = float(w)
        except ValueError:
            errors.append(f"Línea {i}: peso no numérico → '{w}'")
            continue
        if w_val < 0:
            errors.append(f"Línea {i}: peso negativo no permitido → {w_val}")
            continue
        graph.setdefault(u, {})
        graph.setdefault(v, {})  # asegura nodos aislados como claves
        graph[u][v] = w_val
        if not directed:
            graph[v][u] = w_val

    if errors:
        raise DijkstraInputError("\n".join(errors))

    return graph
