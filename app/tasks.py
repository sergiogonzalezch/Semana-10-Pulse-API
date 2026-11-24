"""Lo que corre DESPUÉS de responder: el aviso por WebSocket, el "email" y los analytics.

Reglas de toda background task:
- Recibe ids y datos simples, nunca la sesión ni objetos del request.
- Abre su propia sesión, y la cierra antes de esperar algo lento.
- Atrapa sus errores y los deja en el log: el cliente ya tiene su respuesta y nadie más
  se va a enterar de que falló.
"""
from __future__ import annotations

# asyncio para simular la espera del servidor de correo; json y logging para escribir
import asyncio
import json
import logging
# La hora de cada línea, en UTC; Path y Any para los tipos
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# aiofiles escribe archivos sin bloquear el event loop
import aiofiles

# La configuración, la fábrica de sesiones y el manager de WebSockets
from app.config import settings
from app.database import async_session_factory
from app.realtime import manager
# Los repositories y el schema con el que viaja la notificación
from app.repositories.notification_repository import NotificationRepository
from app.repositories.user_repo import UserRepository
from app.schemas.notification import NotificationResponse

# El logger de las tareas
logger = logging.getLogger("pulse_api.tasks")


async def append_line(path: Path, line: str) -> None:
    # La carpeta ya existe: la crea el lifespan al arrancar
    # "a": agrega al final sin borrar lo que había
    async with aiofiles.open(path, "a", encoding="utf-8") as file:
        await file.write(line + "\n")


async def push_notification(notification_id: int) -> None:
    """Manda la notificación por WebSocket a su destinatario, si está conectado."""
    try:
        # Una sesión propia: la del request es del request
        async with async_session_factory() as db:
            notification = await NotificationRepository(db).get(notification_id)
        # Se borró antes de que la tarea corriera (el comentario o el post): nada que mandar
        if notification is None:
            logger.info("notification %s no longer exists, push skipped", notification_id)
            return
        # El mismo JSON que devuelve GET /notifications
        payload = NotificationResponse.model_validate(notification).model_dump(mode="json")
        delivered = await manager.send_to_user(
            notification.user_id, {"type": "notification", "data": payload}
        )
        # Cero si no estaba conectado: no es un error, la lee después
        logger.info("notification %s pushed to %s connection(s)", notification_id, delivered)
    # Cualquier error queda en el log, con su traceback
    except Exception:
        logger.exception("push of notification %s failed", notification_id)


async def send_comment_email(notification_id: int) -> None:
    """El "email" al autor del post. Simulado: espera y escribe una línea en outbox.log."""
    try:
        # Lee lo necesario y CIERRA la sesión antes de la espera lenta
        async with async_session_factory() as db:
            notification = await NotificationRepository(db).get(notification_id)
            # Ya no existe: no hay email que mandar
            if notification is None:
                logger.info("notification %s no longer exists, email skipped", notification_id)
                return
            # El destinatario: su email está en users
            recipient = await UserRepository(db).get(notification.user_id)
        # Lo que tardaría hablar con un servidor de correo (SMTP o la API de un proveedor)
        await asyncio.sleep(settings.email_delay_seconds)
        # La línea del outbox: cuándo, a quién y el asunto
        subject = f"{notification.actor.username} comentó tu post {notification.post_id}"
        sent_at = datetime.now(UTC).isoformat(timespec="seconds")
        await append_line(settings.outbox_path, f"{sent_at} to={recipient.email} subject={subject!r}")
        # Y la línea del log del servidor
        logger.info("email sent to %s", recipient.email)
    # El cliente ya recibió su 201: el error solo puede quedar aquí
    except Exception:
        logger.exception("email for notification %s failed", notification_id)


async def log_event(event: str, data: dict[str, Any]) -> None:
    """Un evento de analytics: una línea JSON en analytics.log."""
    try:
        # La hora, el nombre del evento y sus datos, en una sola línea
        record = {"at": datetime.now(UTC).isoformat(timespec="seconds"), "event": event, **data}
        await append_line(settings.analytics_path, json.dumps(record, ensure_ascii=False))
        logger.info("event %s logged", event)
    # Un evento perdido no tumba nada: se registra y se sigue
    except Exception:
        logger.exception("event %s could not be logged", event)
