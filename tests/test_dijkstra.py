import math
from dijkstra import dijkstra, reconstruct_path


def build_graph():
    return {
        'a': {'b': 4, 'c': 3},
        'b': {'d': 5},
        'c': {'b': 2, 'd': 7},
        'd': {},
    }


def test_distances_and_path():
    graph = build_graph()
    dist, prev = dijkstra(graph, 'a')
    assert dist['a'] == 0
    assert dist['b'] == 4
    assert dist['c'] == 3
    assert dist['d'] == 9  # a->b->d (4 + 5)
    path = reconstruct_path(prev, 'a', 'd')
    assert path == ['a', 'b', 'd']


def test_unreachable():
    graph = {'a': {'b': 1}, 'b': {}, 'x': {}}
    dist, prev = dijkstra(graph, 'a')
    assert dist['x'] == math.inf
    assert reconstruct_path(prev, 'a', 'x') == []
