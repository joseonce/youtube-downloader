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
from ui_mpv import pedir_confirmacion_eliminar_favorito
from favorites_dialogs import SelectFavoriteListDialog



def _get_ui_func(name, default_val):
    mod = sys.modules.get('ui')
    if mod and hasattr(mod, name):
        return getattr(mod, name)
    return default_val



class MPVPlayerCompatFacade:
    """Fachada de compatibilidad para código o pruebas que consulten la interfaz tipo VLC."""
    def __init__(self, mpv_player=None):
        self._mpv = mpv_player

    def get_time(self):
        if not self._mpv:
            return 0
        try:
            t = self._mpv.time_pos
            return int(t * 1000) if t is not None else 0
        except Exception:
            return 0

    def set_time(self, ms):
        if self._mpv:
            try:
                self._mpv.time_pos = max(0.0, ms / 1000.0)
            except Exception:
                pass

    def get_length(self):
        if not self._mpv:
            return 0
        try:
            d = self._mpv.duration
            return int(d * 1000) if d is not None else 0
        except Exception:
            return 0

    def get_state(self):
        class _State:
            NothingSpecial = 0
            Opening = 1
            Buffering = 2
            Playing = 3
            Paused = 4
            Stopped = 5
            Ended = 6
            Error = 7
        if not self._mpv:
            return _State.Stopped
        try:
            if getattr(self._mpv, 'idle_active', False) or self._mpv.time_pos is None:
                return _State.Stopped
            if getattr(self._mpv, 'pause', False):
                return _State.Paused
            return _State.Playing
        except Exception:
            return _State.Stopped

    def play(self):
        if self._mpv:
            try:
                self._mpv.pause = False
            except Exception:
                pass

    def pause(self):
        if self._mpv:
            try:
                self._mpv.pause = True
            except Exception:
                pass

    def stop(self):
        if self._mpv:
            try:
                self._mpv.stop()
            except Exception:
                pass

    def set_rate(self, r):
        if self._mpv:
            try:
                self._mpv.speed = float(r)
            except Exception:
                pass

    def audio_set_volume(self, v):
        if self._mpv:
            try:
                self._mpv.volume = float(v)
            except Exception:
                pass

    def audio_get_mute(self):
        if self._mpv:
            try:
                return bool(getattr(self._mpv, 'mute', False))
            except Exception:
                pass
        return False

    def audio_set_mute(self, m):
        if self._mpv:
            try:
                self._mpv.mute = bool(m)
            except Exception:
                pass

    def set_position(self, pos):
        if self._mpv:
            try:
                dur = self._mpv.duration
                if dur:
                    self._mpv.time_pos = pos * dur
            except Exception:
                pass

    def set_hwnd(self, hwnd):
        if self._mpv:
            try:
                if hwnd:
                    self._mpv.wid = int(hwnd)
            except Exception:
                pass

    def audio_output_device_set(self, _, dev_id):
        if self._mpv:
            try:
                from ui_mpv import resolve_mpv_audio_device
                self._mpv['audio-device'] = resolve_mpv_audio_device(dev_id, player=self._mpv)
            except Exception:
                try:
                    self._mpv['audio-device'] = 'auto'
                except Exception:
                    pass

    def set_media(self, _):
        pass

    def release(self):
        pass


