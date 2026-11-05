import os
import sys
import pytest
import wx

from config_manager import DEFAULT_CONFIG, cargar_configuracion, guardar_configuracion
from options_dialog import OptionsDialog
from player_dialog import VideoPreviewDialog
from ui import MainFrame

@pytest.fixture(scope="module")
def wx_app():
    app = wx.GetApp()
    if not app:
        app = wx.App(False)
    yield app

def test_default_config_new_options():
    assert 'reproductor_ventana_independiente' in DEFAULT_CONFIG
    assert 'cerrar_reproductor_al_finalizar' in DEFAULT_CONFIG
    assert DEFAULT_CONFIG['reproductor_ventana_independiente'] is True
    assert DEFAULT_CONFIG['cerrar_reproductor_al_finalizar'] is False

def test_options_dialog_saves_settings(wx_app):
    frame = wx.Frame(None, title="TestParent")
    dlg = OptionsDialog(frame)
    dlg.chk_auto_close_player.SetValue(True)
    dlg.chk_independent_window.SetValue(True)
    dlg.on_save(None)
    dlg.Destroy()
    frame.Destroy()

    cfg = cargar_configuracion()
    assert cfg['cerrar_reproductor_al_finalizar'] is True
    assert cfg['reproductor_ventana_independiente'] is True

    # restore
    cfg['cerrar_reproductor_al_finalizar'] = False
    guardar_configuracion(cfg)

def test_auto_close_on_finish(wx_app):
    cfg = cargar_configuracion()
    cfg['cerrar_reproductor_al_finalizar'] = True
    guardar_configuracion(cfg)

    videos = [{'title': 'Video 1', 'id': 'abc1', 'url': 'http://youtube.com/watch?v=abc1'}]
    dlg = VideoPreviewDialog(None, videos, initial_index=0)
    assert dlg.auto_close_on_finish is True

    # Call on_track_finished with 1 track (it should trigger close)
    dlg.on_track_finished()
    # cleanup
    dlg.on_cleanup()
    try:
        dlg.Destroy()
    except Exception:
        pass

    cfg['cerrar_reproductor_al_finalizar'] = False
    guardar_configuracion(cfg)

def test_independent_window_hierarchy(wx_app):
    cfg = cargar_configuracion()
    cfg['reproductor_ventana_independiente'] = True
    guardar_configuracion(cfg)

    frame = wx.Frame(None, title="TestParent")
    videos = [{'title': 'Video 1', 'id': 'abc1', 'url': 'http://youtube.com/watch?v=abc1'}]
    dlg = VideoPreviewDialog(frame, videos, initial_index=0)
    
    assert dlg.independent_window is True
    # In independent window mode, GetParent returns frame via _custom_parent
    assert dlg.GetParent() is frame
    dlg.on_cleanup()
    try:
        dlg.Destroy()
    except Exception:
        pass
    frame.Destroy()
