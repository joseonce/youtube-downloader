"""
Punto de entrada principal para el Descargador de YouTube.
"""

import sys
import os
import wx

# Asegurar que el directorio del proyecto esté en sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import accessibility
import sound_manager
from ui import MainFrame


class YouTubeApp(wx.App):
    def OnInit(self):
        # Configurar idioma en castellano (español) para wxWidgets / wxPython
        try:
            possible_dirs = []
            if getattr(sys, 'frozen', False):
                if hasattr(sys, '_MEIPASS'):
                    possible_dirs.append(os.path.join(sys._MEIPASS, 'wx', 'locale'))
                    possible_dirs.append(os.path.join(sys._MEIPASS, 'locale'))
                exe_dir = os.path.dirname(sys.executable)
                possible_dirs.append(os.path.join(exe_dir, 'wx', 'locale'))
                possible_dirs.append(os.path.join(exe_dir, 'locale'))
            else:
                try:
                    possible_dirs.append(os.path.join(os.path.dirname(wx.__file__), 'locale'))
                except Exception:
                    pass

            for d in possible_dirs:
                if os.path.exists(d):
                    wx.Locale.AddCatalogLookupPathPrefix(d)

            self.locale = wx.Locale(wx.LANGUAGE_SPANISH)
            if not self.locale.IsOk():
                self.locale = wx.Locale(wx.LANGUAGE_SPANISH_MODERN)
            if not self.locale.IsOk():
                self.locale = wx.Locale(wx.LANGUAGE_DEFAULT)
            self.locale.AddCatalog('wxstd')
        except Exception:
            self.locale = None

        # Inicializar subsistema de accesibilidad
        accessibility.init_accessibility()
        
        # Crear y mostrar la ventana principal
        self.frame = MainFrame()
        self.SetTopWindow(self.frame)
        self.frame.Show(True)
        wx.CallAfter(self._confirm_update_ready)
        return True

    def _confirm_update_ready(self):
        """Confirmar al instalador que la interfaz ya procesa eventos."""
        ready = os.environ.pop("YT_UPDATE_READY", None)
        if ready:
            try:
                with open(ready, "w", encoding="utf-8") as stream:
                    stream.write("ready")
            except OSError:
                pass

    def OnExit(self):
        try:
            sound_manager.stop_waiting_sound()
        except Exception:
            pass
        accessibility.shutdown_accessibility()
        try:
            if 'pythoncom' in sys.modules:
                import pythoncom
                pythoncom.CoUninitialize()
        except Exception:
            pass
        return super().OnExit()




def main():
    app = YouTubeApp(False)
    app.MainLoop()


if __name__ == '__main__':
    main()
