from typing import Any, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors

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
) -> Dict[str, Dict[str, Any]]:
    """Seed areas, tramites, variantes, documentos y enlaces."""
    _ensure_seed_files_exist()

    areas_data = [
        {
            "nombre": "Tránsito y Licencias",
            "descripcion": "Licencias de conducir, exámenes y patentes automotrices.",
        },
        {
            "nombre": "Obras Privadas y Catastro",
            "descripcion": "Permisos de edificación, mensuras, visado de planos y catastro urbano.",
        },
        {
            "nombre": "Comercio e Inspección General",
            "descripcion": "Habilitaciones comerciales, industriales y control bromatológico.",
        },
        {
            "nombre": "Desarrollo Social y Salud",
            "descripcion": "Asistencia social, trámites de discapacidad y carnet de manipulador.",
        },
    ]

    areas_db: Dict[str, Area] = {}
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

    tramites_data = [
        {
            "area_nombre": "Tránsito y Licencias",
            "nombre": "Licencia de Conducir",
            "descripcion": "Gestión presencial de emisión, renovación y duplicados de licencias.",
            "documentacion_requerida": (
                "**DNI Original** y fotocopia de ambas caras.\n"
                "- Certificado de Grupo Sanguíneo firmado por profesional.\n"
                "- Ficha médica de aptitud completada."
            ),
            "requerimientos_previos": (
                "Constatar libre deuda de infracciones de tránsito en el Juzgado de Faltas."
            ),
            "emite_carnet": True,
            "limite_sobreturnos_diarios": 5,
            "variantes": [
                {
                    "nombre": "Examen Médico / Psicofísico",
                    "descripcion": "Evaluación de aptitud visual, auditiva y médica.",
                    "duracion_minutos": 15,
                },
                {
                    "nombre": "Examen Teórico de Conducción",
                    "descripcion": "Examen en aula sobre normas de tránsito.",
                    "duracion_minutos": 30,
                },
            ],
            "enlaces": [
                {
                    "descripcion": "Consulta de Infracciones de Tránsito Santa Fe",
                    "url": "https://www.santafe.gob.ar/infracciones/",
                },
                {
                    "descripcion": "Portal Oficial Municipalidad de Armstrong",
                    "url": "https://armstrong.gob.ar/",
                },
            ],
            "documentos": [
                {
                    "nombre": "Ficha Médica Obligatoria",
                    "ruta_archivo": "/static/uploads/tramites/ficha_medica_ejemplo.pdf",
                }
            ],
        },
        {
            "area_nombre": "Tránsito y Licencias",
            "nombre": "Libre Deuda de Infracciones",
            "descripcion": "Emisión de certificado de libre deuda de faltas de tránsito.",
            "documentacion_requerida": (
                "**DNI Original**.\n- Cédula de identificación del vehículo o título."
            ),
            "requerimientos_previos": "No poseer causas contravencionales pendientes.",
            "emite_carnet": False,
            "limite_sobreturnos_diarios": 10,
            "variantes": [
                {
                    "nombre": "Emisión de Certificado de Libre Deuda",
                    "descripcion": "Verificación contravencional y emisión de certificado.",
                    "duracion_minutos": 15,
                }
            ],
            "enlaces": [
                {
                    "descripcion": "Juzgado de Faltas - Consulta de Infracciones Santa Fe",
                    "url": "https://www.santafe.gob.ar/infracciones/",
                }
            ],
            "documentos": [],
        },
        {
            "area_nombre": "Obras Privadas y Catastro",
            "nombre": "Permiso de Edificación y Obra",
            "descripcion": "Aprobación de planos y permiso de inicio de obra nueva o ampliación.",
            "documentacion_requerida": (
                "**Planos de Obra** en formato digital firmados por profesional matriculado.\n"
                "- Escritura o título de propiedad."
            ),
            "requerimientos_previos": "Informe de factibilidad técnica emitido por Catastro.",
            "emite_carnet": False,
            "limite_sobreturnos_diarios": 3,
            "variantes": [
                {
                    "nombre": "Revisión de Planos de Obra Nueva",
                    "descripcion": "Visado técnico inicial de expediente.",
                    "duracion_minutos": 45,
                },
                {
                    "nombre": "Inspección Final de Obra",
                    "descripcion": "Verificación in situ para final de obra.",
                    "duracion_minutos": 60,
                },
            ],
            "enlaces": [
                {
                    "descripcion": "Colegio de Arquitectos de la Provincia de Santa Fe",
                    "url": "https://www.capsf.org.ar/",
                }
            ],
            "documentos": [],
        },
        {
            "area_nombre": "Comercio e Inspección General",
            "nombre": "Habilitación Comercial e Industrial",
            "descripcion": "Trámite de radicación, apertura y habilitación de locales e industrias.",
            "documentacion_requerida": (
                "**Habilitación previa de Bomberos**.\n"
                "- Contrato de alquiler o título del inmueble.\n"
                "- Constancia de inscripción AFIP/API."
            ),
            "requerimientos_previos": "Zonificación apta aprobada por Planeamiento Urbano.",
            "emite_carnet": True,
            "limite_sobreturnos_diarios": 2,
            "variantes": [
                {
                    "nombre": "Inspección Bromatológica y Sanitaria",
                    "descripcion": "Control higiénico-sanitario del local.",
                    "duracion_minutos": 30,
                },
                {
                    "nombre": "Inspección de Seguridad e Higiene",
                    "descripcion": "Verificación de medidas de matafuegos y salidas.",
                    "duracion_minutos": 30,
                },
            ],
            "enlaces": [
                {
                    "descripcion": "AFIP / ARCA - Inscripción y Constancia",
                    "url": "https://www.afip.gob.ar/",
                },
                {
                    "descripcion": "Municipalidad de Armstrong - Portal de Trámites",
                    "url": "https://armstrong.gob.ar/",
                },
            ],
            "documentos": [],
        },

    ]

    catalog_result: Dict[str, Dict[str, Any]] = {}

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

        vars_db: Dict[str, Variante] = {}
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
