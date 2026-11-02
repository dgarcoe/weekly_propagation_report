# Propagación HF/VHF desde Vigo · semana 2026-W45

**EA1RKV · Unión de Radioaficionados de Vigo-Val Miñor** · estación de referencia
Vigo (IN52PE) · semana analizada: 26 de octubre de 2026 – 1 de noviembre de 2026 ·
previsión: lun 2/11 – dom 8/11

> Este informe combina **lo que dice la teoría** (índices solares, predicciones) con **lo que pasó
> de verdad** (spots reales desde Galicia). Todas las horas en UTC salvo que se indique lo contrario.

## 1. El Sol y el campo geomagnético

- **Flujo solar (SFI):** media **91**, máximo 94, mínimo 89 ·
  tendencia frente a la semana anterior: **a la baja (-14 %)** (media previa 107).
- **SSN efectivo aproximado:** ≈ **31** (SSN ≈ 1,14·SFI − 73,2) · número de manchas observado (media): 25.
- **Campo geomagnético:** 🔴 **tormenta geomagnética (G2)** · Kp máximo **6,00** · Ap medio **11** (máx. 24) · 3 día(s) con Kp ≥ 4.
- **Fulguraciones:** ninguna de clase M o X. Sin apagones de radio por fulguraciones.

| Día | SFI | Manchas | Ap | Kp máx. | |
|---|---:|---:|---:|---:|:-:|
| lun 26/10 | 91 | 25 | 4 | 2,00 | 🟢 |
| mar 27/10 | 89 | 25 | 6 | 2,67 | 🟢 |
| mié 28/10 | 93 | 12 | 7 | 2,33 | 🟢 |
| jue 29/10 | 89 | 22 | 4 | 2,33 | 🟢 |
| vie 30/10 | 90 | 36 | 10 | 4,33 | 🟡 |
| sáb 31/10 | 92 | 24 | 24 | 6,00 | 🔴 |
| dom 1/11 | 94 | 30 | 19 | 4,67 | 🟡 |

_Semáforo Kp: 🟢 ≤ 3 tranquilo · 🟡 4 inquieto · 🔴 ≥ 5 tormenta._

![La semana del Sol: rayos X, SFI y Kp](semana_solar.png)

_Cómo leerla, de arriba abajo. **Rayos X:** cada pico es una fulguración; si entra en la franja
rosa (clases M y X), en la cara iluminada de la Tierra la capa D absorbe la HF durante minutos u
horas (el famoso «apagón de radio»). Los huecos de la línea son cortes de datos: cerca de los
equinoccios el satélite pasa cada día un rato por la sombra de la Tierra. **SFI:** cuanto más alto, más arriba llega la MUF.
**Kp:** agitación del campo magnético cada 3 horas; las barras rojas son tormenta._

![Flujo solar de los últimos 12 meses y previsión](sfi_12meses.png)

_Estamos en la fase descendente del ciclo 25: el SFI baja poco a poco, con altibajos de ~27 días
(la rotación del Sol). La línea discontinua naranja marca la tendencia del último año; a la
derecha, en violeta, la previsión mensual de NOAA con su rango de incertidumbre (zona sombreada)._

### ¿Qué viene? Previsión de la actividad solar

**Próximos 3 días** (NOAA, la previsión más fiable; emitida el lun 2/11 12:30 UTC):

| Día | Kp máx. previsto | | Prob. apagón de radio R1–R2 | Prob. apagón fuerte (R3+) |
|---|---:|:-:|---:|---:|
| lun 2/11 | 3,00 | 🟢 | 1 % | 1 % |
| mar 3/11 | 2,00 | 🟢 | 1 % | 1 % |
| mié 4/11 | 2,00 | 🟢 | 1 % | 1 % |

_R1–R2 = fulguración M (apagón menor o moderado en la cara diurna); R3+ = fulguración X._

**Esta semana:** SFI entre 95 y 115, Ap máximo 10 y
Kp máximo 3 (🟢 tranquilo).

![Previsión de NOAA a 27 días](prevision_27dias.png)

**Hasta el sáb 28/11:** SFI entre 85 y 120; posible
agitación geomagnética (Kp ≥ 4) el lun 9/11, mar 17/11, mié 18/11, vie 27/11, sáb 28/11.
_Esta previsión se basa en que el Sol gira sobre sí mismo cada ~27 días: las regiones activas y
los agujeros coronales que vimos hace una rotación suelen «volver a asomarse». Por eso acierta
bastante con las tendencias, pero no puede anticipar una fulguración concreta._

