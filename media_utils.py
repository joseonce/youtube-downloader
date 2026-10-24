"""
Módulo de utilidades de formato, limpieza de títulos y análisis de URLs.
"""

import re


def formatear_duracion(segundos):
    """Convierte segundos a formato HH:MM:SS o MM:SS."""
    if segundos is None:
        return "Desconocida"
    try:
        seg = int(segundos)
        mins, secs = divmod(seg, 60)
        horas, mins = divmod(mins, 60)
        if horas > 0:
            return f"{horas:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"
    except Exception:
        return str(segundos)


def formatear_visitas(visitas):
    """Convierte un número de visitas a un formato legible en español (ej. 1.5M visitas, 350K visitas, 1200 visitas)."""
    if visitas is None or visitas == "":
        return "--"
    try:
        vc = int(visitas)
        if vc <= 0:
            return "--"
        if vc >= 1_000_000_000:
            val = f"{vc / 1_000_000_000:.1f}".replace('.0', '')
            return f"{val}B visitas"
        elif vc >= 1_000_000:
            val = f"{vc / 1_000_000:.1f}".replace('.0', '')
            return f"{val}M visitas"
        elif vc >= 1_000:
            val = f"{vc / 1_000:.1f}".replace('.0', '')
            return f"{val}K visitas"
        else:
            return f"{vc} visitas"
    except Exception:
        return str(visitas) if visitas else "--"


def formatear_tamano(bytes_cant):
    """Convierte bytes a formato legible (KB, MB, GB)."""
    if not bytes_cant:
        return "Desconocido"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_cant < 1024.0:
            return f"{bytes_cant:.1f} {unit}"
        bytes_cant /= 1024.0
    return f"{bytes_cant:.1f} TB"


def limpiar_caracteres_ansi(texto):
    """Elimina códigos de escape ANSI de cadenas de yt-dlp."""
    if not texto:
        return ""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', str(texto)).strip()


def limpiar_extension_titulo(titulo: str) -> str:
    """
    Elimina extensiones multimedia redundantes al final del título de un vídeo
    (por ejemplo, 'nombre.flv' o 'audio.mp3') para evitar nombres de archivo confusos
    como 'nombre.flv.mp3' o 'audio.mp3.mp3' al descargar.
    """
    if not titulo:
        return titulo
    patron = r'(?i)\.(mp4|flv|mkv|webm|avi|wmv|mov|m4v|3gp|vob|ogv|divx|mp3|m4a|aac|wav|flac|ogg|opus|wma)$'
    res = str(titulo).strip()
    while True:
        m = re.search(patron, res)
        if m:
            res = res[:m.start()].strip()
        else:
            break
    return res


def corregir_doble_extension(filepath: str) -> str:
    """
    Corrige nombres de archivo con doble extensión multimedia redundante
    como 'nombre.flv.mp3' o 'video.mp4.mp3' convirtiéndolos en 'nombre.mp3' o 'video.mp3'.
    """
    if not filepath:
        return filepath
    patron = r'(?i)\.(mp4|flv|mkv|webm|avi|wmv|mov|m4v|3gp|vob|ogv|divx|mp3|m4a|aac|wav|flac|ogg|opus|wma)\.([a-zA-Z0-9]+)$'
    res = str(filepath)
    while True:
        m = re.search(patron, res)
        if m:
            res = res[:m.start(1) - 1] + '.' + m.group(2)
        else:
            break
    return res


def identificar_tipo_url(texto: str) -> str:
    """
    Identifica si un texto/URL corresponde a:
    - 'canal': Canal de YouTube / creador
    - 'playlist': Lista de reproducción (incluye historial y ver más tarde)
    - 'video': Vídeo individual o enlace directo
    - 'texto': Términos de búsqueda comunes
    """
    if not texto:
        return 'texto'
    texto = texto.strip()

    if texto.startswith('@'):
        return 'canal'

    if not (texto.startswith('http://') or texto.startswith('https://') or texto.startswith('www.') or 'youtube.com/' in texto or 'youtu.be/' in texto):
        return 'texto'

    if '/feed/history' in texto or '/feed/playlists' in texto or '/feed/library' in texto:
        return 'playlist'

    if '/playlists' in texto:
        return 'canal'

    if 'playlist?list=' in texto or ('list=' in texto and 'watch' in texto):
        return 'playlist'

    if re.search(r'youtube\.com/(@[\w\-\.]+|channel/[\w\-]+|c/[\w\-]+|user/[\w\-]+)(?:/.*)?', texto, re.IGNORECASE):
        return 'canal'
    if re.search(r'/(?:@[\w\-\.]+|channel/[\w\-]+|c/[\w\-]+|user/[\w\-]+)', texto, re.IGNORECASE):
        return 'canal'

    return 'video'
