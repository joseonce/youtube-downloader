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

def test_favorites_multiple_lists_system():
    print("\n[6/6] Probando sistema persistente de múltiples listas de Favoritos (ficheros independientes en config/favoritos/)...")
    from downloader import (
        get_favoritos_dir,
        get_favoritos_file_path,
        obtener_nombres_listas_favoritos,
        obtener_favoritos,
        crear_lista_favoritos,
        eliminar_lista_favoritos,
        agregar_favorito,
        eliminar_favorito,
        es_favorito,
        mover_favorito_de_lista,
        obtener_listas_de_item
    )

    fav_dir = get_favoritos_dir()
    assert os.path.isdir(fav_dir), "La carpeta config/favoritos/ debe existir"
    fav_principal = get_favoritos_file_path('Principal')
    assert fav_principal.endswith("Principal.json"), "El archivo de la lista Principal debe ser Principal.json"
    assert os.path.dirname(fav_principal) == fav_dir, "Principal.json debe residir en config/favoritos/"

    test_video_1 = {
        'id': 'test_fav_001',
        'title': 'Vídeo Favorito General',
        'channel': 'Canal Test',
        'duration': '04:20',
        'duration_seconds': 260,
        'url': 'https://www.youtube.com/watch?v=test_fav_001'
    }

    test_video_2 = {
        'id': 'test_fav_002',
        'title': 'Canción Favorita Rock',
        'channel': 'Canal Rock',
        'duration': '03:10',
        'duration_seconds': 190,
        'url': 'https://www.youtube.com/watch?v=test_fav_002'
    }

    # Limpiar si existían
    eliminar_favorito('test_fav_001')
    eliminar_favorito('test_fav_002')
    assert not es_favorito('test_fav_001')
    assert not es_favorito('test_fav_002')

    # Crear lista personalizada
    crear_lista_favoritos('Música Rock')
    nombres = obtener_nombres_listas_favoritos()
    assert 'Música Rock' in nombres
    fav_rock_file = get_favoritos_file_path('Música Rock')
    assert os.path.isfile(fav_rock_file), "Debe crearse el fichero independiente Música Rock.json"

    # Añadir a Principal y a lista personalizada
    ok1 = agregar_favorito(test_video_1, nombre_lista='Principal')
    assert ok1 is True
    ok2 = agregar_favorito(test_video_2, nombre_lista='Música Rock')
    assert ok2 is True

    # Verificar que los archivos .json existen en el disco de forma separada
    assert os.path.isfile(fav_principal), f"Principal.json debe existir en {fav_principal}"
    assert os.path.isfile(fav_rock_file), f"Música Rock.json debe existir en {fav_rock_file}"

    # Verificar pertenencia
    assert es_favorito('test_fav_001') is True
    assert es_favorito('test_fav_002') is True

    # Verificar filtrado por lista
    favs_rock = obtener_favoritos(nombre_lista='Música Rock')
    assert any(f['id'] == 'test_fav_002' for f in favs_rock)
    assert not any(f['id'] == 'test_fav_001' for f in favs_rock)

    favs_todos = obtener_favoritos(nombre_lista=None)
    assert any(f['id'] == 'test_fav_001' for f in favs_todos)
    assert any(f['id'] == 'test_fav_002' for f in favs_todos)

    # Eliminar
    del_ok1 = eliminar_favorito('test_fav_001')
    assert del_ok1 is True
    del_ok2 = eliminar_favorito('test_fav_002')
    assert del_ok2 is True
    assert es_favorito('test_fav_001') is False
    assert es_favorito('test_fav_002') is False

    # Probar que canales y playlists guardados en favoritos preservan su tipo de contenido
    canal_fav = {'id': 'ch_fav_1', 'title': 'Canal Python', 'url': 'https://www.youtube.com/@python', 'is_channel': True}
    pl_fav = {'id': 'pl_fav_1', 'title': 'Curso Django', 'url': 'https://www.youtube.com/playlist?list=PL_DJANGO', 'is_playlist': True}
    agregar_favorito(canal_fav, nombre_lista='Principal')
    agregar_favorito(pl_fav, nombre_lista='Principal')
    favs_check = obtener_favoritos(nombre_lista='Principal')
    f_ch = next(f for f in favs_check if f['id'] == 'ch_fav_1')
    f_pl = next(f for f in favs_check if f['id'] == 'pl_fav_1')
    assert f_ch['type'] == 'channel' and f_ch['is_channel'] is True
    assert f_pl['type'] == 'playlist' and f_pl['is_playlist'] is True
    # Probar mover un elemento de una lista de favoritos a otra
    test_move_vid = {
        'id': 'test_move_001',
        'title': 'Vídeo para Mover de Lista',
        'channel': 'Canal Move',
        'url': 'https://www.youtube.com/watch?v=test_move_001'
    }
    agregar_favorito(test_move_vid, nombre_lista='Principal')
    assert 'Principal' in obtener_listas_de_item('test_move_001')

    # Mover a Música Rock
    mover_favorito_de_lista(test_move_vid, lista_destino='Música Rock', lista_origen='Principal')
    listas_del_item = obtener_listas_de_item('test_move_001')
    assert 'Música Rock' in listas_del_item, "Debe haberse añadido a Música Rock"
    assert 'Principal' not in listas_del_item, "Debe haberse eliminado de Principal"

    eliminar_favorito('test_move_001')
    eliminar_lista_favoritos('Música Rock')

    print(f"  -> Archivos independientes por lista en config/favoritos/ ({fav_dir}), tipos y cambio de listas validados con éxito.")


