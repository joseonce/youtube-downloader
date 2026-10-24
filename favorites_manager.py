"""
Módulo de gestión de listas de favoritos independientes, persistencia y operaciones CRUD.
"""

import json
import os
import re

from config_manager import get_config_dir
from media_utils import identificar_tipo_url


def get_favoritos_dir():
    """Retorna la ruta al directorio donde se guardan las listas de favoritos independientes."""
    path = os.path.join(get_config_dir(), 'favoritos')
    os.makedirs(path, exist_ok=True)
    return path


def _nombre_lista_a_filename(nombre_lista: str) -> str:
    """Convierte el nombre de una lista de favoritos a un nombre de archivo seguro."""
    nombre = (nombre_lista or 'Principal').strip()
    seguro = re.sub(r'[<>:"/\\|?*]', '_', nombre)
    if not seguro:
        seguro = 'Principal'
    return f"{seguro}.json"


def _filename_a_nombre_lista(filename: str) -> str:
    """Obtiene el nombre de la lista a partir del nombre del archivo json."""
    base, _ = os.path.splitext(filename)
    return base


def get_favoritos_file_path(nombre_lista='Principal'):
    """Retorna la ruta al archivo .json de una lista de favoritos específica dentro de config/favoritos/."""
    fav_dir = get_favoritos_dir()
    fname = _nombre_lista_a_filename(nombre_lista)
    return os.path.join(fav_dir, fname)


def _normalizar_favoritos(cfg_o_dict):
    """Asegura que el diccionario de favoritos sea un diccionario de listas."""
    favs = cfg_o_dict.get('favoritos') if isinstance(cfg_o_dict, dict) and 'favoritos' in cfg_o_dict else cfg_o_dict
    if isinstance(favs, list):
        fav_dict = {'Principal': favs}
    elif isinstance(favs, dict):
        fav_dict = favs
        if not fav_dict:
            fav_dict = {'Principal': []}
    else:
        fav_dict = {'Principal': []}
    return fav_dict


