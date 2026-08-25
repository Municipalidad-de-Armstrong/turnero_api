AREAS_DATA = [
    {
        "nombre": "Tránsito y Licencias",
        "descripcion": "Licencias de conducir, exámenes y patentes automotrices.",
        "direccion": "San Martín 1790 (Palacio Municipal)",
    },
    {
        "nombre": "Obras Privadas y Catastro",
        "descripcion": "Permisos de edificación, mensuras, visado de planos y catastro urbano.",
        "direccion": "San Martín 1790 (Piso 1)",
    },
    {
        "nombre": "Comercio e Inspección General",
        "descripcion": "Habilitaciones comerciales, industriales y control bromatológico.",
        "direccion": "San Martín 1790 (Planta Baja)",
    },
    {
        "nombre": "Desarrollo Social y Salud",
        "descripcion": "Asistencia social, trámites de discapacidad y carnet de manipulador.",
        "direccion": "Rivadavia y Fischer (Centro Asistencial)",
    },
]

TRAMITES_DATA = [
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
