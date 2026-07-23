"""Utilidades para mapear entre paths de filesystem y URLs públicas de archivos subidos.

El proyecto sirve archivos desde el directorio ``UPLOAD_DIR`` (``uploads/``) montados
bajo el prefijo ``STATIC_URL_PREFIX`` (``/static/uploads``) en FastAPI. Históricamente
estos valores estaban hardcodeados en varios puntos, lo que provocó un bug donde el
listener de borrado trataba una URL relativa como un path FS y nunca eliminaba el
archivo físico. Este módulo centraliza la conversión para que ambos extremos usen la
misma definición de la relación URL <-> filesystem.
"""
import os

from app.core.config import settings


def fs_path_to_url(fs_path: str) -> str:
    """Convierte un path de filesystem relativo (ej. ``uploads/tramites/x.pdf``) a la
    URL pública que sirve StaticFiles (``/static/uploads/tramites/x.pdf``)."""
    normalized = fs_path.replace("\\", "/").lstrip("/")
    prefix = settings.UPLOAD_DIR.replace("\\", "/").rstrip("/")
    if normalized.startswith(prefix + "/"):
        relative = normalized[len(prefix) + 1:]
    elif normalized == prefix:
        relative = ""
    else:
        relative = normalized
    base = settings.STATIC_URL_PREFIX.rstrip("/")
    return f"{base}/{relative}" if relative else f"{base}/"


def url_to_fs_path(url: str) -> str:
    """Convierte una URL pública (``/static/uploads/tramites/x.pdf``) al path de
    filesystem relativo donde realmente vive el archivo (``uploads/tramites/x.pdf``)."""
    if not url:
        return ""
    normalized = url.replace("\\", "/")
    prefix = settings.STATIC_URL_PREFIX.replace("\\", "/").rstrip("/")
    if normalized.startswith(prefix + "/"):
        relative = normalized[len(prefix) + 1:]
    elif normalized == prefix:
        relative = ""
    else:
        # Ya es un path FS o un valor inesperado: devolver tal cual para no romper.
        return normalized.lstrip("/")
    base = settings.UPLOAD_DIR.replace("\\", "/").rstrip("/")
    return os.path.join(base, relative) if relative else base