def test_mover_multiples_favoritos_y_busqueda():
    print("\n[Extra] Probando movimiento por lotes a lista nueva con selección múltiple y búsqueda...")
    from downloader import (
        crear_lista_favoritos,
        eliminar_lista_favoritos,
        agregar_favorito,
        eliminar_favorito,
        obtener_listas_de_item
    )
    import wx
    from ui import MainFrame

    vid_fav1 = {'id': 'mv_fav_1', 'title': 'Vid Fav 1', 'url': 'https://youtube.com/watch?v=mv_fav_1'}
    vid_fav2 = {'id': 'mv_fav_2', 'title': 'Vid Fav 2', 'url': 'https://youtube.com/watch?v=mv_fav_2'}
    vid_busq = {'id': 'mv_search_1', 'title': 'Vid Busqueda 1', 'url': 'https://youtube.com/watch?v=mv_search_1'}

    for v in ('mv_fav_1', 'mv_fav_2', 'mv_search_1'):
        eliminar_favorito(v)

    agregar_favorito(vid_fav1, nombre_lista='Principal')
    agregar_favorito(vid_fav2, nombre_lista='Principal')
    crear_lista_favoritos('Nueva Lista Test')

    app = wx.App.Get() or wx.App(False)
    frame = MainFrame()

    # Caso 1: Varios marcados (uno de lista, uno de búsqueda)
    frame.resultados = [
        {'id': 'mv_fav_1', 'title': 'Vid Fav 1', 'url': 'https://youtube.com/watch?v=mv_fav_1', 'selected': True, 'list_name': 'Principal'},
        {'id': 'mv_fav_2', 'title': 'Vid Fav 2', 'url': 'https://youtube.com/watch?v=mv_fav_2', 'selected': False, 'list_name': 'Principal'},
        {'id': 'mv_search_1', 'title': 'Vid Busqueda 1', 'url': 'https://youtube.com/watch?v=mv_search_1', 'selected': True}
    ]

    frame.lista_resultados.DeleteAllItems()
    for idx, r in enumerate(frame.resultados):
        frame.lista_resultados.InsertItem(idx, r['title'])

    items_a_mover = frame._get_videos_para_cambio_lista()
    assert len(items_a_mover) == 2, f"Deben ser 2 items marcados, obtenidos: {len(items_a_mover)}"
    assert items_a_mover[0]['id'] == 'mv_fav_1'
    assert items_a_mover[1]['id'] == 'mv_search_1'

    # Mover a 'Nueva Lista Test'
    frame.cambiar_favorito_a_lista(lista_destino='Nueva Lista Test')

    assert 'Nueva Lista Test' in obtener_listas_de_item('mv_fav_1')
    assert 'Principal' not in obtener_listas_de_item('mv_fav_1')
    assert 'Nueva Lista Test' in obtener_listas_de_item('mv_search_1')
    assert 'Principal' in obtener_listas_de_item('mv_fav_2')

    assert not frame.resultados[0].get('selected')
    assert not frame.resultados[2].get('selected')

    # Caso 2: Sin selección -> Mueve el que está bajo el cursor
    frame.resultados[0]['selected'] = False
    frame.resultados[1]['selected'] = False
    frame.resultados[2]['selected'] = False

    frame.lista_resultados.DeleteAllItems()
    for idx, r in enumerate(frame.resultados):
        frame.lista_resultados.InsertItem(idx, r['title'])
    frame.lista_resultados.Select(1)

    items_sin_sel = frame._get_videos_para_cambio_lista()
    assert len(items_sin_sel) == 1
    assert items_sin_sel[0]['id'] == 'mv_fav_2'

    frame.cambiar_favorito_a_lista(lista_destino='Nueva Lista Test')
    assert 'Nueva Lista Test' in obtener_listas_de_item('mv_fav_2')
    assert 'Principal' not in obtener_listas_de_item('mv_fav_2')

    for v in ('mv_fav_1', 'mv_fav_2', 'mv_search_1'):
        eliminar_favorito(v)
    eliminar_lista_favoritos('Nueva Lista Test')
    frame.Destroy()
    print("  -> Movimiento por lotes de selección múltiple, elementos de búsqueda y fallback a cursor validados con éxito.")


