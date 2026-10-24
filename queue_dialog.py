"""
Diálogo para la gestión de la cola de reproducción continua.
"""

import os
import sys
import threading
import wx

import accessibility
import sound_manager
from config_manager import cargar_configuracion
from media_utils import formatear_duracion, limpiar_extension_titulo
from ui_vlc import pedir_confirmacion_eliminar_favorito
from favorites_manager import (
    agregar_favorito,
    eliminar_favorito,
    obtener_favoritos,
    es_favorito,
    obtener_nombres_listas_favoritos,
    mover_favorito_de_lista
)
from favorites_dialogs import SelectFavoriteListDialog, ChangeFavoriteListDialog

class ColaReproduccionDialog(wx.Dialog):
    """
    Diálogo accesible para visualizar y gestionar la cola de reproducción continua.
    Permite revisar las pistas en espera, marcar/seleccionar con Espacio o Ctrl+A igual que en Favoritos,
    menú contextual con múltiples opciones, eliminar con Supr, reproducir con Enter y vaciar la cola.
    """
    def __init__(self, parent, videos, current_index=0, is_player=True):
        self.is_player = is_player
        self.videos_ref = videos
        self.current_index = current_index
        total = len(self.videos_ref)

        super().__init__(
            parent,
            title=f"Cola de reproducción ({total} {'pistas' if is_player else 'elementos'})",
            size=(760, 480),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.MAXIMIZE_BOX
        )

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.lbl_info = wx.StaticText(
            self,
            label=f"Pistas en la cola ({total}). Pulsa Espacio para marcar, Supr para eliminar o Enter para reproducir:"
        )
        self.lbl_info.SetFont(self.lbl_info.GetFont().Bold())
        sizer.Add(self.lbl_info, 0, wx.ALL, 10)

        self.lista_cola = wx.ListCtrl(
            self,
            style=wx.LC_REPORT | wx.BORDER_SUNKEN
        )
        self.lista_cola.SetName("Pistas en la cola de reproducción")
        self.lista_cola.InsertColumn(0, "Nº", width=65)
        self.lista_cola.InsertColumn(1, "Título", width=380)
        self.lista_cola.InsertColumn(2, "Canal", width=170)
        self.lista_cola.InsertColumn(3, "Duración", width=90)
        sizer.Add(self.lista_cola, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # Barra de botones
        row_btn = wx.BoxSizer(wx.HORIZONTAL)

        self.btn_play = wx.Button(self, label="Reproducir seleccionada (Enter)")
        self.btn_play.Bind(wx.EVT_BUTTON, self.on_reproducir_seleccion)
        row_btn.Add(self.btn_play, 0, wx.RIGHT, 8)

        self.btn_delete = wx.Button(self, label="Eliminar de la cola (Supr)")
        self.btn_delete.Bind(wx.EVT_BUTTON, self.on_eliminar_item)
        row_btn.Add(self.btn_delete, 0, wx.RIGHT, 8)

        self.btn_clear = wx.Button(self, label="Vaciar cola")
        self.btn_clear.Bind(wx.EVT_BUTTON, self.on_vaciar_cola)
        row_btn.Add(self.btn_clear, 0, wx.RIGHT, 8)

        row_btn.AddStretchSpacer()

        self.btn_close = wx.Button(self, id=wx.ID_CANCEL, label="Cerrar (Escape)")
        self.btn_close.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(wx.ID_CANCEL))
        row_btn.Add(self.btn_close, 0)
        self.SetEscapeId(wx.ID_CANCEL)

        sizer.Add(row_btn, 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(sizer)

        # Eventos de teclado, activación, navegación y menú contextual
        self.lista_cola.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        self.lista_cola.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_reproducir_seleccion)
        self.lista_cola.Bind(wx.EVT_LEFT_DCLICK, self.on_reproducir_seleccion)
        self.lista_cola.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
        self.lista_cola.Bind(wx.EVT_LIST_ITEM_FOCUSED, self.on_item_focused)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)

        self._poblar_lista()
        self.CenterOnParent()

        # Foco inicial
        wx.CallAfter(self._enfocar_inicial)

    def _poblar_lista(self):
        self.lista_cola.DeleteAllItems()
        for idx, v in enumerate(self.videos_ref):
            raw_tit = v.get('title', 'Sin título')
            for p in ('Marcado - ', '[Vídeo] ', '[Canal] ', '[Lista] '):
                if raw_tit.startswith(p):
                    raw_tit = raw_tit[len(p):]
            canal = v.get('channel', 'Desconocido')
            dur = v.get('duration', '--:--')
            is_sel = v.get('selected', False)
            prefix_sel = "Marcado - " if is_sel else ""

            if self.is_player and idx == self.current_index:
                prefijo_num = f"▶ {idx + 1}"
                tit_display = f"{prefix_sel}{raw_tit} [Reproduciendo]"
            else:
                prefijo_num = str(idx + 1)
                tit_display = f"{prefix_sel}{raw_tit}"

            item_idx = self.lista_cola.InsertItem(idx, prefijo_num)
            self.lista_cola.SetItem(item_idx, 1, tit_display)
            self.lista_cola.SetItem(item_idx, 2, canal)
            self.lista_cola.SetItem(item_idx, 3, dur)

        total = len(self.videos_ref)
        num_sel = sum(1 for v in self.videos_ref if v.get('selected'))
        tipo_lbl = "pistas" if self.is_player else "elementos"
        marc_str = f", {num_sel} marcados" if num_sel > 0 else ""
        self.lbl_info.SetLabel(f"Pistas en la cola ({total}{marc_str}). Pulsa Espacio para marcar, Supr para eliminar o Enter para reproducir:")
        self.SetTitle(f"Cola de reproducción ({total} {tipo_lbl}{marc_str})")

    def _enfocar_inicial(self):
        if not self.videos_ref:
            self.btn_close.SetFocus()
            return
        target = self.current_index if (self.is_player and 0 <= self.current_index < len(self.videos_ref)) else 0
        if 0 <= target < self.lista_cola.GetItemCount():
            self.lista_cola.Select(target)
            self.lista_cola.Focus(target)
        self.lista_cola.SetFocus()

    def on_item_focused(self, event):
        idx = event.GetIndex()
        if 0 <= idx < len(self.videos_ref):
            v = self.videos_ref[idx]
            raw_tit = v.get('title', 'Sin título')
            for p in ('Marcado - ', '[Vídeo] ', '[Canal] ', '[Lista] '):
                if raw_tit.startswith(p):
                    raw_tit = raw_tit[len(p):]
            canal = v.get('channel', 'Desconocido')
            dur = v.get('duration', '--:--')
            prefix_sel = "Marcado, " if v.get('selected') else ""
            if self.is_player and idx == self.current_index:
                play_str = "En reproducción, "
            else:
                play_str = ""
            accessibility.speak(f"{prefix_sel}{play_str}{idx + 1}: {raw_tit}, {canal}, {dur}")
        event.Skip()

    def on_char_hook(self, event):
        keycode = event.GetKeyCode()
        modifiers = event.GetModifiers()
        ctrl_down = (modifiers == wx.MOD_CONTROL)

        if keycode in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            self.on_eliminar_item(None)
            return
        elif keycode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.on_reproducir_seleccion(None)
            return
        elif keycode == wx.WXK_SPACE:
            self.on_toggle_marca(None)
            return
        elif keycode in (ord('A'), ord('a')) and ctrl_down:
            self.seleccionar_todos(None)
            return
        elif keycode in (ord('C'), ord('c')) and ctrl_down:
            self.on_copiar_enlace(None)
            return
        elif keycode in (ord('B'), ord('b')) and ctrl_down:
            self.on_toggle_favorito(None)
            return
        elif keycode in (ord('D'), ord('d')) and ctrl_down:
            self.on_descargar_seleccion(None)
            return
        elif keycode == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
            return
        event.Skip()

    def on_toggle_marca(self, event=None):
        if not self.videos_ref:
            return
        if len(self.videos_ref) == 1:
            accessibility.speak("Solo hay 1 elemento en la cola; no es necesario marcarlo.")
            return

        sel = self.lista_cola.GetFirstSelected()
        if sel == -1:
            sel = self.lista_cola.GetFocusedItem()
        if sel == -1 or sel >= len(self.videos_ref):
            return

        v = self.videos_ref[sel]
        v['selected'] = not v.get('selected', False)

        raw_tit = v.get('title', 'Sin título')
        for p in ('Marcado - ', '[Vídeo] ', '[Canal] ', '[Lista] '):
            if raw_tit.startswith(p):
                raw_tit = raw_tit[len(p):]
        prefix_sel = "Marcado - " if v['selected'] else ""

        if self.is_player and sel == self.current_index:
            tit_display = f"{prefix_sel}{raw_tit} [Reproduciendo]"
        else:
            tit_display = f"{prefix_sel}{raw_tit}"

        self.lista_cola.SetItem(sel, 1, tit_display)

        estado_str = "Marcado" if v['selected'] else "Desmarcado"
        accessibility.speak(f"{estado_str}: {raw_tit}")

        total = len(self.videos_ref)
        num_sel = sum(1 for x in self.videos_ref if x.get('selected'))
        tipo_lbl = "pistas" if self.is_player else "elementos"
        marc_str = f", {num_sel} marcados" if num_sel > 0 else ""
        self.lbl_info.SetLabel(f"Pistas en la cola ({total}{marc_str}). Pulsa Espacio para marcar, Supr para eliminar o Enter para reproducir:")
        self.SetTitle(f"Cola de reproducción ({total} {tipo_lbl}{marc_str})")

    def seleccionar_todos(self, event=None):
        if not self.videos_ref or len(self.videos_ref) <= 1:
            return
        for v in self.videos_ref:
            v['selected'] = True
        self._poblar_lista()
        total = len(self.videos_ref)
        accessibility.speak(f"Seleccionados todos los {total} elementos de la cola.")

    def deseleccionar_todos(self, event=None):
        if not self.videos_ref:
            return
        for v in self.videos_ref:
            v['selected'] = False
        self._poblar_lista()
        accessibility.speak("Deseleccionados todos los elementos.")

    def invertir_seleccion(self, event=None):
        if not self.videos_ref or len(self.videos_ref) <= 1:
            return
        for v in self.videos_ref:
            v['selected'] = not v.get('selected', False)
        self._poblar_lista()
        accessibility.speak("Selección invertida.")

    def on_context_menu(self, event=None):
        sel = self.lista_cola.GetFirstSelected()
        if sel == -1:
            sel = self.lista_cola.GetFocusedItem()
        if sel == -1 and self.videos_ref:
            sel = 0
            self.lista_cola.Select(0)
            self.lista_cola.Focus(0)
        if sel == -1 or sel >= len(self.videos_ref):
            return

        video = self.videos_ref[sel]
        num_sel = sum(1 for v in self.videos_ref if v.get('selected'))
        hay_multiples = len(self.videos_ref) > 1

        menu = wx.Menu()

        item_play = menu.Append(wx.ID_ANY, "&Reproducir este elemento	Enter")

        lbl_del = f"&Eliminar los {num_sel} elementos marcados de la cola	Supr" if num_sel > 1 else "&Eliminar de la cola	Supr"
        item_del = menu.Append(wx.ID_ANY, lbl_del)

        menu.AppendSeparator()

        vid_id_or_url = video.get('url') or video.get('id', '')
        is_fav = es_favorito(vid_id_or_url)
        fav_label = "&Eliminar de Favoritos	Ctrl+B" if is_fav else "&Añadir a Favoritos	Ctrl+B"
        item_fav = menu.Append(wx.ID_ANY, fav_label)

        lbl_dl = f"&Descargar los {num_sel} vídeos seleccionados	Ctrl+D" if num_sel > 1 else "&Descargar este vídeo	Ctrl+D"
        item_dl = menu.Append(wx.ID_ANY, lbl_dl)
        item_copy = menu.Append(wx.ID_ANY, "&Copiar enlace al portapapeles	Ctrl+C")
        item_desc = menu.Append(wx.ID_ANY, "Ver &descripción del vídeo...")

        menu.AppendSeparator()
        item_toggle = menu.Append(wx.ID_ANY, "&Marcar / Desmarcar elemento (Espacio)")
        item_toggle.Enable(hay_multiples)
        item_sel_all = menu.Append(wx.ID_ANY, "&Seleccionar todos	Ctrl+A")
        item_sel_all.Enable(hay_multiples)
        item_desel_all = menu.Append(wx.ID_ANY, "&Deseleccionar todos")
        item_desel_all.Enable(hay_multiples)
        item_inv_sel = menu.Append(wx.ID_ANY, "&Invertir selección")
        item_inv_sel.Enable(hay_multiples)

        menu.AppendSeparator()
        item_vaciar = menu.Append(wx.ID_ANY, "&Vaciar cola de reproducción")

        self.Bind(wx.EVT_MENU, self.on_reproducir_seleccion, item_play)
        self.Bind(wx.EVT_MENU, self.on_eliminar_item, item_del)
        self.Bind(wx.EVT_MENU, lambda e, v=video: self.on_toggle_favorito(v), item_fav)
        self.Bind(wx.EVT_MENU, lambda e, v=video: self.on_descargar_seleccion(v), item_dl)
        self.Bind(wx.EVT_MENU, lambda e, v=video: self.on_copiar_enlace(v), item_copy)
        self.Bind(wx.EVT_MENU, lambda e, v=video: self.mostrar_descripcion(v), item_desc)
        self.Bind(wx.EVT_MENU, lambda e: self.on_toggle_marca(), item_toggle)
        self.Bind(wx.EVT_MENU, lambda e: self.seleccionar_todos(), item_sel_all)
        self.Bind(wx.EVT_MENU, lambda e: self.deseleccionar_todos(), item_desel_all)
        self.Bind(wx.EVT_MENU, lambda e: self.invertir_seleccion(), item_inv_sel)
        self.Bind(wx.EVT_MENU, self.on_vaciar_cola, item_vaciar)

        self.PopupMenu(menu)
        menu.Destroy()

    def on_copiar_enlace(self, video=None):
        if video is None:
            sel = self.lista_cola.GetFirstSelected()
            if sel == -1:
                sel = self.lista_cola.GetFocusedItem()
            if 0 <= sel < len(self.videos_ref):
                video = self.videos_ref[sel]
        if not video:
            return
        url = video.get('url') or (f"https://www.youtube.com/watch?v={video.get('id')}" if video.get('id') else "")
        if url and wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(url))
            wx.TheClipboard.Close()
            accessibility.speak("Enlace copiado al portapapeles.")

    def mostrar_descripcion(self, video=None):
        if video is None:
            sel = self.lista_cola.GetFirstSelected()
            if sel == -1:
                sel = self.lista_cola.GetFocusedItem()
            if 0 <= sel < len(self.videos_ref):
                video = self.videos_ref[sel]
        if not video:
            return
        main_w = self.GetParent()
        if self.is_player:
            main_w = getattr(self.GetParent(), 'parent', self.GetParent())
        downloader = getattr(main_w, 'downloader', None)
        dlg = DescriptionDialog(self, video, downloader)
        dlg.ShowModal()
        dlg.Destroy()

    def on_toggle_favorito(self, video=None):
        marcados = [v for v in self.videos_ref if v.get('selected')]
        items = marcados if len(marcados) > 1 else ([video] if video else [])
        if not items:
            sel = self.lista_cola.GetFirstSelected()
            if sel == -1:
                sel = self.lista_cola.GetFocusedItem()
            if 0 <= sel < len(self.videos_ref):
                items = [self.videos_ref[sel]]

        if not items:
            return

        if len(items) == 1:
            v = items[0]
            vid_id_or_url = v.get('url') or v.get('id', '')
            tit = v.get('title', 'Vídeo')
            if es_favorito(vid_id_or_url):
                eliminar_favorito(vid_id_or_url)
                accessibility.speak(f"Eliminado de favoritos: {tit}")
            else:
                dlg = SelectFavoriteListDialog(self, tit)
                if dlg.ShowModal() == wx.ID_OK:
                    n_lista = dlg.selected_list_name or "Principal"
                    agregar_favorito(v, nombre_lista=n_lista)
                    accessibility.speak(f"Añadido a favoritos en la lista '{n_lista}': {tit}")
                dlg.Destroy()
        else:
            todos_son_fav = all(es_favorito(v.get('url') or v.get('id', '')) for v in items)
            if todos_son_fav:
                for v in items:
                    eliminar_favorito(v.get('url') or v.get('id', ''))
                    v['selected'] = False
                accessibility.speak(f"{len(items)} elementos eliminados de favoritos.")
            else:
                dlg = SelectFavoriteListDialog(self, f"{len(items)} elementos")
                if dlg.ShowModal() == wx.ID_OK:
                    n_lista = dlg.selected_list_name or "Principal"
                    for v in items:
                        agregar_favorito(v, nombre_lista=n_lista)
                        v['selected'] = False
                    accessibility.speak(f"{len(items)} elementos añadidos a favoritos en la lista '{n_lista}'.")
                dlg.Destroy()
        self._poblar_lista()

    def on_descargar_seleccion(self, video=None):
        marcados = [v for v in self.videos_ref if v.get('selected')]
        items = marcados if len(marcados) > 1 else ([video] if video else [])
        if not items:
            sel = self.lista_cola.GetFirstSelected()
            if sel == -1:
                sel = self.lista_cola.GetFocusedItem()
            if 0 <= sel < len(self.videos_ref):
                items = [self.videos_ref[sel]]

        if not items:
            return

        main_w = self.GetParent()
        if self.is_player:
            main_w = getattr(self.GetParent(), 'parent', self.GetParent())

        if hasattr(main_w, '_agregar_descargas_o_iniciar'):
            main_w._agregar_descargas_o_iniciar(items)
            cant = len(items)
            accessibility.speak(f"{cant} elemento{'s' if cant > 1 else ''} añadido{'s' if cant > 1 else ''} a la cola de descargas.")

    def on_eliminar_item(self, event=None):
        marcados_indices = [idx for idx, v in enumerate(self.videos_ref) if v.get('selected')]
        if not marcados_indices:
            sel = self.lista_cola.GetFirstSelected()
            if sel == -1:
                sel = self.lista_cola.GetFocusedItem()
            if sel != -1 and 0 <= sel < len(self.videos_ref):
                marcados_indices = [sel]

        if not marcados_indices:
            accessibility.speak("No hay ningún elemento seleccionado en la cola.")
            return

        eliminados = []
        for idx in sorted(marcados_indices, reverse=True):
            eliminados.append(self.videos_ref.pop(idx))

        cant_del = len(eliminados)
        titulo_primero = eliminados[-1].get('title', 'Elemento')

        if self.is_player:
            player = self.GetParent()
            if hasattr(player, 'videos'):
                player.videos = self.videos_ref

            if hasattr(player, '_original_videos') and isinstance(player._original_videos, list):
                del_ids = {x.get('url') or x.get('id', '') for x in eliminados}
                player._original_videos = [
                    x for x in player._original_videos
                    if (x.get('url') or x.get('id', '')) not in del_ids
                ]

            main_w = getattr(player, 'parent', None)
            if main_w and hasattr(main_w, 'cola_reproduccion') and isinstance(main_w.cola_reproduccion, list):
                del_ids = {x.get('url') or x.get('id', '') for x in eliminados}
                main_w.cola_reproduccion = [
                    x for x in main_w.cola_reproduccion
                    if (x.get('url') or x.get('id', '')) not in del_ids
                ]
                if hasattr(main_w, 'actualizar_estados_interfaz'):
                    main_w.actualizar_estados_interfaz()

            if self.current_index in marcados_indices:
                if self.videos_ref:
                    if self.current_index >= len(self.videos_ref):
                        self.current_index = 0
                    player.current_index = self.current_index
                    wx.CallAfter(player.load_and_play_current)
                else:
                    self.current_index = 0
                    player.current_index = 0
                    player.stop()
            else:
                menores = sum(1 for idx in marcados_indices if idx < self.current_index)
                self.current_index = max(0, self.current_index - menores)
                player.current_index = self.current_index

            player._update_ui_state()
        else:
            main_w = self.GetParent()
            if hasattr(main_w, 'cola_reproduccion'):
                main_w.cola_reproduccion = self.videos_ref
            if hasattr(main_w, 'actualizar_estados_interfaz'):
                main_w.actualizar_estados_interfaz()
            act_player = getattr(main_w, 'active_preview_dialog', None)
            if act_player and hasattr(act_player, 'videos'):
                del_ids = {x.get('url') or x.get('id', '') for x in eliminados}
                act_player.videos = [
                    x for x in act_player.videos
                    if (x.get('url') or x.get('id', '')) not in del_ids
                ]
                act_player._update_ui_state()

        quedan = len(self.videos_ref)
        tipo_str = "pistas" if self.is_player else "elementos"
        if cant_del == 1:
            if quedan == 1:
                msg = f"Eliminado de la cola: {titulo_primero}. Queda 1 {tipo_str[:-1]}."
            elif quedan == 0:
                msg = f"Eliminado de la cola: {titulo_primero}. La cola de reproducción está vacía."
            else:
                msg = f"Eliminado de la cola: {titulo_primero}. Quedan {quedan} {tipo_str}."
        else:
            if quedan == 1:
                msg = f"Eliminados {cant_del} elementos de la cola. Queda 1 {tipo_str[:-1]}."
            elif quedan == 0:
                msg = f"Eliminados {cant_del} elementos de la cola. La cola de reproducción está vacía."
            else:
                msg = f"Eliminados {cant_del} elementos de la cola. Quedan {quedan} {tipo_str}."

        accessibility.speak(msg)
        self._poblar_lista()

        if quedan > 0:
            target_sel = min(marcados_indices[0], quedan - 1)
            self.lista_cola.Select(target_sel)
            self.lista_cola.Focus(target_sel)
            self.lista_cola.SetFocus()
        else:
            self.btn_close.SetFocus()

    def on_reproducir_seleccion(self, event=None):
        sel = self.lista_cola.GetFirstSelected()
        if sel == -1:
            sel = self.lista_cola.GetFocusedItem()
        if sel == -1 or sel >= len(self.videos_ref):
            accessibility.speak("No hay ningún elemento seleccionado.")
            return

        tit = self.videos_ref[sel].get('title', 'Pista')
        accessibility.speak(f"Reproduciendo: {tit}")

        if self.is_player:
            player = self.GetParent()
            self.current_index = sel
            player.current_index = sel
            player.load_and_play_current()
            self.EndModal(wx.ID_OK)
        else:
            main_w = self.GetParent()
            self.EndModal(wx.ID_OK)
            main_w.reproducir_cola(initial_index=sel)

    def on_vaciar_cola(self, event=None):
        if not self.videos_ref:
            accessibility.speak("La cola ya está vacía.")
            return

        resp = wx.MessageBox(
            "¿Estás seguro de que deseas vaciar todos los elementos de la cola de reproducción?",
            "Confirmar vaciado de cola",
            wx.YES_NO | wx.ICON_QUESTION,
            self
        )
        if resp != wx.YES:
            return

        self.videos_ref.clear()
        if self.is_player:
            player = self.GetParent()
            player.videos = []
            player.current_index = 0
            player.stop()
            player._update_ui_state()
            main_w = getattr(player, 'parent', None)
            if main_w and hasattr(main_w, 'cola_reproduccion'):
                main_w.cola_reproduccion = []
            if main_w and hasattr(main_w, 'actualizar_estados_interfaz'):
                main_w.actualizar_estados_interfaz()
        else:
            main_w = self.GetParent()
            if hasattr(main_w, 'cola_reproduccion'):
                main_w.cola_reproduccion = []
            if hasattr(main_w, 'actualizar_estados_interfaz'):
                main_w.actualizar_estados_interfaz()

        accessibility.speak("Cola de reproducción vaciada.")
        self._poblar_lista()
        self.btn_close.SetFocus()

