"""
Mixin de descargas y cola de procesamiento para MainFrame.
"""

import os
import sys
import threading
import time
import wx

import re

import accessibility
import sound_manager
from config_manager import cargar_configuracion
from media_utils import limpiar_caracteres_ansi, limpiar_extension_titulo
from ui_vlc import mostrar_notificacion_bandeja

FORMATOS_MAP = {
    0: 'video_best',
    1: 'audio_mp3_192',
    2: 'audio_mp3_320',
    3: 'audio_m4a'
}


class MainDownloadMixin:
    def iniciar_sonido_espera(self):
        """Inicia el sonido de espera periódico si está habilitado en las preferencias."""
        cfg = getattr(self, 'config', {}) or {}
        if cfg.get('sonido_espera_descarga', True):
            sound_manager.start_waiting_sound(interval=2.0)

    def detener_sonido_espera(self):
        """Detiene de forma segura el sonido de espera."""
        sound_manager.stop_waiting_sound()

    def sugerir_nombre_subcarpeta(self, seleccionados):
        """
        Determina el nombre sugerido para la subcarpeta de descargas múltiples:
        - Si los vídeos pertenecen a una lista (favoritos, playlist de YouTube, etc.): nombre de la lista.
        - Si no pertenecen a una lista: nombre del canal (o del primer canal si difieren).
        - Si no se puede determinar canal ni lista: término de búsqueda (si no es URL) o 'Descargas'.
        """
        es_url = lambda s: bool(s and (s.startswith('http://') or s.startswith('https://') or s.startswith('www.')))

        # 1. Pertenecen a una lista de favoritos
        if getattr(self, 'is_showing_favorites', False):
            fav_nombre = getattr(self, 'current_fav_name', None) or "Favoritos"
            if fav_nombre == "Todas las listas":
                fav_nombre = "Favoritos"
            return fav_nombre

        # 2. Pertenecen a una lista de YouTube (playlist, ver más tarde, historial)
        kind = getattr(self, 'last_search_kind', '')
        pl_title = getattr(self, 'current_playlist_title', '').strip()
        if kind == 'playlist_videos' or pl_title:
            if pl_title and not es_url(pl_title):
                return pl_title
            return "Lista de reproducción"

        if kind == 'ver_mas_tarde':
            return "Ver más tarde"
        if kind == 'historial':
            return "Historial"

        # 3. No pertenecen a una lista -> nombre del canal
        ch_title = getattr(self, 'current_channel_title', '').strip()
        if ch_title and not es_url(ch_title) and ch_title != 'Canal':
            return ch_title

        canales = [r.get('channel') for r in (seleccionados or []) if r.get('channel') and r.get('channel') not in ('Desconocido', 'Canal')]
        if canales:
            return canales[0].strip()

        # 4. Fallback: término de búsqueda si no es URL
        query = (getattr(self, 'last_search_query', '') or '').strip()
        if query and not es_url(query):
            return query

        return "Descargas"

    def _descargar_contenedores(self, contenedores):
        """Descarga todos los vídeos de los canales o listas de reproducción indicados."""
        if not contenedores:
            return

        primer_cont = contenedores[0]
        titulo_cont = primer_cont.get('title') or primer_cont.get('channel') or "Descargas"
        tipo_nombre = "canal" if primer_cont.get('is_channel') else "lista de reproducción"

        self.btn_descargar.Enable(False)
        self.btn_buscar.Enable(False)
        msg_esp = f"Obteniendo vídeos de {tipo_nombre} '{titulo_cont}' para descargar..."
        self.set_status(msg_esp, field=0, announce=True)
        self.lbl_progreso_detalle.SetLabel(f"Obteniendo lista completa de vídeos de {tipo_nombre}...")
        self.iniciar_sonido_espera()

        def _worker():
            todos_videos = []
            nombre_subcarpeta = titulo_cont
            try:
                for c in contenedores:
                    u = c.get('url', '')
                    if not u and c.get('id'):
                        u = f"https://www.youtube.com/playlist?list={c.get('id')}" if c.get('is_playlist') else f"https://www.youtube.com/{c.get('id')}"
                    if not u:
                        continue
                    if c.get('is_channel'):
                        vids = self.downloader.buscar_canal_videos(u, max_results=1000)
                    else:
                        vids = self.downloader.buscar_playlist_videos(u, max_results=1000)
                    if vids:
                        todos_videos.extend(vids)
                        if not nombre_subcarpeta and getattr(self.downloader, 'last_container_title', ''):
                            nombre_subcarpeta = self.downloader.last_container_title
                
                wx.CallAfter(self._on_contenedores_extraidos, todos_videos, nombre_subcarpeta)
            except Exception as e:
                wx.CallAfter(self._on_contenedores_error, str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_contenedores_error(self, err_msg):
        self.detener_sonido_espera()
        self.btn_descargar.Enable(True)
        self.btn_buscar.Enable(True)
        self.set_status("Error al obtener los vídeos para descargar.", field=0, announce=True)
        wx.MessageBox(f"No se pudieron obtener los vídeos para descargar:\n\n{err_msg}", "Error", wx.OK | wx.ICON_ERROR, self)

    def _on_contenedores_extraidos(self, videos, sugerencia_subcarpeta):
        self.detener_sonido_espera()
        self.btn_descargar.Enable(True)
        self.btn_buscar.Enable(True)
        if not videos:
            wx.MessageBox("No se encontraron vídeos disponibles en este canal o lista para descargar.", "Sin vídeos", wx.OK | wx.ICON_INFORMATION, self)
            self.set_status("No se encontraron vídeos para descargar.", field=0, announce=True)
            return

        user_home = os.path.expanduser("~")
        default_downloads = os.path.join(user_home, "Downloads") if os.path.exists(os.path.join(user_home, "Downloads")) else user_home
        carpeta_base = (getattr(self, 'destino_dir', '') or '').strip() or default_downloads
        destino_final = carpeta_base

        sugerencia_limpia = re.sub(r'[\\/*?:"<>|]', '', sugerencia_subcarpeta).strip().rstrip('. ')
        if not sugerencia_limpia:
            sugerencia_limpia = "Descargas"

        cant_str = f"{len(videos)} vídeos"
        msg = (
            f"Vas a descargar {cant_str} de '{sugerencia_subcarpeta}'.\n\n"
            f"Carpeta base predeterminada:\n{carpeta_base}\n\n"
            f"Introduce el nombre de la subcarpeta donde deseas guardarlos\n"
            f"(o deja este campo vacío para guardarlos directamente en la carpeta base):"
        )

        accessibility.speak("Introduce el nombre de la subcarpeta para guardar los vídeos o pulsa Escape para cancelar.")
        dlg = wx.TextEntryDialog(
            self,
            msg,
            caption="Organizar descargas en subcarpeta",
            value=sugerencia_limpia
        )
        res_dlg = dlg.ShowModal()
        subcarpeta_val = dlg.GetValue().strip()
        dlg.Destroy()

        if res_dlg != wx.ID_OK:
            self.set_status("Descarga cancelada por el usuario.", field=0, announce=True)
            return

        if subcarpeta_val:
            subcarpeta_limpia = re.sub(r'[\\/*?:"<>|]', '', subcarpeta_val).strip().rstrip('. ')
            if subcarpeta_limpia:
                destino_final = os.path.join(carpeta_base, subcarpeta_limpia)

        if not os.path.exists(destino_final):
            try:
                os.makedirs(destino_final, exist_ok=True)
            except Exception as e:
                wx.MessageBox(f"Error con la carpeta de destino:\n{e}", "Error", wx.OK | wx.ICON_ERROR, self)
                return

        self.destino_descarga_actual = destino_final

        sel_format_idx = self.choice_formato.GetSelection()
        if sel_format_idx < 0:
            sel_format_idx = 0
            self.choice_formato.SetSelection(0)
        formato_str = FORMATOS_MAP.get(sel_format_idx, 'video_best')

        self.cola_descargas = list(videos)
        self.total_cola = len(self.cola_descargas)
        self.indice_cola = 0
        self.descargas_completadas = 0
        self.descargas_fallidas = 0
        self.ultimo_error_descarga = ""

        self.btn_descargar.Enable(False)
        self.btn_cancelar.Enable(True)
        self.btn_buscar.Enable(False)
        self.gauge_progreso.SetValue(0)
        self.last_announced_percent = -1

        self.iniciar_sonido_espera()
        self._iniciar_siguiente_descarga_cola(formato_str, self.destino_descarga_actual)

    def on_btn_descargar(self, event):
        if not self.verificar_libreria_ytdlp():
            return

        # 1. Comprobar si hay canales o playlists seleccionados o como elemento activo
        contenedores = [r for r in self.resultados if r.get('selected') and (r.get('is_channel') or r.get('is_playlist'))]
        if not contenedores and not any(r.get('selected') for r in self.resultados):
            activo = self._get_selected_video()
            if activo and (activo.get('is_channel') or activo.get('is_playlist')):
                contenedores = [activo]

        if contenedores:
            self._descargar_contenedores(contenedores)
            return

        seleccionados = [r for r in self.resultados if r.get('selected') and not r.get('is_channel') and not r.get('is_playlist')]
        
        if not seleccionados:
            activo = self._get_selected_video()
            if activo:
                seleccionados = [activo]

        if not seleccionados:
            wx.MessageBox(
                "Por favor, selecciona o marca al menos un vídeo de la lista antes de pulsar Descargar.",
                "Ningún vídeo seleccionado",
                wx.OK | wx.ICON_INFORMATION,
                self
            )
            self.lista_resultados.SetFocus()
            return

        es_multiple = len(seleccionados) > 1

        user_home = os.path.expanduser("~")
        default_downloads = os.path.join(user_home, "Downloads") if os.path.exists(os.path.join(user_home, "Downloads")) else user_home
        carpeta_base = (getattr(self, 'destino_dir', '') or '').strip() or default_downloads
        destino_final = carpeta_base

        # Si hay más de una descarga seleccionada, preguntar en qué subcarpeta organizarlas
        if es_multiple:
            sugerencia = self.sugerir_nombre_subcarpeta(seleccionados)
            sugerencia_limpia = re.sub(r'[\\/*?:"<>|]', '', sugerencia).strip().rstrip('. ')
            if not sugerencia_limpia:
                sugerencia_limpia = "Descargas"

            cant_str = f"{len(seleccionados)} elementos"
            msg = (
                f"Vas a descargar {cant_str}.\n\n"
                f"Carpeta base predeterminada:\n{carpeta_base}\n\n"
                f"Introduce el nombre de la subcarpeta donde deseas guardarlos\n"
                f"(o deja este campo vacío para guardarlos directamente en la carpeta base):"
            )

            accessibility.speak("Introduce el nombre de la subcarpeta para guardar los vídeos o pulsa Escape para cancelar.")
            dlg = wx.TextEntryDialog(
                self,
                msg,
                caption="Organizar descargas en subcarpeta",
                value=sugerencia_limpia
            )
            res_dlg = dlg.ShowModal()
            subcarpeta_val = dlg.GetValue().strip()
            dlg.Destroy()

            if res_dlg != wx.ID_OK:
                self.set_status("Descarga cancelada por el usuario.", field=0, announce=True)
                return

            if subcarpeta_val:
                subcarpeta_limpia = re.sub(r'[\\/*?:"<>|]', '', subcarpeta_val).strip().rstrip('. ')
                if subcarpeta_limpia:
                    destino_final = os.path.join(carpeta_base, subcarpeta_limpia)

        if not os.path.exists(destino_final):
            try:
                os.makedirs(destino_final, exist_ok=True)
            except Exception as e:
                wx.MessageBox(f"Error con la carpeta de destino:\n{e}", "Error", wx.OK | wx.ICON_ERROR, self)
                return

        self.destino_descarga_actual = destino_final

        sel_format_idx = self.choice_formato.GetSelection()
        if sel_format_idx < 0:
            sel_format_idx = 0
            self.choice_formato.SetSelection(0)
        formato_str = FORMATOS_MAP.get(sel_format_idx, 'video_best')

        self.cola_descargas = list(seleccionados)
        self.total_cola = len(self.cola_descargas)
        self.indice_cola = 0
        self.descargas_completadas = 0
        self.descargas_fallidas = 0
        self.ultimo_error_descarga = ""

        self.btn_descargar.Enable(False)
        self.btn_cancelar.Enable(True)
        self.btn_buscar.Enable(False)
        self.gauge_progreso.SetValue(0)
        self.last_announced_percent = -1

        self.iniciar_sonido_espera()
        self._iniciar_siguiente_descarga_cola(formato_str, self.destino_descarga_actual)

    def descargar_todos_los_videos_lista_actual(self, event=None):
        """Descarga todos los vídeos de la lista, canal o favoritos visualizados actualmente."""
        if not self.verificar_libreria_ytdlp():
            return
        if not hasattr(self, 'resultados') or not self.resultados:
            wx.MessageBox("No hay elementos disponibles en la lista para descargar.", "Lista vacía", wx.OK | wx.ICON_INFORMATION, self)
            return

        if getattr(self, 'is_showing_fav_lists', False):
            self.on_btn_descargar(None)
            return

        videos = [r for r in self.resultados if not r.get('is_channel') and not r.get('is_playlist') and not r.get('is_fav_list')]
        if not videos:
            wx.MessageBox("No hay vídeos disponibles en esta vista para descargar.", "Sin vídeos", wx.OK | wx.ICON_INFORMATION, self)
            return

        sugerencia = getattr(self, 'current_playlist_title', '') or getattr(self, 'current_channel_title', '') or getattr(self, 'current_fav_name', '') or "Descargas"
        sugerencia_limpia = re.sub(r'[\\/*?:"<>|]', '', sugerencia).strip().rstrip('. ') or "Descargas"

        user_home = os.path.expanduser("~")
        default_downloads = os.path.join(user_home, "Downloads") if os.path.exists(os.path.join(user_home, "Downloads")) else user_home
        carpeta_base = (getattr(self, 'destino_dir', '') or '').strip() or default_downloads
        destino_final = carpeta_base

        if len(videos) > 1:
            cant_str = f"{len(videos)} vídeos"
            nombre_ref = f" de '{sugerencia_limpia}'" if sugerencia_limpia != "Descargas" else ""
            msg = (
                f"Descargando {cant_str}{nombre_ref}.\n"
                f"Nombre de la subcarpeta (o vacío para carpeta base):"
            )

            accessibility.speak(f"Subcarpeta para {cant_str}:")
            dlg = wx.TextEntryDialog(
                self,
                msg,
                caption="Subcarpeta de descargas",
                value=sugerencia_limpia
            )
            res_dlg = dlg.ShowModal()
            subcarpeta_val = dlg.GetValue().strip()
            if res_dlg == wx.ID_CANCEL:
                dlg.Destroy()
                return
            dlg.Destroy()
            if subcarpeta_val:
                destino_final = os.path.join(carpeta_base, subcarpeta_val)
                os.makedirs(destino_final, exist_ok=True)

        for v in videos:
            v['_destino'] = destino_final
        self._agregar_descargas_o_iniciar(videos)

    def _agregar_descargas_o_iniciar(self, items):
        if not items:
            return
        descarga_activa = self.btn_cancelar.IsEnabled()
        self.cola_descargas.extend(items)
        if not descarga_activa:
            self.total_cola = len(self.cola_descargas)
            self.indice_cola = 0
            self.descargas_completadas = 0
            self.descargas_fallidas = 0
            self._iniciar_siguiente_descarga_cola()
        else:
            total = len(self.cola_descargas)
            accessibility.speak(f"{total} descargas")

    def _iniciar_siguiente_descarga_cola(self, formato_str=None, destino=None):
        if self.indice_cola >= len(self.cola_descargas):
            self._finalizar_cola_descargas()
            return

        self.iniciar_sonido_espera()

        item = self.cola_descargas[self.indice_cola]
        num_actual = self.indice_cola + 1
        total = self.total_cola

        fmt_actual = item.get('_formato') or formato_str or FORMATOS_MAP.get(self.choice_formato.GetSelection(), 'video_best')
        dest_actual = item.get('_destino') or destino or getattr(self, 'destino_descarga_actual', self.destino_dir)
        formato_nombre = item.get('_formato_nombre') or self.choice_formato.GetString(self.choice_formato.GetSelection())

        titulo = item.get('title', 'Vídeo')

        if total > 1:
            msg_status = f"Descargando [{num_actual}/{total}]: {titulo} ({formato_nombre})..."
            accessibility.speak(f"{num_actual} de {total}")
        else:
            msg_status = f"Iniciando descarga: {titulo} ({formato_nombre})..."
            accessibility.speak("1 de 1")

        self.set_status(msg_status, field=0, announce=False)
        self.lbl_progreso_detalle.SetLabel(msg_status)
        self.gauge_progreso.SetValue(0)
        self.last_announced_percent = -1
        self.current_download_percent = 0
        self.current_download_status = 'starting'
        self.btn_descargar.Enable(True)
        self.btn_cancelar.Enable(True)
        self.btn_buscar.Enable(True)

        def _progress(info):
            wx.CallAfter(self._on_download_progress, info, num_actual, total)

        def _finished(res):
            wx.CallAfter(self._on_item_queue_finished, res)

        def _error(err, cancelled=False):
            wx.CallAfter(self._on_item_queue_error, err, cancelled)

        url_target = item.get('url') or item.get('webpage_url') or (f"https://www.youtube.com/watch?v={item.get('id')}" if item.get('id') else '')
        if not url_target:
            wx.CallAfter(self._on_item_queue_error, "No se encontró enlace URL para el vídeo.", False)
            return

        try:
            self.downloader.descargar(
                url=url_target,
                formato=fmt_actual,
                destino=dest_actual,
                on_progress=_progress,
                on_finished=_finished,
                on_error=_error
            )
        except Exception as e:
            wx.CallAfter(self._on_item_queue_error, str(e), False)

    def on_btn_cancelar(self, event):
        self.detener_sonido_espera()
        self.btn_cancelar.Enable(False)
        self.cola_descargas = []
        self.indice_cola = 0
        self.total_cola = 0
        self.current_download_percent = 0
        self.current_download_status = None
        self.set_status("Cancelando descargas...", field=0, announce=True)
        self.lbl_progreso_detalle.SetLabel("Cancelando proceso...")
        self.downloader.request_cancel()

    def anunciar_porcentaje_descarga(self, event=None):
        """Anuncia al lector de pantalla el porcentaje de descarga del vídeo actual (F8)."""
        descarga_activa = (
            self.btn_cancelar.IsEnabled() or
            (bool(self.cola_descargas) and self.indice_cola < len(self.cola_descargas))
        ) and not getattr(self.downloader, '_cancel_requested', False)
        if not descarga_activa:
            accessibility.speak("No hay ninguna descarga en curso.")
            return

        status = getattr(self, 'current_download_status', None)
        percent = getattr(self, 'current_download_percent', 0)
        total = getattr(self, 'total_cola', 1)
        num_actual = getattr(self, 'indice_cola', 0) + 1
        prefijo = f"[{num_actual}/{total}] " if total > 1 else ""

        if status == 'processing':
            msg = f"{prefijo}Procesando archivo final."
        elif status == 'downloading' or percent > 0:
            msg = f"{prefijo}{percent} por ciento."
        else:
            msg = f"{prefijo}Iniciando descarga."

        accessibility.speak(msg)

    def _on_download_progress(self, info, num_actual=1, total=1):
        status = info.get('status')
        self.current_download_status = status
        if status == 'downloading':
            percent = int(info.get('percent', 0))
            self.current_download_percent = percent
            self.gauge_progreso.SetValue(min(max(percent, 0), 100))
            
            speed = info.get('speed', '')
            eta = info.get('eta', '')
            descargado = info.get('downloaded', '')
            total_size = info.get('total', '')

            prefijo = f"[{num_actual}/{total}] " if total > 1 else ""
            detalle = f"{prefijo}Descargando: {percent}% ({descargado} de {total_size}) - Velocidad: {speed} - ETA: {eta}"
            self.lbl_progreso_detalle.SetLabel(detalle)
            self.status_bar.SetStatusText(f"{percent}% a {speed}", 1)

            # Anunciar hitos de progreso al lector de pantalla cada 25%
            for hito in [25, 50, 75]:
                if percent >= hito and self.last_announced_percent < hito:
                    anuncio = f"{prefijo}Descargando: {hito} por ciento." if total > 1 else f"Descargando: {hito} por ciento."
                    accessibility.speak(anuncio)
                    self.last_announced_percent = hito
                    break

        elif status == 'processing':
            self.gauge_progreso.SetValue(100)
            msg = info.get('message', 'Procesando archivo final...')
            prefijo = f"[{num_actual}/{total}] " if total > 1 else ""
            self.lbl_progreso_detalle.SetLabel(f"{prefijo}{msg}")
            self.set_status(f"{prefijo}{msg}", field=0, announce=False)

    def _on_item_queue_finished(self, res):
        try:
            self.descargas_completadas += 1
            self.indice_cola += 1
            
            sel_format_idx = self.choice_formato.GetSelection()
            formato_str = FORMATOS_MAP.get(sel_format_idx, 'video_best')
            destino = getattr(self, 'destino_descarga_actual', self.destino_dir)

            if self.indice_cola < len(self.cola_descargas):
                accessibility.speak(f"Completado {self.indice_cola} de {self.total_cola}.")
                self._iniciar_siguiente_descarga_cola(formato_str, destino)
            else:
                self._finalizar_cola_descargas()
        except Exception:
            self._finalizar_cola_descargas(con_errores=True)

    def _on_item_queue_error(self, err_msg, cancelled):
        try:
            if cancelled:
                self.detener_sonido_espera()
                self.btn_descargar.Enable(True)
                self.btn_cancelar.Enable(False)
                self.btn_buscar.Enable(True)
                self.gauge_progreso.SetValue(0)
                self.set_status("Descargas canceladas por el usuario.", field=0, announce=True)
                self.lbl_progreso_detalle.SetLabel("Descargas canceladas.")
                self.cola_descargas = []
                self.current_download_percent = 0
                self.current_download_status = None
                return

            self.descargas_fallidas += 1
            self.ultimo_error_descarga = str(err_msg)
            self.indice_cola += 1
            
            sel_format_idx = self.choice_formato.GetSelection()
            formato_str = FORMATOS_MAP.get(sel_format_idx, 'video_best')
            destino = getattr(self, 'destino_descarga_actual', self.destino_dir)

            if self.indice_cola < len(self.cola_descargas):
                self.set_status("Error en archivo actual. Continuando con el siguiente...", field=0, announce=True)
                self._iniciar_siguiente_descarga_cola(formato_str, destino)
            else:
                self._finalizar_cola_descargas(con_errores=True)
        except Exception:
            self._finalizar_cola_descargas(con_errores=True)

    def _finalizar_cola_descargas(self, con_errores=False):
        if not con_errores and getattr(self, 'descargas_completadas', 0) > 0:
            sound_manager.play_completion_sound()
        else:
            self.detener_sonido_espera()
        self.btn_descargar.Enable(True)
        self.btn_cancelar.Enable(False)
        self.btn_buscar.Enable(True)

        total = self.total_cola
        completadas = self.descargas_completadas
        fallidas = self.descargas_fallidas
        ultimo_err = getattr(self, 'ultimo_error_descarga', '')

        # Limpiar la cola de descargas activas al finalizar
        self.cola_descargas = []
        self.indice_cola = 0
        self.total_cola = 0
        self.current_download_percent = 0
        self.current_download_status = None

        if completadas == 0:
            self.gauge_progreso.SetValue(0)
            self.status_bar.SetStatusText("Error", 1)
            if total > 1:
                msg = f"Error: No se pudo completar ninguna de las {total} descargas."
            else:
                msg = "Error en la descarga: no se pudo descargar el archivo."

            self.set_status(msg, field=0, announce=True)
            self.lbl_progreso_detalle.SetLabel(msg)

            texto_dialogo = f"{msg}\n\nDetalle del error:\n{ultimo_err}" if ultimo_err else msg
            wx.MessageBox(
                texto_dialogo,
                "Error de descarga",
                wx.OK | wx.ICON_ERROR,
                self
            )
            return

        self.gauge_progreso.SetValue(100)
        self.status_bar.SetStatusText("100%", 1)

        if total > 1:
            if fallidas > 0:
                msg = f"Descargas finalizadas: {completadas} completadas con éxito, {fallidas} con error de {total} totales."
            else:
                msg = f"Se han procesado {total} descargas ({completadas} completadas con éxito)."
        else:
            msg = "Descarga completada con éxito."

        self.set_status(msg, field=0, announce=True)
        self.lbl_progreso_detalle.SetLabel(f"Completado: {msg}")

        # Comprobar si la configuración tiene activado abrir carpeta automáticamente o preguntar
        if self.config.get('abrir_carpeta_al_terminar', False):
            self.on_abrir_carpeta(None)
        elif self.config.get('preguntar_abrir_carpeta', True):
            dlg = wx.MessageDialog(
                self,
                f"{msg}\n\n¿Deseas abrir la carpeta contenedora de descargas?",
                "Descarga finalizada",
                wx.YES_NO | wx.ICON_INFORMATION
            )
            if dlg.ShowModal() == wx.ID_YES:
                self.on_abrir_carpeta(None)
            dlg.Destroy()

    # ---------------- DIÁLOGOS DE AYUDA, ACTUALIZACIÓN Y ACERCA DE ----------------
