"""
Mixin de gestión de favoritos y navegación por canales para MainFrame.
"""

import os
import sys
import wx

import threading

import sys
import accessibility
from config_manager import FORMATOS_MAP
import favorites_manager
from favorites_manager import (
    cargar_favoritos,
    guardar_favoritos,
    obtener_favoritos,
    obtener_listas_favoritos,
    obtener_nombres_listas_favoritos,
    agregar_favorito,
    eliminar_favorito,
    guardar_lista_favoritos,
    eliminar_lista_favoritos,
    crear_lista_favoritos,
    es_favorito,
    obtener_listas_de_item,
    mover_favorito_de_lista,
    detectar_tipo_elemento
)

from ui_vlc import pedir_confirmacion_eliminar_favorito
from player_dialog import VideoPreviewDialog
from favorites_dialogs import (
    SelectFavoriteListDialog,
    ChangeFavoriteListDialog,
    ViewFavoritesChoiceDialog
)


def _get_fav_func(name):
    mod = sys.modules.get('ui')
    if mod and hasattr(mod, name):
        return getattr(mod, name)
    if hasattr(favorites_manager, name):
        return getattr(favorites_manager, name)
    import ui_vlc
    return getattr(ui_vlc, name, None)



class MainFavoritesMixin:
    def mostrar_favoritos(self, event=None):
        if hasattr(self, 'navigation_stack'):
            self.navigation_stack.clear()
        self._pending_nav_state = None
        if hasattr(self, 'btn_siguientes'):
            self.btn_siguientes.Enable(False)
        if hasattr(self, 'item_siguientes'):
            self.item_siguientes.Enable(False)
        self.last_search_query = ""
        self.last_target_url = ""
        self.current_playlist_title = ""
        self.current_channel_title = ""

        nombres = _get_fav_func('obtener_nombres_listas_favoritos')()
        nombre_elegido = None
        
        if len(nombres) > 1:
            dlg = ViewFavoritesChoiceDialog(self, action_label="Ver")
            if dlg.ShowModal() == wx.ID_OK:
                nombre_elegido = dlg.selected_list
            dlg.Destroy()
            if not nombre_elegido:
                return
        
        favs = _get_fav_func('obtener_favoritos')(nombre_lista=nombre_elegido)
        if not favs:
            msg_vacia = f"No hay elementos en la lista de favoritos '{nombre_elegido}'." if nombre_elegido else "Aún no tienes elementos en tu lista de favoritos.\n\nPuedes añadir cualquier vídeo, canal o playlist pulsando Ctrl+B o desde el menú Edición."
            wx.MessageBox(msg_vacia, "Lista de Favoritos vacía", wx.OK | wx.ICON_INFORMATION, self)
            return


        self.is_showing_favorites = True
        self.current_fav_name = nombre_elegido or "Principal"
        self.current_playlist_title = self.current_fav_name
        self.resultados = []
        for idx, f in enumerate(favs, 1):
            tipo = detectar_tipo_elemento(f)
            es_canal = (tipo == 'channel')
            es_pl = (tipo == 'playlist')
            self.resultados.append({
                'index': idx,
                'id': f.get('id', str(idx)),
                'title': f.get('title', 'Sin título'),
                'channel': f.get('channel', 'Desconocido'),
                'duration': f.get('duration', 'Desconocida'),
                'duration_seconds': f.get('duration_seconds', 0),
                'views': f.get('views', '--'),
                'url': f.get('url', ''),
                'selected': False,
                'list_name': f.get('list_name', 'Principal'),
                'is_channel': es_canal,
                'is_playlist': es_pl,
                'tipo_item': tipo,
                'type': tipo
            })

        self.lista_resultados.DeleteAllItems()
        self.col_activa_resultados = 0
        for idx, r in enumerate(self.resultados):
            titulo_text, img_idx = self._get_item_display_title_and_image(r, is_fav_view=True)
            item_row = self.lista_resultados.InsertItem(self.lista_resultados.GetItemCount(), titulo_text, img_idx)
            self.lista_resultados.SetItem(item_row, 1, r.get('channel', 'Desconocido'))
            self.lista_resultados.SetItem(item_row, 2, r.get('duration', '--:--'))
            self.lista_resultados.SetItem(item_row, 3, str(r.get('views', '--')))

        total = len(self.resultados)
        tag_lista = f" ({nombre_elegido})" if (nombre_elegido and nombre_elegido != "Todas las listas") else ""
        self.current_fav_tag = tag_lista
        item_str = "1 ítem" if total == 1 else f"{total} ítems"
        msg = f"Mostrando {item_str}."
        self.set_status(msg, field=0, announce=True)
        self.lbl_results_info.SetLabel(f"&Mis Favoritos{tag_lista} ({item_str}):")
        self.lbl_progreso_detalle.SetLabel("Pulsa Enter en un canal/lista para ver su contenido, o Ctrl+P para reproducir.")
        self._actualizar_contador_seleccion()

        self.lista_resultados.Select(0)
        self.lista_resultados.Focus(0)
        self.lista_resultados.SetFocus()
        self.set_modo_boton_buscar('limpiar')

    def mostrar_listas_favoritos(self):
        """Muestra en la tabla de resultados las listas de favoritos disponibles como nivel superior de la jerarquía."""
        favs_dict = cargar_favoritos()
        nombres = obtener_nombres_listas_favoritos()

        self.is_showing_favorites = False
        self.is_showing_fav_lists = True
        self.current_fav_name = ""
        self.current_fav_tag = ""
        self.current_playlist_title = "Mis listas de favoritos"
        self.current_channel_title = ""
        self.resultados = []

        todos_total = len(obtener_favoritos())
        self.resultados.append({
            'index': 1,
            'id': 'fav_list_all',
            'title': 'Todas las listas',
            'channel': 'Colección completa de favoritos',
            'duration': f"{todos_total} elementos" if todos_total != 1 else "1 elemento",
            'duration_seconds': 0,
            'views': '--',
            'url': '',
            'selected': False,
            'list_name': 'Todas las listas',
            'is_channel': False,
            'is_playlist': True,
            'is_fav_list': True,
            'tipo_item': 'fav_list',
            'type': 'fav_list'
        })

        for idx, n in enumerate(nombres, 2):
            cant = len(favs_dict.get(n, []))
            cant_str = f"{cant} elementos" if cant != 1 else "1 elemento"
            desc_canal = "Lista principal de favoritos" if n == 'Principal' else "Lista temática de favoritos"
            self.resultados.append({
                'index': idx,
                'id': f"fav_list_{n}",
                'title': n,
                'channel': desc_canal,
                'duration': cant_str,
                'duration_seconds': 0,
                'views': '--',
                'url': '',
                'selected': False,
                'list_name': n,
                'is_channel': False,
                'is_playlist': True,
                'is_fav_list': True,
                'tipo_item': 'fav_list',
                'type': 'fav_list'
            })

        self.lista_resultados.DeleteAllItems()
        self.col_activa_resultados = 0
        for idx, r in enumerate(self.resultados):
            titulo_text, img_idx = self._get_item_display_title_and_image(r, is_fav_view=False)
            item_row = self.lista_resultados.InsertItem(self.lista_resultados.GetItemCount(), titulo_text, img_idx)
            self.lista_resultados.SetItem(item_row, 1, r.get('channel', 'Desconocido'))
            self.lista_resultados.SetItem(item_row, 2, r.get('duration', '--:--'))
            self.lista_resultados.SetItem(item_row, 3, str(r.get('views', '--')))

        total = len(self.resultados)
        item_str = f"{total} listas"
        msg = f"Mostrando {item_str} de favoritos."
        self.set_status(msg, field=0, announce=True)
        self.lbl_results_info.SetLabel(f"&Mis listas de favoritos ({item_str}):")
        self.lbl_progreso_detalle.SetLabel("Pulsa Enter en una lista para ver su contenido o Espacio para marcar.")
        self._actualizar_contador_seleccion()

        self.lista_resultados.Select(0)
        self.lista_resultados.Focus(0)
        self.lista_resultados.SetFocus()
        self.set_modo_boton_buscar('limpiar')

    def mostrar_favoritos_de_lista(self, nombre_elegido="Principal", push_state=True):
        """Carga el contenido de una lista de favoritos específica preservando la jerarquía de navegación."""
        if push_state and (getattr(self, 'is_showing_fav_lists', False) or (hasattr(self, 'resultados') and self.resultados)):
            if not hasattr(self, 'navigation_stack'):
                self.navigation_stack = []
            self.navigation_stack.append(self._capturar_estado_navegacion())

        favs = obtener_favoritos(nombre_lista=nombre_elegido)
        if not favs:
            msg_vacia = f"No hay elementos en la lista de favoritos '{nombre_elegido}'." if nombre_elegido != "Todas las listas" else "Aún no tienes elementos en tu lista de favoritos.\n\nPuedes añadir cualquier vídeo, canal o playlist pulsando Ctrl+B o desde el menú Edición."
            wx.MessageBox(msg_vacia, "Lista de Favoritos vacía", wx.OK | wx.ICON_INFORMATION, self)
            return

        self.is_showing_fav_lists = False
        self.is_showing_favorites = True
        self.current_fav_name = nombre_elegido or "Principal"
        self.current_playlist_title = self.current_fav_name
        self.resultados = []
        for idx, f in enumerate(favs, 1):
            tipo = detectar_tipo_elemento(f)
            es_canal = (tipo == 'channel')
            es_pl = (tipo == 'playlist')
            self.resultados.append({
                'index': idx,
                'id': f.get('id', str(idx)),
                'title': f.get('title', 'Sin título'),
                'channel': f.get('channel', 'Desconocido'),
                'duration': f.get('duration', 'Desconocida'),
                'duration_seconds': f.get('duration_seconds', 0),
                'views': f.get('views', '--'),
                'url': f.get('url', ''),
                'selected': False,
                'list_name': f.get('list_name', self.current_fav_name),
                'is_channel': es_canal,
                'is_playlist': es_pl,
                'tipo_item': tipo,
                'type': tipo
            })

        self.lista_resultados.DeleteAllItems()
        self.col_activa_resultados = 0
        for idx, r in enumerate(self.resultados):
            titulo_text, img_idx = self._get_item_display_title_and_image(r, is_fav_view=True)
            item_row = self.lista_resultados.InsertItem(self.lista_resultados.GetItemCount(), titulo_text, img_idx)
            self.lista_resultados.SetItem(item_row, 1, r.get('channel', 'Desconocido'))
            self.lista_resultados.SetItem(item_row, 2, r.get('duration', '--:--'))
            self.lista_resultados.SetItem(item_row, 3, str(r.get('views', '--')))

        total = len(self.resultados)
        tag_lista = f" ({nombre_elegido})" if (nombre_elegido and nombre_elegido != "Todas las listas") else ""
        self.current_fav_tag = tag_lista
    def reproducir_favoritos(self, event=None):
        nombres = obtener_nombres_listas_favoritos()
        nombre_elegido = None
        
        if len(nombres) > 1:
            dlg = ViewFavoritesChoiceDialog(self, action_label="Reproducir")
            if dlg.ShowModal() == wx.ID_OK:
                nombre_elegido = dlg.selected_list
            dlg.Destroy()
            if not nombre_elegido:
                return
        
        favs = obtener_favoritos(nombre_lista=nombre_elegido)
        if not favs:
            wx.MessageBox("No hay vídeos en favoritos para reproducir.", "Favoritos vacíos", wx.OK | wx.ICON_INFORMATION, self)
            return

        tag_lista = f" de {nombre_elegido}" if (nombre_elegido and nombre_elegido != "Todas las listas") else ""
        self.set_status(f"Iniciando reproducción continua de {len(favs)} favoritos{tag_lista}...", field=0, announce=True)
        dlg = VideoPreviewDialog(self, favs, initial_index=0)
        res = dlg.ShowModal()
        wants_dl = getattr(dlg, 'wants_download', False)
        dl_video = getattr(dlg, 'download_target_video', None)
        dlg.Destroy()

        if res == wx.ID_OK and wants_dl:
            if dl_video:
                self.cola_descargas = [dl_video]
                self.total_cola = 1
                self.indice_cola = 0
                self.descargas_completadas = 0
                self.descargas_fallidas = 0
                self.btn_descargar.Enable(False)
                self.btn_cancelar.Enable(True)
                self.btn_buscar.Enable(False)
                sel_format_idx = self.choice_formato.GetSelection()
                formatos_map = {0: 'video_best', 1: 'audio_mp3_192', 2: 'audio_mp3_320', 3: 'audio_m4a'}
                formato_str = formatos_map.get(sel_format_idx, 'video_best')
                destino = self.destino_dir
                self._iniciar_siguiente_descarga_cola(formato_str, destino)
            else:
                self.on_btn_descargar(None)

    def _sincronizar_vista_favoritos_tras_reproduccion(self):
        """Sincroniza la lista de resultados si algún elemento fue eliminado de favoritos en el reproductor."""
        if getattr(self, 'is_showing_favorites', False):
            items_to_del = []
            for i, r in enumerate(self.resultados):
                vid_ref = r.get('url') or r.get('id', '')
                if not es_favorito(vid_ref):
                    items_to_del.append(i)
            if items_to_del:
                for i in reversed(items_to_del):
                    self.resultados.pop(i)
                    self.lista_resultados.DeleteItem(i)
                total = len(self.resultados)
                tag_lista = getattr(self, 'current_fav_tag', '')
                self.lbl_results_info.SetLabel(f"&Mis Favoritos{tag_lista} ({total} guardados):")
                self._actualizar_contador_seleccion()
                if total > 0:
                    sel = min(items_to_del[0], total - 1)
                    self.lista_resultados.Select(sel)
                    self.lista_resultados.Focus(sel)
                else:
                    self.set_modo_boton_buscar('buscar')
        else:
            for i in range(len(self.resultados)):
                self._actualizar_item_fila(i)

    def _procesar_descarga_desde_reproductor(self, dlg):
        """Procesa la solicitud de descarga originada desde el reproductor multimedia."""
        wants_dl = getattr(dlg, 'wants_download', False)
        dl_video = getattr(dlg, 'download_target_video', None)
        dlg.Destroy()
        self._sincronizar_vista_favoritos_tras_reproduccion()

        if not wants_dl:
            return
        if not self.verificar_libreria_ytdlp():
            return
        if dl_video:
            self.cola_descargas = [dl_video]
            self.total_cola = 1
            self.indice_cola = 0
            self.descargas_completadas = 0
            self.descargas_fallidas = 0
            self.btn_descargar.Enable(False)
            self.btn_cancelar.Enable(True)
            self.btn_buscar.Enable(False)
            self.iniciar_sonido_espera()
            formato_str = FORMATOS_MAP.get(self.choice_formato.GetSelection(), 'video_best')
            self._iniciar_siguiente_descarga_cola(formato_str, self.destino_dir)
        else:
            self.on_btn_descargar(None)

    def eliminar_favorito_seleccion(self, event=None):
        """Elimina de favoritos el elemento seleccionado en la lista (Tecla Supr), solicitando confirmación si está configurado."""
        marcados = [r for r in self.resultados if r.get('selected')]
        items = marcados if len(marcados) > 1 else ([self._get_selected_video()] if self._get_selected_video() else [])
        if not items:
            accessibility.speak("No hay ningún elemento seleccionado en la lista.")
            return

        es_fav_view = getattr(self, 'is_showing_favorites', False)
        _conf_fn = _get_fav_func('pedir_confirmacion_eliminar_favorito')
        _del_fn = _get_fav_func('eliminar_favorito')
        _es_fav_fn = _get_fav_func('es_favorito')

        if len(items) == 1:
            video = items[0]
            vid_id_or_url = video.get('url') or video.get('id', '')
            titulo = video.get('title', 'Elemento')
            is_fav = es_fav_view or _es_fav_fn(vid_id_or_url)

            if not is_fav:
                accessibility.speak(f"'{titulo}' no está en la lista de favoritos.")
                self.set_status("El elemento seleccionado no está en favoritos.", field=0, announce=False)
                return

            if not _conf_fn(self, titulo):
                return

            _del_fn(vid_id_or_url)
            accessibility.speak(f"Eliminado de favoritos: {titulo}")
            self.set_status(f"Eliminado de favoritos: {titulo}", field=0, announce=False)

            if es_fav_view:
                idx = self._get_current_index()
                if 0 <= idx < len(self.resultados):
                    self.resultados.pop(idx)
                    self.lista_resultados.DeleteItem(idx)
                    total = len(self.resultados)
                    tag_lista = getattr(self, 'current_fav_tag', '')
                    self.lbl_results_info.SetLabel(f"&Mis Favoritos{tag_lista} ({total} guardados):")
                    self._actualizar_contador_seleccion()
                    if total > 0:
                        new_sel = min(idx, total - 1)
                        self.lista_resultados.Select(new_sel)
                        self.lista_resultados.Focus(new_sel)
                    else:
                        self.set_modo_boton_buscar('buscar')
            else:
                idx = self._get_current_index()
                if idx != -1:
                    self._actualizar_item_fila(idx)
        else:
            fav_items = [v for v in items if es_fav_view or _es_fav_fn(v.get('url') or v.get('id', ''))]
            if not fav_items:
                accessibility.speak("Ninguno de los elementos seleccionados está en favoritos.")
                self.set_status("Ninguno de los elementos seleccionados está en favoritos.", field=0, announce=False)
                return

            titulo_conf = f"{len(fav_items)} elementos"
            if not _conf_fn(self, titulo_conf):
                return
            eliminados = 0
            for v in fav_items:
                vid_id_or_url = v.get('url') or v.get('id', '')
                if _del_fn(vid_id_or_url, self.current_fav_name if es_fav_view else None):
                    eliminados += 1

            if es_fav_view:
                self.mostrar_favoritos_de_lista(self.current_fav_name)
            msg = f"Se eliminaron {eliminados} elementos de favoritos."
            self.set_status(msg, field=0, announce=True)

    def toggle_favorito_seleccion(self, event=None):
        marcados = [r for r in self.resultados if r.get('selected')]
        items = marcados if len(marcados) > 1 else ([self._get_selected_video()] if self._get_selected_video() else [])
        if not items:
            wx.MessageBox("Selecciona primero un elemento de la lista.", "Aviso", wx.OK | wx.ICON_INFORMATION, self)
            return

        es_fav_view = getattr(self, 'is_showing_favorites', False)
        if len(items) == 1:
            video = items[0]
            vid_id_or_url = video.get('url') or video.get('id', '')
            tipo = detectar_tipo_elemento(video)
            tipo_nombre = "canal" if tipo == 'channel' else ("lista de reproducción" if tipo == 'playlist' else "vídeo")
            titulo = video.get('title', 'Elemento')

            if es_fav_view or es_favorito(vid_id_or_url):
                self.eliminar_favorito_seleccion()
                return
            else:
                dlg = SelectFavoriteListDialog(self, titulo)
                if dlg.ShowModal() == wx.ID_OK:
                    n_lista = dlg.selected_list_name or "Principal"
                    agregar_favorito(video, nombre_lista=n_lista)
                    accessibility.speak(f"Añadido a favoritos en la lista '{n_lista}': {titulo}")
                    self.set_status(f"Añadido a favoritos ({n_lista}): {titulo}", field=0, announce=False)
                dlg.Destroy()

            idx = self._get_current_index()
            if idx != -1:
                self._actualizar_item_fila(idx)
        else:
            todos_son_fav = es_fav_view or all(es_favorito(v.get('url') or v.get('id', '')) for v in items)
            if todos_son_fav:
                self.eliminar_favorito_seleccion()
                return
            else:
                dlg = SelectFavoriteListDialog(self, f"{len(items)} elementos")
                if dlg.ShowModal() == wx.ID_OK:
                    n_lista = dlg.selected_list_name or "Principal"
                    agregados = 0
                    for v in items:
                        agregar_favorito(v, nombre_lista=n_lista)
                        v['selected'] = False
                        agregados += 1
                    accessibility.speak(f"{agregados} elementos añadidos a favoritos en la lista '{n_lista}'.")
                    self.set_status(f"{agregados} elementos añadidos a favoritos en '{n_lista}'.", field=0, announce=False)
                    self._actualizar_contador_seleccion()
                dlg.Destroy()

            for idx in range(len(self.resultados)):
                self._actualizar_item_fila(idx)

    def vaciar_favoritos(self, event=None):
        favs = obtener_favoritos()
        if not favs:
            wx.MessageBox("La lista de favoritos ya está vacía.", "Favoritos", wx.OK | wx.ICON_INFORMATION, self)
            return

        dlg = wx.MessageDialog(
            self,
            f"¿Estás seguro de que deseas eliminar todos los elementos de tus listas de favoritos?",
            "Confirmar vaciado de favoritos",
            wx.YES_NO | wx.ICON_QUESTION
        )
        if dlg.ShowModal() == wx.ID_YES:
            fav_dict = cargar_favoritos()
            for k in fav_dict:
                fav_dict[k] = []
            guardar_favoritos(fav_dict)
            accessibility.speak("Listas de favoritos vaciadas.")
            self.set_status("Listas de favoritos vaciadas.", field=0, announce=False)
            if getattr(self, 'is_showing_favorites', False) or "Favoritos" in self.lbl_results_info.GetLabel():
                self.lista_resultados.DeleteAllItems()
                self.resultados = []
                self.lbl_results_info.SetLabel("&Mis Favoritos (0 guardados):")
                self._actualizar_contador_seleccion()
                self.set_modo_boton_buscar('buscar')
        dlg.Destroy()

    # ---------------- GESTIÓN DE SELECCIÓN Y MARCAS CON ESPACIO ----------------
    def _get_videos_para_cambio_lista(self, video_especifico=None):
        """
        Retorna los elementos a mover de lista de favoritos:
        - Si hay varios ítems marcados (con Espacio / Ctrl+A), retorna todos los marcados.
        - Si no hay selección, retorna el elemento bajo el cursor (o el específico proporcionado).
        """
        marcados = [r for r in self.resultados if r.get('selected')]
        if marcados:
            return marcados
        cursor = video_especifico or self._get_selected_video()
        if cursor:
            return [cursor]
        return []

    def cambiar_favorito_a_lista(self, video=None, lista_destino="Principal"):
        """Mueve los elementos seleccionados (o el que está bajo el cursor) a la lista de destino y los quita de la lista anterior."""
        if isinstance(video, (list, tuple)):
            items = list(video)
        else:
            items = self._get_videos_para_cambio_lista(video_especifico=video if isinstance(video, dict) else None)

        if not items:
            accessibility.speak("No hay ningún elemento seleccionado en la lista.")
            return

        es_fav_view = getattr(self, 'is_showing_favorites', False)
        if not es_fav_view and not any(es_favorito(v.get('url') or v.get('id', '')) for v in items):
            return

        lista_destino = (lista_destino or 'Principal').strip()

        movidos = []
        ya_estaban = []
        fallidos = []

        es_fav_view = getattr(self, 'is_showing_favorites', False)
        current_fav = getattr(self, 'current_fav_name', None)

        for v in items:
            vid_id_or_url = v.get('url') or v.get('id', '')
            if not vid_id_or_url:
                continue

            lista_origen = None
            if es_fav_view and current_fav != "Todas las listas":
                lista_origen = v.get('list_name') or current_fav
            else:
                listas_item = obtener_listas_de_item(vid_id_or_url)
                lista_origen = v.get('list_name') or (listas_item[0] if listas_item else None)

            if lista_origen and lista_origen == lista_destino:
                ya_estaban.append(v)
                continue

            exito = mover_favorito_de_lista(v, lista_destino=lista_destino, lista_origen=lista_origen)
            if exito:
                movidos.append(v)
            else:
                fallidos.append(v)

        total_items = len(items)
        if total_items == 1:
            titulo = items[0].get('title', 'Elemento')
            if movidos:
                msg = f"'{titulo}' movido a la lista '{lista_destino}'."
                accessibility.speak(msg)
                self.set_status(msg, field=0, announce=False)
            elif ya_estaban:
                msg = f"'{titulo}' ya se encuentra en la lista '{lista_destino}'."
                accessibility.speak(msg)
                self.set_status(f"El elemento ya está en '{lista_destino}'.", field=0, announce=False)
                return
            else:
                msg = f"No se pudo mover '{titulo}' a la lista '{lista_destino}'."
                accessibility.speak(msg)
                return
        else:
            if movidos:
                if ya_estaban:
                    msg = f"{len(movidos)} elementos movidos a la lista '{lista_destino}' ({len(ya_estaban)} ya estaban en ella)."
                else:
                    msg = f"{len(movidos)} elementos movidos a la lista '{lista_destino}'."
                accessibility.speak(msg)
                self.set_status(msg, field=0, announce=False)
            elif ya_estaban:
                msg = f"Los {len(ya_estaban)} elementos ya se encuentran en la lista '{lista_destino}'."
                accessibility.speak(msg)
                self.set_status(f"Los elementos ya están en '{lista_destino}'.", field=0, announce=False)
                return
            else:
                msg = f"No se pudieron mover los elementos a la lista '{lista_destino}'."
                accessibility.speak(msg)
                return

        # Desmarcar los elementos procesados
        for v in items:
            v['selected'] = False

        if es_fav_view:
            if current_fav != "Todas las listas":
                movidos_ids = {str(m.get('url') or m.get('id', '')) for m in movidos}
                indices_a_eliminar = [
                    i for i, r in enumerate(self.resultados)
                    if str(r.get('url') or r.get('id', '')) in movidos_ids
                ]
                for idx in sorted(indices_a_eliminar, reverse=True):
                    self.resultados.pop(idx)
                    self.lista_resultados.DeleteItem(idx)

                total = len(self.resultados)
                tag_lista = getattr(self, 'current_fav_tag', '')
                self.lbl_results_info.SetLabel(f"&Mis Favoritos{tag_lista} ({total} guardados):")
                self._actualizar_contador_seleccion()
                if total > 0:
                    first_idx = indices_a_eliminar[0] if indices_a_eliminar else 0
                    new_sel = min(first_idx, total - 1)
                    self.lista_resultados.Select(new_sel)
                    self.lista_resultados.Focus(new_sel)
                else:
                    self.set_modo_boton_buscar('buscar')
            else:
                movidos_ids = {str(m.get('url') or m.get('id', '')) for m in movidos}
                for idx, r in enumerate(self.resultados):
                    if str(r.get('url') or r.get('id', '')) in movidos_ids:
                        r['list_name'] = lista_destino
                    self._actualizar_item_fila(idx)
                self._actualizar_contador_seleccion()
        else:
            affected_ids = {str(v.get('url') or v.get('id', '')) for v in items}
            for idx, r in enumerate(self.resultados):
                if str(r.get('url') or r.get('id', '')) in affected_ids:
                    self._actualizar_item_fila(idx)
            self._actualizar_contador_seleccion()

    def cambiar_favorito_a_nueva_lista(self, video=None):
        """Pide el nombre de una nueva lista, la crea y mueve los elementos seleccionados (o bajo el cursor) a ella."""
        items = self._get_videos_para_cambio_lista(video_especifico=video if isinstance(video, dict) else None)
        if not items:
            accessibility.speak("No hay ningún elemento seleccionado en la lista.")
            return

        es_fav_view = getattr(self, 'is_showing_favorites', False)
        if not es_fav_view:
            hay_favoritos = any(es_favorito(v.get('url') or v.get('id', '')) for v in items)
            if not hay_favoritos:
                if len(items) == 1:
                    msg = "El elemento seleccionado no está en ninguna lista de favoritos. Solo puedes añadirlo a favoritos."
                else:
                    msg = "Ninguno de los elementos seleccionados está en una lista de favoritos. Solo puedes añadirlos a favoritos."
                accessibility.speak(msg)
                self.set_status(msg, field=0, announce=False)
                wx.MessageBox(
                    f"{msg}\n\nUsa 'Añadir a Favoritos' (Ctrl+B) para guardarlo en una lista.",
                    "No está en favoritos",
                    wx.OK | wx.ICON_INFORMATION,
                    self
                )
                return

        dlg = wx.TextEntryDialog(self, "Introduce el nombre de la nueva lista de favoritos:", "Nueva lista de favoritos")
    def on_cambiar_favorito_lista(self, event=None, video_especifico=None):
        """Abre un diálogo accesible para cambiar los elementos seleccionados a otra lista de favoritos o crear una nueva."""
        items = self._get_videos_para_cambio_lista(video_especifico=video_especifico if isinstance(video_especifico, dict) else None)
        if not items:
            accessibility.speak("No hay ningún elemento seleccionado en la lista.")
            return

        es_fav_view = getattr(self, 'is_showing_favorites', False)
        current_fav = getattr(self, 'current_fav_name', None)

        if len(items) == 1:
            video = items[0]
            vid_id_or_url = video.get('url') or video.get('id', '')
            titulo = video.get('title', 'Elemento')
            if es_fav_view and current_fav != "Todas las listas":
                lista_actual = video.get('list_name') or current_fav or ''
            else:
                listas_item = obtener_listas_de_item(vid_id_or_url)
                lista_actual = video.get('list_name') or (listas_item[0] if listas_item else '')
            dlg = ChangeFavoriteListDialog(self, video_title=titulo, lista_actual=lista_actual)
        else:
            titulo = f"{len(items)} elementos seleccionados"
            if es_fav_view and current_fav != "Todas las listas":
                lista_actual = current_fav or ''
            else:
                lista_actual = ""
            dlg = ChangeFavoriteListDialog(self, video_title=titulo, lista_actual=lista_actual)

        if dlg.ShowModal() == wx.ID_OK:
            dest = dlg.selected_list_name
            if dest:
                self.cambiar_favorito_a_lista(items, dest)
        dlg.Destroy()

    def _agregar_submenu_cambiar_lista(self, menu, video):
        """Añade al menú contextual el submenú interactivo para cambiar de lista de favoritos."""
        es_fav_view = getattr(self, 'is_showing_favorites', False)
        if not es_fav_view:
            marcados = [r for r in self.resultados if r.get('selected')]
            items_to_check = marcados if marcados else ([video] if video else [])
            if not any(es_favorito(v.get('url') or v.get('id', '')) for v in items_to_check):
                return

        menu_cambiar = wx.Menu()
        nombres = obtener_nombres_listas_favoritos()

        num_sel = sum(1 for r in self.resultados if r.get('selected'))
        current_fav = getattr(self, 'current_fav_name', None)


        lista_actual = ""
        if num_sel <= 1:
            vid_id_or_url = video.get('url') or video.get('id', '')
            if es_fav_view and current_fav != "Todas las listas":
                lista_actual = video.get('list_name') or current_fav or ''
            else:
                listas_item = obtener_listas_de_item(vid_id_or_url)
                lista_actual = video.get('list_name') or (listas_item[0] if listas_item else '')
        else:
            if es_fav_view and current_fav != "Todas las listas":
                lista_actual = current_fav or ''
            else:
                lista_actual = ""

        for nom in nombres:
            label = f"{nom} (Actual)" if (lista_actual and nom == lista_actual) else nom
            item_nom = menu_cambiar.Append(wx.ID_ANY, label)
            if lista_actual and nom == lista_actual:
                item_nom.Enable(False)
            else:
                self.Bind(wx.EVT_MENU, lambda e, target=nom, v=video: self.cambiar_favorito_a_lista(v, target), item_nom)

        menu_cambiar.AppendSeparator()
        item_nueva = menu_cambiar.Append(wx.ID_ANY, "[+] &Nueva lista...")
        self.Bind(wx.EVT_MENU, lambda e, v=video: self.cambiar_favorito_a_nueva_lista(v), item_nueva)

        menu_cambiar.AppendSeparator()
        item_dlg = menu_cambiar.Append(wx.ID_ANY, "&Elegir mediante ventana...")
        self.Bind(wx.EVT_MENU, lambda e, v=video: self.on_cambiar_favorito_lista(e, video_especifico=v), item_dlg)

        if num_sel > 1:
            label_sub = f"&Cambiar de lista de favoritos ({num_sel} seleccionados)"
        else:
            label_sub = "&Cambiar de lista de favoritos"
        menu.AppendSubMenu(menu_cambiar, label_sub)

    # ---------------- GESTIÓN DE SELECCIÓN Y MARCAS CON ESPACIO ----------------
    def mostrar_videos_del_canal_seleccionado(self, video=None):
        if video is None:
            video = self._get_selected_video()
        if not video:
            wx.MessageBox("Selecciona primero un elemento de la lista.", "Aviso", wx.OK | wx.ICON_INFORMATION, self)
            return

        ch_title = (video.get('title') if video.get('is_channel') else (video.get('channel') or '')) or ''
        if video.get('is_channel'):
            channel_url = video.get('url')
            if channel_url:
                self.ejecutar_busqueda_canal_videos(channel_url, ch_title)
            return

        channel_url = video.get('channel_url')
        if channel_url:
            self.ejecutar_busqueda_canal_videos(channel_url, ch_title)
            return

        target_url = video.get('url') or (f"https://www.youtube.com/watch?v={video.get('id')}" if video.get('id') else '')
        if not target_url:
            wx.MessageBox("No se pudo determinar el canal de este elemento.", "Aviso", wx.OK | wx.ICON_INFORMATION, self)
            return

        self.set_status("Obteniendo información del canal...", field=0, announce=True)

        def _worker():
            try:
                ch_url = self.downloader.obtener_canal_url(target_url)
                if ch_url:
                    video['channel_url'] = ch_url
                    wx.CallAfter(self.ejecutar_busqueda_canal_videos, ch_url, ch_title)
                else:
                    wx.CallAfter(wx.MessageBox, "No se pudo obtener la dirección del canal de este elemento.", "Aviso", wx.OK | wx.ICON_INFORMATION, self)
                    wx.CallAfter(self.set_status, "No se encontró el canal.", 0, True)
            except Exception as e:
                wx.CallAfter(self._on_search_error, f"Error al obtener canal: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def copiar_url_del_canal_seleccionado(self, video=None):
        if video is None:
            video = self._get_selected_video()
        if not video:
            wx.MessageBox("Selecciona primero un elemento de la lista.", "Aviso", wx.OK | wx.ICON_INFORMATION, self)
            return

        if video.get('is_channel'):
            channel_url = video.get('url')
        else:
            channel_url = video.get('channel_url')

        if channel_url:
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(channel_url))
                wx.TheClipboard.Close()
                self.set_status("URL del canal copiada al portapapeles.", field=0, announce=True)
            return

        target_url = video.get('url') or (f"https://www.youtube.com/watch?v={video.get('id')}" if video.get('id') else '')
        if not target_url:
            wx.MessageBox("No se pudo determinar el canal de este elemento.", "Aviso", wx.OK | wx.ICON_INFORMATION, self)
            return

        self.set_status("Obteniendo URL del canal...", field=0, announce=True)

        def _worker():
            try:
                ch_url = self.downloader.obtener_canal_url(target_url)
                if ch_url:
                    video['channel_url'] = ch_url
                    def _copy():
                        if wx.TheClipboard.Open():
                            wx.TheClipboard.SetData(wx.TextDataObject(ch_url))
                            wx.TheClipboard.Close()
                            self.set_status("URL del canal copiada al portapapeles.", field=0, announce=True)
                    wx.CallAfter(_copy)
                else:
                    wx.CallAfter(wx.MessageBox, "No se pudo obtener la dirección del canal de este elemento.", "Aviso", wx.OK | wx.ICON_INFORMATION, self)
                    wx.CallAfter(self.set_status, "No se encontró el canal.", 0, True)
            except Exception as e:
                wx.CallAfter(self._on_search_error, f"Error al obtener canal: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def mostrar_listas_del_canal_seleccionado(self, event=None):
        video = self._get_selected_video()
        if not video:
            wx.MessageBox("Selecciona primero un elemento de la lista.", "Aviso", wx.OK | wx.ICON_INFORMATION, self)
            return

        ch_title = (video.get('title') if video.get('is_channel') else (video.get('channel') or '')) or ''
        if video.get('is_channel'):
            channel_url = video.get('url')
            if channel_url:
                self.ejecutar_busqueda_canal_playlists(channel_url, ch_title)
            return

        channel_url = video.get('channel_url')
        if channel_url:
            self.ejecutar_busqueda_canal_playlists(channel_url, ch_title)
            return

        target_url = video.get('url') or (f"https://www.youtube.com/watch?v={video.get('id')}" if video.get('id') else '')
        if not target_url:
            wx.MessageBox("No se pudo determinar el canal de este elemento.", "Aviso", wx.OK | wx.ICON_INFORMATION, self)
            return

        self.set_status("Obteniendo información del canal...", field=0, announce=True)

        def _worker():
            try:
                ch_url = self.downloader.obtener_canal_url(target_url)
                if ch_url:
                    video['channel_url'] = ch_url
                    wx.CallAfter(self.ejecutar_busqueda_canal_playlists, ch_url, ch_title)
                else:
                    wx.CallAfter(wx.MessageBox, "No se pudo obtener la dirección del canal de este elemento.", "Aviso", wx.OK | wx.ICON_INFORMATION, self)
                    wx.CallAfter(self.set_status, "No se encontró el canal.", 0, True)
            except Exception as e:
                wx.CallAfter(self._on_search_error, f"Error al obtener canal: {e}")

        threading.Thread(target=_worker, daemon=True).start()

