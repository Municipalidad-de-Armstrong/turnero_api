from datetime import datetime, timezone

from app.models.turno import Turno
from app.schemas.turno import TurnoResponse

def turno_to_response(turno: Turno, include_pii: bool = False) -> TurnoResponse:
    """Converts a Turno ORM instance to TurnoResponse schema, handling PII decryption."""
    from app.services.turno_service import decrypt_pii

    c = turno.ciudadano
    t = turno.tramite
    a = t.area if t else None
    dni_v = decrypt_pii(c.dni_cifrado) if (include_pii and c and c.dni_cifrado) else None
    ph_v = decrypt_pii(c.telefono_cifrado) if (include_pii and c and c.telefono_cifrado) else None
    return TurnoResponse(
        id=turno.id,
        ciudadano_id=turno.ciudadano_id,
        ciudadano_nombre_completo=f"{c.nombre} {c.apellido}" if c else None,
        ciudadano_dni=dni_v,
        ciudadano_telefono=ph_v,
        tramite_id=turno.tramite_id,
        tramite_nombre=t.nombre if t else None,
        area_id=a.id if a else (t.area_id if t else None),
        area_nombre=a.nombre if a else None,
        area_direccion=a.direccion if a else None,
        emite_carnet=t.emite_carnet if t else None,
        fecha_hora_inicio=turno.fecha_hora_inicio,
        fecha_hora_fin=turno.fecha_hora_fin,
        estado=turno.estado,
        es_sobreturno=turno.es_sobreturno if turno.es_sobreturno is not None else False,
        sobreturno_prioridad=turno.sobreturno_prioridad,
        motivo_cancelacion=turno.motivo_cancelacion,
        cancelado_por_id=turno.cancelado_por_id,
        resultado_comentario=turno.resultado_comentario,
        variantes=list(turno.variantes) if turno.variantes else [],
        created_at=turno.created_at or datetime.now(timezone.utc),
    )
