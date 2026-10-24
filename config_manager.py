"""
Módulo de gestión de configuración, rutas del sistema y parámetros de sesión/cookies.
"""

import json
import os
import shutil
import subprocess
import sys
import webbrowser


DEFAULT_CONFIG = {
    'destino_dir': '',
    'formato_idx': 0,
    'engine_idx': 0,
    'search_type_idx': 0,
    'max_results': 25,
    'volumen': 80,
    'repetir_reproductor': False,
    'aleatorio_reproductor': False,
    'reproducir_con_video': True,
    'velocidad_reproduccion': 1.0,
    'audio_output_device': '',      # Identificador GUID de dispositivo libvlc ('', o {0.0.0...})
    'audio_output_device_name': '', # Nombre descriptivo del dispositivo de salida
    'abrir_carpeta_al_terminar': False,
    'preguntar_abrir_carpeta': True,
    'confirmar_eliminar_favorito': True,
    'sonido_espera_descarga': True,  # Sonido de espera periódico durante la descarga
    'modo_locuciones': 'auto',       # 'auto' (solo con lector activo), 'siempre', 'desactivado'
    'cookie_source': 'none',        # 'none', 'browser', 'file'
    'cookie_browser': 'firefox',    # 'firefox', 'chrome', 'edge', 'brave', 'opera', 'vivaldi'
    'cookie_file': ''               # ruta a cookies.txt
}

ENGINES_MAP = {
    0: ('ytsearch', 'YouTube'),
    1: ('scsearch', 'SoundCloud'),
    2: ('bcsearch', 'Bandcamp'),
    3: ('bilisearch', 'Bilibili'),
}

FORMATOS_MAP = {
    0: 'video_best',
    1: 'audio_mp3_192',
    2: 'audio_mp3_320',
    3: 'audio_m4a'
}



