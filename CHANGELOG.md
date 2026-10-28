# Registro de Cambios (Changelog) - Descargador de YouTube

Todas las novedades, mejoras y correcciones notables de este proyecto quedan documentadas en este archivo.

---

## [1.6.1] - 2026-10-28

### Añadido
- **Navegación jerárquica escalonada completa con la tecla Escape**:
  - Al explorar favoritos temáticos, canales y playlists anidadas, la tecla Escape retrocede ordenadamente paso a paso: vídeos -> listas del canal -> lista de favoritos -> 'Mis listas de favoritos' -> limpiar resultados.
  - Se garantiza que nunca se salte el nivel de 'Mis listas de favoritos' al regresar de listas temáticas.
- **Señalización sonora continua durante la actualización y descompresión**:
  - Durante el proceso de relevo, descompresión, verificación e inicio de la nueva versión tras una actualización, el instalador reproduce periódicamente el tono suave y armónico de espera en segundo plano, informando al usuario y facilitando el seguimiento del proceso a personas que utilicen lectores de pantalla.

### Cambiado
- **Optimización y depuración de listas de favoritos**:
  - Supresión de la lista automática 'Principal' cuando el usuario dispone de sus propias listas temáticas o cuando se encuentra vacía, evitando elementos redundantes junto a 'Todas las listas'.
  - Las listas de favoritos se pueden eliminar o gestionar con total libertad sin listas residuales forzadas por el sistema.

---

## [1.6.0] - 2026-10-27

### Añadido
- **Transición del sistema de actualizaciones a GitHub Releases**:
  - El sistema de comprobación de versiones en segundo plano y manual consulta el repositorio oficial en GitHub (`joseonce/youtube-downloader`) como servidor principal.
  - Para futuras versiones, las actualizaciones y paquetes ZIP portables se descargarán directamente desde GitHub Releases.
  - Se mantiene una arquitectura de respaldo redundante hacia `buscaapps.com` para garantizar disponibilidad continua si ocurren cortes o incidencias de red externas.
- **Descarga con redundancia y conmutación automática de servidores**:
  - Diálogo de actualización mejorado con soporte para servidores alternativos: si la descarga en un servidor falla, el actualizador conmuta de forma transparente al servidor de respaldo.

---

## [1.5.9] - 2026-10-20

### Añadido
- **Tecla Enter en la lista de resultados para reproducir**:
  - Al pulsar la tecla Enter (o doble clic) sobre cualquier elemento de la lista de resultados se reproduce de inmediato el elemento enfocado o se explora su catálogo si es una lista o canal, delegando la descarga al botón correspondiente o al atajo `Ctrl + D`.
- **Eliminación completa del menú Plataformas y compatibilidad universal por URL**:
  - Se suprime por completo el menú secundario Plataformas de la barra superior.
  - La descarga desde cualquier otra plataforma multimedia se realiza de forma directa y transparente pegando el enlace en la barra de búsqueda para cualquiera de los más de 2.000 servicios web compatibles con `yt-dlp`.
- **Mejoras internas en el ciclo de descarga y finalización de transferencias**:
  - Optimización integral en la gestión de eventos y estado al concluir las descargas en curso, asegurando la detención instantánea de las señales acústicas de espera, sincronización inmediata de la botonera (habilitando 'Descargar' y desactivando 'Cancelar') y emisión puntual del aviso sonoro de finalización.
- **Mejoras internas en la gestión, navegación y menús de listas de reproducción y canales**:
  - Perfeccionamiento en la resolución y apertura interna de elementos contenedores al pulsar la tecla Enter o Intro, facilitando una exploración ágil y fluida de sus contenidos y la plena disponibilidad de todos sus menús contextuales y operaciones asociadas.
- **Señal acústica contundente y con mayor volumen al finalizar descargas**:
  - Nuevo sonido armónico y vibrante (`completado.wav`) con una amplitud optimizada (~75%) que suena nítidamente al terminar todas las descargas activas en curso.
  - Detiene el sonido de espera previo y garantiza retroalimentación sonora inmediata tanto por VLC como por el subsistema de sonido del sistema operativo.