def test_no_cambiar_lista_si_no_es_favorito():
    print("\n[Extra] Probando que no se permite ni ofrece cambiar de lista si ningún elemento está en favoritos...")
    from downloader import (
        crear_lista_favoritos,
        eliminar_lista_favoritos,
        eliminar_favorito,
        es_favorito
    )
    import wx
    from ui import MainFrame

    vid_no_fav1 = {'id': 'no_fav_1', 'title': 'No Fav 1', 'url': 'https://youtube.com/watch?v=no_fav_1'}
    vid_no_fav2 = {'id': 'no_fav_2', 'title': 'No Fav 2', 'url': 'https://youtube.com/watch?v=no_fav_2'}

    eliminar_favorito('no_fav_1')
    eliminar_favorito('no_fav_2')
    crear_lista_favoritos('Destino Test')

    app = wx.App.Get() or wx.App(False)
    frame = MainFrame()

    # Caso 1: Un solo vídeo no favorito seleccionado
    frame.resultados = [
        {'id': 'no_fav_1', 'title': 'No Fav 1', 'url': 'https://youtube.com/watch?v=no_fav_1', 'selected': False},
        {'id': 'no_fav_2', 'title': 'No Fav 2', 'url': 'https://youtube.com/watch?v=no_fav_2', 'selected': False}
    ]
    frame.lista_resultados.DeleteAllItems()
    for idx, r in enumerate(frame.resultados):
        frame.lista_resultados.InsertItem(idx, r['title'])
    frame.lista_resultados.Select(0)

    menu_test = wx.Menu()
    frame._agregar_submenu_cambiar_lista(menu_test, frame.resultados[0])
    assert menu_test.GetMenuItemCount() == 0, "No debe añadirse submenú de cambiar lista si el vídeo no está en favoritos"
    menu_test.Destroy()

    # Intentar cambiar lista de un vídeo no favorito
    frame.cambiar_favorito_a_lista(video=frame.resultados[0], lista_destino='Destino Test')
    assert not es_favorito('no_fav_1'), "No debe haberse añadido a favoritos porque cambiar lista no aplica"

    # Caso 2: Múltiples vídeos seleccionados donde NINGUNO es favorito
    frame.resultados[0]['selected'] = True
    frame.resultados[1]['selected'] = True
    menu_test2 = wx.Menu()
    frame._agregar_submenu_cambiar_lista(menu_test2, frame.resultados[0])
    assert menu_test2.GetMenuItemCount() == 0, "No debe añadirse submenú si ninguno de los seleccionados es favorito"
    menu_test2.Destroy()

    frame.cambiar_favorito_a_lista(lista_destino='Destino Test')
    assert not es_favorito('no_fav_1')
    assert not es_favorito('no_fav_2')

    eliminar_lista_favoritos('Destino Test')
    frame.Destroy()
    print("  -> Verificación de no cambiar lista si ningún elemento es favorito validada con éxito.")


