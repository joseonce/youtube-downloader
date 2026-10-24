"""
Mixin de búsqueda y navegación para MainFrame.
"""

import os
import sys
import threading
import time
import wx

import accessibility
from config_manager import cargar_configuracion, get_docs_dir
from media_utils import identificar_tipo_url, formatear_visitas
from downloader import YouTubeDownloader


class MainSearchMixin:
    def set_modo_boton_buscar(self, modo: str):
        """Cambia el modo y la etiqueta del botón de búsqueda ('buscar' o 'limpiar')."""
        self.modo_boton_buscar = modo
        if not hasattr(self, 'btn_buscar') or not self.btn_buscar:
            return
        if modo == 'limpiar':
            self.btn_buscar.SetLabel("&Limpiar resultados")
            self.btn_buscar.SetToolTip("Borra la lista de resultados, elimina el campo de búsqueda y lo focaliza (Alt+L)")
        else:
            self.modo_boton_buscar = 'buscar'
            self.btn_buscar.SetLabel("&Buscar")
            self.btn_buscar.SetToolTip("Busca vídeos, canales o listas de reproducción según los términos introducidos (Alt+B)")
        try:
            parent = self.btn_buscar.GetParent()
            if parent:
                parent.Layout()
        except Exception:
            pass

    def limpiar_resultados(self, event=None):
        """
        Borra la lista de resultados, elimina el campo de edición de búsqueda,
        focaliza dicho campo y cambia el botón de nuevo a 'Buscar'.
        Si no hay nada que limpiar, no realiza ninguna acción ni emite locución.
        """
        hay_que_limpiar = (
            (hasattr(self, 'resultados') and len(self.resultados) > 0)
            or (hasattr(self, 'lista_resultados') and self.lista_resultados.GetItemCount() > 0)
            or (hasattr(self, 'txt_busqueda') and bool(self.txt_busqueda.GetValue()))
            or getattr(self, 'is_showing_favorites', False)
            or getattr(self, 'modo_boton_buscar', 'buscar') == 'limpiar'
        )
        if not hay_que_limpiar:
            return

        self.lista_resultados.DeleteAllItems()
        self.resultados = []
        self.is_showing_favorites = False
        self.last_search_query = ""
        self.last_target_url = ""
        self.current_playlist_title = ""
        self.current_channel_title = ""
        self.next_start_index = 1
        self.col_activa_resultados = 0

        self.btn_siguientes.Enable(False)
        if hasattr(self, 'item_siguientes'):
            self.item_siguientes.Enable(False)

        if hasattr(self, 'navigation_stack'):
            self.navigation_stack.clear()
        self._pending_nav_state = None

        self.lbl_results_info.SetLabel("&Lista de resultados (0 ítems):")
        self.lbl_progreso_detalle.SetLabel("Resultados limpiados. Campo de búsqueda listo.")
        self.set_status("Resultados limpiados.", field=0, announce=True)
        self._actualizar_contador_seleccion()

        # Eliminar el texto del campo de edición de búsqueda y focalizar dicho campo
        self.txt_busqueda.Clear()
        self.txt_busqueda.SetFocus()

        # Ahora se llamará de nuevo buscar
        self.set_modo_boton_buscar('buscar')

    def _capturar_estado_navegacion(self):
        """Captura una instantánea del estado actual de la vista para la pila de navegación."""
        if not hasattr(self, 'resultados') or not self.resultados:
            return None
        idx_sel = self._get_current_index()
        btn_sig_en = hasattr(self, 'btn_siguientes') and self.btn_siguientes.IsEnabled()
        return {
            'resultados': [dict(r) for r in self.resultados],
            'is_showing_favorites': getattr(self, 'is_showing_favorites', False),
            'is_showing_fav_lists': getattr(self, 'is_showing_fav_lists', False),
            'current_fav_name': getattr(self, 'current_fav_name', 'Principal'),
            'current_fav_tag': getattr(self, 'current_fav_tag', ''),
            'current_playlist_title': getattr(self, 'current_playlist_title', ''),
            'current_channel_title': getattr(self, 'current_channel_title', ''),
            'last_search_query': getattr(self, 'last_search_query', ''),
            'last_search_engine': getattr(self, 'last_search_engine', 'ytsearch'),
            'last_search_type': getattr(self, 'last_search_type', 'video'),
            'last_search_kind': getattr(self, 'last_search_kind', ''),
            'last_target_url': getattr(self, 'last_target_url', ''),
            'next_start_index': getattr(self, 'next_start_index', 1),
            'lbl_results_info': self.lbl_results_info.GetLabel() if hasattr(self, 'lbl_results_info') else "",
            'lbl_progreso_detalle': self.lbl_progreso_detalle.GetLabel() if hasattr(self, 'lbl_progreso_detalle') else "",
            'selected_index': idx_sel if idx_sel >= 0 else 0,
            'btn_siguientes_enabled': btn_sig_en
        }

    def _generar_mensaje_retorno_nivel(self, estado):
        """Genera el mensaje accesible para anunciar el retorno de nivel al usuario."""
        cant = len(self.resultados)
        cant_str = f" ({cant} elemento)" if cant == 1 else f" ({cant} elementos)"
        if estado.get('is_showing_fav_lists'):
            cant_listas = f" ({cant} lista)" if cant == 1 else f" ({cant} listas)"
            return f"Regresando a Mis listas de favoritos{cant_listas}."
        if estado.get('is_showing_favorites'):
            tag = estado.get('current_fav_tag', '')
            return f"Regresando a Favoritos{tag}{cant_str}."
        k = estado.get('last_search_kind', '')
        if k == 'canal_playlists':
            return f"Regresando a listas de reproducción del canal{cant_str}."
        elif k == 'canal_videos':
            return f"Regresando a vídeos del canal{cant_str}."
        elif k == 'playlist_videos':
            return f"Regresando a vídeos de la lista{cant_str}."
        elif k == 'search':
            q = estado.get('last_search_query', '')
            return f"Regresando a resultados de búsqueda '{q}'{cant_str}." if q else f"Regresando a resultados de búsqueda{cant_str}."
        elif k == 'historial':
            return f"Regresando a Historial de reproducciones{cant_str}."
        elif k == 'ver_mas_tarde':
            return f"Regresando a Ver más tarde{cant_str}."
        elif k == 'mis_playlists':
            return f"Regresando a Mis listas de reproducción{cant_str}."
        return f"Regresando al nivel anterior{cant_str}."

    def _restaurar_estado_navegacion(self, estado):
        """Restaura la vista y controles de un nivel de navegación previo."""
        self.is_showing_favorites = estado.get('is_showing_favorites', False)
        self.current_fav_name = estado.get('current_fav_name', 'Principal')
        self.current_fav_tag = estado.get('current_fav_tag', '')
        self.current_playlist_title = estado.get('current_playlist_title', '')
        self.current_channel_title = estado.get('current_channel_title', '')
        self.resultados = estado.get('resultados', [])
        self.last_search_query = estado.get('last_search_query', '')
        self.last_search_engine = estado.get('last_search_engine', 'ytsearch')
        self.last_search_type = estado.get('last_search_type', 'video')
        self.last_search_kind = estado.get('last_search_kind', '')
        self.last_target_url = estado.get('last_target_url', '')
        self.next_start_index = estado.get('next_start_index', 1)
        self.col_activa_resultados = 0

        self.lista_resultados.DeleteAllItems()
        is_fav = self.is_showing_favorites
        for idx, r in enumerate(self.resultados):
            titulo_text, img_idx = self._get_item_display_title_and_image(r, is_fav_view=is_fav)
            item_row = self.lista_resultados.InsertItem(self.lista_resultados.GetItemCount(), titulo_text, img_idx)
            self.lista_resultados.SetItem(item_row, 1, r.get('channel', 'Desconocido'))
            self.lista_resultados.SetItem(item_row, 2, r.get('duration', '--:--'))
            self.lista_resultados.SetItem(item_row, 3, str(r.get('views', '--')))

        lbl_info = estado.get('lbl_results_info', '')
        if lbl_info:
            self.lbl_results_info.SetLabel(lbl_info)
        else:
            total = len(self.resultados)
            item_str = "1 ítem" if total == 1 else f"{total} ítems"
            self.lbl_results_info.SetLabel(f"&Lista de resultados ({item_str}):")

        lbl_prog = estado.get('lbl_progreso_detalle', '')
        if lbl_prog:
            self.lbl_progreso_detalle.SetLabel(lbl_prog)

        btn_sig_en = estado.get('btn_siguientes_enabled', False)
        if hasattr(self, 'btn_siguientes'):
            self.btn_siguientes.Enable(btn_sig_en)
        if hasattr(self, 'item_siguientes'):
            self.item_siguientes.Enable(btn_sig_en)

        self.set_modo_boton_buscar('limpiar')

        sel_idx = estado.get('selected_index', 0)
        count = self.lista_resultados.GetItemCount()
        if count > 0:
            sel_idx = max(0, min(sel_idx, count - 1))
            self.lista_resultados.Select(sel_idx)
            self.lista_resultados.Focus(sel_idx)
            self.lista_resultados.EnsureVisible(sel_idx)
            self.lista_resultados.SetFocus()

        msg_anuncio = self._generar_mensaje_retorno_nivel(estado)
        self.set_status(msg_anuncio, field=0, announce=True)
        self._actualizar_contador_seleccion()

    def retroceder_nivel_o_limpiar(self, event=None):
        """
        Retrocede un nivel en la jerarquía de navegación con la tecla Escape
        (vídeos -> listas de reproducción -> canal -> favoritos/búsqueda).
        Si no hay niveles previos acumulados, limpia los resultados y vuelve al campo de búsqueda.
        """
        if hasattr(self, 'navigation_stack') and self.navigation_stack:
            estado = self.navigation_stack.pop()
            self._restaurar_estado_navegacion(estado)
        else:
            self.limpiar_resultados(event)

    def on_busqueda_enter(self, event=None):
        """Al pulsar Enter en el campo de búsqueda se ejecuta siempre la búsqueda."""
        self.ejecutar_busqueda()

    def on_btn_buscar(self, event=None):
        if getattr(self, 'modo_boton_buscar', 'buscar') == 'limpiar':
            self.limpiar_resultados(event)
            return
        if not self.verificar_libreria_ytdlp():
            return

        if self.is_searching:
            return
        query = self.txt_busqueda.GetValue().strip()
        if not query:
            wx.MessageBox(
                "Por favor, escribe términos de búsqueda o introduce una URL válida.",
                "Búsqueda vacía",
                wx.OK | wx.ICON_INFORMATION,
                self
            )
            self.txt_busqueda.SetFocus()
            return

        tipo_sel_idx = self.choice_tipo_busqueda.GetSelection() if self.choice_tipo_busqueda.IsEnabled() else 0
        tipo_busqueda_map = {0: 'video', 1: 'channel', 2: 'playlist'}
        search_type = tipo_busqueda_map.get(tipo_sel_idx, 'video')

        tipo = identificar_tipo_url(query)
        if tipo == 'canal':
            if search_type == 'playlist':
                self.ejecutar_busqueda_canal_playlists(query)
            else:
                self.ejecutar_busqueda_canal_videos(query)
            return
        elif tipo == 'playlist':
            self.ejecutar_busqueda_playlist_videos(query)
            return

        max_results = int(self.config.get('max_results', 25))
        engine = self.current_engine

        self.is_searching = True
        self.last_search_query = query
        self.last_search_engine = engine
        self.last_search_type = search_type
        self.last_search_kind = 'search'
        self.last_target_url = ""
        self.next_start_index = 1

        self.btn_buscar.Enable(False)
        self.btn_siguientes.Enable(False)
        if hasattr(self, 'item_siguientes'):
            self.item_siguientes.Enable(False)
        self.txt_busqueda.Enable(False)

        if search_type == 'channel' and engine == 'ytsearch':
            msg_status = f"Buscando canales para '{query}'..."
            msg_detalle = "Buscando canales en YouTube..."
        elif search_type == 'playlist' and engine == 'ytsearch':
            msg_status = f"Buscando listas de reproducción para '{query}'..."
            msg_detalle = "Buscando listas de reproducción en YouTube..."
        else:
            msg_status = f"Buscando '{query}'..."
            msg_detalle = "Consultando información en línea..."

        self.set_status(msg_status, field=0, announce=True)
        self.lbl_progreso_detalle.SetLabel(msg_detalle)

        def _worker():
            try:
                resultados = self.downloader.buscar(query, max_results=max_results, engine=engine, search_type=search_type, start_index=1)
                wx.CallAfter(self._on_search_completed, resultados, query, False)
            except Exception as e:
                wx.CallAfter(self._on_search_error, str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def ejecutar_busqueda(self, event=None):
        if not self.verificar_libreria_ytdlp():
            return
        if self.is_searching:
            return
        query = self.txt_busqueda.GetValue().strip()
        if not query:
            wx.MessageBox(
                "Por favor, escribe términos de búsqueda o introduce una URL válida.",
                "Búsqueda vacía",
                wx.OK | wx.ICON_INFORMATION,
                self
            )
            self.txt_busqueda.SetFocus()
            return

        tipo_sel_idx = self.choice_tipo_busqueda.GetSelection() if self.choice_tipo_busqueda.IsEnabled() else 0
        tipo_busqueda_map = {0: 'video', 1: 'channel', 2: 'playlist'}
        search_type = tipo_busqueda_map.get(tipo_sel_idx, 'video')

        tipo = identificar_tipo_url(query)
        if tipo == 'canal':
            if search_type == 'playlist':
                self.ejecutar_busqueda_canal_playlists(query)
            else:
                self.ejecutar_busqueda_canal_videos(query)
            return
        elif tipo == 'playlist':
            self.ejecutar_busqueda_playlist_videos(query)
            return

        max_results = int(self.config.get('max_results', 25))
        engine = self.current_engine

        if hasattr(self, 'navigation_stack'):
            self.navigation_stack.clear()
        self._pending_nav_state = None
        self.current_playlist_title = ""
        self.current_channel_title = ""

        self.is_searching = True
        self.last_search_query = query
        self.last_search_engine = engine
        self.last_search_type = search_type
        self.last_search_kind = 'search'
        self.last_target_url = ""
        self.next_start_index = 1

        self.btn_buscar.Enable(False)
        self.btn_siguientes.Enable(False)
        if hasattr(self, 'item_siguientes'):
            self.item_siguientes.Enable(False)
        self.txt_busqueda.Enable(False)

        msg_status = "Buscando..."
        if search_type == 'channel' and engine == 'ytsearch':
            msg_detalle = "Buscando canales en YouTube..."
        elif search_type == 'playlist' and engine == 'ytsearch':
            msg_detalle = "Buscando listas de reproducción en YouTube..."
        else:
            msg_detalle = "Consultando información en línea..."

        self.set_status(msg_status, field=0, announce=True)
        self.lbl_progreso_detalle.SetLabel(msg_detalle)

        def _worker():
            try:
                resultados = self.downloader.buscar(query, max_results=max_results, engine=engine, search_type=search_type, start_index=1)
                wx.CallAfter(self._on_search_completed, resultados, query, False)
            except Exception as e:
                wx.CallAfter(self._on_search_error, str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def ejecutar_busqueda_canal_videos(self, channel_url, channel_title=""):
        if self.is_searching:
            return
        if hasattr(self, 'resultados') and self.resultados:
            self._pending_nav_state = self._capturar_estado_navegacion()
        max_results = int(self.config.get('max_results', 25))
        self.is_searching = True
        self.last_search_query = channel_url
        self.last_search_kind = 'canal_videos'
        self.last_target_url = channel_url
        self.current_channel_title = channel_title or ""
        self.current_playlist_title = ""
        self.next_start_index = 1

        self.btn_buscar.Enable(False)
        self.btn_siguientes.Enable(False)
        if hasattr(self, 'item_siguientes'):
            self.item_siguientes.Enable(False)
        self.txt_busqueda.Enable(False)
        self.set_status("Buscando...", field=0, announce=True)
        lbl_canal = f" del canal {self.current_channel_title}" if self.current_channel_title else ""
        self.lbl_progreso_detalle.SetLabel(f"Listando hasta {max_results} vídeos{lbl_canal}...")

        def _worker():
            try:
                resultados = self.downloader.buscar_canal_videos(channel_url, max_results=max_results, start_index=1)
                detected = getattr(self.downloader, 'last_container_title', '')
                if not self.current_channel_title and detected:
                    self.current_channel_title = detected
                ch_nombre = self.current_channel_title or channel_url
                wx.CallAfter(self._on_search_completed, resultados, f"Vídeos del canal {ch_nombre}", False)
            except Exception as e:
                wx.CallAfter(self._on_search_error, str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def ejecutar_busqueda_canal_playlists(self, channel_url, channel_title=""):
        if self.is_searching:
            return
        if hasattr(self, 'resultados') and self.resultados:
            self._pending_nav_state = self._capturar_estado_navegacion()
        max_results = int(self.config.get('max_results', 25))
        self.is_searching = True
        self.last_search_query = channel_url
        self.last_search_kind = 'canal_playlists'
        self.last_target_url = channel_url
        self.current_channel_title = channel_title or ""
        self.current_playlist_title = ""
        self.next_start_index = 1

        self.btn_buscar.Enable(False)
        self.btn_siguientes.Enable(False)
        if hasattr(self, 'item_siguientes'):
            self.item_siguientes.Enable(False)
        self.txt_busqueda.Enable(False)
        self.set_status("Buscando...", field=0, announce=True)
        lbl_canal = f" del canal {self.current_channel_title}" if self.current_channel_title else ""
        self.lbl_progreso_detalle.SetLabel(f"Listando listas de reproducción{lbl_canal}...")

        def _worker():
            try:
                resultados = self.downloader.buscar_canal_playlists(channel_url, max_results=max_results, start_index=1)
                detected = getattr(self.downloader, 'last_container_title', '')
                if not self.current_channel_title and detected:
                    self.current_channel_title = detected
                ch_nombre = self.current_channel_title or channel_url
                wx.CallAfter(self._on_search_completed, resultados, f"Listas de reproducción del canal {ch_nombre}", False)
            except Exception as e:
                wx.CallAfter(self._on_search_error, str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def ejecutar_busqueda_playlist_videos(self, playlist_url, playlist_title=""):
        if self.is_searching:
            return
        if hasattr(self, 'resultados') and self.resultados:
            self._pending_nav_state = self._capturar_estado_navegacion()
        max_results = int(self.config.get('max_results', 25))
        self.is_searching = True
        self.last_search_query = playlist_url
        self.last_search_kind = 'playlist_videos'
        self.last_target_url = playlist_url
        self.current_playlist_title = playlist_title or ""
        self.next_start_index = 1

        self.btn_buscar.Enable(False)
        self.btn_siguientes.Enable(False)
        if hasattr(self, 'item_siguientes'):
            self.item_siguientes.Enable(False)
        self.txt_busqueda.Enable(False)
        self.set_status("Buscando...", field=0, announce=True)
        lbl_pl = f" de {self.current_playlist_title}" if self.current_playlist_title else ""
        self.lbl_progreso_detalle.SetLabel(f"Cargando vídeos de la lista de reproducción{lbl_pl}...")

        def _worker():
            try:
                resultados = self.downloader.buscar_playlist_videos(playlist_url, max_results=max_results, start_index=1)
                detected = getattr(self.downloader, 'last_container_title', '')
                if not self.current_playlist_title and detected:
                    self.current_playlist_title = detected
                pl_nombre = self.current_playlist_title or "la lista"
                wx.CallAfter(self._on_search_completed, resultados, f"Vídeos de la lista {pl_nombre}", False)
            except Exception as e:
                wx.CallAfter(self._on_search_error, str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def _verificar_sesion_configurada(self):
        """Verifica si el usuario tiene una sesión de cookies configurada o le ofrece abrir Opciones."""
        cfg = cargar_configuracion()
        src = cfg.get('cookie_source', 'none')
        if src == 'none':
            resp = wx.MessageBox(
                "Para acceder a tu historial y listas privadas de YouTube necesitas configurar el acceso de sesión con tus cookies "
                "(usando tu navegador Firefox/Brave o seleccionando un archivo cookies.txt).\n\n"
                "¿Deseas abrir la ventana de Opciones ahora para configurarlo?",
                "Sesión de YouTube no configurada",
                wx.YES_NO | wx.ICON_QUESTION,
                self
            )
            if resp == wx.YES:
                self.on_abrir_opciones(None)
                cfg = cargar_configuracion()
                return cfg.get('cookie_source', 'none') != 'none'
            return False
        return True

    def ejecutar_busqueda_historial(self):
        """Carga el historial de reproducciones de YouTube del usuario."""
        if not self.verificar_libreria_ytdlp():
            return
        if not self._verificar_sesion_configurada():
            return
        if self.is_searching:
            return
        if hasattr(self, 'navigation_stack'):
            self.navigation_stack.clear()
        self._pending_nav_state = None
        max_results = int(self.config.get('max_results', 25))
        self.is_searching = True
        self.is_showing_favorites = False
        self.last_search_query = "Historial"
        self.last_search_kind = 'historial'
        self.last_target_url = "https://www.youtube.com/feed/history"
        self.next_start_index = 1

        self.btn_buscar.Enable(False)
        self.btn_siguientes.Enable(False)
        if hasattr(self, 'item_siguientes'):
            self.item_siguientes.Enable(False)
        self.txt_busqueda.Enable(False)
        self.set_status("Obteniendo tu historial de reproducciones de YouTube...", field=0, announce=True)
        self.lbl_progreso_detalle.SetLabel("Cargando historial de reproducciones...")

        def _worker():
            try:
                resultados = self.downloader.buscar_historial(max_results=max_results, start_index=1)
                wx.CallAfter(self._on_search_completed, resultados, "Historial de YouTube", False)
            except Exception as e:
                wx.CallAfter(self._on_search_error, str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def ejecutar_busqueda_ver_mas_tarde(self):
        """Carga los vídeos de la lista 'Ver más tarde' del usuario."""
        if not self.verificar_libreria_ytdlp():
            return
        if not self._verificar_sesion_configurada():
            return
        if self.is_searching:
            return
        if hasattr(self, 'navigation_stack'):
            self.navigation_stack.clear()
        self._pending_nav_state = None
        max_results = int(self.config.get('max_results', 25))
        self.is_searching = True
        self.is_showing_favorites = False
        self.last_search_query = "Ver más tarde"
        self.last_search_kind = 'ver_mas_tarde'
        self.last_target_url = "https://www.youtube.com/playlist?list=WL"
        self.next_start_index = 1

        self.btn_buscar.Enable(False)
        self.btn_siguientes.Enable(False)
        if hasattr(self, 'item_siguientes'):
            self.item_siguientes.Enable(False)
        self.txt_busqueda.Enable(False)
        self.set_status("Obteniendo tu lista 'Ver más tarde' de YouTube...", field=0, announce=True)
        self.lbl_progreso_detalle.SetLabel("Cargando lista Ver más tarde...")

        def _worker():
            try:
                resultados = self.downloader.buscar_ver_mas_tarde(max_results=max_results, start_index=1)
                wx.CallAfter(self._on_search_completed, resultados, "Ver más tarde", False)
            except Exception as e:
                wx.CallAfter(self._on_search_error, str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def ejecutar_busqueda_mis_playlists(self):
        """Carga las listas de reproducción de la cuenta del usuario."""
        if not self.verificar_libreria_ytdlp():
            return
        if not self._verificar_sesion_configurada():
            return
        if self.is_searching:
            return
        if hasattr(self, 'navigation_stack'):
            self.navigation_stack.clear()
        self._pending_nav_state = None
        max_results = int(self.config.get('max_results', 25))
        self.is_searching = True
        self.is_showing_favorites = False
        self.last_search_query = "Mis listas de reproducción"
        self.last_search_kind = 'mis_playlists'
        self.last_target_url = "https://www.youtube.com/feed/playlists"
        self.current_playlist_title = "Mis listas de reproducción"
        self.current_channel_title = ""
        self.next_start_index = 1

        self.btn_buscar.Enable(False)
        self.btn_siguientes.Enable(False)
        if hasattr(self, 'item_siguientes'):
            self.item_siguientes.Enable(False)
        self.txt_busqueda.Enable(False)
        self.set_status("Obteniendo tus listas de reproducción de YouTube...", field=0, announce=True)
        self.lbl_progreso_detalle.SetLabel("Cargando listas de reproducción de la cuenta...")

        def _worker():
            try:
                resultados = self.downloader.buscar_mis_playlists(max_results=max_results, start_index=1)
                wx.CallAfter(self._on_search_completed, resultados, "Mis listas de reproducción", False)
            except Exception as e:
                wx.CallAfter(self._on_search_error, str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def on_btn_siguientes(self, event=None):
        if not self.verificar_libreria_ytdlp():
            return
        if self.is_searching:
            return
        if not self.last_search_query and not self.last_target_url:
            return

        max_results = int(self.config.get('max_results', 25))
        start_index = self.next_start_index
        kind = self.last_search_kind
        query = self.last_search_query
        engine = self.last_search_engine
        search_type = self.last_search_type
        target_url = self.last_target_url

        self.is_searching = True
        self.btn_buscar.Enable(False)
        self.btn_siguientes.Enable(False)
        if hasattr(self, 'item_siguientes'):
            self.item_siguientes.Enable(False)
        self.txt_busqueda.Enable(False)

        msg_status = f"Buscando los siguientes {max_results} resultados..."
        self.set_status(msg_status, field=0, announce=True)
        self.lbl_progreso_detalle.SetLabel(f"Cargando resultados {start_index} a {start_index + max_results - 1}...")

        def _worker():
            try:
                if kind == 'canal_videos':
                    resultados = self.downloader.buscar_canal_videos(target_url, max_results=max_results, start_index=start_index)
                    query_desc = f"Vídeos del canal {target_url}"
                elif kind == 'canal_playlists':
                    resultados = self.downloader.buscar_canal_playlists(target_url, max_results=max_results, start_index=start_index)
                    query_desc = f"Listas de reproducción del canal {target_url}"
                elif kind == 'playlist_videos':
                    resultados = self.downloader.buscar_playlist_videos(target_url, max_results=max_results, start_index=start_index)
                    query_desc = "Vídeos de la lista"
                elif kind == 'historial':
                    resultados = self.downloader.buscar_historial(max_results=max_results, start_index=start_index)
                    query_desc = "Historial de YouTube"
                elif kind == 'ver_mas_tarde':
                    resultados = self.downloader.buscar_ver_mas_tarde(max_results=max_results, start_index=start_index)
                    query_desc = "Ver más tarde"
                elif kind == 'mis_playlists':
                    resultados = self.downloader.buscar_mis_playlists(max_results=max_results, start_index=start_index)
                    query_desc = "Mis listas de reproducción"
                else:
                    resultados = self.downloader.buscar(query, max_results=max_results, engine=engine, search_type=search_type, start_index=start_index)
                    query_desc = query

                wx.CallAfter(self._on_search_completed, resultados, query_desc, True)
            except Exception as e:
                wx.CallAfter(self._on_search_error, str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_search_completed(self, resultados, query_desc, append=False):
        self.is_searching = False
        self.btn_buscar.Enable(True)
        self.txt_busqueda.Enable(True)

        if append:
            if not resultados:
                self.btn_siguientes.Enable(False)
                if hasattr(self, 'item_siguientes'):
                    self.item_siguientes.Enable(False)
                msg = f"No hay más resultados para '{query_desc}'."
                self.set_status(msg, field=0, announce=True)
                self.lbl_progreso_detalle.SetLabel(f"Fin de los resultados. Mostrando {len(self.resultados)} en total.")
                return

            existing_ids = {r.get('id') for r in self.resultados if r.get('id')}
            existing_urls = {r.get('url') for r in self.resultados if r.get('url')}
            nuevos = [
                r for r in resultados
                if (r.get('id') not in existing_ids and r.get('url') not in existing_urls)
            ]

            if not nuevos:
                self.btn_siguientes.Enable(False)
                if hasattr(self, 'item_siguientes'):
                    self.item_siguientes.Enable(False)
                msg = "No se encontraron resultados adicionales nuevos."
                self.set_status(msg, field=0, announce=True)
                self.lbl_progreso_detalle.SetLabel(f"Fin de resultados. Mostrando {len(self.resultados)} en total.")
                return

            prev_count = len(self.resultados)
            for r in nuevos:
                r['index'] = len(self.resultados) + 1
                self.resultados.append(r)
                titulo_text, img_idx = self._get_item_display_title_and_image(r, is_fav_view=False)
                item_row = self.lista_resultados.InsertItem(self.lista_resultados.GetItemCount(), titulo_text, img_idx)
                self.lista_resultados.SetItem(item_row, 1, r.get('channel', 'Desconocido'))
                self.lista_resultados.SetItem(item_row, 2, r.get('duration', '--:--'))
                self.lista_resultados.SetItem(item_row, 3, str(r.get('views', '--')))

            self.next_start_index += len(resultados)
            total_count = len(self.resultados)
            self.btn_siguientes.Enable(True)
            if hasattr(self, 'item_siguientes'):
                self.item_siguientes.Enable(True)

            self.lista_resultados.Select(prev_count)
            self.lista_resultados.Focus(prev_count)
            self.lista_resultados.EnsureVisible(prev_count)
            self.lista_resultados.SetFocus()

            status_msg = f"Cargados {len(nuevos)} resultados más. Mostrando {total_count} en total."
            self.set_status(status_msg, field=0, announce=True)
            self.lbl_results_info.SetLabel(f"&Lista de resultados ({total_count} encontrados):")
            self.lbl_progreso_detalle.SetLabel(f"Mostrando {total_count} resultados. Usa Espacio para marcar vídeos o Alt+S para siguientes.")
            self._actualizar_contador_seleccion()
            self.set_modo_boton_buscar('limpiar')
            return

        if getattr(self, '_pending_nav_state', None) is not None:
            if hasattr(self, 'navigation_stack'):
                self.navigation_stack.append(self._pending_nav_state)
            self._pending_nav_state = None

        self.is_showing_favorites = False
        self.resultados = resultados
        self.lista_resultados.DeleteAllItems()

        self.col_activa_resultados = 0

        if not resultados:
            self.btn_siguientes.Enable(False)
            if hasattr(self, 'item_siguientes'):
                self.item_siguientes.Enable(False)
            msg = f"No se encontraron elementos para '{query_desc}'."
            self.set_status(msg, field=0, announce=True)
            self.lbl_results_info.SetLabel("&Lista de resultados (0 encontrados):")
            self.lbl_progreso_detalle.SetLabel("No se obtuvieron resultados.")
            wx.MessageBox(msg, "Sin resultados", wx.OK | wx.ICON_INFORMATION, self)
            self.txt_busqueda.SetFocus()
            self.set_modo_boton_buscar('buscar')
            return

        for idx, r in enumerate(resultados):
            titulo_text, img_idx = self._get_item_display_title_and_image(r, is_fav_view=False)
            item_row = self.lista_resultados.InsertItem(self.lista_resultados.GetItemCount(), titulo_text, img_idx)
            self.lista_resultados.SetItem(item_row, 1, r.get('channel', 'Desconocido'))
            self.lista_resultados.SetItem(item_row, 2, r.get('duration', '--:--'))
            self.lista_resultados.SetItem(item_row, 3, str(r.get('views', '--')))

        num = len(resultados)
        self.next_start_index = 1 + num
        hay_canales = any(r.get('is_channel') for r in resultados)
        hay_playlists = any(r.get('is_playlist') for r in resultados)

        tipo_query = identificar_tipo_url(self.last_search_query) if self.last_search_query else 'texto'
        es_video_directo = (tipo_query == 'video')
        max_results = int(self.config.get('max_results', 25))
        puede_paginar = not es_video_directo and (num >= max_results)
        self.btn_siguientes.Enable(puede_paginar)
        if hasattr(self, 'item_siguientes'):
            self.item_siguientes.Enable(puede_paginar)


        if hay_canales:
            if num == 1:
                status_msg = f"Canal obtenido: {resultados[0].get('title', '')}. Pulsa Enter para ver sus vídeos."
                detalle_msg = "Canal obtenido. Pulsa Enter o Doble Clic para ver sus vídeos o pulsa Descargar para descargar todos."
            else:
                status_msg = f"Cargados {num} canales. Pulsa Enter en uno para ver sus vídeos o Alt+S para ver más."
                detalle_msg = "Pulsa Enter o Doble Clic en un canal para ver sus vídeos."
        elif hay_playlists:
            if num == 1:
                status_msg = f"Lista obtenida: {resultados[0].get('title', '')}. Pulsa Enter para ver sus vídeos."
                detalle_msg = "Lista obtenida. Pulsa Enter o Doble Clic para ver sus vídeos o pulsa Descargar para descargar todos."
            else:
                status_msg = f"Cargadas {num} listas de reproducción. Pulsa Enter en una para ver sus vídeos o Alt+S para ver más."
                detalle_msg = "Pulsa Enter o Doble Clic en una lista para ver sus vídeos."
        else:
            status_msg = f"Búsqueda completada: {num} resultados encontrados. Usa Espacio para marcar vídeos o Alt+S para los siguientes."
            detalle_msg = "Marca vídeos con Espacio y pulsa Descargar, o pulsa Siguientes resultados (Alt+S)."


        self.set_status(status_msg, field=0, announce=True)
        self.lbl_results_info.SetLabel(f"&Lista de resultados ({num} encontrados):")
        self.lbl_progreso_detalle.SetLabel(detalle_msg)
        self._actualizar_contador_seleccion()

        self.lista_resultados.Select(0)
        self.lista_resultados.Focus(0)
        self.lista_resultados.SetFocus()
        self.set_modo_boton_buscar('limpiar')

    def _on_search_error(self, error_str):
        self._pending_nav_state = None
        self.is_searching = False
        self.btn_buscar.Enable(True)
        self.txt_busqueda.Enable(True)
        if self.resultados:
            max_results = int(self.config.get('max_results', 25))
            puede_paginar = not getattr(self, 'is_showing_favorites', False) and (len(self.resultados) >= max_results)
            self.btn_siguientes.Enable(puede_paginar)
            if hasattr(self, 'item_siguientes'):
                self.item_siguientes.Enable(puede_paginar)
            self.set_modo_boton_buscar('limpiar')
        else:
            self.set_modo_boton_buscar('buscar')
        self.set_status("Error en la búsqueda.", field=0, announce=True)
        self.lbl_progreso_detalle.SetLabel("Error al realizar la búsqueda.")
        if "DRM" in str(error_str):
            msg_err = (
                "El contenido o enlace introducido cuenta con protección DRM oficial del proveedor "
                "(bloqueo de copia digital) y no puede ser procesado ni descargado por restricciones técnicas del sitio."
            )
        else:
            msg_err = f"Ocurrió un error al buscar:\n\n{error_str}"
        wx.MessageBox(msg_err, "Error de búsqueda", wx.OK | wx.ICON_ERROR, self)
        if not self.resultados:
            self.txt_busqueda.SetFocus()
        else:
            self.lista_resultados.SetFocus()

    # ---------------- GESTIÓN DE FAVORITOS ----------------