**A largo plazo:** NOAA prevé para abril de 2027 un SFI medio mensual de
**119** (entre 105 y 129). Es decir, el ciclo 25 sigue
bajando: poco a poco, 10 m y 12 m abrirán menos días. **Ojo:** la media de los últimos
27 días (111) va **por debajo** del rango que NOAA preveía para este mes
(unos 123): el Sol se está apagando más
deprisa de lo esperado, y las bandas altas lo notarán.

## 2. Lo que pasó de verdad desde Galicia

Esta semana se registraron **352 577 spots**: 299 645 de WSPR con una
estación gallega en un extremo (6 estaciones en las cuadrículas IN52/IN53) y
52 932 de la Reverse Beacon Network en CW/RTTY con una estación del **distrito EA1** (el RBN
no da locator, así que no podemos separar Galicia de Asturias, Cantabria y Castilla y León).
Las bandas con más actividad fueron **40m** (77 746), **60m** (66 774), **20m** (61 787), **80m** (48 549), y la hora más movida, las **18 UTC**.

![Mapa de calor de spots por hora UTC y banda](heatmap_hora_banda.png)

_Cómo leerlo: cada casilla es una hora UTC en una banda; cuanto más oscura, más spots. Fíjate en
cómo las bandas altas (10–15 m) se «encienden» con el Sol y las bajas (40–80 m) de noche._

_La línea naranja es la **MUF(3000)F2 medida** por las ionosondas: por debajo de ella, la teoría dice
que la banda abre para un salto de 3 000 km. Si los spots siguen la línea, teoría y realidad coinciden._

### DX de la semana por banda

| Banda | Distancia | Estación gallega (WSPR) | Corresponsal | Locator | Continente | Cuándo | SNR |
|---|---:|---|---|---|---|---|---:|
| 160m | 5 782 km | EB1A | W4KEL (oyó a Galicia) | FM08rd | Norteamérica | dom 1/11 04:42 UTC | -25 dB |
| 80m | 17 045 km | EB1A | VK5ARG (oyó a Galicia) | PF95ht | Oceanía | mar 27/10 20:00 UTC | -25 dB |
| 60m | 19 820 km | EB1A | ZL2005SWL (oyó a Galicia) | RE68mx | Oceanía | mié 28/10 06:40 UTC | -28 dB |
| 40m | 19 876 km | EB1A | ZL2GD (oyó a Galicia) | RE66aq | Oceanía | sáb 31/10 04:54 UTC | -19 dB |
| 30m | 19 820 km | EB1A | ZL2005SWL (oyó a Galicia) | RE68mx | Oceanía | vie 30/10 05:52 UTC | -23 dB |
| 20m | 19 869 km | EB1A | ZL3RCK (oyó a Galicia) | RE66ft | Oceanía | mar 27/10 02:26 UTC | -24 dB |
| 17m | 17 745 km | EB1A | VK5WA/2 (oyó a Galicia) | QG50nf | Oceanía | lun 26/10 13:40 UTC | -25 dB |
| 15m | 19 820 km | EB1A | ZL2005SWL (oyó a Galicia) | RE68mx | Oceanía | mié 28/10 08:42 UTC | -24 dB |

_Distancias de círculo máximo medidas desde IN52PE (WSPR)._

### Rutas por continente

Spots de WSPR (Galicia) y RBN (distrito EA1) juntos, por continente del corresponsal:

| Continente | Spots | 160m | 80m | 60m | 40m | 30m | 20m | 17m | 15m | 12m | 10m | 
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Europa | **291 621** | 29087 | 43744 | 54039 | 65591 | 28165 | 46380 | 9616 | 14272 | 143 | 584 | 
| Norteamérica | **49 833** | 164 | 4049 | 11299 | 10037 | 1484 | 13139 | 1867 | 7586 | 56 | 152 | 
| África | **6 722** | 992 | 664 | 1387 | 878 | 825 | 713 | 366 | 836 | 22 | 39 | 
| Oceanía | **2 320** | · | 33 | 49 | 769 | 561 | 817 | 40 | 51 | · | · | 
| Asia | **1 219** | · | 59 | · | 295 | 30 | 611 | 43 | 159 | 10 | 12 | 
| Sudamérica | **862** | · | · | · | 176 | 17 | 127 | 61 | 381 | 20 | 80 | 