def test_favorites_delete_supr_key_and_confirmation():
    print("\n[Extra] Probando eliminación de favoritos con tecla Supr y confirmación configurable...")
    import wx
    import ui
    from unittest.mock import patch, MagicMock

    # 1. Helper de confirmación
    with patch('ui.cargar_configuracion', return_value={'confirmar_eliminar_favorito': False}):
        assert ui.pedir_confirmacion_eliminar_favorito(None, "Vídeo prueba") is True
    with patch('ui.cargar_configuracion', return_value={'confirmar_eliminar_favorito': True}):
        with patch('wx.MessageBox', return_value=wx.YES):
            assert ui.pedir_confirmacion_eliminar_favorito(None, "Vídeo prueba") is True
        with patch('wx.MessageBox', return_value=wx.NO):
            assert ui.pedir_confirmacion_eliminar_favorito(None, "Vídeo prueba") is False

    app = wx.App(False)

    # 2. Reproductor: Tecla Supr con confirmación
    test_v = {'id': 'v_fav_1', 'title': 'Canción Fav', 'url': 'https://youtube.com/watch?v=v_fav_1'}
    with patch('ui.es_favorito', return_value=True), \
         patch('ui.eliminar_favorito') as mock_del, \
         patch('ui.pedir_confirmacion_eliminar_favorito', return_value=True), \
         patch('ui.accessibility.speak'):
        dlg = ui.VideoPreviewDialog(None, [test_v])
        evt = MagicMock()
        evt.GetKeyCode.return_value = wx.WXK_DELETE
        evt.ControlDown.return_value = False
        dlg.on_key_hook(evt)
        assert mock_del.called
        dlg.Destroy()

    # 3. Lista: Tecla Supr con confirmación en MainFrame
    with patch('updater.start_background_check'), patch('ui.accessibility.speak'):
        frame = ui.MainFrame()
    frame.is_showing_favorites = True
    frame.resultados = [dict(test_v)]
    frame.lista_resultados.DeleteAllItems()
    frame.lista_resultados.InsertItem(0, test_v['title'])
    frame.lista_resultados.Select(0)
    frame.lista_resultados.Focus(0)

    with patch('ui.pedir_confirmacion_eliminar_favorito', return_value=True), \
         patch('ui.eliminar_favorito') as mock_del_list, \
         patch('ui.accessibility.speak'):
        evt = MagicMock()
        evt.GetKeyCode.return_value = wx.WXK_DELETE
        evt.GetModifiers.return_value = 0
        frame.on_lista_key_down(evt)
        assert mock_del_list.called
        assert len(frame.resultados) == 0

    # Probar que al pulsar Enter en la lista se reproduce y NO se descarga
    frame.resultados = [{'title': 'Video Enter Test', 'url': 'https://youtube.com/watch?v=enter1', 'is_playlist': False, 'is_channel': False}]
    frame.lista_resultados.DeleteAllItems()
    frame.lista_resultados.InsertItem(0, 'Video Enter Test')
    frame.lista_resultados.Select(0)
    frame.lista_resultados.Focus(0)
    with patch.object(frame, 'on_previsualizar_video') as mock_prev, \
         patch.object(frame, 'on_btn_descargar') as mock_desc, \
         patch.object(frame, 'FindFocus', return_value=frame.lista_resultados):
        evt_enter = MagicMock()
        evt_enter.GetKeyCode.return_value = wx.WXK_RETURN
        evt_enter.GetModifiers.return_value = 0
        frame.on_char_hook(evt_enter)
        assert mock_prev.called, "Enter en on_char_hook debe llamar a on_previsualizar_video"
        assert not mock_desc.called, "Enter no debe llamar a on_btn_descargar"

        mock_prev.reset_mock()
        mock_desc.reset_mock()
        frame.on_lista_key_down(evt_enter)
        assert mock_prev.called, "Enter en on_lista_key_down debe llamar a on_previsualizar_video"
        assert not mock_desc.called, "Enter en on_lista_key_down no debe llamar a on_btn_descargar"

    frame.Destroy()
    app.Destroy()
    print("  -> Eliminación con tecla Supr y diálogo de confirmación validados en reproductor y lista.")


