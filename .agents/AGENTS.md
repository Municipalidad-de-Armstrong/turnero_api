# Reglas del Proyecto (Municipalidad de Armstrong - Turnero)

Este archivo define las directrices y reglas obligatorias para los agentes de Inteligencia Artificial que colaboren en este repositorio.

## Reglas Obligatorias Compartidas (Backend y Frontend)

1. **Límite de Líneas por Archivo:**
   - Los archivos generados o modificados **no pueden exceder las 300 líneas**.
   - Si un archivo supera este límite, debe ser refactorizado para separar responsabilidades.

2. **Cobertura de Pruebas Automatizadas:**
   - **Todas las funcionalidades deben ser testeadas**.
   - Se deben crear tests automáticos (unitarios o de integración) para cada nueva característica o cambio de lógica de negocio.

3. **Cumplimiento Estricto de Lint:**
   - **Está prohibido ignorar procesos de lint con comentarios** (como `# noqa`, `# type: ignore`, `// eslint-disable-next-line`, `/* eslint-disable */` o `@ts-ignore`).
   - Se deben corregir todos los warnings y errors detectados por las herramientas de linting y analizadores estáticos.

---

## Estructura del Proyecto y Stack Tecnológico

- **Backend (`turnero_api`):** FastAPI 0.139+ (Python 3.13+), SQLAlchemy 2.0 (ORM), Alembic, Pydantic v2, PostgreSQL 18, Redis 8, Celery v5.6.
- **Frontend (`turnero`):** Next.js 16 (App Router), TypeScript 7, Tailwind CSS v4, Zustand v5, Jest/Playwright.
- **Flujo de Trabajo:** Basado en slices verticales definidos en [desarrollo-hoja-ruta.md](file:///c:/Users/pablo/OneDrive/Escritorio/Municipalidad%20de%20Armstrong/docs/proceso/desarrollo-hoja-ruta.md).
