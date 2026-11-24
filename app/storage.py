"""Las imágenes de los posts en disco: validarlas, guardarlas con un nombre nuevo y borrarlas."""
from __future__ import annotations

# uuid para el nombre nuevo de cada archivo; Path para las rutas
import uuid
from pathlib import Path

# aiofiles escribe en disco sin bloquear el event loop
import aiofiles
# El archivo que llega en un multipart/form-data
from fastapi import UploadFile

# La carpeta y el máximo; los dos errores de dominio (413 y 415)
from app.config import settings
from app.exceptions import FileTooLargeError, UnsupportedMediaTypeError

# Los tipos que aceptamos: la extensión con la que se guardan y sus primeros bytes
# ("magic bytes"): todo JPEG empieza con FF D8 FF, todo PNG con \x89PNG\r\n\x1a\n
IMAGE_TYPES: dict[str, tuple[str, bytes]] = {
    "image/jpeg": (".jpg", b"\xff\xd8\xff"),
    "image/png": (".png", b"\x89PNG\r\n\x1a\n"),
}
# Se lee y se escribe de 64 KB en 64 KB: nunca el archivo completo en memoria
CHUNK_SIZE = 64 * 1024


async def save_image(file: UploadFile) -> str:
    """Valida tipo, contenido y tamaño, y guarda el archivo. Devuelve el nombre nuevo."""
    # 1. El tipo que DICE el cliente (el Content-Type de la parte del formulario)
    kind = IMAGE_TYPES.get(file.content_type or "")
    if kind is None:
        raise UnsupportedMediaTypeError(f"Solo JPEG o PNG; llegó {file.content_type}")
    extension, signature = kind
    # 2. Lo que el archivo ES: el cliente puede mentir en el tipo, los bytes no
    chunk = await file.read(CHUNK_SIZE)
    if not chunk.startswith(signature):
        raise UnsupportedMediaTypeError(
            f"El archivo dice ser {file.content_type}, pero su contenido no lo es"
        )
    # 3. Un nombre nuevo: nunca el del cliente (podría ser ../../app/main.py)
    filename = f"{uuid.uuid4().hex}{extension}"
    # La carpeta ya existe: la crea el lifespan al arrancar
    path = settings.upload_dir / filename
    # 4. El tamaño se cuenta mientras se escribe, chunk por chunk
    size = 0
    try:
        async with aiofiles.open(path, "wb") as out:
            # El primer chunk ya está leído: se escribe y se pide el siguiente
            while chunk:
                size += len(chunk)
                # Pasó del máximo: se corta aquí, sin escribir el resto
                if size > settings.max_image_bytes:
                    raise FileTooLargeError(
                        f"La imagen pasa de {settings.max_image_bytes // (1024 * 1024)} MB"
                    )
                await out.write(chunk)
                chunk = await file.read(CHUNK_SIZE)
    # Si se cortó a la mitad, el archivo incompleto se borra: no queda basura en disco
    except FileTooLargeError:
        path.unlink(missing_ok=True)
        raise
    # El nombre con el que quedó guardado
    return filename


def image_path(filename: str) -> Path:
    # La ruta en disco de una imagen guardada
    return settings.upload_dir / filename


def delete_image(filename: str) -> None:
    # Borra el archivo; si ya no estaba, no pasa nada
    image_path(filename).unlink(missing_ok=True)
