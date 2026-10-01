PRONO TÉRMICO — PWA SKEW-T (V4, HASTA 250 hPa)
=============================================

Esta es una modificación de prono_termico_pwa_calendario_v3.zip.
Conserva la PWA original, Python/Pyodide 0.28.3 y la ejecución en el navegador.
No requiere instalar Python en el celular ni utilizar un backend de Python.

CONTROLES CONSERVADOS
- Lugares: SJ, Cuchi, Merlo, Trasla, Ped, Alpina, Rioja, Tuc.
- Coordenadas personalizadas, incluyendo coma decimal.
- Ayer / Hoy / Mañana y el calendario.
- Selección de una o varias horas, de 09 a 18.
- Condiciones del suelo automáticas o Td/T manuales.
- Botones GENERAR SONDEO y Limpiar.
- Tabla de texto con la misma estructura: m, P.R, T, H%, m/s.

CAMBIOS
- Cada tabla aparece arriba del Skew-T de su horario.
- El gráfico ASCII fue reemplazado por SVG: T roja y Td azul.
- Se solicita T, humedad relativa y altura geopotencial para los 31 niveles:
  1000, 975, 950, 925, 900, 875, 850, 825, 800, 775, 750, 725, 700,
  675, 650, 625, 600, 575, 550, 525, 500, 475, 450, 425, 400, 375,
  350, 325, 300, 275 y 250 hPa.
- Se mantienen los siete modelos del código original y los datos a 2 m.
- Se agrega presión superficial para ubicar correctamente el inicio del gráfico.
- Resultado se amplía hasta 1200 px en computadora, sin límite de alto ni
  una caja interna de 62vh: se recorre con el scroll normal de la página.
- Los controles mantienen su ancho máximo de 760 px y su diseño original.
- El gráfico permite zoom con +/− o rueda, arrastre y gesto de dos dedos.
- Ajustar recupera una escala común para comparar las horas generadas.
- Al tocar/pasar el cursor se ven valores del nivel más próximo y su altura.
- Casillas para las líneas de referencia del gráfico.
- Detalle de niveles recibidos por modelo, antes de la interpolación local.

ACTUALIZAR TU WEB ACTUAL
1. Descomprimí este ZIP.
2. Subí TODO EL CONTENIDO de la carpeta prono_termico_pwa a la MISMA ubicación
   donde tenés el index.html actual, reemplazando los archivos anteriores.
   No crees una subcarpeta adicional si querés conservar la misma dirección.
3. Incluí los tres archivos nuevos: skewt.js, skewt-view.js y skewt_data.py.
4. Conservá también la carpeta icons, el manifest y el resto de los archivos.
5. Esperá a que tu alojamiento termine de actualizar los archivos.
6. Abrí/recargá la página con conexión. Luego cerrá las pestañas y la PWA
   anterior y volvé a abrirla. La caché nueva se llama prono-termico-v4-skewt-250.
   Si todavía aparece “Sondeo ASCII”, recargá otra vez. Como último recurso,
   eliminá los datos del sitio de esa web en el navegador y volvé a abrirla.
7. Debería aparecer “Sondeo Skew-T · Open-Meteo” bajo Prono Térmico.

El proyecto sigue siendo un sitio ESTÁTICO. Para instalarlo como PWA se usa
HTTPS, como en tu implementación anterior. No abrir index.html con file://.
La app necesita Internet para cargar Pyodide/NumPy y consultar Open-Meteo.
El service worker guarda los archivos de la app, no promete pronósticos offline.

PRUEBA RÁPIDA
- Elegí SJ, Hoy, 12 y condiciones Automáticas.
- Tocá GENERAR SONDEO y esperá la consulta de los modelos.
- Aparecerán la tabla y el gráfico con sus curvas hasta los datos disponibles.
- Agregá 15 y generá nuevamente: debe aparecer un segundo bloque.

DATOS Y ALCANCE
- Pedir 31 niveles no significa que todos los modelos tengan T y humedad
  en los 31. El programa mantiene la interpolación vertical y las medianas
  del código original, sin extrapolar más allá de los datos disponibles.
- Esa interpolación no crea nueva resolución meteorológica. Open-Meteo
  también puede interpolar internamente, algo que el marcador no identifica.
- Se mantiene tu fórmula aproximada de Td y tu estimación empírica de m/s.
- Las alturas de la tabla son las referencias aproximadas de tu lista;
  no son alturas exactas ni metros sobre el terreno.
- El gráfico se posiciona por presión logarítmica; al inspeccionar usa la
  altura geopotencial si fue recibida. Altitud ISA es una referencia estándar.
- Se excluyen del dibujo los niveles situados bajo la superficie del perfil
  agregado. El cálculo original de las medianas no fue reescrito por modelo.
- Esta versión reproduce T/Td y la grilla del trabajo previo. No incluye
  la trayectoria de parcela, techo térmico, sombreado de ascenso ni viento
  del APK Android.

ARCHIVOS MODIFICADOS
- index.html: nombre del gráfico y contenedor de resultados.
- styles.css: tamaño de Resultado y estilos para tabla/gráficos.
- app.js: recibe los bloques con texto + perfil y conserva el formulario.
- worker.mjs: entrega datos numéricos del sondeo junto con la tabla.
- prono_core.py: 31 niveles, presión/geopotenciales, salida numérica.
- sw.js: nueva caché y registro de archivos nuevos.

ARCHIVOS NUEVOS
- skewt.js: geometría Skew-T y curvas de referencia recuperadas del APK.
- skewt-view.js: dibuja un bloque por horario debajo de su tabla.
- skewt_data.py: convierte estadísticas Python en perfiles para SVG.

requests.py, manifest.webmanifest e íconos se conservan de la PWA original.
