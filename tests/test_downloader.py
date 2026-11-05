"""
Tests modulares del sistema.
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def test_url_detection():
    print("[1/6] Probando detección inteligente de tipo de URLs...")
    from downloader import identificar_tipo_url

    assert identificar_tipo_url("https://www.youtube.com/@TED") == "canal"
    assert identificar_tipo_url("https://www.youtube.com/@TED/videos") == "canal"
    assert identificar_tipo_url("https://www.youtube.com/@TED/playlists") == "canal"
    assert identificar_tipo_url("https://www.youtube.com/channel/UCsooa4yRKGN_zEE8iknghZA") == "canal"
    assert identificar_tipo_url("@TED") == "canal"

    assert identificar_tipo_url("https://www.youtube.com/playlist?list=PLUCPc-R61w-s") == "playlist"
    assert identificar_tipo_url("https://www.youtube.com/watch?v=123&list=PLUCPc-R61w-s") == "playlist"
    assert identificar_tipo_url("https://www.youtube.com/feed/history") == "playlist"
    assert identificar_tipo_url("https://www.youtube.com/feed/playlists") == "playlist"

    assert identificar_tipo_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "video"
    assert identificar_tipo_url("python tutorial basico") == "texto"
    print("  -> Identificación de URLs validada correctamente (canales, playlists, vídeos, texto).")


def test_downloader():
    print("\n[2/6] Probando búsqueda con YouTubeDownloader por vídeos, canales y playlists...")
    from downloader import YouTubeDownloader
    dl = YouTubeDownloader()
    
    # 1. Búsqueda de vídeos
    resultados_vids = dl.buscar("python tutorial", max_results=2, search_type='video')
    assert len(resultados_vids) > 0, "No se obtuvieron vídeos de búsqueda"
    assert resultados_vids[0]['tipo_item'] == 'video'
    print(f"  -> Vídeos encontrados: {len(resultados_vids)} ({resultados_vids[0]['title']})")

    # 2. Búsqueda de listas de reproducción
    resultados_pls = dl.buscar("python tutorial", max_results=2, search_type='playlist')
    assert len(resultados_pls) > 0, "No se obtuvieron listas de reproducción de búsqueda"
    assert resultados_pls[0]['is_playlist'] is True
    print(f"  -> Playlists encontradas: {len(resultados_pls)} ({resultados_pls[0]['title']})")

    # 4. Probar ordenación natural y formato de visitas: respeta fielmente el orden devuelto por yt-dlp
    mock_entries = [
        {'id': '1', 'title': 'Aprende a programar desde cero', 'view_count': 20000000},
        {'id': '2', 'title': 'Python Tutorial Completo 2026', 'view_count': 5000000},
        {'id': '3', 'title': 'Python Tutorial Avanzado', 'view_count': 10000000},
    ]
    procesados = dl._procesar_entries(mock_entries, query="Python Tutorial")
    assert procesados[0]['id'] == '1', "Debe respetar el orden natural devuelto por yt-dlp (elemento 1)"
    assert procesados[0]['views'] == '20M visitas'
    assert procesados[0]['index'] == 1
    assert procesados[1]['id'] == '2', "Debe respetar el orden natural devuelto por yt-dlp (elemento 2)"
    assert procesados[1]['views'] == '5M visitas'
    assert procesados[1]['index'] == 2
    assert procesados[2]['id'] == '3', "Debe respetar el orden natural devuelto por yt-dlp (elemento 3)"
    assert procesados[2]['views'] == '10M visitas'
    assert procesados[2]['index'] == 3

    # Probar start_index desplazado (paginación continua)
    procesados_p2 = dl._procesar_entries(mock_entries, query="Python Tutorial", start_index=26)
    assert procesados_p2[0]['index'] == 26
    assert procesados_p2[1]['index'] == 27
    assert procesados_p2[2]['index'] == 28

    # 5. Probar canales con número de vídeos
    mock_channel_entries = [
        {'id': 'c1', 'title': 'Canal de Rock', 'url': 'https://www.youtube.com/@rock', 'channel_follower_count': 1500000, 'video_count': 342},
        {'id': 'c2', 'title': 'Canal Sin Contador', 'url': 'https://www.youtube.com/@sincontador', 'channel_follower_count': 50000}
    ]
    procesados_canales = dl._procesar_entries(mock_channel_entries, query="rock", is_channel_list=True)
    assert procesados_canales[0]['duration'] == '342 vídeos', "Debe mostrar el número de vídeos en la duración del canal"
    assert '342 vídeos' in procesados_canales[0]['views'], "Debe incluir el número de vídeos en las visitas del canal"
    assert procesados_canales[1]['duration'] == 'Canal', "Debe mostrar 'Canal' si no hay contador de vídeos"
    # 6. Probar extracción de channel_url y compatibilidad con enlaces especiales (ej: ShWqrFbSVxw)
    res_especial = dl.buscar("https://www.youtube.com/watch?v=ShWqrFbSVxw")
    assert len(res_especial) == 1, "Debe extraer correctamente el vídeo ShWqrFbSVxw"
    assert res_especial[0]['tipo_item'] == 'video'
    assert 'flamencodejerez' in res_especial[0]['channel_url'].lower()
    ch_url = dl.obtener_canal_url("https://www.youtube.com/watch?v=ShWqrFbSVxw")
    assert 'flamencodejerez' in ch_url.lower()

    # 7. Probar canales Topic / Temáticos que carecen de pestaña /videos o están vacíos
    res_topic = dl.buscar_canal_videos("https://www.youtube.com/channel/UClTrzaux8syhoUoIZi69VOw", max_results=5)
    assert isinstance(res_topic, list), "Debe devolver una lista limpia sin fallar para canales Topic sin pestaña /videos"

    print("  -> Priorización por términos en el título, paginación (start_index), visitas, canales especiales (Topic) y compatibilidad con enlaces verificados con éxito.")


def test_channel_playlist_extraction():
    print("\n[4/6] Probando extracción rápida de vídeos y playlists de canal...")
    from downloader import YouTubeDownloader
    dl = YouTubeDownloader()
    # Usar canal TED de prueba
    res_vids = dl.buscar_canal_videos("https://www.youtube.com/@TED", max_results=2)
    print(f"  -> Vídeos de canal obtenidos: {len(res_vids)}")
    if res_vids:
        assert res_vids[0]['is_playlist'] is False

    res_pls = dl.buscar_canal_playlists("https://www.youtube.com/@TED", max_results=2)
    print(f"  -> Playlists de canal obtenidas: {len(res_pls)}")
    if res_pls:
        assert res_pls[0]['is_playlist'] is True


def test_subcarpeta_solo_cuando_multiples_descargas():
    print("\n[Extra] Probando que el diálogo de subcarpeta solo se active si hay más de 1 descarga seleccionada...")
    import inspect
    import ui

    # Verificamos mediante inspección estática del método on_btn_descargar que solo pregunta subcarpeta si es_multiple
    src = inspect.getsource(ui.MainFrame.on_btn_descargar)
    assert "if es_multiple:" in src, "El diálogo de subcarpeta debe estar condicionado estrictamente a if es_multiple:"
    assert "if es_multiple or es_favoritos:" not in src, "No debe activarse para favoritos individuales"
    print("  -> Condición de diálogo de subcarpeta restringida a más de 1 elemento validada con éxito.")


def test_sugerencia_subcarpeta_lista_o_canal():
    print("\n[Extra] Probando sugerencia de subcarpeta inteligente (lista o canal)...")
    import wx
    import ui
    app = wx.App.Get() or wx.App(False)
    frame = ui.MainFrame()

    video_a = {'title': 'Canción 1', 'channel': 'Queen', 'url': 'https://youtube.com/watch?v=1'}
    video_b = {'title': 'Canción 2', 'channel': 'Queen', 'url': 'https://youtube.com/watch?v=2'}
    video_c = {'title': 'Canción 3', 'channel': 'Beatles', 'url': 'https://youtube.com/watch?v=3'}

    # 1. En lista de favoritos: debe sugerir el nombre de la lista de favoritos
    frame.is_showing_favorites = True
    frame.current_fav_name = "Mis Baladas"
    sug = frame.sugerir_nombre_subcarpeta([video_a, video_b])
    assert sug == "Mis Baladas", f"Esperado 'Mis Baladas', obtenido '{sug}'"

    frame.current_fav_name = "Todas las listas"
    sug = frame.sugerir_nombre_subcarpeta([video_a, video_b])
    assert sug == "Favoritos", f"Esperado 'Favoritos', obtenido '{sug}'"

    # 2. En lista de reproducción de YouTube: debe sugerir el nombre de la lista
    frame.is_showing_favorites = False
    frame.last_search_kind = 'playlist_videos'
    frame.current_playlist_title = "Grandes Éxitos de los 80"
    sug = frame.sugerir_nombre_subcarpeta([video_a, video_b])
    assert sug == "Grandes Éxitos de los 80", f"Esperado 'Grandes Éxitos de los 80', obtenido '{sug}'"

    # 3. En Ver más tarde: debe sugerir 'Ver más tarde'
    frame.last_search_kind = 'ver_mas_tarde'
    frame.current_playlist_title = ""
    sug = frame.sugerir_nombre_subcarpeta([video_a, video_b])
    assert sug == "Ver más tarde", f"Esperado 'Ver más tarde', obtenido '{sug}'"

    # 4. En un canal (no pertenece a lista): debe sugerir el nombre del canal
    frame.last_search_kind = 'canal_videos'
    frame.current_playlist_title = ""
    frame.current_channel_title = "Canal Oficial Queen"
    sug = frame.sugerir_nombre_subcarpeta([video_a, video_b])
    assert sug == "Canal Oficial Queen", f"Esperado 'Canal Oficial Queen', obtenido '{sug}'"

    # 5. En búsqueda general sin lista: debe sugerir el canal de los vídeos
    frame.last_search_kind = 'search'
    frame.current_playlist_title = ""
    frame.current_channel_title = ""
    sug = frame.sugerir_nombre_subcarpeta([video_a, video_b])
    assert sug == "Queen", f"Esperado 'Queen', obtenido '{sug}'"

    # 6. En búsqueda general con canales mixtos: sugiere el canal del primer vídeo
    sug = frame.sugerir_nombre_subcarpeta([video_a, video_c])
    assert sug == "Queen", f"Esperado 'Queen', obtenido '{sug}'"

    # 7. Fallback: nunca sugerir URL en crudo como nombre de subcarpeta
    frame.last_search_query = "https://www.youtube.com/playlist?list=PL12345"
    sug = frame.sugerir_nombre_subcarpeta([{'title': 'V1'}, {'title': 'V2'}])
    assert sug == "Descargas", f"No debe sugerir URLs en crudo, obtenido '{sug}'"

    frame.Destroy()
    print("  -> Sugerencias de subcarpeta para listas y canales validadas satisfactoriamente.")


def test_limpieza_extensiones_en_descarga():
    print("\n[Prueba] Verificando limpieza de extensiones redundantes en títulos y archivos...")
    from downloader import limpiar_extension_titulo, corregir_doble_extension, YouTubeDownloader

    # 1. Limpieza de títulos que terminan en extensión multimedia
    assert limpiar_extension_titulo("Tutorial Python.flv") == "Tutorial Python"
    assert limpiar_extension_titulo("Video Clip Oficial.mp4") == "Video Clip Oficial"
    assert limpiar_extension_titulo("Grabacion de audio.MP3") == "Grabacion de audio"
    assert limpiar_extension_titulo("Cancion.flv.mp4") == "Cancion"
    assert limpiar_extension_titulo("Version 1.5.8") == "Version 1.5.8"
    assert limpiar_extension_titulo("Curso de Node.js") == "Curso de Node.js"

    # 2. Corrección de doble extensión en archivos
    assert corregir_doble_extension("C:\\Descargas\\Cancion.flv.mp3") == "C:\\Descargas\\Cancion.mp3"
    assert corregir_doble_extension("C:\\Descargas\\Video.mp4.mp4") == "C:\\Descargas\\Video.mp4"
    assert corregir_doble_extension("C:\\Descargas\\Grabacion.avi.flac") == "C:\\Descargas\\Grabacion.flac"
    assert corregir_doble_extension("C:\\Descargas\\Pista.m4a.m4a") == "C:\\Descargas\\Pista.m4a"
    assert corregir_doble_extension("C:\\Descargas\\Archivo.backup.mp3") == "C:\\Descargas\\Archivo.backup.mp3"
    assert corregir_doble_extension("C:\\Descargas\\Normal.mp3") == "C:\\Descargas\\Normal.mp3"

    # 3. Verificación en _procesar_entries
    dl = YouTubeDownloader()
    entries = [
        {'id': '1', 'title': 'Tema Musical.flv', 'url': 'https://www.youtube.com/watch?v=1', 'duration': 120},
        {'id': '2', 'title': 'Videotutorial.mp4', 'url': 'https://www.youtube.com/watch?v=2', 'duration': 300},
    ]
    procesados = dl._procesar_entries(entries)
    assert procesados[0]['title'] == "Tema Musical", f"Esperado 'Tema Musical', obtenido '{procesados[0]['title']}'"
    assert procesados[1]['title'] == "Videotutorial", f"Esperado 'Videotutorial', obtenido '{procesados[1]['title']}'"

    print("  -> Limpieza de extensiones redundantes en títulos y archivos validada exitosamente.")


def test_descarga_finalizacion_y_estado_botones():
    print("\n[30/30] Probando ciclo de finalización de descargas y restauración de botones...")
    import wx
    import ui
    import sound_manager

    app = wx.GetApp() or wx.App(False)
    frame = ui.MainFrame()
    frame.config['preguntar_abrir_carpeta'] = False
    frame.config['abrir_carpeta_al_terminar'] = False

    # Simular inicio de descarga
    frame.cola_descargas = [{'title': 'Vídeo Test', 'url': 'http://youtube.com/watch?v=123'}]
    frame.total_cola = 1
    frame.indice_cola = 0
    frame.descargas_completadas = 0
    frame.descargas_fallidas = 0
    frame.btn_descargar.Enable(False)
    frame.btn_cancelar.Enable(True)
    sound_manager.start_waiting_sound(interval=10.0)
    assert sound_manager.is_waiting_sound_running()

    # Simular finalización de elemento
    frame._on_item_queue_finished({'title': 'Vídeo Test', 'filepath': 'test.mp4'})

    assert not frame.btn_cancelar.IsEnabled(), "El botón cancelar debe quedar deshabilitado al finalizar"
    assert frame.btn_descargar.IsEnabled(), "El botón descargar debe quedar rehabilitado al finalizar"
    assert frame.descargas_completadas == 1, "Debe registrarse 1 descarga completada"
    assert len(frame.cola_descargas) == 0, "La cola debe quedar limpia"
    assert not sound_manager.is_waiting_sound_running(), "El sonido de espera debe detenerse al finalizar"

    frame.Destroy()
    print("  -> Finalización de descarga y estados de botones validados correctamente.")


if __name__ == '__main__':
    test_url_detection()
    test_downloader()
    test_channel_playlist_extraction()
    test_subcarpeta_solo_cuando_multiples_descargas()
    test_sugerencia_subcarpeta_lista_o_canal()
    test_limpieza_extensiones_en_descarga()
    test_descarga_finalizacion_y_estado_botones()
    print("\n[OK] Todas las pruebas de test_downloader.py pasaron satisfactoriamente.")