![Rutas desde Vigo por rumbo y distancia](rutas_continentes.png)

_Mapa centrado en Vigo: el ángulo es el rumbo al que apuntaría tu antena y la distancia al centro,
los kilómetros. Solo WSPR, porque el RBN no da locator: cada punto es un locator distinto
(1 208 en total) y la cifra entre paréntesis es cuántos hay de cada continente. Por eso no
coincide con los spots de la tabla, que suman todos los spots de WSPR y RBN._

### La ionosfera medida

Datos de las digisondas de **Roquetes (Ebro)** (40,8° N), **Dourbes** (50,1° N).
Solo usamos ionogramas con confianza de autoescalado ≥ 70 % y descartamos los valores
que se salen de lo que marcan sus vecinos (los errores típicos del escalado automático).

#### ¿Hubo esporádica E esta semana?

**Algo:** la foEs pasó de 5,6 MHz, lo bastante para aperturas cortas en 10 m, pero no llegó a 6 m.

| Ionosonda | Día | Desde | Hasta (UTC) | foEs máx. | MUF Es (~1 800 km) | Banda | Spots WSPR |
|---|---|---|---|---:|---:|---|---:|
| Roquetes (Ebro) | dom 1/11 | 23:30 | 23:30 | 6,0 MHz | 30 MHz | 10m | 0 |
| Roquetes (Ebro) | lun 26/10 | 10:05 | 10:15 | 6,1 MHz | 30 MHz | 10m | 0 |
| Roquetes (Ebro) | lun 26/10 | 11:00 | 11:00 | 5,6 MHz | 28 MHz | 10m | 0 |
| Roquetes (Ebro) | sáb 31/10 | 13:30 | 13:30 | 5,8 MHz | 29 MHz | 10m | 0 |
| Roquetes (Ebro) | vie 30/10 | 14:40 | 14:50 | 5,7 MHz | 28 MHz | 10m | 0 |

_La MUF de la Es para un salto de 1 500–2 000 km es unas 5 veces la foEs. «Spots WSPR»: spots de esa
banda a 800–2 500 km desde Galicia durante el episodio._

#### Teoría frente a realidad

Comparamos, hora a hora, lo que dice la MUF(3000) medida con lo que se oyó de verdad a 2 000–4 000 km
(un salto de F2) en 20m, 17m, 15m. **Coinciden en el 85 %** de las
72 casillas hora × banda. En 1 la MUF decía «abierta» pero
no hubo spots (poca actividad WSPR en esa banda y hora, o absorción). En 10
hubo spots aunque la MUF típica no llegaba, sobre todo en 20m y 15m: días mejores
que la mediana o esporádica E. La línea naranja del mapa de calor muestra lo mismo de un vistazo.

#### Notas curiosas (Roquetes (Ebro))

- La capa F2 tuvo su pico a **240 km** de altura a mediodía y a 321 km de noche.
- La capa F1 apareció de día, con foF1 de hasta 4,9 MHz (12:10 UTC).
- **Spread-F:** se vio en 6 noche(s) (8 h en total). Son irregularidades de la capa F que en la radio se notan como *flutter* y ecos, sobre todo en 40–80 m de madrugada.

## 3. Previsión para la semana (lun 2/11 – dom 8/11)

### DX: fiabilidad prevista (VOACAP)

**En FT8** (el modo más usado, y el más parecido a los spots WSPR/RBN de la sección 2): bandas con
fiabilidad media ≥ 50 % por franja horaria (UTC), la mejor primero. En cursiva, la mejor banda
cuando ninguna llega al 50 % (apertura posible pero poco fiable):

