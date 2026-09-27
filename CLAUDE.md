# Informe semanal de propagación — EA1RKV

## Contexto

Este repo genera un **informe semanal de propagación HF/VHF** para el blog del radioclub
EA1RKV (Unión de Radioafeccionados de Vigo-Val Miñor, Vigo, Galicia).

- Estación de referencia: Vigo, locator **IN52PE**.
- Público: socios del club y radioaficionados de Galicia, desde principiantes hasta DXers veteranos.
- Idioma del informe: **español**. Código y comentarios pueden ir en inglés o español.
- Idea central: combinar **lo que dice la teoría** (índices solares, predicciones) con
  **lo que pasó de verdad** (spots reales desde Galicia). Eso es lo que lo diferencia de un
  copia-pega de hamqsl.

## Estructura del informe

### 1. El Sol y el campo geomagnético (semana pasada)
- Fuente: NOAA SWPC (JSON públicos: flujo F10.7, Kp planetario, fulguraciones) y el
  *27-day outlook* (texto plano).
- Calcular: SFI medio/máx/mín y tendencia frente a la semana anterior; SSN efectivo aproximado
  (SSN ≈ 1,14·SFI − 73,2, válida aprox. entre 70 y 250 de SFI); Ap medio y Kp máximo con semáforo
  (≤3 tranquilo, 4 inquieto, ≥5 tormenta); fulguraciones M/X.
- Gráfica de SFI de los últimos 6-12 meses con tendencia (fase descendente del ciclo 25).

### 2. Lo que pasó de verdad desde Galicia (sección estrella)
- **WSPR** vía wspr.live (ClickHouse por HTTP/SQL, sin API key). Filtrar spots con tx_loc o
  rx_loc en IN52/IN53 (ampliable a IN62/IN63). Verificar nombres de columnas y codificación de
  `band` en la documentación de wspr.live.
- **RBN** (Reverse Beacon Network): archivos diarios de spots CW/RTTY.
- **PSKReporter** (FT8): opcional, respetar sus límites de uso.
- Salidas: **mapa de calor hora UTC × banda** (spots), **DX de la semana** por banda (distancia
  de círculo máximo desde IN52PE) y mapa de rutas por continente.

### 3. Previsión para la semana siguiente
- Predicción **VOACAP** (voacapl) o **ITURHFProp** desde IN52PE hacia: Norteamérica este,
  Caribe, Sudamérica, Japón, Oceanía, Sudáfrica. Tabla de fiabilidad por banda y franja horaria,
  con colores.
- **NVIS/regional (40 y 80 m)**: foF2 de la ionosonda de El Arenosillo (GIRO/DIDBase).
  MUF de un salto ≈ foF2 · sec(φ). Incluir una breve explicación didáctica.
- **Línea gris**: orto/ocaso en Vigo y en los destinos DX y ventanas comunes en el terminador
  (`skyfield` o `astral`).

### 4. Agenda y efemérides
- Concursos del fin de semana, lluvias de meteoros (meteor scatter en 6 m/2 m) y pases de
  satélites visibles desde Vigo (`skyfield` + TLE de CelesTrak).

### 5. Comentario humano
- Dejar un hueco marcado (`<!-- COMENTARIO -->`) para que un socio añada un párrafo propio.
  El informe no debe publicarse sin él.

## Automatización
- Script principal en Python (≥3.11), modular: un módulo por fuente de datos y otro por sección.
- Ejecución semanal los lunes con **GitHub Actions** (cron) y también lanzable a mano
  (`workflow_dispatch`).
- Salida: un borrador en Markdown (y opcionalmente HTML) en `informes/AAAA-Wnn/`, con las
  gráficas como PNG/SVG, listo para el blog. El workflow puede abrir un PR con el borrador en
  lugar de publicar directamente.
- Gráficas: matplotlib (estáticas) o Plotly (interactivas); priorizar que se lean bien en móvil.

## Criterios
- Sin API keys ni secretos en el repo. Si alguna fuente los requiere, usar GitHub Secrets.
- Caché local de descargas y reintentos: si una fuente falla, el informe se genera igualmente
  con esa sección marcada como «sin datos esta semana».
- Comprobar cada endpoint antes de depender de él (URLs y formatos pueden haber cambiado).
- Citar las fuentes de datos al pie del informe.
- Tests básicos para los cálculos (SSN, distancias, línea gris).

## Orden de trabajo sugerido
1. Esqueleto del repo, `requirements.txt`, README.
2. Sección 1 (NOAA) + plantilla Markdown del informe.
3. Sección 2 (wspr.live → mapa de calor + DX de la semana).
4. Workflow de GitHub Actions.
5. Secciones 3 y 4 (VOACAP/ITURHFProp, foF2, línea gris, satélites).