def cargar_favoritos():
    """
    Carga todas las listas de favoritos desde ficheros separados en config/favoritos/<lista>.json.
    Realiza migración automática transparente desde el antiguo config/favoritos.json
    o desde config.json si existieran.
    Retorna un diccionario {nombre_lista: [videos]}.
    """
    fav_dir = get_favoritos_dir()
    legacy_fav_file = os.path.join(get_config_dir(), 'favoritos.json')
    legacy_cfg_file = os.path.join(get_config_dir(), 'config.json')

    # 1. Migración automática si existe el archivo monolítico config/favoritos.json
    if os.path.isfile(legacy_fav_file):
        try:
            with open(legacy_fav_file, 'r', encoding='utf-8') as f:
                legacy_data = json.load(f)
            if isinstance(legacy_data, list):
                target_path = os.path.join(fav_dir, 'Principal.json')
                with open(target_path, 'w', encoding='utf-8') as f:
                    json.dump(legacy_data, f, indent=2, ensure_ascii=False)
            elif isinstance(legacy_data, dict):
                for n_lista, vids in legacy_data.items():
                    target_path = os.path.join(fav_dir, _nombre_lista_a_filename(n_lista))
                    with open(target_path, 'w', encoding='utf-8') as f:
                        json.dump(vids if isinstance(vids, list) else [], f, indent=2, ensure_ascii=False)
            try:
                os.remove(legacy_fav_file)
            except Exception:
                pass
        except Exception:
            pass

    # 2. Migración si había favoritos en config.json
    if os.path.isfile(legacy_cfg_file):
        try:
            with open(legacy_cfg_file, 'r', encoding='utf-8') as f:
                cfg_data = json.load(f)
            if isinstance(cfg_data, dict) and 'favoritos' in cfg_data:
                favs_en_cfg = cfg_data.pop('favoritos')
                fav_dict = _normalizar_favoritos(favs_en_cfg)
                for n_lista, vids in fav_dict.items():
                    target_path = os.path.join(fav_dir, _nombre_lista_a_filename(n_lista))
                    if not os.path.isfile(target_path):
                        with open(target_path, 'w', encoding='utf-8') as f:
                            json.dump(vids if isinstance(vids, list) else [], f, indent=2, ensure_ascii=False)
                with open(legacy_cfg_file, 'w', encoding='utf-8') as f:
                    json.dump(cfg_data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # 3. Leer todos los archivos .json independientes dentro de config/favoritos/
    favs = {}
    try:
        archivos = [f for f in os.listdir(fav_dir) if f.lower().endswith('.json')]
    except Exception:
        archivos = []

    for arch in archivos:
        nombre_lista = _filename_a_nombre_lista(arch)
        arch_path = os.path.join(fav_dir, arch)
        try:
            with open(arch_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    favs[nombre_lista] = data
                elif isinstance(data, dict):
                    favs[nombre_lista] = data.get('videos', []) if 'videos' in data else []
                else:
                    favs[nombre_lista] = []
        except Exception:
            favs[nombre_lista] = []

    if 'Principal' not in favs:
        favs['Principal'] = []
        try:
            with open(os.path.join(fav_dir, 'Principal.json'), 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    return favs


def guardar_favoritos(fav_dict):
    """
    Guarda cada lista de favoritos en su propio archivo config/favoritos/<lista>.json.
    Si alguna lista fue eliminada de fav_dict, se elimina su archivo correspondiente del disco.
    """
    fav_dir = get_favoritos_dir()
    try:
        existentes = {os.path.splitext(f)[0]: f for f in os.listdir(fav_dir) if f.lower().endswith('.json')}
    except Exception:
        existentes = {}

    exito = True
    for nombre_lista, videos in fav_dict.items():
        fname = _nombre_lista_a_filename(nombre_lista)
        fpath = os.path.join(fav_dir, fname)
        try:
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(videos if isinstance(videos, list) else [], f, indent=2, ensure_ascii=False)
        except Exception:
            exito = False

    # Eliminar archivos de listas que ya no existen en fav_dict
    for n_existente, fname in existentes.items():
        if n_existente not in fav_dict:
            fpath = os.path.join(fav_dir, fname)
            try:
                os.remove(fpath)
            except Exception:
                pass

    return exito


def guardar_lista_favoritos(nombre_lista: str, videos: list):
    """Guarda directamente una lista de favoritos específica en su propio archivo .json."""
    fpath = get_favoritos_file_path(nombre_lista)
    try:
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(videos if isinstance(videos, list) else [], f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def eliminar_lista_favoritos(nombre_lista: str):
    """Elimina el archivo .json de una lista de favoritos específica del disco."""
    if nombre_lista == 'Principal':
        return guardar_lista_favoritos('Principal', [])
    fpath = get_favoritos_file_path(nombre_lista)
    if os.path.isfile(fpath):
        try:
            os.remove(fpath)
            return True
        except Exception:
            return False
    return False


def obtener_listas_favoritos():
    """Retorna el diccionario con todas las listas de favoritos {nombre_lista: [videos]}."""
    return cargar_favoritos()


def obtener_nombres_listas_favoritos():
    """Retorna la lista de nombres de las listas de favoritos disponibles con 'Principal' al inicio."""
    favs_dict = cargar_favoritos()
    otros = [k for k in favs_dict.keys() if k != 'Principal']
    otros.sort(key=lambda s: s.lower())
    return ['Principal'] + otros


def obtener_favoritos(nombre_lista=None):
    """
    Retorna la lista de vídeos favoritos guardados.
    Si nombre_lista es None o 'Todas', retorna todos los vídeos sin duplicados.
    """
    favs_dict = cargar_favoritos()
    if nombre_lista and nombre_lista != 'Todas':
        return favs_dict.get(nombre_lista, [])

    todos = []
    vistos = set()
    for n_lista, vids in favs_dict.items():
        for f in vids:
            ident = f.get('url') or f.get('id')
            if ident and ident not in vistos:
                vistos.add(ident)
                item_copy = dict(f)
                item_copy['list_name'] = n_lista
                todos.append(item_copy)
    return todos


def detectar_tipo_elemento(item: dict) -> str:
    """
    Retorna 'channel', 'playlist' o 'video' analizando un elemento de favoritos o resultados.
    """
    if not isinstance(item, dict):
        return 'video'
    if item.get('is_channel') or item.get('tipo_item') in ('channel', 'canal') or item.get('type') in ('channel', 'canal'):
        return 'channel'
    if item.get('is_playlist') or item.get('tipo_item') == 'playlist' or item.get('type') == 'playlist':
        return 'playlist'
    url = item.get('url', '')
    if url:
        t = identificar_tipo_url(url)
        if t in ('canal', 'channel'):
            return 'channel'
        if t == 'playlist':
            return 'playlist'
    duration = str(item.get('duration', ''))
    views = str(item.get('views', ''))
    if duration == 'Canal' or 'suscriptor' in views.lower():
        return 'channel'
    if 'vídeos' in duration.lower() and not item.get('duration_seconds'):
        return 'playlist'
    return 'video'


def agregar_favorito(video_data, nombre_lista="Principal"):
    """Añade un vídeo, canal o playlist a la lista de favoritos indicada si no está ya presente en ella."""
    fav_dict = cargar_favoritos()

    nombre_lista = (nombre_lista or 'Principal').strip()
    if nombre_lista not in fav_dict:
        fav_dict[nombre_lista] = []

    lista = fav_dict[nombre_lista]
    vid_id = str(video_data.get('id', ''))
    vid_url = video_data.get('url', '')

    if any(f.get('id') == vid_id or (vid_url and f.get('url') == vid_url) for f in lista):
        return False

    tipo = detectar_tipo_elemento(video_data)

    fav_item = {
        'id': vid_id,
        'title': video_data.get('title', 'Sin título'),
        'channel': video_data.get('channel', 'Desconocido'),
        'duration': video_data.get('duration', 'Desconocida'),
        'duration_seconds': video_data.get('duration_seconds', 0),
        'views': video_data.get('views', '--'),
        'url': vid_url,
        'type': tipo,
        'is_channel': (tipo == 'channel'),
        'is_playlist': (tipo == 'playlist'),
        'tipo_item': tipo,
        'list_name': nombre_lista
    }
    lista.append(fav_item)
    return guardar_lista_favoritos(nombre_lista, lista)


def crear_lista_favoritos(nombre_lista):
    """Crea una nueva lista de favoritos vacía en su propio archivo .json."""
    nombre_lista = (nombre_lista or '').strip()
    if not nombre_lista:
        return False
    fav_dir = get_favoritos_dir()
    fname = _nombre_lista_a_filename(nombre_lista)
    fpath = os.path.join(fav_dir, fname)
    if os.path.isfile(fpath):
        return True
    try:
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def eliminar_favorito(video_id_o_url, nombre_lista=None):
    """Elimina un vídeo de una lista específica o de todas las listas de favoritos."""
    fav_dict = cargar_favoritos()
    hubo_cambios = False

    listas_a_procesar = [nombre_lista] if (nombre_lista and nombre_lista in fav_dict) else list(fav_dict.keys())
    for n in listas_a_procesar:
        antes = len(fav_dict[n])
        fav_dict[n] = [
            f for f in fav_dict[n]
            if str(f.get('id', '')) != str(video_id_o_url) and f.get('url') != str(video_id_o_url)
        ]
        if len(fav_dict[n]) != antes:
            hubo_cambios = True
            guardar_lista_favoritos(n, fav_dict[n])

    return hubo_cambios


def es_favorito(video_id_o_url, nombre_lista=None):
    """Verifica si un vídeo está guardado en favoritos."""
    favoritos = obtener_favoritos(nombre_lista=nombre_lista)
    return any(
        str(f.get('id', '')) == str(video_id_o_url) or (f.get('url') and f.get('url') == str(video_id_o_url))
        for f in favoritos
    )


def obtener_listas_de_item(video_id_o_url):
    """Retorna una lista con los nombres de todas las listas de favoritos donde está guardado el elemento."""
    fav_dict = cargar_favoritos()
    encontradas = []
    vid_str = str(video_id_o_url)
    for nombre_lista, videos in fav_dict.items():
        if any(str(f.get('id', '')) == vid_str or (f.get('url') and str(f.get('url')) == vid_str) for f in videos):
            encontradas.append(nombre_lista)
    return encontradas


def mover_favorito_de_lista(video_data, lista_destino, lista_origen=None):
    """
    Mueve un elemento favorito de una lista a otra.
    Si lista_origen no se especifica o es 'Todas las listas', busca en qué lista(s) se encuentra
    y lo elimina de allí, añadiéndolo a lista_destino.
    Retorna True si se movió o ya estaba en la lista destino.
    """
    if not isinstance(video_data, dict):
        return False
    vid_id_or_url = video_data.get('url') or video_data.get('id', '')
    if not vid_id_or_url:
        return False

    fav_dict = cargar_favoritos()
    lista_destino = (lista_destino or 'Principal').strip()

    if lista_destino not in fav_dict:
        crear_lista_favoritos(lista_destino)
        fav_dict = cargar_favoritos()

    origenes = []
    if lista_origen and lista_origen != "Todas las listas" and lista_origen in fav_dict:
        origenes = [lista_origen]
    else:
        origenes = obtener_listas_de_item(vid_id_or_url)

    if not origenes:
        return agregar_favorito(video_data, nombre_lista=lista_destino)

    if len(origenes) == 1 and origenes[0] == lista_destino:
        return True

    item_completo = dict(video_data)
    for orig in origenes:
        for f in fav_dict.get(orig, []):
            if str(f.get('id', '')) == str(vid_id_or_url) or (f.get('url') and f.get('url') == str(vid_id_or_url)):
                item_completo = dict(f)
                break

    agregar_favorito(item_completo, nombre_lista=lista_destino)

    for orig in origenes:
        if orig != lista_destino:
            eliminar_favorito(vid_id_or_url, nombre_lista=orig)

    return True
