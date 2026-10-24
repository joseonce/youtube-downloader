# Descargador de YouTube - Manual de Usuario y Guía de Atajos de Teclado

Bienvenido al **Descargador de YouTube**, una aplicación de escritorio diseñada para buscar, reproducir en streaming continuo y descargar vídeos, pistas de audio, canales y listas de reproducción de YouTube y más de 50 plataformas multimedia compatibles.

---

## Índice

1. [Estructura de Carpetas de la Aplicación](#1-estructura-de-carpetas-de-la-aplicación)
2. [Búsqueda de Contenidos](#2-búsqueda-de-contenidos)
3. [Tipos de Búsqueda: Vídeos, Canales y Listas](#3-tipos-de-búsqueda-vídeos-canales-y-listas)
4. [Plataformas Multimedia Soportadas](#4-plataformas-multimedia-soportadas)
5. [Reproducción Multimedia Continua (VLC)](#5-reproducción-multimedia-continua-vlc)
6. [Descarga de Archivos y Formatos](#6-descarga-de-archivos-y-formatos)
7. [Sistema de Múltiples Listas de Favoritos](#7-sistema-de-múltiples-listas-de-favoritos)
8. [Configuración y Opciones del Programa](#8-configuración-y-opciones-del-programa)
9. [Actualizaciones del Motor yt-dlp (Nightly)](#9-actualizaciones-del-motor-yt-dlp-nightly)
10. [Tabla Completa de Atajos de Teclado](#10-tabla-completa-de-atajos-de-teclado)

---

## 1. Estructura de Carpetas de la Aplicación

La aplicación organiza sus componentes en carpetas independientes para máxima modularidad y portabilidad:

- **`bin/`**: Aloja el motor de descarga `yt-dlp.exe` y recibe automáticamente las actualizaciones Nightly descargadas desde el programa.
- **`config/`**: Contiene la configuración general del usuario (`config.json`) y la subcarpeta **`config/favoritos/`**, donde se almacena cada lista de favoritos en un fichero independiente `.json`.
- **`docs/`**: Incluye este manual de usuario (`manual.md`), la versión web interactiva (`manual.html`) y la guía de atajos (`atajos.md` / `atajos.html`).
- **`resources/`** (y `resources/vlc/`): Contiene los módulos y librerías externas de reproducción nativa (VLC), manteniendo el ejecutable ligero y desacoplado.

---

## 2. Búsqueda de Contenidos

Para buscar en la plataforma activa:
1. Pulsa **`Alt + T`** o **`Ctrl + F`** para situar el cursor en el campo **Términos o URL**.
2. Escribe palabras clave o pega directamente un enlace (vídeo, canal `@nombre` o lista de reproducción).
3. Selecciona el tipo de búsqueda en el cuadro combinado **Tipo** (`Alt + I`).
4. Pulsa **`Enter`** o haz clic en el botón **Buscar** (`Alt + B`).

> **Criterio de ordenación natural de yt-dlp:** Los resultados se devuelven y presentan respetando fielmente el orden de relevancia por defecto de yt-dlp. La cantidad de resultados a obtener se configura cómodamente en **Opciones y Preferencias** (`Ctrl + ,` o `F2`), manteniendo la barra de búsqueda limpia y despejada.

---

## 3. Tipos de Búsqueda: Vídeos, Canales y Listas

Por defecto, la aplicación se inicia lista para buscar en **YouTube** con el tipo de búsqueda en **Vídeos**. El tipo de búsqueda se puede alternar en el selector **Tipo** (`Alt + I`):

- **Vídeos** *(por defecto)*: Busca vídeos individuales ordenados de más visitados a menos, mostrando su título, canal creador, duración e identificador.
- **Canales**: Busca canales o creadores de contenido. Muestra el nombre del canal, su identificador `@usuario`, el número de suscriptores y, siempre que esté disponible en los metadatos de la plataforma, el número de vídeos que contiene (al igual que las listas de reproducción). Al pulsar **`Enter`** o **doble clic** sobre un canal, se cargarán automáticamente todos los vídeos subidos por dicho canal.
- **Listas de reproducción**: Busca listas temáticas mostrando el número de vídeos que contiene cada lista. Al pulsar **`Enter`** o **doble clic**, se listarán todos los vídeos de dicha lista.

---

## 4. Descarga Universal desde Más de 2.000 Plataformas Multimedia

El motor universal de **yt-dlp** reconoce y procesa automáticamente cualquier enlace directo que pegues en el campo de búsqueda (YouTube, SoundCloud, Bandcamp, Bilibili, Vimeo, Dailymotion, Twitch, TikTok, Facebook, Twitter/X, Instagram, Mixcloud, Ivoox, RTVE y más de 2.000 servicios compatibles).

No es necesario seleccionar ninguna plataforma previa: basta con pegar cualquier enlace directo en la barra de búsqueda y pulsar **`Enter`** o el botón **`Descargar`** para obtener el contenido en el formato deseado.

---

## 5. Reproducción Multimedia Continua (VLC)

La aplicación cuenta con un reproductor integrado con soporte de streaming directo y pre-carga en segundo plano:

- **Reproducir selección individual o marcada**: Pulsa **`Ctrl + P`** o el botón *Reproducir selección*.
- **Reproducción continua de pistas marcadas (salteadas)**: Puedes marcar con la barra espaciadora (**`Espacio`**) cualquier combinación de pistas no consecutivas de la lista de resultados (por ejemplo: la 1ª, la 3ª, la 6ª y la 10ª). Al pulsar **`Ctrl + P`** o el botón *Reproducir (N)*, el reproductor reproducirá en secuencia continua exclusivamente esas pistas seleccionadas, saltando automáticamente las intermedias.
- **Reproducir toda la lista continua**: Pulsa **`Ctrl + L`** para iniciar la reproducción ininterrumpida de todos los vídeos de la búsqueda.
- **Pausar o reanudar**: Pulsa **`Espacio`** dentro del reproductor para pausar o continuar la reproducción.
- **Control de volumen**: Pulsa **`Flecha Arriba`** para subir volumen (+5%) o **`Flecha Abajo`** para bajarlo (-5%).
- **Silenciar / Activar sonido (Mute)**: Pulsa la tecla **`M`** para silenciar el sonido o volver al volumen anterior.
- **Avanzar / Retroceder canciones de la lista en reproducción**: Pulsa **`Ctrl + Flecha Derecha`** (o tecla **`N`**) para pasar a la siguiente canción de la lista, y **`Ctrl + Flecha Izquierda`** (o tecla **`P`**) para volver a la canción anterior.
- **Añadir o quitar de Favoritos**: Pulsa la tecla **`B`** o **`F`** para añadir o eliminar de favoritos la pista que estás escuchando.
- **Descargar la pista en reproducción**: Pulsa **`Ctrl + D`** para descargar directamente el archivo en curso.
- **Cerrar el reproductor**: Pulsa **`Escape`** para detener la reproducción y regresar a la lista de resultados.
- **Activar / Desactivar ventana de vídeo (`F11`)**: Puedes ocultar o mostrar el panel de vídeo en cualquier instante pulsando **`F11`** o el botón de la barra de controles. Al desactivar el vídeo, el reproductor adopta un modo compacto de solo audio.
- **Modo Solo Audio Ultrarrápido**: Si configuras en Preferencias reproducir sin vídeo, la aplicación descarga y transmite exclusivamente el flujo de audio ligero, logrando transiciones instantáneas entre canciones con mínimo consumo de datos y CPU.
- **Pre-buffering inteligente**: A los 2 segundos de comenzar cada pista (y 15 segundos antes del final), el programa precarga automáticamente el siguiente contenido para una transición fluida y sin silencios.
- **Recuperación automática de foco tras cambio de tarea**: Si cambias de ventana o tarea en Windows (`Alt + Tab`) mientras estás reproduciendo y luego vuelves a YouTubeDownloader, la aplicación eleva automáticamente la ventana del reproductor y le devuelve el foco de inmediato para que puedas continuar controlando la reproducción, alternar vídeo (**`F11`**), volumen y atajos sin ninguna fricción.
- **Repetición continua**: Desactivada por defecto, pero conmutable al instante con la tecla **`R`**, el botón de repetición o en Preferencias.
- **Resumen de teclas en el reproductor**:
  - **`Espacio`**: Pausar / Reanudar reproducción.
  - **`Flecha Arriba / Abajo`**: Subir / Bajar volumen (+/- 5%).
  - **`M`**: Silenciar / Activar sonido (Mute).
  - **`Ctrl + Flecha Derecha`** o **`N`**: Avanzar a la siguiente canción / pista de la lista en reproducción.
  - **`Ctrl + Flecha Izquierda`** o **`P`**: Retroceder a la canción / pista anterior de la lista en reproducción.
  - **`B`** o **`F`**: Añadir o quitar de favoritos.
  - **`R`**: Alternar repetición continua (bucle).
  - **`F11`**: Activar / Desactivar ventana de vídeo (modo solo audio).
  - **`F9`**: Anunciar tiempo transcurrido con el lector de pantalla.
  - **`F10`**: Anunciar tiempo restante con el lector de pantalla.
  - **`Ctrl + D`**: Descargar el contenido en reproducción.
  - **`Escape`**: Cerrar el reproductor y volver a la ventana principal.
  - *Navegación temporal dentro de la misma canción*:
    - **`Flecha Derecha / Izquierda`**: Avanzar / Retroceder 10 segundos.
    - **`Shift + Flechas`**: Avanzar / Retroceder 1 segundo.
    - **`Shift + Alt + Flechas`**: Avanzar / Retroceder 5 segundos.
    - **`Ctrl + Shift + Flechas`**: Avanzar / Retroceder 1 minuto.
    - **`Ctrl + Alt + Shift + Flechas`**: Avanzar / Retroceder 5 minutos.

---

## 6. Descarga de Archivos y Formatos

Para descargar contenidos:
1. Marca los elementos deseados en la lista pulsando **`Espacio`** (o pulsa **`Ctrl + A`** para seleccionar todos).
2. Elige el formato de salida en el desplegable **Formato** (`Alt + F`):
   - **Vídeo (Mejor calidad MP4)**: Descarga la máxima resolución disponible con audio combinado.
   - **Audio MP3 (192 kbps - Estándar)**: Conversión rápida a MP3 de buena calidad.
   - **Audio MP3 (320 kbps - Alta fidelidad)**: Máxima calidad de audio MP3.
   - **Audio M4A (Original AAC)**: Audio original sin recodificación.
   - **Audio FLAC (Sin pérdida)**: Calidad de estudio sin pérdida (Free Lossless Audio Codec).
   - **Audio WAV (PCM sin comprimir)**: Formato de audio puro de máxima fidelidad.
3. Elige la carpeta de destino en **Carpeta de descarga** (`Alt + C`).
4. Pulsa el botón **Descargar selección** (`Alt + D` o `Ctrl + D`).
5. **Organización en subcarpetas para descargas múltiples**:
   - Si has seleccionado o marcado **más de un vídeo** (por ejemplo, mediante selección múltiple o varios elementos marcados con la barra espaciadora), la aplicación te preguntará en qué subcarpeta de la carpeta predeterminada deseas guardarlos. Si descargas un único elemento, se guardará directamente en la carpeta principal sin solicitar subcarpeta.
   - El programa sugerirá automáticamente el nombre de la lista (si los vídeos pertenecen a una lista de reproducción o de favoritos) o el nombre del canal correspondiente si no pertenecen a una lista.
   - Puedes escribir un nombre nuevo, dejar el sugerido, o dejar el campo vacío para guardarlos directamente en la carpeta principal sin crear subcarpeta.
   - Para cancelar la descarga completa en este punto, pulsa `Cancelar` o la tecla `Escape`.
- **Señalización sonora de espera**: Al iniciar la descarga se emite un leve sonido periódico (cada 2 segundos) que indica que la tarea está en curso y procesándose en segundo plano, deteniéndose automáticamente cuando la descarga finaliza o se cancela.
6. Puedes cancelar la descarga en cualquier momento durante el proceso pulsando **Cancelar** (`Alt + X`).

---

## 7. Sistema de Múltiples Listas de Favoritos en Ficheros Separados

Puedes organizar tus pistas y vídeos favoritos en diferentes listas temáticas:
- **Añadir a favoritos**: Pulsa **`Ctrl + B`** sobre cualquier elemento de la lista. Podrás elegir entre la lista *Principal*, cualquier lista existente o crear una nueva (ej. *Música Rock*, *Flamenco*, *Podcasts*, *Tutoriales*).
- **Ver favoritos**: Pulsa **`Ctrl + H`** para cargar la lista de favoritos deseada en la tabla de resultados.
- **Reproducción continua de favoritos**: Pulsa **`Ctrl + Shift + P`** para escuchar toda tu colección de favoritos sin interrupciones.
- **Eliminar de favoritos con la tecla Supr**: Tanto desde la lista de resultados como directamente desde el reproductor multimedia, puedes pulsar la tecla **`Supr`** para eliminar el elemento de favoritos. El programa solicitará confirmación previa por defecto, comportamiento configurable en Opciones.
- **Archivos independientes para compartir**: Cada lista de favoritos se guarda en un archivo `.json` independiente dentro de la carpeta **`config/favoritos/`** (por ejemplo: `Principal.json`, `Música Rock.json`, `Flamenco.json`). De esta forma, si quieres pasarle a un amigo tu lista de rock y a otro tu lista de flamenco según sus preferencias musicales, no necesitas compartir toda tu colección: simplemente le envías el archivo individual deseado (`Música Rock.json` o `Flamenco.json`). Al copiarlo en su carpeta `config/favoritos/`, el programa lo reconocerá automáticamente.

---

## 8. Configuración y Opciones del Programa

Accede al diálogo de **Preferencias** pulsando **`Ctrl + ,`** o **`F2`** para personalizar:
- **Carpeta de destino predeterminada**: Directorio en el que se guardarán los archivos descargados.
- **Formato de salida predeterminado**: Formato preseleccionado al iniciar la aplicación (MP4, MP3 192k, MP3 320k o M4A).
- **Cantidad de resultados por búsqueda**: Número máximo de resultados a recuperar por búsqueda (de 1 a 500, con **25** por defecto).
- **Abrir carpeta de descargas automáticamente al finalizar**: Abre de forma inmediata la carpeta de descargas en el Explorador de Windows cuando concluye la descarga de archivos.
- **Preguntar si abrir la carpeta al finalizar la descarga (cuadro Sí / No)**: Si la apertura automática está desmarcada, al finalizar la descarga la aplicación muestra un cuadro de diálogo accesible preguntando si deseas abrir la carpeta de destino ahora.
- **Emitir un leve sonido de espera periódico mientras se procesa la descarga**: Activa o desactiva el suave pulso auditivo cada 2 segundos mientras las descargas están en curso (activado por defecto).
- **Repetición continua activada por defecto en el reproductor**: Define si el reproductor multimedia arranca en bucle continuo o no (por defecto desactivada).
- **Reproducir con vídeo por defecto**: Activa la visualización de vídeo o el modo ultrarrápido de solo audio.
- **Dispositivo de salida de audio**: Permite elegir la tarjeta de sonido, altavoces o auriculares específicos exclusivos para el reproductor multimedia, con botón **Probar sonido** interactivo y **Actualizar** lista de dispositivos. Las locuciones TTS y los lectores de pantalla (NVDA, JAWS, Narrador) no se ven afectados por este cambio, manteniéndose siempre en el dispositivo habitual del sistema.
- **Locuciones de voz y lectores de pantalla**: Permite configurar cuándo emite la aplicación avisos hablados. Incluye tres opciones: **Automático** (recomendado: detecta automáticamente si hay un lector de pantalla activo como NVDA, JAWS o Narrador y solo emite locuciones en ese caso; las personas que ven y no usan lector no escucharán voces del sistema), **Siempre activadas** (emite locuciones usando la voz de Windows SAPI aunque no haya lector) y **Desactivadas** (silencio absoluto de locuciones de voz).
- **Pedir confirmación al eliminar un elemento de favoritos**: Solicita confirmación mediante un cuadro de diálogo antes de eliminar cualquier elemento de favoritos (activada por defecto).
- **Cuenta y Sesión de YouTube (Listas e Historial)**: Permite conectar la sesión activa de YouTube (usando el navegador Firefox/Brave o seleccionando un archivo `cookies.txt` exportado) para acceder a listas privadas, la lista "Ver más tarde" y el historial de reproducciones. Incluye un botón para probar la conexión en tiempo real.

### 8.1. Configuración de Cuenta de YouTube, Cookies y Complementos de Navegador

Para sacar el máximo provecho a la aplicación y vincular tu cuenta personal de YouTube:

#### ¿Para qué sirven las cookies de sesión?
1. **Acceso a contenidos privados**: Permite que el programa cargue tu Historial de reproducciones (**`Ctrl + Shift + H`**), tu lista de "Ver más tarde" (**`Ctrl + Shift + W`**) y todas las listas de reproducción privadas o creadas en tu cuenta (**`Ctrl + Shift + Y`**).
2. **Evitar bloqueos y restricciones de YouTube**: YouTube puede restringir temporalmente peticiones anónimas (mensajes como *"Sign in to confirm you're not a bot"*, límites de descargas o vídeos con restricción de edad para mayores de 18 años). Al suministrar tus cookies de sesión iniciada, YouTube identifica que eres un usuario humano registrado y autoriza la reproducción y descarga directa sin obstáculos.

#### Métodos de autenticación disponibles
En el diálogo de **Preferencias** (**`Ctrl + ,`** o **`F2`**), dentro del grupo **Cuenta y Sesión de YouTube**:
- **Desactivado**: No se envían credenciales (modo anónimo estándar).
- **Extraer del navegador**: Intenta leer las cookies directamente del perfil del navegador indicado (Firefox, Chrome, Edge, Brave, Opera, Vivaldi). *Nota*: En Windows, navegadores como Google Chrome o Microsoft Edge bloquean su base de datos de cookies en modo exclusivo mientras están en ejecución, o aplican cifrado DPAPI a nivel de proceso.
- **Archivo de cookies (`cookies.txt` exportado - Método Recomendado)**: Es la opción más fiable, universal y rápida. No depende de que el navegador esté abierto o cerrado y evita cualquier bloqueo del sistema operativo.

#### Cómo conseguir complementos y generar tu archivo `cookies.txt`
Para obtener tu archivo `cookies.txt` basta con instalar una extensión de navegador gratuita, segura y de código abierto que exporte cookies en el formato estándar Netscape:

1. **Extensiones recomendadas**:
   - **Get cookies.txt LOCALLY**:
     - Para navegadores basados en Chromium (Google Chrome, Microsoft Edge, Brave, Opera, Vivaldi): Disponible en la **Chrome Web Store** buscando *"Get cookies.txt LOCALLY"*.
     - Para Mozilla Firefox: Disponible en el catálogo oficial de **Firefox Browser Add-ons (AMO)** buscando *"Get cookies.txt LOCALLY"*.
   - *(Esta extensión destaca porque procesa las cookies de forma 100% local en tu equipo, sin enviarlas a servidores de terceros).*

2. **Paso a paso para exportar y configurar**:
   1. Instala el complemento en tu navegador habitual.
   2. Abre tu navegador y entra en [YouTube](https://www.youtube.com).
   3. Inicia sesión con tu cuenta de Google / YouTube habitual (comprueba que aparece tu avatar en la esquina superior).
   4. Haz clic en el icono del complemento "Get cookies.txt LOCALLY" en la barra de herramientas de tu navegador.
   5. En el menú que se despliega, pulsa el botón **"Export"** o **"Export as cookies.txt"**.
   6. El navegador descargará un archivo de texto (habitualmente `cookies.txt` o `youtube.com_cookies.txt`). Guárdalo en una carpeta fija de tu equipo (por ejemplo, en tus Documentos o en la carpeta del programa).
   7. En **Descargador de YouTube**, pulsa **`Ctrl + ,`** (o **`F2`**) para abrir Opciones.
   8. En el selector *Origen de sesión / cookies*, selecciona **Archivo de cookies (cookies.txt exportado)**.
   9. Pulsa el botón **Examinar...** y elige tu archivo `cookies.txt`.
   10. Pulsa el botón **Probar conexión** para comprobar que la verificación es exitosa y pulsa **Aceptar** para guardar.

---

## 9. Motor yt-dlp y Descarga Bajo Demanda

Para optimizar el tamaño del ejecutable y garantizar la máxima compatibilidad frente a cambios en las plataformas:
- **Desacoplado del ejecutable**: El motor de descarga `yt-dlp` no está embebido en el ejecutable principal, sino que reside de forma independiente como `bin/yt-dlp.exe`.
- **Descarga guiada al inicio**: Si el programa no encuentra el ejecutable en la carpeta, avisa al usuario: *"no se encuentra la librería necesaria para la ejecución del programa, se va a proceder a su descarga"*. Al pulsar Aceptar, se descarga la versión más reciente automáticamente.
- **Actualización manual accesible**: Pulsa **`Ctrl + U`** para consultar y actualizar la versión Nightly en cualquier momento.
  - Si la versión instalada ya coincide con la más reciente disponible en GitHub, el diálogo informa claramente: *"Ya dispones de la versión Nightly más reciente."*, oculta el botón de actualizar para no ofrecerlo innecesariamente, enfoca el botón **Aceptar** y permite cerrarse inmediatamente con la tecla **Escape**.
  - Si decides actualizar, tras completarse la descarga al 100%, la ventana actualiza la versión instalada en pantalla, oculta el botón de descarga y deja activo el botón **Aceptar**, pudiendo igualmente cerrarse en cualquier momento pulsando **Escape**.
- **Notificación en bandeja del sistema**: Cuando la descarga finaliza con éxito, aparece una notificación en la bandeja del sistema: *"librería descargada con éxito"*, leída en voz alta por el lector de pantalla.

---

## 10. Tabla Completa de Atajos de Teclado

### Atajos Globales y de Navegación
| Tecla | Acción |
| :--- | :--- |
| **`Ctrl + F`** | Enfocar el campo de búsqueda de texto o URL |
| **`Ctrl + P`** | Ver o reproducir los vídeos seleccionados / marcados |
| **`Ctrl + L`** | Reproducir toda la lista completa en modo continuo |
| **`Ctrl + D`** | Iniciar la descarga de los elementos seleccionados |
| **`Ctrl + O`** | Abrir la carpeta de descargas en el Explorador de Windows |
| **`Ctrl + H`** | Ver y cargar la lista de favoritos guardados |
| **`Ctrl + Shift + H`** | Cargar el Historial de reproducciones de YouTube |
| **`Ctrl + Shift + W`** | Cargar la lista "Ver más tarde" de YouTube |
| **`Ctrl + Shift + Y`** | Cargar las listas de reproducción de la cuenta de YouTube |
| **`Ctrl + Shift + P`** | Reproducir de forma continua la lista de favoritos |
| **`Ctrl + B`** | Añadir o eliminar el elemento actual de favoritos |
| **`Supr`** | Eliminar el elemento seleccionado de favoritos (con confirmación según preferencias) |
| **`Ctrl + C`** | Copiar el enlace del elemento seleccionado al portapapeles |
| **`Ctrl + U`** | Comprobar y actualizar yt-dlp a la versión Nightly |
| **`Ctrl + ,`** o **`F2`** | Abrir la ventana de Preferencias y Opciones |
| **`F1`** | Abrir este Manual de Usuario en el navegador |
| **`Shift + F1`** | Abrir la Guía rápida de Atajos de Teclado en el navegador |
| **`Escape`** | Limpiar resultados de búsqueda y volver al campo de texto (o cerrar diálogos) |
| **`Alt + F4`** | Salir de la aplicación |

### Atajos de Acceso Rápido (Mnemonics Alt + Letra)
| Tecla | Control Destino |
| :--- | :--- |
| **`Alt + T`** | Campo de edición de búsqueda (Términos o URL) |
| **`Alt + I`** | Cuadro combinado de Tipo de búsqueda (Vídeos, Canales, Listas) |
| **`Alt + B`** | Botón Buscar |
| **`Alt + L`** | Lista de resultados encontrados |
| **`Alt + F`** | Selector de Formato de descarga (MP4, MP3, M4A) |
| **`Alt + C`** | Campo de ruta de la Carpeta de descarga |
| **`Alt + E`** | Botón Examinar carpeta de descargas |
| **`Alt + D`** | Botón Descargar selección |
| **`Alt + P`** | Botón Reproducir selección |
| **`Alt + X`** | Botón Cancelar descarga activa |

### Interacción en la Lista de Resultados
| Tecla | Acción |
| :--- | :--- |
| **`Espacio`** | Marcar o desmarcar la casilla del elemento enfocado |
| **`Ctrl + A`** | Seleccionar y marcar todos los elementos de la lista |
| **`Enter`** | En un canal: listar sus vídeos. En una playlist: listar sus vídeos. En un vídeo: reproducir / abrir reproductor |
| **`Doble Clic`** | En un canal o playlist: abrir contenidos. En un vídeo: reproducir / abrir reproductor |
| **`Menú Contextual`** *(Tecla Aplicaciones / Clic Derecho)* | Opciones avanzadas: reproducir, descargar, favoritos, mostrar vídeos del canal al que pertenece, copiar URL del canal, etc. |

### Controles Dentro del Reproductor Multimedia
| Tecla | Acción |
| :--- | :--- |
| **`Espacio`** | Pausar o reanudar reproducción |
| **`Flecha Arriba`** | Subir volumen (+5%) |
| **`Flecha Abajo`** | Bajar volumen (-5%) |
| **`M`** | Silenciar o reactivar sonido (Mute) |
| **`Ctrl + Flecha Derecha`** o **`N`** | Avanzar a la siguiente canción / pista de la lista en reproducción |
| **`Ctrl + Flecha Izquierda`** o **`P`** | Retroceder a la canción / pista anterior de la lista en reproducción |
| **`B`** o **`F`** | Añadir o eliminar pista actual de Favoritos |
| **`Supr`** | Eliminar la pista en reproducción de Favoritos (con confirmación configurable) |
| **`R`** | Alternar repetición continua (activar / desactivar bucle) |
| **`F11`** | Activar o desactivar la ventana de vídeo (alternar modo vídeo y modo solo audio) |
| **`F9`** | Anunciar al lector de pantalla el tiempo transcurrido |
| **`F10`** | Anunciar al lector de pantalla el tiempo restante |
| **`Ctrl + D`** | Descargar el vídeo que se está reproduciendo |
| **`Escape`** | Cerrar el reproductor y volver a la ventana principal |
| **`Flecha Derecha`** | Avanzar 10 segundos en la reproducción |
| **`Flecha Izquierda`** | Retroceder 10 segundos en la reproducción |
| **`Shift + Flecha Derecha`** | Avanzar 1 segundo en la reproducción |
| **`Shift + Flecha Izquierda`** | Retroceder 1 segundo en la reproducción |
| **`Shift + Alt + Flecha Derecha`** | Avanzar 5 segundos en la reproducción |
| **`Shift + Alt + Flecha Izquierda`** | Retroceder 5 segundos en la reproducción |
| **`Ctrl + Shift + Flecha Derecha`** | Avanzar 1 minuto en la reproducción |
| **`Ctrl + Shift + Flecha Izquierda`** | Retroceder 1 minuto en la reproducción |
| **`Ctrl + Alt + Shift + Flecha Derecha`** | Avanzar 5 minutos en la reproducción |
| **`Ctrl + Alt + Shift + Flecha Izquierda`** | Retroceder 5 minutos en la reproducción |