- **Sincronización de versión a 1.5.9 y actualización automática**:
  - Incremento de la versión a 1.5.9 en ejecutable, manifiesto y servidor para habilitar la auto-actualización fluida en instalaciones existentes con versión 1.5.8.
- **Limpieza automática de extensiones multimedia redundantes en títulos y descargas**:
  - Detecta y elimina extensiones de vídeo o audio que los creadores hayan incluido en el título original del contenido en YouTube (ej. `.flv`, `.mp4`, `.mp3`, `.avi`, `.mkv`, etc.).
  - Evita que las descargas queden con doble extensión redundante y confusa como `nombre.flv.mp3` o `cancion.mp3.mp3`, garantizando archivos finales limpios y directamente reconocibles por reproductores y el explorador de archivos.
- **Recuperación automática de foco en el reproductor tras cambio de tarea**:
  - Al cambiar de aplicación o tarea en Windows (`Alt + Tab`) y regresar a YouTubeDownloader con el reproductor abierto, la aplicación eleva automáticamente la ventana del reproductor y le transfiere el foco.
  - Permite retomar el control inmediato de la reproducción, conmutar vídeo con `F11`, pausar/reanudar con `Espacio` o `P`, variar velocidad con `F6`/`F7` y usar todos los atajos sin quedar atrapado en la ventana principal.
  - Delegación de atajos de control multimedia desde la ventana principal como salvaguarda adicional si el usuario interactúa con ella.
- **Dispositivo de salida de audio exclusivo para el reproductor con total aislamiento de locuciones TTS**:
  - Nuevo grupo accesible 'Dispositivo de salida de audio' dentro de la pestaña 'Reproducción y Favoritos' en Preferencias (`Ctrl + ,` / `F2`).
  - La redirección de dispositivo aplica de manera exclusiva al reproductor multimedia integrado.
  - Las locuciones TTS y los lectores de pantalla (NVDA, JAWS, Narrador de Windows) no son afectados por dicho cambio, manteniéndose siempre en su dispositivo habitual del sistema.
- **Emisión de locuciones TTS condicionada al foco activo de la aplicación**:
  - Las salidas de voz y anuncios para lectores de pantalla solo se emiten cuando alguna ventana de YouTubeDownloader tiene el foco en primer plano.
  - Si el usuario está trabajando en otra aplicación (navegador, procesador de textos, etc.), las locuciones en segundo plano se silencian automáticamente para evitar interferencias auditivas indeseadas.
- **Detección inteligente de lectores de pantalla y modo de locuciones configurable**:
  - Los usuarios videntes ya no escucharán locuciones de voz sintética: la aplicación detecta automáticamente si hay un lector de pantalla activo (NVDA, JAWS, Dolphin, Narrador de Windows) y, en su defecto, silencia las locuciones SAPI5.
  - Nuevo grupo accesible en Preferencias (`Ctrl + ,` / `F2`) dentro de la pestaña 'Reproducción y Favoritos' para configurar el modo de locuciones: 'Automático (solo si se detecta un lector activo)', 'Siempre activadas' o 'Desactivadas'.
- **Búsqueda y pegado directo de canales y listas como contenedores únicos**:
  - Al pegar o buscar la URL de un canal o lista de reproducción, la aplicación muestra el contenedor como un único resultado con su nombre y estadísticas en lugar de expandir directamente sus vídeos.
  - Permite descargar todo el canal o la lista completa con `Ctrl + D` o el botón 'Descargar' con sugerencia automática de subcarpeta con el nombre del contenedor.
  - Permite añadir el canal o lista a favoritos con `Ctrl + F` o moverlo con `Ctrl + M`.
  - Permite pulsar `Enter` o doble clic para explorar el contenido de sus vídeos en la jerarquía de navegación.