| Destino | km | Rumbo | 00–04 | 04–08 | 08–12 | 12–16 | 16–20 | 20–24 | 
|---|---:|---:|---|---|---|---|---|---|
| Norteamérica este (Nueva York) | 5 307 | 291° | 80m, 40m, 30m | 80m, 40m | 40m, 30m | 20m, 17m, 15m | 20m, 30m, 17m | 40m, 30m, 80m | 
| Caribe (Santo Domingo) | 6 288 | 265° | 40m, 80m, 30m | 40m, 30m, 80m | 30m, 40m, 20m | 17m, 15m, 20m | 20m, 17m, 15m | 40m, 30m, 20m | 
| Sudamérica (Buenos Aires) | 9 922 | 219° | 20m, 30m, 17m | 30m, 20m, 40m | 17m, 15m, 20m | 12m, 15m | 12m, 15m, 10m | 17m, 20m, 15m | 
| Japón (Tokio) | 10 780 | 25° | _30m (25 %)_ | — | _20m (37 %)_ | _30m (34 %)_ | 30m | 30m | 
| Oceanía (Sídney) | 18 035 | 69° | — | — | 12m | 12m | _20m (38 %)_ | — | 
| Sudáfrica (Johannesburgo) | 8 489 | 146° | 20m, 30m, 17m | _20m (35 %)_ | 12m, 15m | 10m, 12m, 15m | 15m, 12m, 17m | 20m, 17m, 30m | 

![Fiabilidad VOACAP por destino, banda y hora](voacap_fiabilidad.png)

**En CW** (a oído hace falta unos 14 dB más de señal que en FT8, así que se abren menos bandas):

| Destino | 00–04 | 04–08 | 08–12 | 12–16 | 16–20 | 20–24 | 
|---|---|---|---|---|---|---|
| Norteamérica este (Nueva York) | 40m, 80m | 40m, 80m | 40m, 30m | 20m, 17m | 20m, 17m | 40m, 30m | 
| Caribe (Santo Domingo) | 40m | 40m | _30m (39 %)_ | _17m (45 %)_ | 17m | 30m, 40m | 
| Sudamérica (Buenos Aires) | 20m | _30m (48 %)_ | 15m | 12m | 12m | 17m | 
| Japón (Tokio) | — | — | — | — | _30m (25 %)_ | _30m (22 %)_ | 
| Oceanía (Sídney) | — | — | _12m (26 %)_ | _12m (26 %)_ | — | — | 
| Sudáfrica (Johannesburgo) | _20m (46 %)_ | — | _12m (42 %)_ | 10m | 12m, 10m, 15m | 17m | 

_Supuestos: 100 W, dipolos de media onda a media longitud de onda de altura en los dos extremos,
ángulo de salida mínimo de 3° y ruido residencial. SSN usado: **47** (SSN efectivo del SFI previsto (106)).
En SSB hacen falta ~30 dB más que en FT8. VOACAP describe el promedio mensual: un día concreto puede
ir mucho mejor o peor._

### NVIS y contactos regionales (80 y 40 m)

Combinando Roquetes (Ebro), Dourbes y llevándolas a la latitud y la hora local de Vigo
(El Arenosillo sola, 5° más al sur, resulta algo optimista), la **foF2 mediana estimada en Vigo fue de
4,7 MHz** la
semana pasada: de 3,3 MHz de madrugada a 8,8 MHz hacia las
12 UTC. El pico de la
capa F2 estuvo de mediana a 255 km.

![foF2 por hora](fof2_arenosillo.png)

| Trayecto | sec φ | 80 m abierta | 40 m abierta | MUF (mín.–máx.) |
|---|---:|---|---|---|
| NVIS (Galicia, < 200 km) | 1,00 | 07–21 UTC | 11–17 UTC | 3,3–8,8 MHz |
| Vigo – Madrid (~460 km) | 1,34 | todo el día | 08–18 UTC | 4,2–12,1 MHz |
| Vigo – Barcelona (~900 km) | 1,94 | 20–10, 15–18 UTC · _absorción: 10–15, 18–20 UTC_ | 07–20 UTC | 5,7–17,8 MHz |

**A 3 000 km** (un salto de F2, p. ej. Canarias–Escandinavia): la **MUF(3000)F2 medida** fue de
10,1 a 29,8 MHz (máxima hacia las 12 UTC).
20m: 07–19 UTC · 17m: 08–18 UTC · 15m: 08–18 UTC · 12m: 10–17 UTC · 10m: cerrada.

