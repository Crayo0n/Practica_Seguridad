from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, Response
from dijkstra import dijkstra, reconstruct_path, parse_edges_text, DijkstraInputError
import math
import io
import base64
import networkx as nx
import matplotlib
matplotlib.use('Agg')  # backend sin ventana
import matplotlib.pyplot as plt 

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'  # para flash messages


def graph_image_from_rows(edges_rows, directed=False, path_nodes=None):
    """Genera un PNG (base64) del grafo y resalta el camino si se provee."""
    G = nx.DiGraph() if directed else nx.Graph()
    for u, v, w in edges_rows:
        if not (u and v and str(w) != ''):
            continue
        try:
            w_val = float(w)
        except ValueError:
            continue
        G.add_edge(u, v, weight=w_val)

    if len(G.nodes) == 0:
        return None

    # Layout estable
    pos = nx.spring_layout(G, seed=42)

    # Preparar estilos
    path_set = set(path_nodes or [])
    node_colors = ['#ffcc66' if n in path_set else '#89a2ff' for n in G.nodes]

    plt.figure(figsize=(6, 4), dpi=150)
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=600, edgecolors='#222636')
    nx.draw_networkx_labels(G, pos, font_size=10)
    nx.draw_networkx_edges(
        G, pos,
        arrows=directed,
        arrowstyle='-|>',
        arrowsize=12,
        width=1.5,
        connectionstyle='arc3,rad=0.07'
    )
    labels = {(u, v): f"{d.get('weight','')}" for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=labels, font_size=9)

    # Resaltar camino
    if path_nodes and len(path_nodes) >= 2:
        path_edges = []
        for a, b in zip(path_nodes[:-1], path_nodes[1:]):
            if isinstance(G, nx.DiGraph):
                if G.has_edge(a, b):
                    path_edges.append((a, b))
            else:  # no dirigido
                if G.has_edge(a, b) or G.has_edge(b, a):
                    path_edges.append((a, b))
        nx.draw_networkx_edges(
            G, pos, edgelist=path_edges, width=3, edge_color='#ff6b6b',
            arrows=directed, arrowstyle='-|>', arrowsize=14
        )

    plt.axis('off')
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close()
    return base64.b64encode(buf.getvalue()).decode('ascii')


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/solve', methods=['POST'])
def solve():
    # Recoge campos del formulario
    start = (request.form.get('start') or '').strip()
    target = (request.form.get('target') or '').strip()
    directed = request.form.get('directed') == 'on'

    if not start:
        flash('Debes indicar el nodo de salida (start).', 'error')
        return redirect(url_for('index'))

    # Listas de campos repetidos
    us = [u.strip() for u in request.form.getlist('u')]
    vs = [v.strip() for v in request.form.getlist('v')]
    ws = [w.strip() for w in request.form.getlist('w')]

    # Valida filas y construye líneas
    lines = []
    edges_rows = []
    n = max(len(us), len(vs), len(ws))
    errors = []
    for i in range(n):
        u = us[i] if i < len(us) else ''
        v = vs[i] if i < len(vs) else ''
        w = ws[i] if i < len(ws) else ''
        # ignora filas completamente vacías
        if not (u or v or w):
            continue
        # si hay algo escrito, la fila debe estar completa y con peso numérico >= 0
        if not u or not v or not w:
            errors.append(f"Fila {i+1}: completa origen, destino y peso.")
        else:
            try:
                w_val = float(w)
                if w_val < 0:
                    errors.append(f"Fila {i+1}: el peso no puede ser negativo.")
            except ValueError:
                errors.append(f"Fila {i+1}: el peso debe ser numérico.")
        edges_rows.append((u, v, w))
        if not errors:
            lines.append(f"{u} {v} {w}")

    if errors:
        for msg in errors[:5]:
            flash(msg, 'error')
        if len(errors) > 5:
            flash(f"+ {len(errors)-5} errores más…", 'error')
        return redirect(url_for('index'))

    try:
        text = "\n".join(lines)
        graph = parse_edges_text(text, directed=directed)
        dist, prev = dijkstra(graph, start)
    except DijkstraInputError as e:
        flash(str(e), 'error')
        return redirect(url_for('index'))

    path = []
    cost = math.inf
    if target:
        path = reconstruct_path(prev, start, target)
        cost = dist.get(target, math.inf)

    # Prepara datos ordenados para la vista
    nodes_sorted = sorted(dist.keys())
    distances = [(n, dist[n] if dist[n] != math.inf else None) for n in nodes_sorted]

    # Genera imagen del grafo (base64)
    graph_png_b64 = graph_image_from_rows(edges_rows, directed=directed, path_nodes=path if path else None)

    return render_template(
        'result.html',
        start=start,
        target=target or None,
        directed=directed,
        distances=distances,
        path=path,
        cost=None if cost == math.inf else cost,
        edges_rows=edges_rows,
        graph_png_b64=graph_png_b64,
    )


@app.post('/api/dijkstra')
def api_dijkstra():
    data = request.get_json(silent=True) or {}
    edges = data.get('edges')
    start = data.get('start')
    target = data.get('target')
    directed = bool(data.get('directed', False))

    if not isinstance(edges, list) or not start:
        return jsonify({
            'error': "Se requiere 'edges' (lista de [u, v, w]) y 'start'"
        }), 400

    # Construye texto a partir de edges para reutilizar parseador
    try:
        lines = []
        edges_rows = []
        for e in edges:
            if not (isinstance(e, (list, tuple)) and len(e) == 3):
                return jsonify({'error': f"Arista inválida: {e}"}), 400
            u, v, w = e
            edges_rows.append((u, v, w))
            lines.append(f"{u} {v} {w}")
        text = "\n".join(lines)
        graph = parse_edges_text(text, directed=directed)
        dist, prev = dijkstra(graph, start)
    except DijkstraInputError as e:
        return jsonify({'error': str(e)}), 400

    resp = {
        'dist': {k: (None if v == math.inf else v) for k, v in dist.items()},
        'prev': {k: (None if p is None else p) for k, p in prev.items()},
    }
    if target:
        path = reconstruct_path(prev, start, target)
        resp['path'] = path
        resp['cost'] = None if dist.get(target, math.inf) == math.inf else dist[target]

    # Además: imagen del grafo codificada en base64
    resp['graph_png_b64'] = graph_image_from_rows(edges_rows, directed=directed, path_nodes=resp.get('path'))

    return jsonify(resp), 200


@app.get('/graph.png')
def graph_png():
    # e=a,b,4 en la URL; puedes poner varias: ?e=a,b,4&e=a,c,3&...
    raw_edges = request.args.getlist('e')
    directed = request.args.get('directed', '0') == '1'
    path = request.args.get('path', '')  # ej: a,b,d
    edges_rows = []
    for e in raw_edges:
        try:
            u, v, w = e.split(',')
            edges_rows.append((u.strip(), v.strip(), w.strip()))
        except ValueError:
            pass
    path_nodes = [p.strip() for p in path.split(',')] if path else None
    b64 = graph_image_from_rows(edges_rows, directed=directed, path_nodes=path_nodes)
    if not b64:
        return Response("No hay grafo para dibujar", status=400)
    return Response(base64.b64decode(b64), mimetype='image/png')


if __name__ == '__main__':
    app.run(debug=True)
