import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notificacion import Notificacion

logger = logging.getLogger("turnero.notifications")


async def create_in_app_notification(
    db: AsyncSession,
    usuario_id: int,
    titulo: str,
    mensaje: str,
) -> Notificacion:
    """Creates a persistent platform notification for a citizen/user."""
    notif = Notificacion(
        usuario_id=usuario_id,
        titulo=titulo,
        mensaje=mensaje,
        leida=False,
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return notif


async def send_email_notification(
    to_email: str,
    subject: str,
    body: str,
) -> bool:
    """Sends an email notification via SMTP (Mock/Log in development environment)."""
    logger.info(f"[EMAIL NOTIFICATION] To: {to_email} | Subject: '{subject}' | Body: {body[:100]}...")
    return True


async def send_whatsapp_notification(
    telefono: str,
    mensaje: str,
) -> bool:
    """Sends a WhatsApp notification via municipal HTTP gateway (Mocked in dev)."""
    logger.info(f"[WHATSAPP MOCK] To: {telefono} | Message: {mensaje[:100]}...")
    return True


async def get_user_notifications(
    db: AsyncSession,
    usuario_id: int,
    solo_no_leidas: bool = False,
) -> list[Notificacion]:
    """Retrieves notifications for a user."""
    query = select(Notificacion).where(Notificacion.usuario_id == usuario_id)
    if solo_no_leidas:
        query = query.where(Notificacion.leida.is_(False))
    query = query.order_by(Notificacion.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_notification_read_status(
    db: AsyncSession,
    notificacion_id: int,
    usuario_id: int,
    leida: bool,
) -> Notificacion | None:
    """Updates the read status of a notification belonging to the user."""
    query = select(Notificacion).where(
        Notificacion.id == notificacion_id,
        Notificacion.usuario_id == usuario_id,
    )
    result = await db.execute(query)
    notif = result.scalar_one_or_none()
    if not notif:
        return None

    notif.leida = leida
    await db.commit()
    await db.refresh(notif)
    return notif
