# Ficha para BuscaApps.com: Descargador de YouTube Accesible

A continuación tienes el texto preparado con la estructura y estilo habituales de **BuscaApps.com** (siguiendo el formato de fichas como la de SonicRoom y similares), listo para enviar o publicar en el portal.

---

## Título de la aplicación
**Descargador de YouTube Accesible (Windows)**

## Descripción breve (Meta Description)
Una herramienta de escritorio rápida, portable y 100% accesible diseñada para buscar, reproducir en streaming continuo y descargar vídeos, audios, canales y listas de reproducción de YouTube y múltiples plataformas multimedia.

---

## Datos de la aplicación
- **Versión de la aplicación:** 1.6.0
- **Precio:** Gratis (código abierto)
- **Idioma:** Español
- **En la sección de:** Audio e Imagen / Utilidades
- **Con grado de accesibilidad:** Excelente
- **Compatibilidad con lectores de pantalla:** NVDA, JAWS y Narrador de Windows
- **Publicada por:** José Manuel Fernández Cortés
- **Autor de la app:** José Manuel Fernández Cortés
- **Link de descarga:** [https://buscaapps.com/youtube/](https://buscaapps.com/youtube/) (Descarga directa: [https://buscaapps.com/youtube/YouTubeDownloader.zip](https://buscaapps.com/youtube/YouTubeDownloader.zip))

---

## Notas de la aplicación

**Descargador de YouTube Accesible** es una aplicación de escritorio para Windows concebida desde sus cimientos para ofrecer una experiencia fluida, rápida y sin barreras a la hora de localizar, escuchar y descargar contenidos audiovisuales en Internet.

A diferencia de la mayoría de descargadores y clientes multimedia del mercado —que suelen presentar interfaces complejas, botones sin etiquetar, publicidad invasiva y escasa o nula compatibilidad con tecnologías de asistencia—, esta aplicación ha sido creada siguiendo una rigurosa filosofía **screen-reader-first**, garantizando que cualquier persona ciega o con baja visión pueda controlar todas sus funciones de forma autónoma mediante teclado y lector de pantalla.

### Búsqueda versátil de contenidos: vídeos, canales y listas
El programa permite buscar cómodamente en YouTube y descargar desde más de 2.000 plataformas sin necesidad de abrir el navegador web:

- **Búsqueda por palabras clave o URL directa:** puedes escribir términos de búsqueda convencionales o pegar directamente el enlace de un vídeo, lista de reproducción o canal (`Alt + T` o `Ctrl + F`).
- **Vídeos individuales:** muestra títulos limpios, canal creador, duración y código identificador.
- **Canales enteros:** permite localizar canales mediante su nombre o alias `@usuario`, mostrando el número de suscriptores y vídeos. Al pulsar `Enter` o doble clic sobre un canal, se despliega automáticamente el catálogo completo de sus vídeos para explorar o descargar.
- **Listas de reproducción (Playlists):** localiza listas temáticas y permite explorar todos sus elementos de forma individual o descargarlas al completo.
- **Compatibilidad con más de 2.000 plataformas:** el motor universal reconoce y procesa automáticamente cualquier enlace directo pegado en la barra de búsqueda (SoundCloud, Bandcamp, Bilibili, Twitch, TikTok, Vimeo, RTVE, Ivoox y miles de servicios compatibles).

### Reproductor multimedia integrado con streaming continuo
Una de las grandes fortalezas del programa es que no obliga a descargar los archivos para poder disfrutarlos. Incorpora un reproductor nativo basado en **VLC** optimizado para accesibilidad:

- **Streaming inmediato:** escucha cualquier vídeo o pista al instante sin esperar a que termine de descargarse.
- **Reproducción continua de selecciones salteadas:** mediante la barra espaciadora (`Espacio`), puedes marcar elementos no consecutivos de la lista (por ejemplo, el 1º, el 4º y el 7º) y pulsar `Ctrl + P` para que el reproductor los emita en secuencia continua sin silencios ni pausas intermedias.
- **Pre-buffering inteligente:** a los 2 segundos de comenzar una pista (y 15 segundos antes de concluirla), el reproductor precarga en segundo plano el siguiente contenido para garantizar transiciones instantáneas y transparentes.
- **Modo Solo Audio Ultrarrápido (`F11`):** pensado especialmente para usuarios de lectores de pantalla y conexiones modestas, permite desactivar la ventana de vídeo con una sola pulsación, consumiendo el mínimo de ancho de banda y recursos de procesador.
- **Consultas habladas de tiempo:** pulsando `F9` o `F10` dentro del reproductor, el lector de pantalla anuncia de viva voz el tiempo transcurrido o el tiempo restante sin interrumpir la audición.

### Formatos de descarga flexibles y de alta fidelidad
Al momento de guardar contenidos en el equipo, el usuario dispone de opciones claras adaptadas a cada necesidad:

- **Vídeo MP4 en máxima calidad:** descarga la resolución más alta disponible combinando vídeo y pista de audio en un único contenedor reproducible en cualquier dispositivo.
- **Audio MP3 estándar (192 kbps):** ideal para audiolibros, charlas, programas de radio o podcasts, ahorrando espacio de almacenamiento.
- **Audio MP3 de alta fidelidad (320 kbps):** máxima calidad de compresión para melómanos y aficionados a la música.
- **Audio M4A (Original AAC):** extracción directa del flujo sonoro original sin pérdida por recodificación.

### Sistema de listas de favoritos en ficheros independientes
El programa cuenta con un gestor de favoritos multicategoría (`Ctrl + B` para añadir, `Ctrl + H` para consultar) que guarda cada lista en un fichero `.json` independiente dentro de la carpeta `config/favoritos/`. 

Esta arquitectura modular ofrece una ventaja extraordinaria: si quieres compartir con un amigo tu recopilación de "Música Clásica" o "Tutoriales de Informática", no necesitas compartir toda tu base de datos; basta con enviarle el archivo `Música Clásica.json`. Al pegarlo en su carpeta, la aplicación lo reconocerá de forma inmediata.

### Accesibilidad de primer nivel para lectores de pantalla
El programa ha sido probado exhaustivamente con **NVDA**, **JAWS** y **Narrador de Windows**:

- **Navegación 100% por teclado:** cada campo, lista, menú y botón cuenta con su correspondiente mnemónico (`Alt + Letra`) y atajos globales estándar (`Ctrl + Letra`).
- **Anuncios de voz discretos y no invasivos:** durante las descargas, el lector de pantalla recibe avisos hablados del porcentaje completado (cada 25%) y del término del proceso, sin desubicar el foco del usuario ni saturar la síntesis.
- **Señales acústicas y avisos en bandeja:** finalizada una descarga o actualización, se emite una sutil señal sonora accesible acompañada de notificación en el área de notificación de Windows.
- **Gestión automática de foco:** al cerrar diálogos o volver del reproductor, el cursor regresa exactamente a la posición donde se encontraba.

### Actualizaciones automáticas y motor yt-dlp desacoplado
- **Aplicación portable con actualizador silencioso:** no requiere instalación ni privilegios de administrador. Al publicarse una nueva versión, el actualizador integrado actualiza los archivos del programa preservando intactas las preferencias del usuario y sus listas de favoritos.
- **Motor `yt-dlp` actualizable bajo demanda (`Ctrl + U`):** el núcleo de descarga reside como componente independiente (`bin/yt-dlp.exe`). Si una plataforma modifica sus algoritmos, basta pulsar `Ctrl + U` para descargar la versión Nightly más reciente de yt-dlp sin necesidad de recompilar la aplicación.

---

## Tabla resumida de atajos de teclado clave

| Atajo | Acción |
| :--- | :--- |
| **`Ctrl + F` / `Alt + T`** | Enfocar el campo de búsqueda |
| **`Alt + I`** | Cambiar tipo de búsqueda (Vídeos, Canales, Listas) |
| **`Alt + B`** | Iniciar búsqueda |
| **`Espacio`** | Marcar / desmarcar elementos en la lista |
| **`Ctrl + P` / `Alt + P`** | Reproducir selección (individual o salteada) |
| **`Ctrl + L`** | Reproducir toda la lista completa en streaming |
| **`Ctrl + D` / `Alt + D`** | Descargar los elementos seleccionados |
| **`Ctrl + B`** | Añadir elemento a favoritos |
| **`Ctrl + H`** | Abrir y consultar listas de favoritos |
| **`Ctrl + Shift + P`** | Reproducir lista de favoritos de forma continua |
| **`Ctrl + U`** | Actualizar motor de descarga yt-dlp a la última versión |
| **`Ctrl + ,` / `F2`** | Abrir diálogo de Preferencias y Opciones |
| **`F1` / `Shift + F1`** | Abrir Manual de Usuario o Guía rápida de atajos |

---

## En resumen
**Descargador de YouTube Accesible** demuestra que la accesibilidad universal y la máxima potencia multimedia pueden ir de la mano en una herramienta moderna, ligera y completamente autónoma. Es una solución idónea tanto para usuarios ciegos o con discapacidad visual que buscan acceder a sus contenidos preferidos sin obstáculos, como para cualquier persona que valore la sencillez, el control por teclado y el rendimiento.

---

## Nota del desarrollador
> *"Esta aplicación nació con el objetivo de brindar una alternativa honesta, rápida y 100% amigable con lectores de pantalla para disfrutar de YouTube y otras plataformas de audio y vídeo en Windows, sin publicidad, sin interfaces confusas y con total libertad de movimiento mediante atajos de teclado.*
>
> *El proyecto es totalmente gratuito y portable. Si tenéis sugerencias, detectáis alguna necesidad de accesibilidad no cubierta o queréis proponer mejoras, vuestra retroalimentación es siempre muy bienvenida."*

---

## Recursos y enlaces de interés
- **Página oficial del proyecto y descarga:**  
  [https://buscaapps.com/youtube/](https://buscaapps.com/youtube/)
- **Enlace de descarga directa (paquete ZIP portable):**  
  [https://buscaapps.com/youtube/YouTubeDownloader.zip](https://buscaapps.com/youtube/YouTubeDownloader.zip)
- **Manifiesto de versiones y actualizaciones:**  
  [https://buscaapps.com/youtube/version.json](https://buscaapps.com/youtube/version.json)
