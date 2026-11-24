"""Las rutas HTTP de la app, una por línea: método y path. Para comparar antes y después.

Las saca del schema OpenAPI, el mismo que dibuja /docs. Las rutas de WebSocket no están
ahí: OpenAPI solo describe HTTP.

Uso, desde pulse-api/:   uv run python -m scripts.list_routes
"""

# La app ya armada, con todos sus routers incluidos
from app.main import app

# El schema OpenAPI: {"paths": {"/api/v1/posts": {"get": {...}, "post": {...}}, ...}}
schema = app.openapi()
# Una línea por método y path: "GET    /api/v1/posts"
lines = [
    # El método en mayúsculas, alineado a 6 caracteres, y el path
    f"{method.upper():<6} {path}"
    # Cada path del schema...
    for path, operations in schema["paths"].items()
    # ...y cada método (get, post...) de ese path
    for method in operations
]
# Ordenadas por path y método: el orden en que se registraron no cambia el resultado
print("\n".join(sorted(lines, key=lambda line: (line.split()[1], line))))