class PlayerControlsMixin:
    def on_slider_start_drag(self, event):
        self.is_dragging_slider = True
        event.Skip()

    def on_slider_seek(self, event):
        self.is_dragging_slider = False
        val = self.slider_pos.GetValue()
        pos_frac = val / 1000.0
        mp = getattr(self, 'mpv_player', None)
        if mp:
            try:
                dur = getattr(mp, 'duration', None)
                if dur:
                    mp.time_pos = pos_frac * dur
            except Exception:
                pass
        event.Skip()

    def _redirigir_foco_desde_slider_pos(self):
        """Redirige el foco fuera de la barra de progreso si llegase a recibirlo."""
        if hasattr(self, 'btn_play_pause') and self.btn_play_pause:
            self.btn_play_pause.SetFocus()

    def on_volume_change(self, event):
        vol = self.slider_vol.GetValue()
        mp = getattr(self, 'mpv_player', None)
        if mp:
            try:
                mp.volume = float(vol)
            except Exception:
                pass
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
        mp = getattr(self, 'mpv_player', None)
        if mp:
            try:
                mp.stop()
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
        if hasattr(self, 'btn_fav') and self.btn_fav:
            self.btn_fav.SetLabel("Añadir a favoritos (F)")
        accessibility.speak(f"Eliminado de favoritos: {titulo}")
        self.lbl_status.SetLabel("Eliminado de la lista de favoritos.")

    def on_toggle_favorito(self, event=None):
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
                if hasattr(self, 'btn_fav') and self.btn_fav:
                    self.btn_fav.SetLabel("Eliminar de favoritos (F)")
                accessibility.speak(f"Añadido a favoritos en la lista '{n_lista}': {titulo}")
                self.lbl_status.SetLabel(f"Añadido a favoritos ({n_lista}).")
            dlg.Destroy()


    def anunciar_porcentaje(self):
        """Anuncia al lector de pantalla el porcentaje de reproducción del vídeo (F8)."""
        mp = getattr(self, 'mpv_player', None)
        length_s = 0
        time_s = 0
        if mp:
            try:
                dur = getattr(mp, 'duration', None)
                if dur and dur > 0:
                    length_s = float(dur)
                pos = getattr(mp, 'time_pos', None)
                if pos is not None and pos >= 0:
                    time_s = float(pos)
            except Exception:
                pass

        vp = getattr(self, 'vlc_player', None)
        if vp and length_s <= 0:
            try:
                l_ms = getattr(vp, 'get_length', lambda: 0)() or 0
                t_ms = getattr(vp, 'get_time', lambda: 0)() or 0
                if l_ms > 0:
                    length_s = float(l_ms) / 1000.0
                    time_s = max(0.0, float(t_ms) / 1000.0)
            except Exception:
                pass

        if length_s <= 0 and hasattr(self, 'video') and self.video:
            length_s = float(self.video.get('duration_seconds') or 0)
            if length_s <= 0 and self.video.get('duration'):
                try:
                    parts = [int(p) for p in self.video['duration'].split(':')]
                    if len(parts) == 2:
                        length_s = float(parts[0] * 60 + parts[1])
                    elif len(parts) == 3:
                        length_s = float(parts[0] * 3600 + parts[1] * 60 + parts[2])
                except Exception:
                    pass

        if length_s <= 0:
            accessibility.speak("Porcentaje no disponible.")
            return

        percent = int((time_s / length_s) * 100)
        percent = min(100, max(0, percent))
        msg = f"{percent} por ciento."
        accessibility.speak(msg)
        self.lbl_status.SetLabel(f"Porcentaje: {percent}%")

    def anunciar_tiempo_transcurrido(self):
        """Anuncia al lector de pantalla el tiempo transcurrido de la reproducción (F9)."""
        mp = getattr(self, 'mpv_player', None)
        cur_sec = -1
        if mp:
            try:
                t = getattr(mp, 'time_pos', None)
                if t is not None and t >= 0:
                    cur_sec = int(t)
                elif getattr(mp, 'idle_active', False) is False and getattr(mp, 'duration', None):
                    cur_sec = 0
            except Exception:
                pass

        if cur_sec < 0 and getattr(self, 'vlc_player', None):
            try:
                t = self.vlc_player.get_time()
                if t >= 0:
                    cur_sec = int(t / 1000)
            except Exception:
                pass

        if cur_sec < 0:
            accessibility.speak("Tiempo transcurrido no disponible.")
            return

        duracion_str = formatear_duracion(cur_sec)
        msg = f"Tiempo transcurrido: {duracion_str}"
        accessibility.speak(msg)
        self.lbl_status.SetLabel(msg)

    def anunciar_tiempo_restante(self):
        """Anuncia al lector de pantalla el tiempo restante de la reproducción (F10)."""
        mp = getattr(self, 'mpv_player', None)
        length_s = 0
        time_s = 0
        if mp:
            try:
                dur = getattr(mp, 'duration', None)
                if dur and dur > 0:
                    length_s = float(dur)
                pos = getattr(mp, 'time_pos', None)
                if pos is not None and pos >= 0:
                    time_s = float(pos)
            except Exception:
                pass

        vp = getattr(self, 'vlc_player', None)
        if vp and length_s <= 0:
            try:
                l_ms = getattr(vp, 'get_length', lambda: 0)() or 0
                t_ms = getattr(vp, 'get_time', lambda: 0)() or 0
                if l_ms > 0:
                    length_s = float(l_ms) / 1000.0
                    time_s = max(0.0, float(t_ms) / 1000.0)
            except Exception:
                pass

        if length_s <= 0 and hasattr(self, 'video') and self.video:
            length_s = float(self.video.get('duration_seconds') or 0)
            if length_s <= 0 and self.video.get('duration'):
                try:
                    parts = [int(p) for p in self.video['duration'].split(':')]
                    if len(parts) == 2:
                        length_s = float(parts[0] * 60 + parts[1])
                    elif len(parts) == 3:
                        length_s = float(parts[0] * 3600 + parts[1] * 60 + parts[2])
                except Exception:
                    pass

        if length_s <= 0:
            accessibility.speak("Tiempo restante no disponible.")
            return

        rem_sec = max(0, int(length_s - time_s))
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

        mp = getattr(self, 'mpv_player', None)
        if mp:
            try:
                mp.speed = float(nueva_vel)
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

        mp = getattr(self, 'mpv_player', None)
        if not self.show_video:
            if not self.IsMaximized():
                self.SetSize((920, 260))
            self.btn_toggle_video.SetLabel("Vídeo: Desactivado (F11)")
            msg = "Vídeo desactivado"
            if mp:
                try:
                    mp.vid = 'no'
                except Exception:
                    pass
        else:
            if not self.IsMaximized():
                self.SetSize((920, 680))
            self.btn_toggle_video.SetLabel("Vídeo: Activado (F11)")
            msg = "Vídeo activado"
            if mp:
                try:
                    mp.vid = 'auto'
                except Exception:
                    pass

        self.lbl_status.SetLabel(msg)
        accessibility.speak(msg)
        if hasattr(self, 'btn_toggle_video') and self.btn_toggle_video:
            wx.CallAfter(self.btn_toggle_video.SetFocus)

    def toggle_play_pause(self, event):
        mp = getattr(self, 'mpv_player', None)
        if mp:
            try:
                is_paused = getattr(mp, 'pause', False)
                if not is_paused:
                    mp.pause = True
                    self.btn_play_pause.SetLabel("Reanudar")
                    self.lbl_status.SetLabel("Vídeo pausado.")
                    accessibility.speak("Pausa.")
                else:
                    mp.pause = False
                    self.btn_play_pause.SetLabel("Pausar")
                    self.lbl_status.SetLabel("Reproduciendo vídeo.")
                    accessibility.speak("Reanudado.")
                    if hasattr(self, 'timer') and not self.timer.IsRunning():
                        self.timer.Start(500)
                return
            except Exception:
                pass

    def seek_relative(self, seconds):
        mp = getattr(self, 'mpv_player', None)
        if mp:
            try:
                mp.seek(seconds, reference='relative')
                cur_sec = int(mp.time_pos or 0)
                tot_sec = int(mp.duration or 0)
                self.lbl_time.SetLabel(f"{formatear_duracion(cur_sec)} / {formatear_duracion(tot_sec) if tot_sec else '--:--'}")
                return
            except Exception:
                pass

    def toggle_mute(self, event):
        mp = getattr(self, 'mpv_player', None)
        if mp:
            try:
                is_muted = getattr(mp, 'mute', False)
                new_mute = not is_muted
                mp.mute = new_mute
                if new_mute:
                    self.btn_mute.SetLabel("Activar sonido")
                    accessibility.speak("Sonido silenciado.")
                else:
                    self.btn_mute.SetLabel("Silenciar")
                    accessibility.speak("Sonido activado.")
                return
            except Exception:
                pass

    def on_download_click(self, event):
        if getattr(self, '_is_closing', False):
            return
        self._is_closing = True
        self.wants_download = True
        self.download_target_video = self.video
        self.on_cleanup()
        parent = self.GetParent()
        if hasattr(parent, 'active_preview_dialog') and parent.active_preview_dialog is self:
            parent.active_preview_dialog = None
        if hasattr(parent, '_procesar_descarga_desde_reproductor'):
            parent._procesar_descarga_desde_reproductor(self)
        if hasattr(parent, '_sincronizar_vista_favoritos_tras_reproduccion'):
            parent._sincronizar_vista_favoritos_tras_reproduccion()
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

        mp = getattr(self, 'mpv_player', None)
        self.mpv_player = None

        if mp:
            def _cleanup_mpv(player):
                try:
                    player.stop()
                except Exception:
                    pass
                try:
                    player.terminate()
                except Exception:
                    pass

            t = threading.Thread(target=_cleanup_mpv, args=(mp,), daemon=True)
            t.start()
            t.join(timeout=0.1)

