# Informe semanal de propagación — EA1RKV

Generador del **informe semanal de propagación HF/VHF** del radioclub EA1RKV (Unión de
Radioaficionados de Vigo-Val Miñor). Estación de referencia: Vigo, locator **IN52PE**.

La idea: combinar **lo que dice la teoría** (índices solares, predicciones VOACAP) con **lo que
pasó de verdad** (spots WSPR y RBN desde Galicia).

## Qué contiene cada informe

| Sección | Contenido | Fuentes |
|---|---|---|
| 1. El Sol | SFI medio/máx./mín. y tendencia, SSN efectivo (≈ 1,14·SFI − 73,2), Ap medio, Kp máx. con semáforo 🟢🟡🔴, fulguraciones M/X, outlook de NOAA para la semana y gráfica de SFI de 12 meses | NOAA SWPC, DRAO Penticton |
| 2. Lo que pasó de verdad | Mapa de calor hora UTC × banda, DX de la semana por banda (distancia desde IN52PE), rutas por continente y mapa azimutal | wspr.live (IN52/IN53), RBN (distrito EA1) |
| 3. Previsión | Fiabilidad VOACAP hacia NA este, Caribe, Sudamérica, Japón, Oceanía y Sudáfrica; NVIS/regional en 80 y 40 m a partir de foF2 de El Arenosillo; línea gris | voacapl, GIRO DIDBase, cálculo propio |
| 4. Agenda | Concursos del fin de semana, lluvias de meteoros, pases de satélites sobre Vigo | WA7BNM, IMO, CelesTrak + skyfield |
| 5. Comentario | Hueco `<!-- COMENTARIO -->` para un socio. **No se publica sin él.** | — |

Si una fuente falla, el informe se genera igualmente con esa sección marcada como
«_Sin datos esta semana._».

## Uso

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

python -m propagacion                       # informe de esta semana → informes/AAAA-Wnn/
python -m propagacion --fecha 2026-09-28    # como si hoy fuera esa fecha
python -m propagacion --sin-rbn             # sin RBN (los ZIP diarios pesan ~15 MB cada uno)
python -m propagacion comprobar informes/2026-W40/informe.md   # ¿está el comentario del socio?

python -m pytest -q                         # tests (no necesitan red)
```

La salida queda en `informes/AAAA-Wnn/` (semana ISO del lunes de publicación):
`informe.md`, `informe.html` y las gráficas PNG (`sfi_12meses.png`, `heatmap_hora_banda.png`,
`rutas_continentes.png`, `voacap_fiabilidad.png`, `fof2_arenosillo.png`). Las rutas de las imágenes
son relativas, así que la carpeta se puede subir tal cual al blog.

Las descargas se guardan en `cache/` (ignorada por git) y se reutilizan unas horas; si una fuente
falla y hay copia antigua en caché, se usa esa.

### VOACAP

La sección de predicción usa [voacapl](https://github.com/jawatson/voacapl). Para tenerlo en local:

```bash
sudo apt-get install gfortran automake autoconf
git clone https://github.com/jawatson/voacapl.git && cd voacapl
autoreconf -fi                               # evita el error «aclocal-1.15 is missing»
./configure && make && sudo make install     # make sin -j
makeitshfbc                                  # crea ~/itshfbc
```

Supuestos del modelo: CW a 100 W, dipolos de media onda a λ/2 de altura apuntados al destino
(`voacap_antenas/dipolo.voa`), ruido residencial (−145 dBW a 3 MHz), SNR requerida 27 dB·Hz.
El SSN es el efectivo del SFI previsto por NOAA para la semana. Se cambian en
`propagacion/voacap.py` (`Parametros`).

## Automatización (GitHub Actions)

- **`informe-semanal.yml`**: todos los lunes a las 06:17 UTC (y a mano con *Run workflow*,
  opcionalmente con otra fecha) compila voacapl, genera el borrador y **abre un PR** con la carpeta
  del informe. Hay que habilitar *Settings → Actions → General → Allow GitHub Actions to create and
  approve pull requests*.
- **`ci.yml`**: tests en cada push/PR y, en los PR que tocan `informes/*/informe.md`, la
  comprobación `comentario-humano`, que falla mientras el comentario del socio siga pendiente.
  (Los PR abiertos por el bot con `GITHUB_TOKEN` no lanzan otros workflows; la comprobación corre
  cuando el socio sube su comentario.)

No hace falta ninguna API key: todas las fuentes son públicas.

## Estructura

```
propagacion/
  config.py            estación, destinos DX, bandas y URLs
  http.py              descargas con caché y reintentos
  geo.py               locators Maidenhead, distancias, rumbos, continentes
  solar.py             SSN, semáforo Kp, MUF (ley de la secante), orto/ocaso (algoritmo NOAA)
  voacap.py            tarjeta de entrada y lectura de la salida de voacapl
  charts.py            gráficas matplotlib
  periodo.py           semana analizada y semana prevista
  report.py            orquestación y plantilla
  sources/             un módulo por fuente: noaa, drao, wspr, rbn, giro, celestrak, contests
  sections/            un módulo por sección: sol, realidad, prevision, agenda
templates/informe.md.j2
tests/                 tests de cálculos, parsers y un informe completo con datos sintéticos
```

## Notas sobre las fuentes

- **wspr.live**: consulta SQL por HTTP a la tabla `wspr.rx`, filtrando `tx_loc`/`rx_loc` por
  cuadrícula (`GALICIA_SQUARES` en `config.py`; se puede ampliar a IN62/IN63). La banda se deriva
  de `frequency` para no depender de la codificación de la columna `band`.
- **RBN**: los ficheros diarios no traen locator, así que se filtra por indicativo (distrito EA1,
  `RBN_CALL_REGEX`) y se usan los continentes del propio fichero. Es una aproximación: EA1 incluye
  también Asturias, Cantabria y Castilla y León.
- **PSKReporter** (FT8) no está incluido todavía: su API tiene límites de uso estrictos.
- **Meteoros**: calendario fijo aproximado de la IMO en `sections/agenda.py`; revisar cada año.
- Los formatos de las fuentes pueden cambiar: los tests de `tests/test_fuentes.py` documentan el
  formato esperado de cada una.
