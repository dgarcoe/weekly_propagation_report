"""Descargas HTTP con caché local en disco y reintentos.

Si una fuente falla se lanza ``FuenteNoDisponible``; las secciones la capturan
y marcan su bloque como «sin datos esta semana».
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import config

log = logging.getLogger(__name__)


class FuenteNoDisponible(RuntimeError):
    """Una fuente de datos no ha respondido o ha devuelto algo inservible."""


_session: requests.Session | None = None


def session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        retry = Retry(
            total=int(os.environ.get("PROPAGACION_REINTENTOS", 4)),
            backoff_factor=2,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "POST"),
        )
        s.mount("https://", HTTPAdapter(max_retries=retry))
        s.mount("http://", HTTPAdapter(max_retries=retry))
        s.headers["User-Agent"] = config.USER_AGENT
        _session = s
    return _session


def _cache_path(url: str, params: dict | None) -> Path:
    key = url + "?" + repr(sorted((params or {}).items()))
    h = hashlib.sha256(key.encode()).hexdigest()[:24]
    return config.CACHE_DIR / h


def fetch_bytes(url: str, params: dict | None = None, max_age_h: float = 6,
                timeout: float | None = None) -> bytes:
    """Descarga ``url`` (con caché de ``max_age_h`` horas).

    Si la descarga falla pero hay una copia en caché (aunque sea antigua),
    se usa esa copia antes que rendirse.
    """
    path = _cache_path(url, params)
    if path.exists() and (time.time() - path.stat().st_mtime) < max_age_h * 3600:
        log.debug("caché: %s", url)
        return path.read_bytes()
    try:
        r = session().get(url, params=params, timeout=timeout or config.HTTP_TIMEOUT)
        r.raise_for_status()
        data = r.content
    except requests.RequestException as e:
        if path.exists():
            log.warning("fallo al descargar %s (%s); uso caché antigua", url, e)
            return path.read_bytes()
        raise FuenteNoDisponible(f"{url}: {e}") from e
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


def fetch_text(url: str, params: dict | None = None, **kw) -> str:
    return fetch_bytes(url, params, **kw).decode("utf-8", errors="replace")


def fetch_json(url: str, params: dict | None = None, **kw):
    import json

    try:
        return json.loads(fetch_text(url, params, **kw))
    except ValueError as e:
        raise FuenteNoDisponible(f"{url}: JSON no válido ({e})") from e
