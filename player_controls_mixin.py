"""
Mixin de controles de interacción, atajos de teclado y eventos para el reproductor multimedia.
"""

import os
import sys
import threading
import wx

import accessibility
import sound_manager
from config_manager import cargar_configuracion, guardar_configuracion
from media_utils import formatear_duracion, formatear_visitas
import favorites_manager
from favorites_manager import es_favorito, eliminar_favorito, agregar_favorito
from ui_vlc import vlc, get_vlc_module, pedir_confirmacion_eliminar_favorito
from favorites_dialogs import SelectFavoriteListDialog



def _get_ui_func(name, default_val):
    mod = sys.modules.get('ui')
    if mod and hasattr(mod, name):
        return getattr(mod, name)
    return default_val



class PlayerControlsMixin:
    def on_slider_start_drag(self, event):
        self.is_dragging_slider = True
        event.Skip()

    def on_slider_seek(self, event):
        self.is_dragging_slider = False
        if not self.vlc_player:
            return
        val = self.slider_pos.GetValue()
        pos_frac = val / 1000.0
        self.vlc_player.set_position(pos_frac)
        event.Skip()

    def _redirigir_foco_desde_slider_pos(self):
        """Redirige el foco fuera de la barra de progreso si llegase a recibirlo."""
        if hasattr(self, 'btn_play_pause') and self.btn_play_pause:
            self.btn_play_pause.SetFocus()

    def on_volume_change(self, event):
        vol = self.slider_vol.GetValue()
        if self.vlc_player:
            self.vlc_player.audio_set_volume(vol)
        cfg = cargar_configuracion()
        cfg['volumen'] = vol
        guardar_configuracion(cfg)

    def on_toggle_repeat(self, event):
        self.repeat_mode = not self.repeat_mode
        self.btn_repeat.SetLabel(f"Repetición: {'Activada' if self.repeat_mode else 'Desactivada'}")
        estado = "Repetición continua activada." if self.repeat_mode else "Repetición continua desactivada."
        accessibility.speak(estado)
        cfg = cargar_configuracion()
        cfg['repetir_reproductor'] = self.repeat_mode
        guardar_configuracion(cfg)

    def on_toggle_shuffle(self, event=None):
        self.shuffle_mode = not getattr(self, 'shuffle_mode', False)
        self.btn_shuffle.SetLabel(f"Aleatorio: {'Activado' if self.shuffle_mode else 'Desactivado'}")
        estado = "Modo aleatorio activado." if self.shuffle_mode else "Modo aleatorio desactivado."
        accessibility.speak(estado)
        self.lbl_status.SetLabel(estado)
        cfg = cargar_configuracion()
        cfg['aleatorio_reproductor'] = self.shuffle_mode
        guardar_configuracion(cfg)

        if hasattr(self, 'videos') and len(self.videos) > 1:
            import random
            if self.shuffle_mode:
                if not hasattr(self, '_original_videos') or not self._original_videos:
                    self._original_videos = list(self.videos)
                cur_vid = self.video if hasattr(self, 'video') and self.video else self.videos[self.current_index]
                cur_u = cur_vid.get('url') or cur_vid.get('id', '')
                resto = [v for v in self.videos if (v.get('url') or v.get('id', '')) != cur_u]
                random.shuffle(resto)
                self.videos = [cur_vid] + resto
                self.current_index = 0
            else:
                if hasattr(self, '_original_videos') and self._original_videos:
                    cur_vid = self.video if hasattr(self, 'video') and self.video else (self.videos[self.current_index] if self.videos else {})
                    cur_u = cur_vid.get('url') or cur_vid.get('id', '')
                    self.videos = list(self._original_videos)
                    idx_found = 0
                    for i, v in enumerate(self.videos):
                        if (v.get('url') or v.get('id', '')) == cur_u:
                            idx_found = i
                            break
                    self.current_index = idx_found

            if hasattr(self, '_update_ui_state'):
                self._update_ui_state()
            if hasattr(self, '_trigger_prefetch_pipeline'):
                self._trigger_prefetch_pipeline()

    def stop(self, event=None):
        if not self.vlc_player:
            return
        try:
            self.vlc_player.stop()
        except Exception:
            pass
        if hasattr(self, 'timer') and self.timer.IsRunning():
            self.timer.Stop()
        self.slider_pos.SetValue(0)
        self.lbl_time.SetLabel("00:00 / --:--")
        self.btn_play_pause.SetLabel("Reproducir")
        self.lbl_status.SetLabel("Reproducción detenida.")
        accessibility.speak("Detenido.")

    def on_eliminar_favorito(self, event=None):
        if not self.video:
            return
        vid_id_or_url = self.video.get('url') or self.video.get('id', '')
        titulo = self.video.get('title', 'Vídeo')
        _es_fav = _get_ui_func('es_favorito', es_favorito)
        _conf_fav = _get_ui_func('pedir_confirmacion_eliminar_favorito', pedir_confirmacion_eliminar_favorito)
        _del_fav = _get_ui_func('eliminar_favorito', eliminar_favorito)

        if not _es_fav(vid_id_or_url):
            accessibility.speak(f"'{titulo}' no está en la lista de favoritos.")
            self.lbl_status.SetLabel("El elemento actual no está en favoritos.")
            return

        if not _conf_fav(self, titulo):
            return

        _del_fav(vid_id_or_url)
        self.btn_fav.SetLabel("+ Favorito")
        accessibility.speak(f"Eliminado de favoritos: {titulo}")
        self.lbl_status.SetLabel("Eliminado de la lista de favoritos.")

    def on_toggle_favorito(self, event):
        vid_id_or_url = self.video.get('url') or self.video.get('id', '')
        titulo = self.video.get('title', 'Vídeo')
        _es_fav = _get_ui_func('es_favorito', es_favorito)
        _add_fav = _get_ui_func('agregar_favorito', agregar_favorito)
        if _es_fav(vid_id_or_url):
            self.on_eliminar_favorito(None)
        else:
            dlg = SelectFavoriteListDialog(self, titulo)
            if dlg.ShowModal() == wx.ID_OK:
                n_lista = dlg.selected_list_name or "Principal"
                _add_fav(self.video, nombre_lista=n_lista)
                self.btn_fav.SetLabel("En Favoritos")
                accessibility.speak(f"Añadido a favoritos en la lista '{n_lista}': {titulo}")
                self.lbl_status.SetLabel(f"Añadido a favoritos ({n_lista}).")
            dlg.Destroy()


    def anunciar_porcentaje(self):
        """Anuncia al lector de pantalla el porcentaje de reproducción del vídeo (F8)."""
        if not self.vlc_player:
            accessibility.speak("Reproductor no inicializado.")
            return
        length_ms = self.vlc_player.get_length()
        time_ms = self.vlc_player.get_time()
        if length_ms <= 0 or time_ms < 0:
            accessibility.speak("Porcentaje no disponible.")
            return
        percent = int((time_ms / length_ms) * 100)
        percent = min(100, max(0, percent))
        msg = f"{percent} por ciento."
        accessibility.speak(msg)
        self.lbl_status.SetLabel(f"Porcentaje: {percent}%")

    def anunciar_tiempo_transcurrido(self):
        """Anuncia al lector de pantalla el tiempo transcurrido de la reproducción (F9)."""
        if not self.vlc_player:
            accessibility.speak("Reproductor no inicializado.")
            return
        time_ms = self.vlc_player.get_time()
        if time_ms < 0:
            accessibility.speak("Tiempo transcurrido no disponible.")
            return
        cur_sec = int(time_ms / 1000)
        duracion_str = formatear_duracion(cur_sec)
        msg = f"Tiempo transcurrido: {duracion_str}"
        accessibility.speak(msg)
        self.lbl_status.SetLabel(msg)

    def anunciar_tiempo_restante(self):
        """Anuncia al lector de pantalla el tiempo restante de la reproducción (F10)."""
        if not self.vlc_player:
            accessibility.speak("Reproductor no inicializado.")
            return
        length_ms = self.vlc_player.get_length()
        time_ms = self.vlc_player.get_time()
        if length_ms <= 0 or time_ms < 0:
            accessibility.speak("Tiempo restante no disponible.")
            return
        rem_sec = max(0, int((length_ms - time_ms) / 1000))
        duracion_str = formatear_duracion(rem_sec)
        msg = f"Tiempo restante: {duracion_str}"
        accessibility.speak(msg)
        self.lbl_status.SetLabel(msg)

    def copiar_enlace_actual(self, event=None):
        """Copia el enlace del vídeo actual en reproducción al portapapeles (Ctrl+Shift+C o Ctrl+C)."""
        if not self.video:
            accessibility.speak("No hay información del vídeo actual.")
            return
        url = self.video.get('url', '')
        if not url:
            vid_id = self.video.get('id', '')
            if vid_id:
                url = f"https://www.youtube.com/watch?v={vid_id}"
        if not url:
            accessibility.speak("No hay enlace disponible para este vídeo.")
            return
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(url))
            wx.TheClipboard.Close()
            msg = "Enlace del vídeo copiado al portapapeles."
            accessibility.speak(msg)
            self.lbl_status.SetLabel(msg)
        else:
            accessibility.speak("No se pudo acceder al portapapeles.")

    def cambiar_velocidad(self, delta: float):
        """
        Modifica la velocidad de reproducción en incrementos de delta (F6: -0.1, F7: +0.1)
        dentro del rango [0.5, 2.0] y anuncia el nuevo valor al lector de pantalla (ej: '0,8', '1,2').
        """
        vel_actual = getattr(self, 'playback_speed', 1.0)
        nueva_vel = round(vel_actual + delta, 1)
        nueva_vel = max(0.5, min(2.0, nueva_vel))
        self.playback_speed = nueva_vel

        if self.vlc_player:
            try:
                self.vlc_player.set_rate(nueva_vel)
            except Exception:
                pass

        cfg = cargar_configuracion()
        cfg['velocidad_reproduccion'] = nueva_vel
        guardar_configuracion(cfg)

        vel_str = f"{nueva_vel:.1f}".replace('.', ',')
        accessibility.speak(vel_str)
        self.lbl_status.SetLabel(f"Velocidad: {vel_str}x")

    def on_player_activate(self, event):
        if event.GetActive():
            focus = self.FindFocus()
            valid_controls = (
                getattr(self, 'btn_play_pause', None),
                getattr(self, 'btn_prev', None),
                getattr(self, 'btn_next', None),
                getattr(self, 'btn_stop', None),
                getattr(self, 'btn_fav', None),
                getattr(self, 'btn_queue', None),
                getattr(self, 'slider_vol', None),
                getattr(self, 'btn_mute', None),
                getattr(self, 'btn_repeat', None),
                getattr(self, 'btn_shuffle', None),
                getattr(self, 'btn_toggle_video', None),
                getattr(self, 'btn_download_current', None),
                getattr(self, 'btn_copy_url', None),
                getattr(self, 'btn_close', None),
            )
            if not focus or focus not in valid_controls:
                if hasattr(self, 'btn_play_pause') and self.btn_play_pause:
                    wx.CallAfter(self.btn_play_pause.SetFocus)
        event.Skip()

    def on_key_hook(self, event):
        keycode = event.GetKeyCode()
        ctrl_down = event.ControlDown()
        alt_down = event.AltDown()
        shift_down = event.ShiftDown()

        if keycode == wx.WXK_ESCAPE:
            self.on_close_click(None)
            return
        elif ctrl_down and keycode in (ord('C'), ord('c')):
            self.copiar_enlace_actual()
            return
        # La barra espaciadora no se intercepta aquí para permitir accionar
        # con total libertad cualquier botón enfocado en la ventana del reproductor
        elif keycode in (wx.WXK_LEFT, wx.WXK_RIGHT):
            direction = 1 if keycode == wx.WXK_RIGHT else -1
            if ctrl_down and alt_down and shift_down:
                self.seek_relative(300 * direction)
            elif ctrl_down and shift_down and not alt_down:
                self.seek_relative(60 * direction)
            elif shift_down and alt_down and not ctrl_down:
                self.seek_relative(5 * direction)
            elif shift_down and not ctrl_down and not alt_down:
                self.seek_relative(1 * direction)
            elif ctrl_down and not shift_down and not alt_down:
                if keycode == wx.WXK_RIGHT:
                    self.play_next()
                else:
                    self.play_prev()
            elif not ctrl_down and not alt_down and not shift_down:
                self.seek_relative(10 * direction)
            else:
                event.Skip()
        elif keycode == wx.WXK_UP:
            new_vol = min(100, self.slider_vol.GetValue() + 5)
            self.slider_vol.SetValue(new_vol)
            self.on_volume_change(None)
        elif keycode == wx.WXK_DOWN:
            new_vol = max(0, self.slider_vol.GetValue() - 5)
            self.slider_vol.SetValue(new_vol)
            self.on_volume_change(None)
        elif keycode == wx.WXK_F6:
            self.cambiar_velocidad(-0.1)
        elif keycode == wx.WXK_F7:
            self.cambiar_velocidad(0.1)
        elif keycode == wx.WXK_F8:
            self.anunciar_porcentaje()
        elif keycode == wx.WXK_F9:
            self.anunciar_tiempo_transcurrido()
        elif keycode == wx.WXK_F10:
            self.anunciar_tiempo_restante()
        elif keycode == wx.WXK_F11:
            self.toggle_video_display(None)
        elif ctrl_down and keycode in (ord('P'), ord('p')):
            self.play_prev()
        elif ctrl_down and keycode in (ord('N'), ord('n')):
            self.play_next()
        elif keycode in (ord('Q'), ord('q')):
            self.abrir_dialogo_cola()
        elif keycode in (ord('N'), ord('n')) and not ctrl_down:
            self.play_next()
        elif keycode in (ord('P'), ord('p')) and not ctrl_down:
            self.toggle_play_pause(None)
        elif keycode in (ord('S'), ord('s')) and not ctrl_down:
            self.stop(None)
        elif keycode in (ord('A'), ord('a')) and not ctrl_down:
            self.on_toggle_shuffle(None)
        elif keycode in (ord('M'), ord('m')) and not ctrl_down:
            self.toggle_mute(None)
        elif keycode in (ord('R'), ord('r')) and not ctrl_down:
            self.on_toggle_repeat(None)
        elif keycode in (ord('B'), ord('b'), ord('F'), ord('f')) and not ctrl_down:
            self.on_toggle_favorito(None)
        elif keycode in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            self.on_eliminar_favorito(None)
        else:
            event.Skip()

    def abrir_dialogo_cola(self, event=None):
        """Abre la ventana accesible para consultar y gestionar la cola de reproducción (Q)."""
        if len(self.videos) <= 1:
            accessibility.speak("La cola de reproducción está vacía.")
            return
        dlg = ColaReproduccionDialog(self, videos=self.videos, current_index=self.current_index, is_player=True)
        dlg.ShowModal()
        dlg.Destroy()
        self._update_ui_state()

    def toggle_video_display(self, event=None):
        """Activa o desactiva la visualización de la ventana de vídeo (F11)."""
        self.show_video = not self.show_video
        self.video_panel.Show(self.show_video)
        self.Layout()

        cur_pos = self.vlc_player.get_time() if self.vlc_player else 0
        is_playing = False
        if self.vlc_player:
            try:
                is_playing = (self.vlc_player.get_state() == vlc.State.Playing)
            except Exception:
                pass

        if not self.show_video:
            if not self.IsMaximized():
                self.SetSize((920, 260))
            self.btn_toggle_video.SetLabel("Vídeo: Desactivado (F11)")
            msg = "Vídeo desactivado"
            # Detener salida de vídeo y desvincular HWND para evitar ventanas emergentes de Direct3D
            if self.vlc_player and sys.platform.startswith('win'):
                try:
                    self.vlc_player.set_hwnd(0)
                except Exception:
                    pass
            # Recargar media con :no-video para liberar completamente el renderizador de vídeo
            stream_url = getattr(self, '_current_stream_url', None)
            if stream_url and self.vlc_player and self.vlc_instance:
                try:
                    media = self.vlc_instance.media_new(stream_url)
                    media.add_option(':network-caching=300')
                    media.add_option(':no-video')
                    self.vlc_player.set_media(media)
                    if is_playing:
                        self.vlc_player.play()
                        if cur_pos > 0:
                            self.vlc_player.set_time(cur_pos)
                        if hasattr(self, 'playback_speed'):
                            try:
                                self.vlc_player.set_rate(self.playback_speed)
                            except Exception:
                                pass
                except Exception:
                    pass
        else:
            if not self.IsMaximized():
                self.SetSize((920, 680))
            self.btn_toggle_video.SetLabel("Vídeo: Activado (F11)")
            msg = "Vídeo activado"
            if self.vlc_player and sys.platform.startswith('win'):
                try:
                    hwnd = self.video_panel.GetHandle()
                    self.vlc_player.set_hwnd(hwnd)
                except Exception:
                    pass
            # Recargar media sin :no-video para mostrar el vídeo en el panel
            stream_url = getattr(self, '_current_stream_url', None)
            if stream_url and self.vlc_player and self.vlc_instance:
                try:
                    media = self.vlc_instance.media_new(stream_url)
                    media.add_option(':network-caching=300')
                    self.vlc_player.set_media(media)
                    if is_playing:
                        self.vlc_player.play()
                        if cur_pos > 0:
                            self.vlc_player.set_time(cur_pos)
                        if hasattr(self, 'playback_speed'):
                            try:
                                self.vlc_player.set_rate(self.playback_speed)
                            except Exception:
                                pass
                except Exception:
                    pass

        self.lbl_status.SetLabel(msg)
        accessibility.speak(msg)
        if hasattr(self, 'btn_toggle_video') and self.btn_toggle_video:
            wx.CallAfter(self.btn_toggle_video.SetFocus)

    def toggle_play_pause(self, event):
        if not self.vlc_player:
            return
        state = self.vlc_player.get_state()
        if state == vlc.State.Playing:
            self.vlc_player.pause()
            self.btn_play_pause.SetLabel("Reanudar")
            self.lbl_status.SetLabel("Vídeo pausado.")
            accessibility.speak("Pausa.")
        elif state in (vlc.State.Ended, vlc.State.Stopped):
            self.load_and_play_current()
        else:
            self.vlc_player.play()
            self.btn_play_pause.SetLabel("Pausar")
            self.lbl_status.SetLabel("Reproduciendo vídeo.")
            accessibility.speak("Reanudado.")
            if hasattr(self, 'timer') and not self.timer.IsRunning():
                self.timer.Start(500)

    def seek_relative(self, seconds):
        if not self.vlc_player:
            return
        cur_time = self.vlc_player.get_time()
        if cur_time >= 0:
            new_time = max(0, cur_time + (seconds * 1000))
            length_ms = self.vlc_player.get_length()
            if length_ms > 0:
                new_time = min(new_time, length_ms)
            self.vlc_player.set_time(new_time)
            cur_sec = int(new_time / 1000)
            tot_sec = int(length_ms / 1000) if length_ms > 0 else 0
            self.lbl_time.SetLabel(f"{formatear_duracion(cur_sec)} / {formatear_duracion(tot_sec) if tot_sec else '--:--'}")

    def toggle_mute(self, event):
        if not self.vlc_player:
            return
        is_muted = self.vlc_player.audio_get_mute()
        new_mute = not is_muted
        self.vlc_player.audio_set_mute(new_mute)
        if new_mute:
            self.btn_mute.SetLabel("Activar sonido")
            accessibility.speak("Sonido silenciado.")
        else:
            self.btn_mute.SetLabel("Silenciar")
            accessibility.speak("Sonido activado.")

    def on_download_click(self, event):
        if getattr(self, '_is_closing', False):
            return
        self._is_closing = True
        self.wants_download = True
        self.download_target_video = self.video
        self.on_cleanup()
        if self.IsModal():
            self.EndModal(wx.ID_OK)
        else:
            self.Destroy()

    def on_close_click(self, event=None):
        self._is_closing = True
        self.on_cleanup()
        parent = self.GetParent()
        if hasattr(parent, 'active_preview_dialog') and parent.active_preview_dialog is self:
            parent.active_preview_dialog = None
        if hasattr(parent, '_procesar_descarga_desde_reproductor'):
            parent._procesar_descarga_desde_reproductor(self)
        if hasattr(parent, '_sincronizar_vista_favoritos_tras_reproduccion'):
            parent._sincronizar_vista_favoritos_tras_reproduccion()
        if self.IsModal():
            self.EndModal(wx.ID_CANCEL)
        else:
            self.Destroy()

    def on_window_close(self, event):
        self._is_closing = True
        self.on_cleanup()
        parent = self.GetParent()
        if hasattr(parent, 'active_preview_dialog') and parent.active_preview_dialog is self:
            parent.active_preview_dialog = None
        if hasattr(parent, '_procesar_descarga_desde_reproductor'):
            parent._procesar_descarga_desde_reproductor(self)
        if hasattr(parent, '_sincronizar_vista_favoritos_tras_reproduccion'):
            parent._sincronizar_vista_favoritos_tras_reproduccion()
        if self.IsModal():
            self.EndModal(wx.ID_CANCEL)
        else:
            self.Destroy()

    def on_cleanup(self):
        self._is_closing = True
        if getattr(self, '_cleanup_done', False):
            return
        self._cleanup_done = True

        if hasattr(self, 'timer') and self.timer.IsRunning():
            self.timer.Stop()

        if hasattr(self, '_prefetch_timer') and self._prefetch_timer and self._prefetch_timer.IsRunning():
            self._prefetch_timer.Stop()

        p = getattr(self, 'vlc_player', None)
        self.vlc_player = None
        inst = getattr(self, 'vlc_instance', None)
        self.vlc_instance = None

        if p and sys.platform.startswith('win'):
            try:
                p.set_hwnd(0)
            except Exception:
                pass

        if p or inst:
            def _cleanup_vlc(player, instance):
                if player:
                    try:
                        cur_st = player.get_state()
                        if vlc and cur_st not in (vlc.State.Ended, vlc.State.Stopped):
                            player.stop()
                    except Exception:
                        pass
                    try:
                        player.release()
                    except Exception:
                        pass
                if instance:
                    try:
                        instance.release()
                    except Exception:
                        pass

            t = threading.Thread(target=_cleanup_vlc, args=(p, inst), daemon=True)
            t.start()
            t.join(timeout=0.1)