---

## [1.5.7] - 2026-10-15

### Añadido
- **Coherencia y reorganización estructural de menús sin duplicidades**:
  - Nuevo menú dedicado `Reproducción` (`Alt + R`) que centraliza todas las opciones de previsualización continua y cola de reproducción.
  - Eliminación de entradas redundantes y duplicadas en los menús `Edición` y `Favoritos`.
  - Inclusión del atajo de teclado global `Ctrl + M` en la tabla de aceleradores para alternar de lista de favoritos.
- **Control accesible de velocidad de reproducción (F6 y F7)**:
  - Atajos `F6` (disminuir -0,1x hasta 0,5x) y `F7` (aumentar +0,1x hasta 2,0x) con locución concisa para lectores de pantalla (`0,8`, `1,2`).
  - Configuración de velocidad predeterminada en Preferencias y retención durante la reproducción en lista.
- **Atenuación contextual dinámica e inteligente de menús y botonera**:
  - `Reproducir toda la lista continua (Ctrl+L)` y `Descargar todos los vídeos (Ctrl+Shift+D)` se atenúan automáticamente cuando la lista contiene 1 o 0 elementos.
  - `Marcar o desmarcar elemento (Espacio)`, `Seleccionar todos (Ctrl+A)`, `Deseleccionar todos` e `Invertir selección` se atenúan automáticamente con 1 solo ítem o lista vacía.
  - `Ver cola (Ctrl+J)`, `Reproducir cola (Ctrl+Shift+Q)` y `Vaciar cola` se atenúan en tiempo real mientras la cola esté vacía.
  - Botones y menús de descarga y reproducción se atenúan cuando la lista no contiene elementos.
- **Navegación multimedia en el reproductor (Ctrl+P / Ctrl+N)**:
  - Atajos `Ctrl + P` para pista anterior y `Ctrl + N` para pista siguiente en el reproductor.
  - Tecla `P` para pausar o reanudar reproducción, manteniendo `N` también como acceso rápido para siguiente.
- **Ventana accesible para ver y gestionar la cola de reproducción**:
  - Tecla `Q` y botón "Ver cola" en el reproductor para desplegar el listado completo de temas en cola.
  - Atajo `Ctrl + J`, botón "Ver cola..." en la ventana principal y opciones en los menús Archivo, Edición, Favoritos y contextual.
  - Eliminación de pistas de la cola con la tecla `Supr` (`Delete`) con locución informativa al lector de pantalla de los elementos restantes.
  - Salto y reproducción inmediata de cualquier tema seleccionado con la tecla `Enter`.
- **Cola de reproducción secuencial entre múltiples listas y búsquedas**:
  - Atajo global `Ctrl + Q` y botón accesible "Añadir a la cola" para enviar vídeos seleccionados a una lista de espera.
  - Atajo global `Ctrl + Shift + Q` y botón accesible "Reproducir cola" para escuchar secuencialmente todos los temas acumulados.
  - Compatibilidad dinámica: si el reproductor multimedia ya está en ejecución, añadir nuevos elementos a la cola los inserta en tiempo real al final de la lista activa con pre-buffering predictivo continuo.
  - Opción de vaciar cola de reproducción desde menús y ventana principal.
- **Anuncio progresivo de descargas añadidas en curso**:
  - Al solicitar la descarga de nuevos elementos mientras ya hay descargas activas, el lector de pantalla anuncia de forma inmediata el total de descargas acumuladas: `"2 descargas"`, `"3 descargas"`, etc.
- **Descarga unificada de colecciones completas**:
  - Atajo `Ctrl + Shift + D` ("Descargar todos los vídeos de esta lista / canal / lista de favoritos").
  - Menú contextual coherente y adaptativo según el tipo de elemento enfocado.
- **Resumen conciso en diálogo de subcarpeta**:
  - Locución y texto resumidos al solicitar el nombre de la carpeta para lotes de descarga (`"Subcarpeta para X vídeos:"`).