> **¿Por qué importa foF2?** Es la frecuencia más alta que la capa F2 devuelve a tierra cuando
> la señal sube en vertical. En NVIS (*Near Vertical Incidence Skywave*, antenas bajas que radian
> hacia arriba) solo rebotan las frecuencias **por debajo de foF2**: si foF2 cae por debajo de
> 7,1 MHz, los 40 m «saltan» Galicia y hay que bajar a 80 m. Para trayectos más largos la señal
> llega inclinada y la capa aguanta más: la MUF de un salto es aproximadamente
> **foF2 · sec(φ)**, donde φ es el ángulo de incidencia en la ionosfera, calculado con la altura
> real del pico (hmF2) que mide la ionosonda. Para 3 000 km usamos directamente la MUF(3000)F2 que
> publica la digisonda, que ya tiene en cuenta la curvatura de la Tierra.
>
> **¿Y por abajo?** La capa D absorbe las frecuencias bajas de día. La **fmin** (frecuencia más
> baja del ionograma) sube a mediodía por esa absorción: la usamos para estimar la LUF
> (≈ fmin · √sec φ en la capa D). Una banda está «abierta» si la MUF la supera con un 10 % de
> margen y la LUF queda por debajo; «absorción» son las horas en que la MUF la deja pasar pero la
> capa D la cierra.

### Línea gris

El jue 5/11, en Vigo amanece a las **07:12 UTC** y anochece a las **17:23 UTC**.
Durante el crepúsculo la absorción de la capa D desaparece antes de que se deshaga la capa F: es
el momento de buscar DX en 160, 80 y 40 m a lo largo del terminador.

| Destino | Orto DX | Ocaso DX | Terminador común (±45 min) | Noche en los dos extremos |
|---|---|---|---|---|
| Norteamérica este (Nueva York) | 11:31 | 21:47 | — | 21:48–07:12 |
| Caribe (Santo Domingo) | 10:41 | 22:05 | — | 22:05–07:12 |
| Sudamérica (Buenos Aires) | 08:47 | 22:26 | — | 22:25–07:12 |
| Japón (Tokio) | 21:06 | 07:42 | 06:57–07:57 UTC (orto Vigo / ocaso DX) | 17:23–21:07 |
| Oceanía (Sídney) | 18:51 | 08:26 | 07:41–07:57 UTC (orto Vigo / ocaso DX) | 17:23–18:50 |
| Sudáfrica (Johannesburgo) | 03:15 | 16:27 | 16:38–17:12 UTC (ocaso Vigo / ocaso DX) | 17:24–03:15 |

_El «terminador común» es la línea gris propiamente dicha (amanecer o anochecer a la vez en los dos
extremos). La «noche en los dos extremos» es la ventana para 160 y 80 m, y a menudo para 40 m._

## 4. Agenda y efemérides

### Concursos del fin de semana

