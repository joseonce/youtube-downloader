import os
import wx
import pytest
from downloader import YouTubeDownloader
from misc_dialogs import TranscripcionDialog

@pytest.fixture(scope="module")
def wx_app():
    app = wx.GetApp() or wx.App()
    yield app

def test_transcripcion_dialog(wx_app):
    items = [{'title': 'Vídeo de prueba', 'url': 'https://www.youtube.com/watch?v=5MPLuKYPV8E'}]
    dlg = TranscripcionDialog(None, items)
    assert dlg.radio_formato.GetSelection() == 0, "Por defecto debe ser texto limpio"
    assert dlg.choice_idioma.GetSelection() == 0, "Por defecto debe ser idioma original"
    assert dlg.con_marcas is False
    assert dlg.idioma == 'orig'

    # Simular cambio a con marcas y cambio a inglés
    dlg.radio_formato.SetSelection(1)
    dlg.choice_idioma.SetSelection(2) # Inglés
    dlg.on_aceptar(None)
    assert dlg.con_marcas is True
    assert dlg.idioma == 'en'
    dlg.Destroy()

def test_extraer_transcripcion_unit():
    dl = YouTubeDownloader()
    # Usar el mock de procesamiento interno con marcas musicales para comprobar limpieza y separación por líneas
    mock_data = {
        "events": [
            {"tStartMs": 500, "segs": [{"utf8": "[♪♪♪]"}]},
            {"tStartMs": 1000, "segs": [{"utf8": "Primera frase del vídeo."}]},
            {"tStartMs": 3000, "segs": [{"utf8": "[Música]"}]},
            {"tStartMs": 4000, "segs": [{"utf8": "Segunda frase con más detalle [♪]."}]}
        ]
    }
    texto_sin = dl._procesar_json3_transcripcion(mock_data, con_marcas=False)
    # Debe limpiar las marcas de música y separar por líneas
    assert "[♪♪♪]" not in texto_sin
    assert "[Música]" not in texto_sin
    assert "[♪]" not in texto_sin
    assert "Primera frase del vídeo." in texto_sin
    assert "Segunda frase con más detalle." in texto_sin
    lineas_sin = [l for l in texto_sin.splitlines() if l.strip()]
    assert len(lineas_sin) == 2
    assert lineas_sin[0] == "Primera frase del vídeo."
    assert lineas_sin[1] == "Segunda frase con más detalle."

    texto_con = dl._procesar_json3_transcripcion(mock_data, con_marcas=True)
    assert "[♪♪♪]" not in texto_con
    assert "[Música]" not in texto_con
    assert "[00:01] Primera frase del vídeo." in texto_con
    assert "[00:04] Segunda frase con más detalle." in texto_con
    lineas_con = [l for l in texto_con.splitlines() if l.strip()]
    assert len(lineas_con) == 2

def test_limpiar_linea_transcripcion():
    dl = YouTubeDownloader()
    assert dl._limpiar_linea_transcripcion("[♪♪♪]") == ""
    assert dl._limpiar_linea_transcripcion("♪ ♪ ♪") == ""
    assert dl._limpiar_linea_transcripcion("[Música]") == ""
    assert dl._limpiar_linea_transcripcion("[00:05] [♪♪♪]") == ""
    assert dl._limpiar_linea_transcripcion("[00:10] [♪] Hola amigos [♪]") == "[00:10] Hola amigos"
    assert dl._limpiar_linea_transcripcion("♪ Bienvenidos al tutorial ♪") == "Bienvenidos al tutorial"
    assert dl._limpiar_linea_transcripcion("[01:23:45] [Aplausos] Gracias a todos.") == "[01:23:45] Gracias a todos."

def test_context_menu_has_transcription(wx_app):
    import ui
    frame = ui.MainFrame()
    # Mockear un vídeo en resultados
    video_item = {
        'id': 'test1',
        'title': 'Vídeo Test',
        'url': 'https://www.youtube.com/watch?v=test1',
        'channel': 'Canal Test',
        'duration': '03:00',
        'is_channel': False,
        'is_playlist': False,
        'is_fav_list': False,
        'type': 'video'
    }
    frame.resultados = [video_item]
    frame.lista_resultados.InsertItem(0, video_item['title'])

    menu_labels = []
    def mock_popup(menu, *args, **kwargs):
        menu_labels.extend([item.GetItemLabelText() for item in menu.GetMenuItems()])
    frame.PopupMenu = mock_popup

    evt = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU)
    frame.on_context_menu(evt)
    
    assert any("transcripción a texto (.txt)" in it.lower() for it in menu_labels), f"El menú contextual debe incluir opción de transcripción: {menu_labels}"
    frame.Destroy()