---

## [1.5.6] - 2026-10-15

### Añadido
- **Modo Aleatorio (Shuffle) en el Reproductor**:
  - Atajo de teclado `A` y botón interactivo para alternar el modo aleatorio de reproducción continua.
- **Nuevos controles y atajos en el Reproductor**:
  - Tecla `P` para pausar/reanudar y tecla `S` para detener por completo la reproducción.
  - Botón accesible "Detener" en los controles.
  - Barra espaciadora liberada para accionar cualquier botón enfocado en la interfaz.
- **Navegación jerárquica con Escape en Favoritos y exploración profunda**:
  - Retroceso escalonado paso a paso por toda la ruta de exploración.

---

## [1.5.5] - 2026-10-13

### Añadido
- **Atajo F8 para anunciar porcentaje del vídeo bajo demanda**:
  - Al pulsar la tecla `F8` en la ventana principal mientras se está descargando un vídeo (o varios en cola), el sintetizador de voz anuncia el porcentaje actual de descarga alcanzado (por ejemplo, "45 por ciento" o "[1/3] 45 por ciento"). Si no hay descargas activas, anuncia "No hay ninguna descarga en curso".
  - En el reproductor multimedia (VLC), la tecla `F8` anuncia el porcentaje de reproducción del vídeo actual (por ejemplo, "35 por ciento"), completando la terna de atajos accesibles junto a `F9` (tiempo transcurrido) y `F10` (tiempo restante).
- **Sonido de espera armónico durante la descarga de descripciones**:
  - Al consultar la descripción de un vídeo, lista de reproducción o canal desde el menú contextual, se emite periódicamente el tono suave y armónico de espera (`espera.wav`) mientras la información se descarga en segundo plano, proporcionando feedback sonoro inmediato a personas ciegas o con lectores de pantalla.
  - El sonido se detiene automáticamente en cuanto se recibe la descripción o al cerrar el diálogo.
  - Respeta la configuración de sonido de espera en Preferencias (`sonido_espera_descarga`).

---

## [1.5.4] - 2026-10-13

### Optimizado
- **Barra de progreso del reproductor excluida del tabulador**:
  - La barra de progreso de reproducción (`slider_pos`) ha sido excluida de la navegación secuencial con la tecla Tabulador (`AcceptsFocusFromKeyboard` desactivado y remoción de `WS_TABSTOP`).
  - Esto evita paradas y lecturas innecesarias para personas ciegas o usuarias de lectores de pantalla (NVDA, JAWS), quienes cuentan con atajos de teclado dedicados para desplazarse en el tiempo (`Flechas Izquierda/Derecha`, atajos extendidos, `F9`/`F10` y `Espacio`).
  - La barra permanece plenamente operativa para visualización y arrastre con el ratón por personas videntes.
- **Diálogo de subcarpeta condicionado a descargas múltiples y sugerencia inteligente**:
  - El diálogo para elegir u organizar archivos en una subcarpeta ahora solo se muestra cuando hay más de una descarga seleccionada (por ejemplo, múltiples vídeos marcados con la barra espaciadora o seleccionados por lotes).
  - Al descargar un único elemento (tanto desde la lista de resultados como desde una lista de favoritos), la descarga se inicia directamente en la carpeta predeterminada de descargas sin abrir el diálogo emergente, agilizando el flujo de trabajo.
  - **Sugerencia inteligente de subcarpeta**: Si se guardan múltiples vídeos de una lista (favoritos, listas de reproducción de YouTube, Ver más tarde o Historial), la subcarpeta sugerida es automáticamente el nombre de dicha lista. Si los vídeos no pertenecen a una lista (por ejemplo, vídeos de un canal o resultados de una búsqueda general), la sugerencia es el nombre del canal al que pertenecen. Se evita además la aparición de URLs en crudo como sugerencia.

