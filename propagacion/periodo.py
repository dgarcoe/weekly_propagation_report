"""Fechas del informe: semana analizada (pasada) y semana prevista (siguiente)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone


@dataclass(frozen=True)
class Periodo:
    publicacion: date          # lunes en que se genera el informe
    inicio: date               # lunes de la semana analizada
    fin: date                  # domingo de la semana analizada (incluido)

    @classmethod
    def para(cls, hoy: date) -> "Periodo":
        """Informe «de este lunes». Un domingo se considera ya el informe del lunes
        siguiente: la semana está prácticamente completa y la previsión mira adelante."""
        if hoy.weekday() == 6:
            hoy += timedelta(days=1)
        lunes = hoy - timedelta(days=hoy.weekday())
        return cls(lunes, lunes - timedelta(days=7), lunes - timedelta(days=1))

    @property
    def etiqueta(self) -> str:
        """``AAAA-Wnn`` (semana ISO de publicación): nombre del directorio de salida."""
        y, w, _ = self.publicacion.isocalendar()
        return f"{y}-W{w:02d}"

    @property
    def inicio_dt(self) -> datetime:
        return datetime.combine(self.inicio, time(0), tzinfo=timezone.utc)

    @property
    def fin_dt(self) -> datetime:
        """Instante final (exclusivo) de la semana analizada."""
        return datetime.combine(self.publicacion, time(0), tzinfo=timezone.utc)

    @property
    def prev_inicio(self) -> date:
        return self.inicio - timedelta(days=7)

    @property
    def sig_inicio(self) -> date:
        return self.publicacion

    @property
    def sig_fin(self) -> date:
        return self.publicacion + timedelta(days=6)

    def dias(self) -> list[date]:
        return [self.inicio + timedelta(days=i) for i in range(7)]

    def dias_siguientes(self) -> list[date]:
        return [self.sig_inicio + timedelta(days=i) for i in range(7)]


MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]


def fecha_larga(d: date) -> str:
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def fecha_corta(d: date) -> str:
    return f"{DIAS[d.weekday()]} {d.day}/{d.month}"
