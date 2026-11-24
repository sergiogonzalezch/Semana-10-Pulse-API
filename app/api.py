"""El router de la versión 1 de la API: junta los routers de cada recurso bajo /api/v1."""

# APIRouter: el mismo objeto que usa cada recurso, aquí como router padre
from fastapi import APIRouter

# Los routers de cada recurso; cada uno trae su prefix (/auth, /posts...) y su tag
from app.routers import auth, categories, comments, notifications, posts, users, ws

# El prefix de la versión vive en UN solo lugar: una v2 sería otro router como este
api_router = APIRouter(prefix="/api/v1")

# Cada include_router suma las rutas de un recurso: /api/v1 + /auth + /token
api_router.include_router(auth.router)
api_router.include_router(users.router)
# Categorías y posts
api_router.include_router(categories.router)
api_router.include_router(posts.router)
# Comentarios: sus rutas ya empiezan con /posts/... o /comments/...
api_router.include_router(comments.router)
api_router.include_router(notifications.router)
api_router.include_router(ws.router)