### Añadido
- **Navegación jerárquica nivel a nivel con la tecla Escape**:
  - Al explorar el contenido en profundidad (por ejemplo, desde una lista de favoritos acceder a un canal, desde el canal a sus listas de reproducción y desde una lista a sus vídeos), pulsar la tecla `Escape` (o `Alt + Flecha Izquierda`) retrocede de forma escalonada al nivel inmediatamente anterior (vídeos -> listas -> canal -> favoritos).
  - Preserva fielmente la selección, posición del cursor y elementos marcados en cada nivel previo para no perder el contexto de navegación.
  - Al alcanzar el nivel raíz (la lista inicial de favoritos o la búsqueda principal), una pulsación adicional de `Escape` limpia los resultados y devuelve el foco al campo de búsqueda.
  - Anuncia adecuadamente al lector de pantalla cada transición de nivel y el número de elementos restaurados.
- **Visualización contextual de descripciones para vídeos, listas y canales**:
  - Nueva opción en el menú contextual de cada elemento de la lista adaptada a su contexto: "Descripción del vídeo", "Descripción de la lista" o "Descripción del canal".
  - Diálogo accesible que presenta la descripción completa con botón para copiar al portapapeles y botón para aceptar y salir.
  - Carga asíncrona en segundo plano con soporte y anuncios inmediatos para lectores de pantalla (NVDA, JAWS).
- **Sonido de espera periódico y continuo durante las descargas**:
  - Nuevo módulo `sound_manager.py` que genera y emite un pulso armónico sutil y no intrusivo (`espera.wav`, 523 Hz, ~90 ms a bajo volumen) cada 2 segundos mientras las descargas se procesan en segundo plano.
  - Compatible y respetuoso con lectores de pantalla (NVDA, JAWS).
  - Casilla configurable en Preferencias (`Ctrl + ,` / `F2`) -> pestaña *Descargas*.

---

## [1.5.3] - 2026-10-11

### Añadido
- **Cambiar elementos de una lista de favoritos a otra**:
  - Al abrir el menú contextual de un elemento que se encuentra en favoritos (tanto en la vista de favoritos como en resultados), aparece la opción/submenú "Cambiar de lista de favoritos".
  - Muestra todas las listas existentes (indicando cuál es la actual), la opción "[+] Nueva lista..." para crear una lista sobre la marcha y la opción de seleccionarla mediante diálogo accesible.
  - Al seleccionar la lista de destino, el elemento se añade a esa lista elegida y se elimina de la anterior.
  - **Soporte de movimiento por lotes y control de favoritos**: si hay varios elementos marcados/seleccionados (con la barra espaciadora o `Ctrl + A`), se moverán simultáneamente a la nueva lista elegida. Si el elemento o ninguno de los elementos seleccionados está en favoritos, la opción "Cambiar de lista" no se muestra ni se permite, ofreciendo únicamente "Añadir a favoritos" (ya que no se puede cambiar algo que no está en ninguna lista).
  - Nuevo atajo de teclado accesible **`Ctrl + M`** para cambiar de lista de favoritos los elementos que ya pertenezcan a alguna lista.
- **Copiar enlace del vídeo en reproducción (Ctrl + Shift + C)**:
  - Posibilidad de copiar al portapapeles el enlace del vídeo actualmente en reproducción pulsando el atajo `Ctrl + Shift + C` (o `Ctrl + C`).
  - Nuevo botón "Copiar enlace (Ctrl+Shift+C)" integrado directamente en los controles de reproducción.
  - Atajo `Ctrl + Shift + C` registrado también globalmente en la ventana principal.

---

## [1.5.2] - 2026-10-11

### Añadido
- **Organización automática en subcarpetas para descargas múltiples**:
  - Al descargar varios vídeos seleccionados o una lista completa de favoritos, la aplicación pregunta en qué subcarpeta de la carpeta predeterminada se desean guardar los archivos.
  - Se sugiere automáticamente el nombre de la lista de favoritos o los términos de búsqueda, permitiendo también dejar el campo en blanco para guardar directamente en la carpeta principal.