def test_navegacion_jerarquica_mis_listas_favoritos():
    print("\n[Extra] Probando navegación jerárquica con Mis listas de favoritos (Escape)...")
    import wx
    import ui
    import favorites_manager

    app = wx.App.Get() or wx.App(False)
    frame = ui.MainFrame()

    orig_nombres = favorites_manager.obtener_nombres_listas_favoritos
    orig_favs = favorites_manager.obtener_favoritos
    orig_cargar = favorites_manager.cargar_favoritos

    dummy_dict = {
        'Principal': [
            {'title': 'Video Principal', 'tipo_item': 'video', 'is_channel': False, 'is_playlist': False, 'url': 'https://youtube.com/watch?v=P1'}
        ],
        'Mi Lista': [
            {'title': 'Canal en Mi Lista', 'tipo_item': 'channel', 'is_channel': True, 'is_playlist': False, 'url': 'https://youtube.com/@CanalTest'}
        ]
    }

    import main_favorites_mixin
    orig_mfm_nombres = main_favorites_mixin.obtener_nombres_listas_favoritos
    orig_mfm_favs = main_favorites_mixin.obtener_favoritos
    orig_mfm_cargar = main_favorites_mixin.cargar_favoritos

    mock_nombres = lambda: ['Mi Lista', 'Principal']
    mock_cargar = lambda: dummy_dict
    mock_favs = lambda nombre_lista=None: (
        (dummy_dict['Principal'] + dummy_dict['Mi Lista']) if not nombre_lista or nombre_lista in ('Todas', 'Todas las listas')
        else dummy_dict.get(nombre_lista, [])
    )

    favorites_manager.obtener_nombres_listas_favoritos = mock_nombres
    favorites_manager.cargar_favoritos = mock_cargar
    favorites_manager.obtener_favoritos = mock_favs
    main_favorites_mixin.obtener_nombres_listas_favoritos = mock_nombres
    main_favorites_mixin.cargar_favoritos = mock_cargar
    main_favorites_mixin.obtener_favoritos = mock_favs

    try:
        # 1. Al invocar mostrar_favoritos con múltiples listas, debe entrar a 'mostrar_listas_favoritos' (Nivel 0)
        frame.mostrar_favoritos()
        assert frame.is_showing_fav_lists is True, "Debe mostrar las listas de favoritos"
        assert frame.is_showing_favorites is False
        assert len(frame.resultados) == 3, "Debe incluir 'Todas las listas', 'Principal' y 'Mi Lista'"
        titles = [r['title'] for r in frame.resultados]
        assert 'Todas las listas' in titles
        assert 'Mi Lista' in titles
        assert 'Principal' in titles
        assert len(frame.navigation_stack) == 0, "En el nivel superior la pila debe estar vacía"

        # 2. Entrar en 'Mi Lista' (Nivel 1)
        frame.mostrar_favoritos_de_lista('Mi Lista', push_state=True)
        assert len(frame.navigation_stack) == 1, "Debe haber guardado el nivel de Mis listas de favoritos en la pila"
        assert frame.navigation_stack[0]['is_showing_fav_lists'] is True
        assert frame.is_showing_fav_lists is False
        assert frame.is_showing_favorites is True
        assert frame.current_fav_name == 'Mi Lista'
        assert len(frame.resultados) == 1
        assert frame.resultados[0]['title'] == 'Canal en Mi Lista'

        # 3. Entrar al canal (Nivel 2)
        frame._pending_nav_state = frame._capturar_estado_navegacion()
        playlists_canal = [
            {'title': 'Playlist del Canal', 'tipo_item': 'playlist', 'is_playlist': True, 'url': 'https://youtube.com/playlist?list=PL1', 'selected': False}
        ]
        frame._on_search_completed(playlists_canal, "Listas de reproducción del canal", False)
        assert len(frame.navigation_stack) == 2, "Pila debe tener 2 niveles (Mis listas y Mi Lista)"
        assert frame.is_showing_favorites is False

        # 4. Entrar a la playlist (Nivel 3)
        frame._pending_nav_state = frame._capturar_estado_navegacion()
        videos_pl = [
            {'title': 'Vídeo 1 de la Lista', 'tipo_item': 'video', 'url': 'https://youtube.com/watch?v=V1', 'selected': False}
        ]
        frame._on_search_completed(videos_pl, "Vídeos de la lista", False)
        assert len(frame.navigation_stack) == 3, "Pila debe tener 3 niveles (Mis listas, Mi Lista y Canal)"
        assert frame.resultados[0]['title'] == 'Vídeo 1 de la Lista'

        # Ahora retrocedemos nivel a nivel con Escape:
        # 1ª pulsación: sube al canal donde se encuentra la lista
        frame.retroceder_nivel_o_limpiar()
        assert len(frame.navigation_stack) == 2
        assert frame.resultados[0]['title'] == 'Playlist del Canal'

        # 2ª pulsación: sube a 'Mi Lista' donde se encuentra el canal
        frame.retroceder_nivel_o_limpiar()
        assert len(frame.navigation_stack) == 1
        assert frame.is_showing_favorites is True
        assert frame.current_fav_name == 'Mi Lista'
        assert frame.resultados[0]['title'] == 'Canal en Mi Lista'

        # 3ª pulsación: sube a 'Mis listas de favoritos'
        frame.retroceder_nivel_o_limpiar()
        assert len(frame.navigation_stack) == 0
        assert frame.is_showing_fav_lists is True
        assert frame.is_showing_favorites is False
        assert len(frame.resultados) == 3

        # 4ª pulsación: limpia resultados y vuelve al campo de búsqueda
        frame.retroceder_nivel_o_limpiar()
        assert len(frame.resultados) == 0
        assert frame.is_showing_fav_lists is False
        assert frame.is_showing_favorites is False

        print("  -> Navegación con Mis listas de favoritos y retroceso paso a paso validado con éxito.")
    finally:
        favorites_manager.obtener_nombres_listas_favoritos = orig_nombres
        favorites_manager.cargar_favoritos = orig_cargar
        favorites_manager.obtener_favoritos = orig_favs
        main_favorites_mixin.obtener_nombres_listas_favoritos = orig_mfm_nombres
        main_favorites_mixin.cargar_favoritos = orig_mfm_cargar
        main_favorites_mixin.obtener_favoritos = orig_mfm_favs
        frame.Destroy()


if __name__ == '__main__':
    test_favorites_multiple_lists_system()
    test_mover_multiples_favoritos_y_busqueda()
    test_no_cambiar_lista_si_no_es_favorito()
    test_favorites_delete_supr_key_and_confirmation()
    test_navegacion_jerarquica_mis_listas_favoritos()
    print("\n[OK] Todas las pruebas de test_favorites.py pasaron satisfactoriamente.")
