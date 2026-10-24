"""
Mixin de gestión de eventos de lista, teclado y selecciones para MainFrame.
"""

import os
import sys
import wx

import accessibility
import sound_manager
from config_manager import cargar_configuracion
from favorites_manager import es_favorito
from media_utils import formatear_duracion, formatear_visitas, formatear_tamano
from misc_dialogs import DescriptionDialog, _navegar_columna
from streaming import precargar_stream_en_segundo_plano



class MainListEventsMixin:
    def on_item_focused(self, event):
        idx = event.GetIndex()
        if 0 <= idx < len(self.resultados):
            self.last_selected_row = idx
        event.Skip()

    def on_item_selected(self, event):
        idx = event.GetIndex()
        if 0 <= idx < len(self.resultados):
            self.last_selected_row = idx
        self.col_activa_resultados = 0
        if 0 <= idx < len(self.resultados):
            r = self.resultados[idx]
            is_sel = r.get('selected', False)
            estado_tag = "Marcado - " if is_sel else ""
            is_fav = getattr(self, 'is_showing_favorites', False)
            if is_fav:
                _, tag, _ = self._get_item_type_and_image(r)
                tipo_str = f"{tag} "
            else:
                tipo_str = ""
            self.status_bar.SetStatusText(f"{estado_tag}{tipo_str}{r.get('title', 'Elemento')} ({r.get('duration', '--:--')})", 0)

            # Precarga predictiva en segundo plano para arranque instantáneo de audio
            if not r.get('is_playlist') and not r.get('is_channel'):
                target_u = r.get('url') or r.get('id', '')
                if target_u:
                    solo_audio = not self.config.get('reproducir_con_video', True)
                    if hasattr(self, '_prefetch_sel_timer') and self._prefetch_sel_timer and self._prefetch_sel_timer.IsRunning():
                        self._prefetch_sel_timer.Stop()
                    self._prefetch_sel_timer = wx.CallLater(300, precargar_stream_en_segundo_plano, target_u, solo_audio)

    def _get_current_index(self):
        idx = self.lista_resultados.GetFirstSelected()
        if idx == -1:
            idx = self.lista_resultados.GetFocusedItem()
        if idx == -1 and hasattr(self, 'last_selected_row') and self.last_selected_row != -1:
            idx = self.last_selected_row
        if idx == -1 and hasattr(self, 'lista_resultados') and self.lista_resultados.GetItemCount() > 0:
            idx = 0
        if 0 <= idx < len(self.resultados):
            return idx
        return -1

    def _get_selected_video(self):
        idx = self._get_current_index()
        if idx == -1:
            return None
        return self.resultados[idx]

    def _actualizar_item_fila(self, idx):
        if 0 <= idx < len(self.resultados) and 0 <= idx < self.lista_resultados.GetItemCount():
            r = self.resultados[idx]
            is_fav = getattr(self, 'is_showing_favorites', False)
            titulo_text, img_idx = self._get_item_display_title_and_image(r, is_fav_view=is_fav)
            self.lista_resultados.SetItem(idx, 0, titulo_text)
            self.lista_resultados.SetItemImage(idx, img_idx)
            self.lista_resultados.SetItem(idx, 1, r.get('channel', 'Desconocido'))
            self.lista_resultados.SetItem(idx, 2, r.get('duration', '--:--'))
            self.lista_resultados.SetItem(idx, 3, str(r.get('views', '--')))

    def navegar_columna_resultados(self, delta):
        _navegar_columna(self.lista_resultados, 'col_activa_resultados', self, delta, self.status_bar)

    def on_char_hook(self, event):
        focus = self.FindFocus()
        keycode = event.GetKeyCode()
        modifiers = event.GetModifiers()

        # Si el reproductor multimedia está abierto, redirigir atajos de control y vídeo
        if hasattr(self, 'active_preview_dialog') and self.active_preview_dialog:
            dlg = self.active_preview_dialog
            if not getattr(dlg, '_is_closing', False) and dlg.IsShown():
                if keycode == wx.WXK_F11:
                    dlg.toggle_video_display(None)
                    self._enfocar_reproductor_activo()
                    return
                elif keycode == wx.WXK_F6:
                    dlg.cambiar_velocidad(-0.1)
                    self._enfocar_reproductor_activo()
                    return
                elif keycode == wx.WXK_F7:
                    dlg.cambiar_velocidad(0.1)
                    self._enfocar_reproductor_activo()
                    return
                elif keycode == wx.WXK_F8 and focus not in (getattr(self, 'lista_resultados', None), getattr(self, 'txt_busqueda', None)):
                    dlg.anunciar_porcentaje()
                    self._enfocar_reproductor_activo()
                    return
                elif keycode == wx.WXK_F9:
                    dlg.anunciar_tiempo_transcurrido()
                    self._enfocar_reproductor_activo()
                    return
                elif keycode == wx.WXK_F10:
                    dlg.anunciar_tiempo_restante()
                    self._enfocar_reproductor_activo()
                    return
                elif keycode == getattr(wx, 'WXK_MEDIA_PLAY_PAUSE', -999):
                    dlg.toggle_play_pause(None)
                    return
                elif keycode == getattr(wx, 'WXK_MEDIA_STOP', -999):
                    dlg.stop(None)
                    return
                elif keycode == getattr(wx, 'WXK_MEDIA_NEXT_TRACK', -999):
                    dlg.play_next()
                    return
                elif keycode == getattr(wx, 'WXK_MEDIA_PREV_TRACK', -999):
                    dlg.play_prev()
                    return

        if keycode == wx.WXK_ESCAPE and modifiers in (wx.MOD_NONE, 0):
            self.retroceder_nivel_o_limpiar()
            return

        if keycode == wx.WXK_F8 and modifiers in (wx.MOD_NONE, 0):
            self.anunciar_porcentaje_descarga()
            return

        if focus == self.lista_resultados:
            if keycode in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
                self.eliminar_favorito_seleccion()
                return
            elif keycode == wx.WXK_LEFT:
                if modifiers == wx.MOD_ALT:
                    self.retroceder_nivel_o_limpiar()
                    return
                self.navegar_columna_resultados(-1)
                return
            elif keycode == wx.WXK_RIGHT:
                self.navegar_columna_resultados(1)
                return
            elif keycode == wx.WXK_SPACE:
                self.toggle_seleccion_actual()
                return
            elif keycode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
                video = self._get_selected_video()
                if video and video.get('is_fav_list'):
                    self.mostrar_favoritos_de_lista(video.get('list_name'), push_state=True)
                elif video and video.get('is_channel'):
                    self.ejecutar_busqueda_canal_videos(video['url'], video.get('title') or video.get('channel', ''))
                elif video and video.get('is_playlist'):
                    self.ejecutar_busqueda_playlist_videos(video['url'], video.get('title', ''))
                else:
                    self.on_previsualizar_video(None)
                return
            elif keycode == ord('A') and modifiers == wx.MOD_CONTROL:
                self.seleccionar_todos()
                return
            elif keycode in (ord('P'), ord('p')) and modifiers == wx.MOD_CONTROL:
                self.on_previsualizar_video(None)
                return
            elif keycode in (ord('L'), ord('l')) and modifiers == wx.MOD_CONTROL:
                self.reproducir_toda_la_lista(None)
                return
            elif keycode in (ord('M'), ord('m')) and modifiers == wx.MOD_CONTROL:
                self.on_cambiar_favorito_lista(None)
                return
            elif keycode in (ord('J'), ord('j')) and modifiers == wx.MOD_CONTROL:
                self.mostrar_dialogo_cola(None)
                return

        event.Skip()

    def on_lista_key_down(self, event):
        keycode = event.GetKeyCode()
        modifiers = event.GetModifiers()

        if keycode in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            self.eliminar_favorito_seleccion()
            return
        elif keycode == wx.WXK_LEFT:
            if modifiers == wx.MOD_ALT:
                self.retroceder_nivel_o_limpiar()
                return
            self.navegar_columna_resultados(-1)
            return
        elif keycode == wx.WXK_RIGHT:
            self.navegar_columna_resultados(1)
            return
        elif keycode == wx.WXK_SPACE:
            self.toggle_seleccion_actual()
            return
        elif keycode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            video = self._get_selected_video()
            if video and video.get('is_fav_list'):
                self.mostrar_favoritos_de_lista(video.get('list_name'), push_state=True)
            elif video and video.get('is_channel'):
                self.ejecutar_busqueda_canal_videos(video['url'], video.get('title') or video.get('channel', ''))
            elif video and video.get('is_playlist'):
                self.ejecutar_busqueda_playlist_videos(video['url'], video.get('title', ''))
            else:
                self.on_previsualizar_video(None)
            return
        elif keycode == ord('A') and modifiers == wx.MOD_CONTROL:
            self.seleccionar_todos()
            return
        elif keycode in (ord('P'), ord('p')) and modifiers == wx.MOD_CONTROL:
            self.on_previsualizar_video(None)
            return
        elif keycode in (ord('L'), ord('l')) and modifiers == wx.MOD_CONTROL:
            self.reproducir_toda_la_lista(None)
            return
        elif keycode in (ord('M'), ord('m')) and modifiers == wx.MOD_CONTROL:
            self.on_cambiar_favorito_lista(None)
            return

        event.Skip()

    def on_left_dclick(self, event):
        video = self._get_selected_video()
        if not video:
            return
        if video.get('is_fav_list'):
            self.mostrar_favoritos_de_lista(video.get('list_name'), push_state=True)
        elif video.get('is_channel'):
            self.ejecutar_busqueda_canal_videos(video['url'], video.get('title') or video.get('channel', ''))
        elif video.get('is_playlist'):
            self.ejecutar_busqueda_playlist_videos(video['url'], video.get('title', ''))
        else:
            self.on_previsualizar_video(None)

    def toggle_seleccion_actual(self):
        if not hasattr(self, 'resultados') or len(self.resultados) <= 1:
            if hasattr(self, 'resultados') and len(self.resultados) == 1:
                accessibility.speak("Solo hay 1 elemento en la lista; no es necesario marcarlo.")
                self.set_status("Solo hay 1 elemento en la lista; no es necesario marcarlo.", field=0, announce=False)
            return
        idx = self._get_current_index()
        if idx == -1:
            return
        r = self.resultados[idx]
        r['selected'] = not r.get('selected', False)
        self._actualizar_item_fila(idx)
        estado_str = "Marcado" if r['selected'] else "Desmarcado"
        is_fav = getattr(self, 'is_showing_favorites', False)
        if is_fav:
            _, tag, _ = self._get_item_type_and_image(r)
            accessibility.speak(f"{estado_str}: {tag} {r['title']}")
        else:
            accessibility.speak(f"{estado_str}: {r['title']}")
        self._actualizar_contador_seleccion()

    def seleccionar_todos(self):
        if not hasattr(self, 'resultados') or len(self.resultados) <= 1:
            return
        for idx, r in enumerate(self.resultados):
            r['selected'] = True
            self._actualizar_item_fila(idx)
        total = len(self.resultados)
        self._actualizar_contador_seleccion()
        accessibility.speak(f"Seleccionados todos los {total} elementos.")
        self.set_status(f"Todos los elementos seleccionados ({total}).", field=0, announce=False)

    def deseleccionar_todos(self):
        if not hasattr(self, 'resultados') or len(self.resultados) <= 1:
            return
        for idx, r in enumerate(self.resultados):
            r['selected'] = False
            self._actualizar_item_fila(idx)
        self._actualizar_contador_seleccion()
        accessibility.speak("Deseleccionados todos los elementos.")
        self.set_status("Todos los elementos deseleccionados.", field=0, announce=False)

    def invertir_seleccion(self):
        if not hasattr(self, 'resultados') or len(self.resultados) <= 1:
            return
        for idx, r in enumerate(self.resultados):
            r['selected'] = not r.get('selected', False)
            self._actualizar_item_fila(idx)
        num_sel = sum(1 for r in self.resultados if r.get('selected'))
        self._actualizar_contador_seleccion()
        accessibility.speak(f"Selección invertida. {num_sel} elementos marcados.")
        self.set_status(f"Selección invertida ({num_sel} marcados).", field=0, announce=False)

    def _actualizar_contador_seleccion(self):
        num_sel = sum(1 for r in self.resultados if r.get('selected')) if hasattr(self, 'resultados') and self.resultados else 0
        if num_sel > 0:
            self.btn_descargar.SetLabel(f"&Descargar Seleccionados ({num_sel})")
            self.btn_previsualizar.SetLabel(f"&Reproducir ({num_sel})")
            self.status_bar.SetStatusText(f"{num_sel} elementos marcados", 0)
        else:
            self.btn_descargar.SetLabel("&Descargar Seleccionado")
            self.btn_previsualizar.SetLabel("&Reproducir selección")
        self.actualizar_estados_interfaz()

    def on_context_menu(self, event):
        video = self._get_selected_video()
        if not video and not self.resultados:
            return

        menu = wx.Menu()

        num_items = len(self.resultados) if hasattr(self, 'resultados') and self.resultados else 0
        hay_multiples = (num_items > 1)
        num_cola = len(self.cola_reproduccion) if hasattr(self, 'cola_reproduccion') and self.cola_reproduccion else 0
        num_sel = sum(1 for r in self.resultados if r.get('selected'))
        is_fav_view = getattr(self, 'is_showing_favorites', False)
        vid_id_or_url = video.get('url') or video.get('id', '') if video else ''

        if num_sel > 1:
            marcados = [r for r in self.resultados if r.get('selected')]
            alguno_fav = is_fav_view or any(es_favorito(r.get('url') or r.get('id', '')) for r in marcados)
            todos_fav = is_fav_view or all(es_favorito(r.get('url') or r.get('id', '')) for r in marcados)
            if todos_fav:
                fav_label = f"&Eliminar de Favoritos ({num_sel} seleccionados)\tSupr"
                is_fav = True
            elif not alguno_fav:
                fav_label = f"&Añadir a Favoritos ({num_sel} seleccionados)\tCtrl+B"
                is_fav = False
            else:
                fav_label = f"&Añadir o quitar selección de Favoritos ({num_sel} seleccionados)\tCtrl+B"
                is_fav = False
        else:
            is_fav = is_fav_view or es_favorito(vid_id_or_url)
            fav_label = "&Eliminar de Favoritos\tSupr" if is_fav else "&Añadir a Favoritos\tCtrl+B"

        if video and video.get('is_fav_list'):
            item_open_fav = menu.Append(wx.ID_ANY, "&Ver elementos de esta lista de favoritos")
            item_add_q_fav = menu.Append(wx.ID_ANY, "A&ñadir todos los favoritos de esta lista a la cola de reproducción\tCtrl+Q")
            item_dl_fav = menu.Append(wx.ID_ANY, "&Descargar todos los vídeos de esta lista de favoritos\tCtrl+D")
            self.Bind(wx.EVT_MENU, lambda e, v=video: self.mostrar_favoritos_de_lista(v.get('list_name'), push_state=True), item_open_fav)
            self.Bind(wx.EVT_MENU, lambda e, v=video: self.agregar_a_cola_reproduccion(e), item_add_q_fav)
            self.Bind(wx.EVT_MENU, self.on_btn_descargar, item_dl_fav)
            if num_cola > 0:
                item_play_q = menu.Append(wx.ID_ANY, "Reproducir &cola de reproducción\tCtrl+Shift+Q")
                item_ver_q = menu.Append(wx.ID_ANY, "Ver &cola de reproducción...\tCtrl+J")
                self.Bind(wx.EVT_MENU, self.reproducir_cola, item_play_q)
                self.Bind(wx.EVT_MENU, self.mostrar_dialogo_cola, item_ver_q)
            menu.AppendSeparator()
        elif video and video.get('is_channel'):
            item_dl = menu.Append(wx.ID_ANY, "&Descargar todos los vídeos de este canal\tCtrl+D")
            item_vids = menu.Append(wx.ID_ANY, "&Ver vídeos de este canal")
            item_pls = menu.Append(wx.ID_ANY, "&Ver listas de reproducción de este canal")
            item_add_q = menu.Append(wx.ID_ANY, "A&ñadir vídeos de este canal a la cola de reproducción\tCtrl+Q")
            self.Bind(wx.EVT_MENU, self.agregar_a_cola_reproduccion, item_add_q)
            if num_cola > 0:
                item_play_q = menu.Append(wx.ID_ANY, "Reproducir &cola de reproducción\tCtrl+Shift+Q")
                item_ver_q = menu.Append(wx.ID_ANY, "Ver &cola de reproducción...\tCtrl+J")
                self.Bind(wx.EVT_MENU, self.reproducir_cola, item_play_q)
                self.Bind(wx.EVT_MENU, self.mostrar_dialogo_cola, item_ver_q)
            item_desc = menu.Append(wx.ID_ANY, "&Descripción del canal")
            item_copy = menu.Append(wx.ID_ANY, "&Copiar enlace del canal\tCtrl+C")
            item_fav = menu.Append(wx.ID_ANY, fav_label)
            self.Bind(wx.EVT_MENU, self.on_btn_descargar, item_dl)
            self.Bind(wx.EVT_MENU, lambda e, v=video: self.ejecutar_busqueda_canal_videos(v['url'], v.get('title') or v.get('channel', '')), item_vids)
            self.Bind(wx.EVT_MENU, lambda e, v=video: self.ejecutar_busqueda_canal_playlists(v['url'], v.get('title') or v.get('channel', '')), item_pls)
            self.Bind(wx.EVT_MENU, lambda e, v=video: self.mostrar_descripcion(v), item_desc)
            self.Bind(wx.EVT_MENU, self.on_copiar_enlace, item_copy)
            if is_fav:
                self.Bind(wx.EVT_MENU, self.eliminar_favorito_seleccion, item_fav)
            else:
                self.Bind(wx.EVT_MENU, self.toggle_favorito_seleccion, item_fav)
            self._agregar_submenu_cambiar_lista(menu, video)
            menu.AppendSeparator()
        elif video and video.get('is_playlist'):
            item_dl = menu.Append(wx.ID_ANY, "&Descargar todos los vídeos de esta lista\tCtrl+D")
            item_open_pl = menu.Append(wx.ID_ANY, "&Ver vídeos de esta lista de reproducción")
            item_add_q = menu.Append(wx.ID_ANY, "A&ñadir vídeos de esta lista a la cola de reproducción\tCtrl+Q")
            self.Bind(wx.EVT_MENU, self.agregar_a_cola_reproduccion, item_add_q)
            if num_cola > 0:
                item_play_q = menu.Append(wx.ID_ANY, "Reproducir &cola de reproducción\tCtrl+Shift+Q")
                item_ver_q = menu.Append(wx.ID_ANY, "Ver &cola de reproducción...\tCtrl+J")
                self.Bind(wx.EVT_MENU, self.reproducir_cola, item_play_q)
                self.Bind(wx.EVT_MENU, self.mostrar_dialogo_cola, item_ver_q)
            item_desc = menu.Append(wx.ID_ANY, "&Descripción de la lista")
            item_copy = menu.Append(wx.ID_ANY, "&Copiar enlace de la lista\tCtrl+C")
            item_canal_pls = menu.Append(wx.ID_ANY, "&Mostrar listas de reproducción del canal al que pertenece")
            item_canal_vids = menu.Append(wx.ID_ANY, "&Mostrar vídeos del canal al que pertenece")
            item_canal_copy = menu.Append(wx.ID_ANY, "Copiar &URL del canal al que pertenece")
            item_fav = menu.Append(wx.ID_ANY, fav_label)
            self.Bind(wx.EVT_MENU, self.on_btn_descargar, item_dl)
            self.Bind(wx.EVT_MENU, lambda e, v=video: self.ejecutar_busqueda_playlist_videos(v['url'], v.get('title', '')), item_open_pl)

            self.Bind(wx.EVT_MENU, lambda e, v=video: self.mostrar_descripcion(v), item_desc)
            self.Bind(wx.EVT_MENU, self.on_copiar_enlace, item_copy)
            self.Bind(wx.EVT_MENU, lambda e: self.mostrar_listas_del_canal_seleccionado(video), item_canal_pls)
            self.Bind(wx.EVT_MENU, lambda e: self.mostrar_videos_del_canal_seleccionado(video), item_canal_vids)
            self.Bind(wx.EVT_MENU, lambda e: self.copiar_url_del_canal_seleccionado(video), item_canal_copy)
            if is_fav:
                self.Bind(wx.EVT_MENU, self.eliminar_favorito_seleccion, item_fav)
            else:
                self.Bind(wx.EVT_MENU, self.toggle_favorito_seleccion, item_fav)
            self._agregar_submenu_cambiar_lista(menu, video)
            menu.AppendSeparator()
        elif video:
            item_prev = menu.Append(wx.ID_ANY, "&Ver / Reproducir vídeo (Continuo)...\tCtrl+P")
            item_play_all = menu.Append(wx.ID_ANY, "&Reproducir toda la lista continua\tCtrl+L")
            item_play_all.Enable(hay_multiples)
            lbl_q = f"A&ñadir los {num_sel} vídeos seleccionados a la cola de reproducción\tCtrl+Q" if num_sel > 1 else "A&ñadir a la cola de reproducción\tCtrl+Q"
            item_add_q = menu.Append(wx.ID_ANY, lbl_q)
            self.Bind(wx.EVT_MENU, self.agregar_a_cola_reproduccion, item_add_q)
            if num_cola > 0:
                item_play_q = menu.Append(wx.ID_ANY, "Reproducir &cola de reproducción\tCtrl+Shift+Q")
                item_ver_q = menu.Append(wx.ID_ANY, "Ver &cola de reproducción...\tCtrl+J")
                self.Bind(wx.EVT_MENU, self.reproducir_cola, item_play_q)
                self.Bind(wx.EVT_MENU, self.mostrar_dialogo_cola, item_ver_q)
            
            dl_label = f"&Descargar los {num_sel} vídeos seleccionados\tCtrl+D" if num_sel > 1 else "&Descargar este vídeo\tCtrl+D"
            item_dl = menu.Append(wx.ID_ANY, dl_label)
            item_dl_all = menu.Append(wx.ID_ANY, "Descargar &todos los vídeos de esta lista\tCtrl+Shift+D")
            item_dl_all.Enable(hay_multiples)
            item_desc = menu.Append(wx.ID_ANY, "&Descripción del vídeo")
            
            item_fav = menu.Append(wx.ID_ANY, fav_label)
            item_copy = menu.Append(wx.ID_ANY, "&Copiar enlace al portapapeles\tCtrl+C")
            item_canal_pls = menu.Append(wx.ID_ANY, "&Mostrar listas de reproducción del canal al que pertenece")
            item_canal_vids = menu.Append(wx.ID_ANY, "&Mostrar vídeos del canal al que pertenece")
            item_canal_copy = menu.Append(wx.ID_ANY, "Copiar &URL del canal al que pertenece")

            self.Bind(wx.EVT_MENU, self.on_previsualizar_video, item_prev)
            self.Bind(wx.EVT_MENU, self.reproducir_toda_la_lista, item_play_all)
            self.Bind(wx.EVT_MENU, self.on_btn_descargar, item_dl)
            self.Bind(wx.EVT_MENU, self.descargar_todos_los_videos_lista_actual, item_dl_all)
            self.Bind(wx.EVT_MENU, lambda e, v=video: self.mostrar_descripcion(v), item_desc)
            if is_fav:
                self.Bind(wx.EVT_MENU, self.eliminar_favorito_seleccion, item_fav)
            else:
                self.Bind(wx.EVT_MENU, self.toggle_favorito_seleccion, item_fav)
            self._agregar_submenu_cambiar_lista(menu, video)
            self.Bind(wx.EVT_MENU, self.on_copiar_enlace, item_copy)
            self.Bind(wx.EVT_MENU, lambda e: self.mostrar_listas_del_canal_seleccionado(video), item_canal_pls)
            self.Bind(wx.EVT_MENU, lambda e: self.mostrar_videos_del_canal_seleccionado(video), item_canal_vids)
            self.Bind(wx.EVT_MENU, lambda e: self.copiar_url_del_canal_seleccionado(video), item_canal_copy)
            menu.AppendSeparator()

        item_toggle = menu.Append(wx.ID_ANY, "&Marcar / Desmarcar elemento (Espacio)")
        item_toggle.Enable(hay_multiples)
        item_sel_all = menu.Append(wx.ID_ANY, "&Seleccionar todos\tCtrl+A")
        item_sel_all.Enable(hay_multiples)
        item_desel_all = menu.Append(wx.ID_ANY, "&Deseleccionar todos")
        item_desel_all.Enable(hay_multiples)
        item_inv_sel = menu.Append(wx.ID_ANY, "&Invertir selección")
        item_inv_sel.Enable(hay_multiples)

        self.Bind(wx.EVT_MENU, lambda e: self.toggle_seleccion_actual(), item_toggle)
        self.Bind(wx.EVT_MENU, lambda e: self.seleccionar_todos(), item_sel_all)
        self.Bind(wx.EVT_MENU, lambda e: self.deseleccionar_todos(), item_desel_all)
        self.Bind(wx.EVT_MENU, lambda e: self.invertir_seleccion(), item_inv_sel)

        if hasattr(self, 'btn_siguientes') and self.btn_siguientes.IsEnabled():
            menu.AppendSeparator()
            item_sig = menu.Append(wx.ID_ANY, "Cargar &siguientes resultados\tAlt+S")
            self.Bind(wx.EVT_MENU, self.on_btn_siguientes, item_sig)

        self.PopupMenu(menu)
        menu.Destroy()

    def mostrar_descripcion(self, video=None):
        if video is None:
            video = self._get_selected_video()
        if not video:
            wx.MessageBox("Selecciona primero un elemento de la lista.", "Aviso", wx.OK | wx.ICON_INFORMATION, self)
            return

        dlg = DescriptionDialog(self, video, self.downloader)
        dlg.ShowModal()
        dlg.Destroy()

    def on_copiar_enlace(self, event):
        video = self._get_selected_video()
        if not video:
            wx.MessageBox("Selecciona primero un elemento de la lista.", "Aviso", wx.OK | wx.ICON_INFORMATION, self)
            return

        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(video['url']))
            wx.TheClipboard.Close()
            self.set_status("Enlace copiado al portapapeles.", field=0, announce=True)

    def on_abrir_carpeta(self, event=None, target_path=None):
        path = target_path or getattr(self, 'destino_descarga_actual', None) or self.destino_dir
        if not os.path.exists(path):
            path = self.destino_dir
        if not os.path.exists(path):
            try:
                os.makedirs(path, exist_ok=True)
            except Exception as e:
                wx.MessageBox(f"No se pudo crear la carpeta:\n{e}", "Error", wx.OK | wx.ICON_ERROR, self)
                return
        try:
            os.startfile(path)
        except Exception as e:
            wx.MessageBox(f"No se pudo abrir la carpeta:\n{e}", "Error", wx.OK | wx.ICON_ERROR, self)

