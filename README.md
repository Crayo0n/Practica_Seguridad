# Flask + Dijkstra (con visualización)

Proyecto en Flask que:
- Calcula distancias con **Dijkstra** y (opcional) el **camino más corto**.
- Captura el grafo por **filas** (origen, destino, peso) con **validación**.
- **Visualiza** el grafo con **NetworkX + Matplotlib**, resaltando el camino.
- Expone `/api/dijkstra` (devuelve también `graph_png_b64`) y `/graph.png` (endpoint directo a PNG).

## Instalación
```bash
python -m venv .venv
# Linux/Mac
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ejecución
```bash
export FLASK_APP=app.py   # Windows: set FLASK_APP=app.py
flask run --debug
# o
python app.py
```

## Uso (UI)
1. Agrega aristas (origen, destino, peso). Pesos **≥ 0**.
2. Indica `start` y opcionalmente `target`.
3. Marca **Grafo dirigido** si aplica.
4. Envía. Verás **distancias**, **camino** y la **imagen** del grafo.

## Uso (API)
`POST /api/dijkstra` con JSON:
```json
{
  "edges": [["a","b",4], ["a","c",3], ["c","b",2], ["b","d",5], ["c","d",7]],
  "directed": false,
  "start": "a",
  "target": "d"
}
```
Respuesta (recortada):
```json
{
  "dist": {"a":0,"b":4,"c":3,"d":9},
  "prev": {"a":null,"b":"a","c":"a","d":"b"},
  "path": ["a","b","d"],
  "cost": 9,
  "graph_png_b64": "..."
}
```

## Endpoint de imagen directa
`GET /graph.png?e=a,b,4&e=a,c,3&e=c,b,2&e=b,d,5&e=c,d,7&directed=0&path=a,b,d`

- `e=u,v,w` (varias veces)
- `directed=1|0`
- `path=n1,n2,...` (opcional)

## Pruebas
```bash
pytest -q
```