- **Nuevos formatos de audio de alta fidelidad (FLAC y WAV)**:
  - Formato `Audio FLAC (Sin pérdida)`: audio de calidad de estudio sin compresión destructiva.
  - Formato `Audio WAV (PCM sin comprimir)`: audio digital en forma de onda pura.
  - Disponibles tanto en el desplegable de descarga de la ventana principal (`Alt + F`) como en las opciones de formato predeterminado en Preferencias (`Ctrl + P`).

### Optimizado
- **Reproducción de audio instantánea y transiciones inmediatas**:
  - Precarga predictiva en segundo plano al seleccionar o recorrer cualquier elemento de la lista de resultados, eliminando tiempos de espera al pulsar Reproducir.
  - Pipeline de precarga continua de hasta 2 pistas en el reproductor multimedia: transiciones instantáneas al saltar entre canciones con la tecla `N`.
  - Caché persistente en memoria para URLs de streaming, evitando demoras de red al repetir o navegar entre pistas previas y siguientes.

---

## [1.5.1] - 2026-10-10

### Añadido
- **Soporte completo para Cookies y Autenticación de sesiones**:
  - Opción de extraer automáticamente cookies desde navegadores instalados (Firefox, Chrome, Edge, Brave, Opera, Vivaldi).
  - Soporte para cargar archivos de cookies exportados en formato `cookies.txt`.
  - Botón "Probar conexión" en la pestaña de Sesión/Cookies de Preferencias para verificar el acceso y validez de la sesión configurada.
  - Permite descargar y reproducir vídeos con restricciones de edad, contenido privado accesible por la cuenta o bloqueos temporales por peticiones.
- **Limpieza rápida con tecla Escape**:
  - En la lista de resultados de búsqueda, pulsar `Escape` borra los resultados y restablece la vista al estado inicial.
  - Si la lista ya se encuentra vacía o limpia, pulsar `Escape` no emite mensajes ni interrumpe la síntesis del lector de pantalla.

### Optimizado
- **Rendimiento y velocidad de reproducción (Streaming)**:
  - Reducción de latencia de red y pre-buffering (`network-caching`, `file-caching`, `live-caching` ajustados).
  - Detención instantánea y no bloqueante del reproductor VLC al saltar entre pistas cuando la reproducción de vídeo está desactivada.
- **Diálogo de actualización de yt-dlp**:
  - Al pulsar `Ctrl + U`, si yt-dlp ya está en su versión más reciente, el botón "Actualizar" se oculta automáticamente, mostrando únicamente la opción de Aceptar o cerrar cómodamente con `Escape`.

### Documentación
- Actualizados el Manual de Usuario (`docs/manual.html`, `docs/manual.md`) y la Guía de Atajos (`docs/atajos.html`, `docs/atajos.md`) con explicaciones detalladas sobre el uso de cookies y extensiones de navegador recomendadas.

---

## [1.5.0] - 2026-10-09

### Añadido
- **Eliminación de favoritos mediante la tecla Supr (Delete)**:
  - Posibilidad de eliminar elementos de una lista de favoritos directamente pulsando `Supr` en la lista de resultados o desde el reproductor multimedia.
- **Confirmación antes de eliminar favoritos**:
  - Petición de confirmación antes de borrar un elemento para prevenir eliminaciones accidentales.
  - Opción configurable desde el diálogo de Opciones y Preferencias (`F2` / `Ctrl + ,`), activada por defecto.

---

## [1.4.9] - 2026-10-08

### Optimizado
- Sistema de actualización transaccional y atómica para evitar bloqueos en entornos portables de Windows.
- Prevención de bloqueos al descargar dependencias de lectores de pantalla.

---

## [1.4.6] - 2026-10-07

### Añadido
- Gestión modular de listas de favoritos guardadas en ficheros `.json` independientes (`config/favoritos/`).
- Reproductor integrado con streaming continuo y modo solo audio rápido (`F11`).
