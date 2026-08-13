from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import encrypt_pii, hash_dni_hmac
from app.models.turno import Turno
from app.models.user import User
from app.models.usurpation_report import UsurpationReport


async def seed_turnos_and_reports(
    session: AsyncSession,
    users: dict[str, User],
    catalog: dict[str, dict[str, Any]],
) -> None:
    """Seed test turnos and DNI usurpation reports."""
    now = datetime.now(timezone.utc)

    c1 = users.get("ciudadano.dev@armstrong.gov.ar")
    c2 = users.get("ciudadano2.dev@armstrong.gov.ar")
    c3 = users.get("ciudadano3.dev@armstrong.gov.ar")
    if not (c1 and c2 and c3):
        return

    licencia = catalog.get("Licencia de Conducir")
    libre_deuda = catalog.get("Libre Deuda de Infracciones")
    edificacion = catalog.get("Permiso de Edificación y Obra")
    habilitacion = catalog.get("Habilitación Comercial e Industrial")

    # Turno 1: Pasado Atendido - Libre Deuda
    if libre_deuda:
        t1_start = (now - timedelta(days=2)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        stmt1 = select(Turno).where(
            Turno.ciudadano_id == c1.id,
            Turno.tramite_id == libre_deuda["tramite"].id,
            Turno.fecha_hora_inicio == t1_start,
        )
        if not (await session.execute(stmt1)).scalar_one_or_none():
            t1 = Turno(
                ciudadano_id=c1.id,
                tramite_id=libre_deuda["tramite"].id,
                fecha_hora_inicio=t1_start,
                fecha_hora_fin=t1_start + timedelta(minutes=30),
                estado="ATENDIDO",
                resultado_comentario="Certificado Libre Deuda emitido N° 4582.",
            )
            session.add(t1)

    # Turno 2: Pasado Cancelado - Licencia
    if licencia:
        t2_start = (now - timedelta(days=1)).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        stmt2 = select(Turno).where(
            Turno.ciudadano_id == c3.id,
            Turno.tramite_id == licencia["tramite"].id,
            Turno.fecha_hora_inicio == t2_start,
        )
        if not (await session.execute(stmt2)).scalar_one_or_none():
            t2 = Turno(
                ciudadano_id=c3.id,
                tramite_id=licencia["tramite"].id,
                fecha_hora_inicio=t2_start,
                fecha_hora_fin=t2_start + timedelta(minutes=30),
                estado="CANCELADO",
                motivo_cancelacion="Cancelado por ciudadano por salud.",
                cancelado_por_id=c3.id,
            )
            var_med = licencia["variantes"].get("Examen Médico / Psicofísico")
            if var_med:
                t2.variantes.append(var_med)
            session.add(t2)

        # Turno 3: Futuro Reservado con Variantes - Licencia
        t3_start = (now + timedelta(days=1)).replace(
            hour=8, minute=30, second=0, microsecond=0
        )
        stmt3 = select(Turno).where(
            Turno.ciudadano_id == c1.id,
            Turno.tramite_id == licencia["tramite"].id,
            Turno.fecha_hora_inicio == t3_start,
        )
        if not (await session.execute(stmt3)).scalar_one_or_none():
            t3 = Turno(
                ciudadano_id=c1.id,
                tramite_id=licencia["tramite"].id,
                fecha_hora_inicio=t3_start,
                fecha_hora_fin=t3_start + timedelta(minutes=45),
                estado="RESERVADO",
            )
            for v_name in (
                "Examen Médico / Psicofísico",
                "Examen Teórico de Conducción",
            ):
                v_obj = licencia["variantes"].get(v_name)
                if v_obj:
                    t3.variantes.append(v_obj)
            session.add(t3)

    # Turno 4: Futuro Reservado - Edificación
    if edificacion:
        t4_start = (now + timedelta(days=2)).replace(
            hour=9, minute=30, second=0, microsecond=0
        )
        stmt4 = select(Turno).where(
            Turno.ciudadano_id == c2.id,
            Turno.tramite_id == edificacion["tramite"].id,
            Turno.fecha_hora_inicio == t4_start,
        )
        if not (await session.execute(stmt4)).scalar_one_or_none():
            t4 = Turno(
                ciudadano_id=c2.id,
                tramite_id=edificacion["tramite"].id,
                fecha_hora_inicio=t4_start,
                fecha_hora_fin=t4_start + timedelta(minutes=45),
                estado="RESERVADO",
            )
            v_obj = edificacion["variantes"].get(
                "Revisión de Planos de Obra Nueva"
            )
            if v_obj:
                t4.variantes.append(v_obj)
            session.add(t4)

    # Turno 5: Futuro Sobreturno - Habilitación
    if habilitacion:
        t5_start = (now + timedelta(days=3)).replace(
            hour=8, minute=30, second=0, microsecond=0
        )
        stmt5 = select(Turno).where(
            Turno.ciudadano_id == c2.id,
            Turno.tramite_id == habilitacion["tramite"].id,
            Turno.fecha_hora_inicio == t5_start,
        )
        if not (await session.execute(stmt5)).scalar_one_or_none():
            t5 = Turno(
                ciudadano_id=c2.id,
                tramite_id=habilitacion["tramite"].id,
                fecha_hora_inicio=t5_start,
                fecha_hora_fin=t5_start + timedelta(minutes=30),
                estado="RESERVADO",
                es_sobreturno=True,
                sobreturno_prioridad="ALTA",
            )
            v_obj = habilitacion["variantes"].get(
                "Inspección Bromatológica y Sanitaria"
            )
            if v_obj:
                t5.variantes.append(v_obj)
            session.add(t5)

    await session.commit()

    # Seed Usurpation Reports
    reports_data = [
        {
            "nombre": "Esteban",
            "apellido": "Martínez",
            "dni": "37123999",
            "email": "esteban.martinez@ejemplo.com",
            "telefono": "3471459888",
            "motivo": "Intento de registro de cita a mi nombre sin autorización.",
            "estado": "PENDIENTE",
            "resolved_at": None,
        },
        {
            "nombre": "Lucía",
            "apellido": "Gómez",
            "dni": "39888777",
            "email": "lucia.gomez@ejemplo.com",
            "telefono": "3471477666",
            "motivo": "Extravío de documento nacional de identidad en vía pública.",
            "estado": "RESUELTO",
            "resolved_at": now,
        },
    ]


    for rep in reports_data:
        dni_hmac = hash_dni_hmac(rep["dni"])
        stmt_rep = select(UsurpationReport).where(
            UsurpationReport.dni_hmac == dni_hmac
        )
        if not (await session.execute(stmt_rep)).scalar_one_or_none():
            report = UsurpationReport(
                nombre=rep["nombre"],
                apellido=rep["apellido"],
                dni_hmac=dni_hmac,
                dni_cifrado=encrypt_pii(rep["dni"]),
                email_contacto=rep["email"],
                telefono_cifrado=encrypt_pii(rep["telefono"]),
                motivo=rep["motivo"],
                estado=rep["estado"],
                resolved_at=rep["resolved_at"],
            )
            session.add(report)
    await session.commit()
