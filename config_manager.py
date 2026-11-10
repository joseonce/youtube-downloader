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
    'normalizar_volumen_reproductor': False,
    'reproductor_ventana_independiente': True,
    'cerrar_reproductor_al_finalizar': False,
    'audio_output_device': '',      # Identificador GUID de dispositivo libvlc ('', o {0.0.0...})
    'audio_output_device_name': '', # Nombre descriptivo del dispositivo de salida
    'abrir_carpeta_al_terminar': False,
    'preguntar_abrir_carpeta': True,
    'confirmar_eliminar_favorito': True,
    'sonido_espera_descarga': True,  # Sonido de espera periódico durante la descarga
    'modo_locuciones': 'auto',       # 'auto' (solo con lector activo), 'siempre', 'desactivado'
    'metodo_extraccion_ytdlp': 'rapido', # 'rapido', 'extendido', 'default'
    'ultimo_check_ytdlp': 0,        # Timestamp del último chequeo silencioso
    'caratula_modo': 'incrustada',   # 'incrustada', 'incrustada_y_jpg', 'solo_jpg', 'ninguna'
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
    3: 'audio_m4a',
    4: 'audio_flac',
    5: 'audio_wav',
}

FORMATOS_TODOS = [
    ('video_best', "Vídeo (Mejor calidad MP4)"),
    ('audio_mp3_192', "Audio MP3 (192 kbps - Estándar)"),
    ('audio_mp3_320', "Audio MP3 (320 kbps - Alta fidelidad)"),
    ('audio_m4a', "Audio M4A (Original AAC)"),
    ('audio_flac', "Audio FLAC (Sin pérdida)"),
    ('audio_wav', "Audio WAV (PCM sin comprimir)"),
]

FORMATOS_SOLO_AUDIO = [
    ('audio_mp3_192', "Audio MP3 (192 kbps - Estándar)"),
    ('audio_mp3_320', "Audio MP3 (320 kbps - Alta fidelidad)"),
    ('audio_m4a', "Audio M4A (Original AAC)"),
    ('audio_flac', "Audio FLAC (Sin pérdida)"),
    ('audio_wav', "Audio WAV (PCM sin comprimir)"),
]

MODOS_CARATULA = [
    ('incrustada', "Incrustada en el archivo de audio"),
    ('incrustada_y_jpg', "Incrustada y archivo .jpg"),
    ('solo_jpg', "Solo archivo .jpg"),
    ('ninguna', "Sin carátula"),
]

METODOS_EXTRACCION = {
    'rapido': {
        'id': 'rapido',
        'nombre': 'Rápido / Estándar (Android, iOS, Web - Recomendado)',
        'extractor_args': 'youtube:player_client=android,ios,web',
        'clients_list': ['android', 'ios', 'web'],
    },
    'extendido': {
        'id': 'extendido',
        'nombre': 'Compatibilidad extendida (VisionOS, TV - directos finalizados)',
        'extractor_args': 'youtube:player_client=android,web,ios,visionos,tv',
        'clients_list': ['android', 'web', 'ios', 'visionos', 'tv'],
    },
    'default': {
        'id': 'default',
        'nombre': 'Predeterminado de yt-dlp (sin restricciones)',
        'extractor_args': None,
        'clients_list': None,
    }
}

METODOS_EXTRACCION_LIST = ['rapido', 'extendido', 'default']


def get_ytdlp_extractor_args(override=None):
    """Retorna el argumento --extractor-args según la configuración o un override explícito."""
    if override and override in METODOS_EXTRACCION:
        return METODOS_EXTRACCION[override]['extractor_args']
    cfg = cargar_configuracion()
    metodo = cfg.get('metodo_extraccion_ytdlp', 'rapido')
    return METODOS_EXTRACCION.get(metodo, METODOS_EXTRACCION['rapido'])['extractor_args']


def get_ytdlp_clients_list(override=None):
    """Retorna la lista de clientes para la librería yt_dlp según la configuración o un override explícito."""
    if override and override in METODOS_EXTRACCION:
        return METODOS_EXTRACCION[override]['clients_list']
    cfg = cargar_configuracion()
    metodo = cfg.get('metodo_extraccion_ytdlp', 'rapido')
    return METODOS_EXTRACCION.get(metodo, METODOS_EXTRACCION['rapido'])['clients_list']



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

    appdata_exe = os.path.join(base_appdata, 'YouTubeDownloader', 'yt-dlp.exe')
    if os.path.isfile(appdata_exe):
        return appdata_exe

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
    return []


def get_cookie_ydl_opts(cfg=None):
    """Retorna opciones de cookies para la API python de yt-dlp."""
    return {}

