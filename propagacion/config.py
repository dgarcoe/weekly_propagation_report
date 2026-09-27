"""Configuración central: estación de referencia, destinos DX, bandas y URLs."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache"
OUTPUT_DIR = ROOT / "informes"
TEMPLATES_DIR = ROOT / "templates"

# --- Estación de referencia -------------------------------------------------
STATION_NAME = "Vigo"
STATION_CALL = "EA1RKV"
STATION_LOCATOR = "IN52PE"

# Cuadrículas que consideramos «Galicia» al filtrar spots (ampliable a IN62/IN63).
GALICIA_SQUARES = ("IN52", "IN53")


@dataclass(frozen=True)
class Destino:
    key: str
    nombre: str
    lat: float
    lon: float


# Destinos DX para la previsión VOACAP y la línea gris.
DESTINOS = (
    Destino("na_este", "Norteamérica este (Nueva York)", 40.71, -74.01),
    Destino("caribe", "Caribe (Santo Domingo)", 18.49, -69.93),
    Destino("sudamerica", "Sudamérica (Buenos Aires)", -34.60, -58.38),
    Destino("japon", "Japón (Tokio)", 35.68, 139.69),
    Destino("oceania", "Oceanía (Sídney)", -33.87, 151.21),
    Destino("sudafrica", "Sudáfrica (Johannesburgo)", -26.20, 28.05),
)

# Bandas HF/VHF: nombre -> (f_min MHz, f_max MHz, frecuencia típica para VOACAP)
BANDAS = {
    "160m": (1.8, 2.0, 1.84),
    "80m": (3.5, 4.0, 3.6),
    "60m": (5.25, 5.45, 5.36),
    "40m": (7.0, 7.3, 7.1),
    "30m": (10.1, 10.15, 10.13),
    "20m": (14.0, 14.35, 14.1),
    "17m": (18.068, 18.168, 18.1),
    "15m": (21.0, 21.45, 21.1),
    "12m": (24.89, 24.99, 24.93),
    "10m": (28.0, 29.7, 28.2),
    "6m": (50.0, 54.0, 50.3),
    "4m": (70.0, 70.5, 70.1),
    "2m": (144.0, 148.0, 144.5),
}
BANDAS_HF = ["160m", "80m", "60m", "40m", "30m", "20m", "17m", "15m", "12m", "10m"]
# Bandas que calculamos en VOACAP (máximo 11 frecuencias por tarjeta FREQUENCY).
BANDAS_VOACAP = ["80m", "40m", "30m", "20m", "17m", "15m", "12m", "10m"]

# --- Fuentes de datos -------------------------------------------------------
URL_NOAA_DSD = "https://services.swpc.noaa.gov/text/daily-solar-indices.txt"
URL_NOAA_DGD = "https://services.swpc.noaa.gov/text/daily-geomagnetic-indices.txt"
URL_NOAA_KP = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
URL_NOAA_FLARES = "https://services.swpc.noaa.gov/json/goes/primary/xray-flares-7-day.json"
URL_NOAA_27DO = "https://services.swpc.noaa.gov/text/27-day-outlook.txt"
URL_NOAA_CYCLE = "https://services.swpc.noaa.gov/json/solar-cycle/observed-solar-cycle-indices.json"
URL_NOAA_CYCLE_PRED = "https://services.swpc.noaa.gov/json/solar-cycle/predicted-solar-cycle.json"
URL_DRAO_FLUX = "https://www.spaceweather.gc.ca/solar_flux_data/daily_flux_values/fluxtable.txt"
URL_WSPR_LIVE = "https://db1.wspr.live/"
URL_RBN_DAY = "https://data.reversebeacon.net/rbn_history/{fecha:%Y%m%d}.zip"
# El antiguo servlet DIDBGetValues ya no existe; el formulario scaled.php redirige a este.
URL_GIRO = "https://lgdc.uml.edu/fastchar/getbest"
GIRO_URSI_ARENOSILLO = "EA036"
URL_CELESTRAK_AMATEUR = "https://celestrak.org/NORAD/elements/gp.php?GROUP=amateur&FORMAT=tle"
# Calendario público de Google que enlaza contestcalendar.com (WA7BNM).
URL_CONTEST_ICS = ("https://calendar.google.com/calendar/ical/"
                   "9o3or51jjdsantmsqoadmm949k%40group.calendar.google.com/public/basic.ics")

# Prefijos para filtrar RBN (el fichero no trae locator): distrito EA1.
RBN_CALL_REGEX = r"^E[A-H]1[A-Z]"

# Satélites de aficionado que listamos (nombre tal cual en el TLE de CelesTrak).
SATELITES = (
    "ISS (ZARYA)",
    "SO-50",
    "AO-7",
    "AO-27",
    "FO-29",
    "RS-44",
    "IO-86",
    "PO-101",
    "AO-123",
    "SO-125",
)

HTTP_TIMEOUT = 60
USER_AGENT = "EA1RKV-informe-propagacion/1.0 (+https://github.com/dgarcoe/weekly_propagation_report)"