| Concurso | Empieza (UTC) | Termina (UTC) | Horas |
|---|---|---|---:|
| [K1USN Slow Speed Test](https://www.contestcalendar.com/weeklycontdetails.php?ref=003gkjfd) | vie 6/11 20:00 | vie 6/11 21:00 | 1 |
| [YBDXPI FT8 Contest](https://www.contestcalendar.com/weeklycontdetails.php?ref=003gftoz) | sáb 7/11 00:00 | dom 8/11 23:59 | 48 |
| [IPARC Contest, CW](https://www.contestcalendar.com/weeklycontdetails.php?ref=003gdgem) | sáb 7/11 06:00 | sáb 7/11 18:00 | 12 |
| [ARRL Sweepstakes Contest, CW](https://www.contestcalendar.com/weeklycontdetails.php?ref=003gbqoh) | sáb 7/11 21:00 | lun 9/11 03:00 | 30 |
| [IPARC Contest, SSB](https://www.contestcalendar.com/weeklycontdetails.php?ref=003gdo4f) | dom 8/11 06:00 | dom 8/11 18:00 | 12 |
| [FIRAC HF Contest](https://www.contestcalendar.com/weeklycontdetails.php?ref=003gctno) | dom 8/11 07:00 | dom 8/11 17:00 | 10 |

### Lluvias de meteoros (meteor scatter en 6 m y 2 m)

- **Oriónidas** — máximo mié 21/10 (hace 12 días), THZ ≈ 20 · _activa esta semana_.
- **Leónidas** — máximo mar 17/11 (dentro de 15 días), THZ ≈ 15 · _activa esta semana_.

_Consejo: el meteor scatter funciona mejor al amanecer local, cuando la Tierra «barre» los
meteoros de frente. Modos: MSK144 (6 m/2 m) con WSJT-X._

### Pases de satélites desde Vigo

Los mejores pases (elevación máxima ≥ 30°) de cada satélite:

| Satélite | Día | AOS (UTC) | LOS (UTC) | Hora local | Elev. máx. | Min |
|---|---|---|---|---|---:|---:|
| AO-27 | lun 2/11 | 11:15 | 11:30 | 12:15 | 76° | 15 |
| ISS | lun 2/11 | 22:58 | 23:09 | 23:58 | 86° | 11 |
| SO-50 | mar 3/11 | 03:00 | 03:14 | 04:00 | 66° | 14 |
| AO-7 | mar 3/11 | 07:39 | 08:01 | 08:39 | 84° | 22 |
| AO-27 | mar 3/11 | 22:03 | 22:18 | 23:03 | 90° | 15 |
| AO-123 | mié 4/11 | 08:59 | 09:10 | 09:59 | 68° | 11 |
| SO-50 | mié 4/11 | 11:46 | 11:59 | 12:46 | 65° | 14 |
| FO-29 | mié 4/11 | 19:22 | 19:38 | 20:22 | 80° | 16 |
| RS-44 | jue 5/11 | 01:32 | 01:53 | 02:32 | 80° | 20 |
| ISS | jue 5/11 | 03:52 | 04:03 | 04:52 | 79° | 11 |
| AO-7 | jue 5/11 | 07:32 | 07:54 | 08:32 | 77° | 22 |
| RS-44 | jue 5/11 | 14:10 | 14:32 | 15:10 | 86° | 23 |
| SO-50 | vie 6/11 | 02:12 | 02:26 | 03:12 | 67° | 14 |
| FO-29 | vie 6/11 | 19:16 | 19:33 | 20:16 | 86° | 16 |
| ISS | vie 6/11 | 21:24 | 21:35 | 22:24 | 87° | 11 |
| AO-27 | vie 6/11 | 22:13 | 22:27 | 23:13 | 75° | 15 |
| AO-123 | sáb 7/11 | 08:50 | 09:01 | 09:50 | 88° | 11 |
| AO-7 | sáb 7/11 | 18:24 | 18:46 | 19:24 | 84° | 22 |
| AO-123 | sáb 7/11 | 21:45 | 21:56 | 22:45 | 88° | 11 |
| RS-44 | dom 8/11 | 00:50 | 01:10 | 01:50 | 74° | 20 |
| FO-29 | dom 8/11 | 19:11 | 19:27 | 20:11 | 87° | 16 |

## 5. Comentario del club

<!-- COMENTARIO -->
> PENDIENTE: un socio debe escribir aquí su comentario (qué trabajó, qué oyó, qué recomienda
> para la semana). **El informe no se publica sin este párrafo.**
<!-- /COMENTARIO -->

---

### Fuentes

- NOAA SWPC — índices solares y geomagnéticos diarios, flujo de rayos X y fulguraciones de GOES, previsión a 3 y 27 días y previsión del ciclo solar (https://www.swpc.noaa.gov/)
- NRC Canada / DRAO Penticton — histórico diario del flujo F10.7 (https://www.spaceweather.gc.ca/)
- WSPRnet vía wspr.live (https://wspr.live/)
- Reverse Beacon Network (https://www.reversebeacon.net/)
- GIRO / DIDBase, Lowell GIRO Data Center (https://giro.uml.edu/), datos CC-BY-NC-SA 4.0 de las digisondas de Roquetes (Observatori de l'Ebre), Dourbes (RMI Bélgica)
- VOACAP (voacapl, port para Linux de J. Watson; https://github.com/jawatson/voacapl)
- WA7BNM Contest Calendar (https://www.contestcalendar.com/)
- International Meteor Organization — calendario de lluvias (https://www.imo.net/)
- CelesTrak — TLE de satélites de radioaficionado (https://celestrak.org/)
- Cálculos propios: SSN efectivo, distancias de círculo máximo, MUF por ley de la secante y
  orto/ocaso (algoritmo de NOAA).

<sub>Borrador generado automáticamente el 2026-11-02 16:08 UTC por el script del radioclub
EA1RKV. Las secciones sin datos indican que la fuente no respondió esta semana.</sub>