def get_base_dir():
    """Retorna el directorio base de la aplicación (carpeta del ejecutable o script principal)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_config_dir():
    """Retorna la ruta al directorio de configuración y favoritos."""
    path = os.path.join(get_base_dir(), 'config')
    os.makedirs(path, exist_ok=True)
    return path


def get_config_file_path():
    """Retorna la ruta al archivo config.json dentro de la carpeta config."""
    return os.path.join(get_config_dir(), 'config.json')


def get_bin_dir():
    """Retorna la ruta al directorio bin para yt-dlp y ejecutables auxiliares."""
    path = os.path.join(get_base_dir(), 'bin')
    os.makedirs(path, exist_ok=True)
    return path


def get_docs_dir():
    """Retorna la ruta al directorio docs donde residen manuales y documentación."""
    path = os.path.join(get_base_dir(), 'docs')
    os.makedirs(path, exist_ok=True)
    return path


def get_resources_dir():
    """Retorna la ruta al directorio resources donde residen librerías externas (VLC, etc.)."""
    path = os.path.join(get_base_dir(), 'resources')
    os.makedirs(path, exist_ok=True)
    return path


def get_app_data_dir():
    """Retorna la carpeta bin/ para guardar binarios actualizados."""
    bin_dir = get_bin_dir()
    if os.access(bin_dir, os.W_OK):
        return bin_dir
    base = os.getenv('LOCALAPPDATA') or os.path.expanduser('~')
    app_dir = os.path.join(base, 'YouTubeDownloader', 'bin')
    os.makedirs(app_dir, exist_ok=True)
    return app_dir


def get_external_ytdlp_exe():
    """Retorna la ruta al ejecutable yt-dlp.exe buscando primero en bin/, luego en la carpeta base, AppData o PATH."""
    exe_in_bin = os.path.join(get_bin_dir(), 'yt-dlp.exe')
    if os.path.isfile(exe_in_bin):
        return exe_in_bin

    exe_in_base = os.path.join(get_base_dir(), 'yt-dlp.exe')
    if os.path.isfile(exe_in_base):
        return exe_in_base

    base_appdata = os.getenv('LOCALAPPDATA') or os.path.expanduser('~')
    custom_exe = os.path.join(base_appdata, 'YouTubeDownloader', 'bin', 'yt-dlp.exe')
    if os.path.isfile(custom_exe):
        return custom_exe

    sys_exe = shutil.which('yt-dlp') or shutil.which('yt-dlp.exe')
    if sys_exe and os.path.isfile(sys_exe):
        return sys_exe

    return None


def get_ffmpeg_dir():
    """Retorna el directorio donde se encuentra ffmpeg.exe (bin/, base_dir, PATH o static_ffmpeg)."""
    bin_ffmpeg = os.path.join(get_bin_dir(), 'ffmpeg.exe')
    if os.path.isfile(bin_ffmpeg):
        return get_bin_dir()

    base_ffmpeg = os.path.join(get_base_dir(), 'ffmpeg.exe')
    if os.path.isfile(base_ffmpeg):
        return get_base_dir()

    sys_ffmpeg = shutil.which('ffmpeg')
    if sys_ffmpeg:
        return os.path.dirname(sys_ffmpeg)

    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
        st_ffmpeg = shutil.which('ffmpeg')
        if st_ffmpeg:
            return os.path.dirname(st_ffmpeg)
    except Exception:
        pass

    return None


def abrir_manual_usuario():
    """Abre el manual de usuario en formato web (manual.html) en el navegador predeterminado."""
    docs_dir = get_docs_dir()
    html_path = os.path.join(docs_dir, 'manual.html')
    md_path = os.path.join(docs_dir, 'manual.md')

    if os.path.isfile(html_path):
        webbrowser.open(f"file:///{os.path.abspath(html_path).replace(os.sep, '/')}")
        return True
    elif os.path.isfile(md_path):
        webbrowser.open(f"file:///{os.path.abspath(md_path).replace(os.sep, '/')}")
        return True
    return False


def abrir_atajos_teclado():
    """Abre la guía rápida de atajos de teclado en el navegador predeterminado."""
    docs_dir = get_docs_dir()
    html_path = os.path.join(docs_dir, 'atajos.html')
    md_path = os.path.join(docs_dir, 'atajos.md')

    if os.path.isfile(html_path):
        webbrowser.open(f"file:///{os.path.abspath(html_path).replace(os.sep, '/')}")
        return True
    elif os.path.isfile(md_path):
        webbrowser.open(f"file:///{os.path.abspath(md_path).replace(os.sep, '/')}")
        return True
    return False


def cargar_configuracion():
    """Carga la configuración persistente desde config/config.json."""
    cfg_path = get_config_file_path()
    legacy_cfg_path = os.path.join(get_base_dir(), 'config.json')
    config = dict(DEFAULT_CONFIG)

    user_home = os.path.expanduser("~")
    downloads_dir = os.path.join(user_home, "Downloads")
    if not os.path.exists(downloads_dir):
        downloads_dir = user_home
    config['destino_dir'] = downloads_dir

    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    config.update(data)
        except Exception:
            pass
    elif os.path.isfile(legacy_cfg_path):
        try:
            with open(legacy_cfg_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    config.update(data)
            guardar_configuracion(config)
        except Exception:
            pass

    if not config.get('destino_dir') or not str(config['destino_dir']).strip():
        config['destino_dir'] = downloads_dir
    return config


def guardar_configuracion(config_dict):
    """Guarda la configuración persistente en config/config.json."""
    cfg_path = get_config_file_path()
    try:
        with open(cfg_path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def get_cookie_args(cfg=None):
    """Retorna los argumentos de línea de comandos para cookies en yt-dlp.exe."""
    if cfg is None:
        cfg = cargar_configuracion()
    src = cfg.get('cookie_source', 'none')
    if src == 'browser':
        b = cfg.get('cookie_browser', 'firefox').strip().lower()
        if b:
            return ['--cookies-from-browser', b]
    elif src == 'file':
        f = cfg.get('cookie_file', '').strip()
        if f and os.path.isfile(f):
            return ['--cookies', f]
    return []


def get_cookie_ydl_opts(cfg=None):
    """Retorna opciones de cookies para la API python de yt-dlp."""
    if cfg is None:
        cfg = cargar_configuracion()
    src = cfg.get('cookie_source', 'none')
    if src == 'browser':
        b = cfg.get('cookie_browser', 'firefox').strip().lower()
        if b:
            return {'cookiesfrombrowser': (b,)}
    elif src == 'file':
        f = cfg.get('cookie_file', '').strip()
        if f and os.path.isfile(f):
            return {'cookiefile': f}
    return {}


def probar_conexion_sesion(cfg=None):
    """
    Comprueba si la sesión configurada (navegador o archivo cookies.txt) tiene acceso autenticado a YouTube.
    Retorna una tupla (éxito: bool, mensaje: str).
    """
    if cfg is None:
        cfg = cargar_configuracion()
    src = cfg.get('cookie_source', 'none')
    if src == 'none':
        return False, "La sesión está desactivada. Selecciona un navegador o archivo cookies.txt."

    if src == 'file':
        cfile = cfg.get('cookie_file', '').strip()
        if not cfile:
            return False, "No has seleccionado ningún archivo cookies.txt."
        if not os.path.isfile(cfile):
            return False, f"El archivo indicado no existe: {cfile}"

    cargs = get_cookie_args(cfg)
    if not cargs:
        return False, "No se pudieron generar los parámetros de cookies."

    custom_exe = get_external_ytdlp_exe()
    test_url = "https://www.youtube.com/feed/playlists"

    if custom_exe:
        cmd = [
            custom_exe,
            test_url,
            "--dump-single-json",
            "--flat-playlist",
            "--no-download",
            "--quiet",
            "--playlist-items", "1-1"
        ] + cargs
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=25,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if res.returncode == 0:
                return True, "¡Sesión conectada con éxito! Se tiene acceso a tus listas e historial de YouTube."

            stderr = res.stderr or ""
            if "Failed to decrypt with DPAPI" in stderr or "DPAPI" in stderr:
                return False, (
                    "Bloqueo de seguridad de Windows: El navegador seleccionado tiene activada la protección App-Bound Encryption "
                    "que impide a programas externos leer sus cookies directamente.\n\n"
                    "Solución recomendada:\n"
                    "1. Exporta tus cookies de YouTube a un archivo cookies.txt usando una extensión de tu navegador "
                    "(por ejemplo, 'Get cookies.txt LOCALLY' o 'Cookie-Editor').\n"
                    "2. En este menú, cambia el origen a 'Archivo cookies.txt' y selecciona el archivo guardado.\n"
                    "3. O usa Firefox como navegador, ya que no aplica el cifrado DPAPI exclusivo de Chromium."
                )

            return False, f"Error al verificar la sesión: {stderr.strip() or 'Código de salida ' + str(res.returncode)}"
        except subprocess.TimeoutExpired:
            return False, "Tiempo de espera agotado al verificar la sesión. Comprueba tu conexión a Internet."
        except Exception as e:
            return False, f"Error al ejecutar yt-dlp para verificar la sesión: {e}"

    try:
        import yt_dlp
    except ImportError:
        yt_dlp = None

    if yt_dlp:
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'playlist_items': '1',
            'skip_download': True
        }
        ydl_opts.update(get_cookie_ydl_opts(cfg))
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(test_url, download=False)
            return True, "¡Sesión conectada con éxito! Se tiene acceso a tus listas e historial de YouTube."
        except Exception as e:
            err_str = str(e)
            if "DPAPI" in err_str:
                return False, "Bloqueo de seguridad de Windows (DPAPI). Usa un archivo cookies.txt o Firefox."
            return False, f"Error al verificar la sesión: {err_str}"

    return False, "No se encontró el ejecutable yt-dlp para verificar la sesión."
