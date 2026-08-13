
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.schemas.notificacion import NotificationResponse, NotificationUpdateRequest
from app.services.notification_service import (
    get_user_notifications,
    update_notification_read_status,
)

router = APIRouter(prefix="/usuarios", tags=["Notificaciones"])


@router.get("/me/notificaciones", response_model=list[NotificationResponse])
async def list_my_notifications(
    solo_no_leidas: bool = True,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> list[NotificationResponse]:
    """Returns platform notifications for the authenticated user."""
    notifs = await get_user_notifications(
        db, usuario_id=current_user.id, solo_no_leidas=solo_no_leidas
    )
    return [NotificationResponse.model_validate(n) for n in notifs]


@router.patch("/me/notificaciones/{notificacion_id}", response_model=NotificationResponse)
async def update_notification_state(
    notificacion_id: int,
    data: NotificationUpdateRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> NotificationResponse:
    """Updates the read status of a notification."""
    notif = await update_notification_read_status(
        db,
        notificacion_id=notificacion_id,
        usuario_id=current_user.id,
        leida=data.leida,
    )
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificación no encontrada o no pertenece al usuario.",
        )
    return NotificationResponse.model_validate(notif)
