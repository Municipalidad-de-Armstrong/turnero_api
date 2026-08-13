from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seeds.catalog_seed_data import AREAS_DATA, TRAMITES_DATA
from app.models.area import Area
from app.models.tramite import Tramite
from app.models.tramite_documento import TramiteDocumento
from app.models.tramite_enlace import TramiteEnlace
from app.models.variante import Variante


def _ensure_seed_files_exist():
    import os
    target = os.path.join("uploads", "tramites", "ficha_medica_ejemplo.pdf")
    if not os.path.exists(target):
        os.makedirs(os.path.dirname(target), exist_ok=True)
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

            doc = SimpleDocTemplate(target, pagesize=letter)
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=16, textColor=colors.HexColor("#FE8F00"), alignment=1)
            body_style = ParagraphStyle("Body", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=14)
            story = [
                Paragraph("MUNICIPALIDAD DE ARMSTRONG", title_style),
                Spacer(1, 10),
                Paragraph("<b>FICHA MÉDICA DE APTITUD OBLIGATORIA</b>", title_style),
                Spacer(1, 15),
                Paragraph("Formulario oficial para trámites de Licencia de Conducir y Habilitaciones. Complete los datos personales y de aptitud médica solicitados.", body_style)
            ]
            doc.build(story)
        except Exception:
            with open(target, "wb") as f:
                f.write(b"%PDF-1.4 sample pdf file")


async def seed_catalog(
    session: AsyncSession,
) -> dict[str, dict[str, Any]]:
    """Seed areas, tramites, variantes, documentos y enlaces."""
    _ensure_seed_files_exist()

    areas_data = AREAS_DATA

    areas_db: dict[str, Area] = {}
    for area_info in areas_data:
        stmt = select(Area).where(Area.nombre == area_info["nombre"])
        res = await session.execute(stmt)
        area = res.scalar_one_or_none()
        if not area:
            area = Area(
                nombre=area_info["nombre"],
                descripcion=area_info["descripcion"],
            )
            session.add(area)
            await session.commit()
            await session.refresh(area)
        areas_db[area_info["nombre"]] = area

    tramites_data = TRAMITES_DATA

    catalog_result: dict[str, dict[str, Any]] = {}

    for tr_info in tramites_data:
        area = areas_db[str(tr_info["area_nombre"])]
        stmt_t = select(Tramite).where(
            Tramite.nombre == str(tr_info["nombre"]), Tramite.area_id == area.id
        )
        res_t = await session.execute(stmt_t)
        tramite = res_t.scalar_one_or_none()

        if not tramite:
            tramite = Tramite(
                area_id=area.id,
                nombre=str(tr_info["nombre"]),
                descripcion=str(tr_info["descripcion"]),
                documentacion_requerida=str(tr_info["documentacion_requerida"]),
                requerimientos_previos=str(tr_info["requerimientos_previos"]),
                emite_carnet=bool(tr_info["emite_carnet"]),
                limite_sobreturnos_diarios=int(tr_info["limite_sobreturnos_diarios"]),
            )
            session.add(tramite)
            await session.commit()
            await session.refresh(tramite)

        vars_db: dict[str, Variante] = {}
        for var_data in tr_info["variantes"]:
            v_name = str(var_data["nombre"])
            stmt_v = select(Variante).where(
                Variante.tramite_id == tramite.id,
                Variante.nombre == v_name,
            )
            res_v = await session.execute(stmt_v)
            var_obj = res_v.scalar_one_or_none()
            if not var_obj:
                var_obj = Variante(
                    tramite_id=tramite.id,
                    nombre=v_name,
                    descripcion=str(var_data["descripcion"]),
                    duracion_minutos=int(var_data["duracion_minutos"]),
                )
                session.add(var_obj)
                await session.commit()
                await session.refresh(var_obj)
            vars_db[v_name] = var_obj

        # Si el trámite no posee variantes creadas, generar variante inicial por defecto
        existing_vars_stmt = select(Variante).where(Variante.tramite_id == tramite.id)
        existing_vars_res = await session.execute(existing_vars_stmt)
        if not list(existing_vars_res.scalars().all()):
            var_def = Variante(
                tramite_id=tramite.id,
                nombre="Atención General",
                descripcion="Atención estándar del trámite",
                duracion_minutos=15,
            )
            session.add(var_def)
            await session.commit()
            await session.refresh(var_def)
            vars_db["Atención General"] = var_def

        for enl_data in tr_info["enlaces"]:
            desc = str(enl_data["descripcion"])
            stmt_e = select(TramiteEnlace).where(
                TramiteEnlace.tramite_id == tramite.id,
                TramiteEnlace.descripcion == desc,
            )
            res_e = await session.execute(stmt_e)
            if not res_e.scalar_one_or_none():
                session.add(
                    TramiteEnlace(
                        tramite_id=tramite.id,
                        descripcion=desc,
                        url=str(enl_data["url"]),
                    )
                )

        for doc_data in tr_info["documentos"]:
            doc_name = str(doc_data["nombre"])
            stmt_d = select(TramiteDocumento).where(
                TramiteDocumento.tramite_id == tramite.id,
                TramiteDocumento.nombre == doc_name,
            )
            res_d = await session.execute(stmt_d)
            if not res_d.scalar_one_or_none():
                session.add(
                    TramiteDocumento(
                        tramite_id=tramite.id,
                        nombre=doc_name,
                        ruta_archivo=str(doc_data["ruta_archivo"]),
                    )
                )

        await session.commit()
        catalog_result[tramite.nombre] = {
            "tramite": tramite,
            "variantes": vars_db,
        }

    return catalog_result
