"""
Mixin de previsualización y gestión de cola de reproducción para MainFrame.
"""

import sys
import wx

import accessibility
from favorites_manager import obtener_favoritos, detectar_tipo_elemento
from player_dialog import VideoPreviewDialog
from queue_dialog import ColaReproduccionDialog


def _get_preview_dialog_cls():
    mod = sys.modules.get('ui')
    if mod and hasattr(mod, 'VideoPreviewDialog'):
        return getattr(mod, 'VideoPreviewDialog')
    return VideoPreviewDialog



class MainPlaybackMixin:
    def on_previsualizar_video(self, event):
        # 1. Si hay elementos marcados con espacio (checkboxes), reproducir esos en secuencia continua
        marcados = [r for r in self.resultados if r.get('selected') and not r.get('is_playlist')]
        
        if marcados:
            videos_to_play = marcados
            initial_idx = 0
        else:
            # 2. Si no hay marcados, reproducir desde el elemento enfocado
            video_sel = self._get_selected_video()
            if not video_sel:
                wx.MessageBox(
                    "Por favor, selecciona primero un vídeo de la lista para reproducir.",
                    "Ningún vídeo seleccionado",
                    wx.OK | wx.ICON_INFORMATION,
                    self
                )
                self.lista_resultados.SetFocus()
                return

            if video_sel.get('is_playlist'):
                self.ejecutar_busqueda_playlist_videos(video_sel['url'])
                return

            videos_to_play = [video_sel]
            initial_idx = 0


        titulo = videos_to_play[initial_idx].get('title', 'Vídeo')
        self.set_status(f"Abriendo reproductor continuo para '{titulo}'...", field=0, announce=False)
        
        dlg = _get_preview_dialog_cls()(self, videos_to_play, initial_index=initial_idx)
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
                destino = getattr(self, 'destino_descarga_actual', self.destino_dir)
                self._iniciar_siguiente_descarga_cola(formato_str, destino)
            else:
                self.on_btn_descargar(None)
        else:
            self.set_status("Reproductor cerrado.", field=0, announce=False)

    def reproducir_toda_la_lista(self, event):
        todos_videos = [r for r in self.resultados if not r.get('is_playlist') and not r.get('is_channel')]
        if not todos_videos:
            wx.MessageBox("No hay vídeos disponibles en la lista para reproducir.", "Lista vacía", wx.OK | wx.ICON_INFORMATION, self)
            return

        self.set_status(f"Iniciando reproducción continua de toda la lista ({len(todos_videos)} vídeos)...", field=0, announce=True)
        dlg = _get_preview_dialog_cls()(self, todos_videos, initial_index=0)
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

    def agregar_a_cola_reproduccion(self, event=None, items=None):
        """Añade los elementos seleccionados o activos a la cola de reproducción secuencial."""
        if not self.verificar_libreria_ytdlp():
            return

        if items is None:
            marcados = [r for r in self.resultados if r.get('selected')]
            if not marcados:
                activo = self._get_selected_video()
                if activo:
                    marcados = [activo]

            if not marcados:
                accessibility.speak("No hay ningún elemento seleccionado para añadir a la cola.")
                self.set_status("No hay ningún elemento seleccionado para añadir a la cola.", field=0, announce=False)
                return

            elementos_a_procesar = []
            for m in marcados:
                if m.get('is_fav_list'):
                    favs = obtener_favoritos(nombre_lista=m.get('list_name'))
                    vids = [f for f in favs if detectar_tipo_elemento(f) == 'video']
                    elementos_a_procesar.extend(vids)
                elif m.get('is_playlist') or m.get('is_channel'):
                    u = m.get('url', '')
                    if not u and m.get('id'):
                        u = f"https://www.youtube.com/playlist?list={m.get('id')}" if m.get('is_playlist') else f"https://www.youtube.com/{m.get('id')}"
                    if u:
                        if m.get('is_channel'):
                            vids = self.downloader.buscar_canal_videos(u, max_results=200)
                        else:
                            vids = self.downloader.buscar_playlist_videos(u, max_results=200)
                        if vids:
                            elementos_a_procesar.extend(vids)
                else:
                    elementos_a_procesar.append(m)
        else:
            elementos_a_procesar = items

        videos_validos = [v for v in elementos_a_procesar if not v.get('is_channel') and not v.get('is_playlist') and not v.get('is_fav_list')]

        if not videos_validos:
            accessibility.speak("No se encontraron vídeos reproducibles para añadir a la cola.")
            return

        reproductor_activo = getattr(self, 'active_preview_dialog', None)
        if reproductor_activo and hasattr(reproductor_activo, 'agregar_a_cola'):
            try:
                total_en_reproductor = reproductor_activo.agregar_a_cola(videos_validos)
                self.cola_reproduccion.extend(videos_validos)
                if len(videos_validos) == 1:
                    tit = videos_validos[0].get('title', 'Vídeo')
                    accessibility.speak(f"Añadido a la cola de reproducción: {tit}. Total en cola: {total_en_reproductor}.")
                else:
                    accessibility.speak(f"Añadidos {len(videos_validos)} elementos a la cola de reproducción. Total en cola: {total_en_reproductor}.")
                self.set_status(f"Añadidos {len(videos_validos)} elemento(s) a la cola de reproducción (Total: {total_en_reproductor}).", field=0, announce=False)
                return
            except Exception:
                self.active_preview_dialog = None

        self.cola_reproduccion.extend(videos_validos)
        total_acum = len(self.cola_reproduccion)
        if hasattr(self, 'actualizar_estados_interfaz'):
            self.actualizar_estados_interfaz()
        if len(videos_validos) == 1:
            tit = videos_validos[0].get('title', 'Vídeo')
            accessibility.speak(f"Añadido a la cola de reproducción: {tit}. Total en cola: {total_acum}.")
        else:
            accessibility.speak(f"Añadidos {len(videos_validos)} elementos a la cola de reproducción. Total en cola: {total_acum}.")
        self.set_status(f"Añadidos {len(videos_validos)} elemento(s) a la cola de reproducción (Total: {total_acum}).", field=0, announce=False)


    def reproducir_cola(self, event=None, initial_index=0):
        """Inicia la reproducción continua y secuencial de todos los elementos acumulados en la cola."""
        if not self.verificar_libreria_ytdlp():
            return

        reproductor_activo = getattr(self, 'active_preview_dialog', None)
        if reproductor_activo:
            try:
                if 0 <= initial_index < len(reproductor_activo.videos):
                    reproductor_activo.current_index = initial_index
                    reproductor_activo.load_and_play_current()
                reproductor_activo.Raise()
                reproductor_activo.SetFocus()
                accessibility.speak(f"El reproductor ya está abierto con {len(reproductor_activo.videos)} elementos en la cola.")
                return
            except Exception:
                self.active_preview_dialog = None

        if not self.cola_reproduccion:
            wx.MessageBox(
                "La cola de reproducción está vacía.\n\n"
                "Para añadir elementos de cualquier lista de favoritos o búsqueda, selecciónalos y pulsa Ctrl+Q o usa el menú contextual.",
                "Cola de reproducción vacía",
                wx.OK | wx.ICON_INFORMATION,
                self
            )
            accessibility.speak("Cola de reproducción vacía. Usa Control Q para añadir elementos.")
            return

        total = len(self.cola_reproduccion)
        self.set_status(f"Iniciando reproducción continua de la cola ({total} elementos)...", field=0, announce=True)
        idx_ini = max(0, min(initial_index, len(self.cola_reproduccion) - 1)) if self.cola_reproduccion else 0
        dlg = _get_preview_dialog_cls()(self, list(self.cola_reproduccion), initial_index=idx_ini)
        self.active_preview_dialog = dlg

        if hasattr(dlg, 'ShowModal') and not hasattr(dlg, 'Show'):
            try:
                dlg.ShowModal()
                self._procesar_descarga_desde_reproductor(dlg)
            finally:
                self.active_preview_dialog = None
        else:
            dlg.Show()

    def vaciar_cola_reproduccion(self, event=None):
        """Vacía los elementos acumulados en la cola de reproducción secuencial."""
        self.cola_reproduccion = []
        reproductor_activo = getattr(self, 'active_preview_dialog', None)
        if reproductor_activo and hasattr(reproductor_activo, 'videos'):
            try:
                cur_idx = getattr(reproductor_activo, 'current_index', 0)
                if 0 <= cur_idx < len(reproductor_activo.videos):
                    reproductor_activo.videos = [reproductor_activo.videos[cur_idx]]
                    reproductor_activo.current_index = 0
                    reproductor_activo._update_ui_state()
            except Exception:
                pass
        if hasattr(self, 'actualizar_estados_interfaz'):
            self.actualizar_estados_interfaz()
        accessibility.speak("Cola de reproducción vaciada.")
        self.set_status("Cola de reproducción vaciada.", field=0, announce=False)


    def mostrar_dialogo_cola(self, event=None):
        """Abre la ventana accesible para consultar y gestionar la cola de reproducción (Ctrl+J)."""
        reproductor_activo = getattr(self, 'active_preview_dialog', None)
        if reproductor_activo and hasattr(reproductor_activo, 'videos') and reproductor_activo.videos:
            reproductor_activo.abrir_dialogo_cola()
            return

        if not self.cola_reproduccion:
            wx.MessageBox(
                "La cola de reproducción está vacía.\n\n"
                "Para añadir elementos de cualquier lista de favoritos o búsqueda, selecciónalos y pulsa Ctrl+Q o usa el menú contextual.",
                "Cola de reproducción vacía",
                wx.OK | wx.ICON_INFORMATION,
                self
            )
            accessibility.speak("Cola de reproducción vacía. Usa Control Q para añadir elementos.")
            return

        dlg = ColaReproduccionDialog(self, videos=self.cola_reproduccion, current_index=0, is_player=False)
        dlg.ShowModal()
        dlg.Destroy()

