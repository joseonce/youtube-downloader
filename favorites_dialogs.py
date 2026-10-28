"""
Diálogos para selección, cambio y gestión de listas de favoritos.
"""

import wx

import accessibility
from favorites_manager import (
    obtener_nombres_listas_favoritos,
    crear_lista_favoritos,
    obtener_listas_de_item
)

class SelectFavoriteListDialog(wx.Dialog):
    """Diálogo accesible para elegir en qué lista de favoritos guardar o crear una nueva."""
    def __init__(self, parent, video_title=""):
        super().__init__(parent, title="Guardar en Favoritos", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        nombres = obtener_nombres_listas_favoritos()
        self.selected_list_name = nombres[0] if nombres else "Principal"
        opciones = list(nombres) + ["[+] Crear nueva lista..."]
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        lbl_info = wx.StaticText(self, label=f"Selecciona la lista donde deseas guardar:\n{video_title}")
        sizer.Add(lbl_info, 0, wx.ALL, 10)
        
        lbl_list = wx.StaticText(self, label="&Listas de favoritos disponibles:")
        sizer.Add(lbl_list, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        
        self.listbox = wx.ListBox(self, choices=opciones, style=wx.LB_SINGLE)
        self.listbox.SetSelection(0)
        self.listbox.Bind(wx.EVT_LISTBOX_DCLICK, self.on_ok)
        sizer.Add(self.listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        
        row_btn = wx.BoxSizer(wx.HORIZONTAL)
        btn_ok = wx.Button(self, wx.ID_OK, "&Guardar")
        btn_ok.SetDefault()
        btn_ok.Bind(wx.EVT_BUTTON, self.on_ok)
        row_btn.Add(btn_ok, 0, wx.RIGHT, 8)
        
        btn_cancel = wx.Button(self, wx.ID_CANCEL, "&Cancelar")
        row_btn.Add(btn_cancel, 0)
        
        sizer.Add(row_btn, 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 10)
        
        self.SetSizer(sizer)
        self.SetSize((440, 320))
        self.CenterOnParent()

    def on_ok(self, event):
        sel_idx = self.listbox.GetSelection()
        if sel_idx == wx.NOT_FOUND:
            return
        
        total = self.listbox.GetCount()
        if sel_idx == total - 1:
            # Opción "[+] Crear nueva lista..."
            dlg = wx.TextEntryDialog(self, "Introduce el nombre de la nueva lista de favoritos:", "Nueva lista de favoritos")
            if dlg.ShowModal() == wx.ID_OK:
                nombre = dlg.GetValue().strip()
                dlg.Destroy()
                if not nombre:
                    wx.MessageBox("El nombre de la lista no puede estar vacío.", "Aviso", wx.OK | wx.ICON_WARNING, self)
                    return
                crear_lista_favoritos(nombre)
                self.selected_list_name = nombre
                self.EndModal(wx.ID_OK)
            else:
                dlg.Destroy()
                return
        else:
            self.selected_list_name = self.listbox.GetString(sel_idx)
            self.EndModal(wx.ID_OK)


class ChangeFavoriteListDialog(wx.Dialog):
    """Diálogo accesible para cambiar un elemento de una lista de favoritos a otra o crear una nueva."""
    def __init__(self, parent, video_title="", lista_actual=""):
        super().__init__(parent, title="Cambiar de lista de favoritos", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.selected_list_name = None
        self.lista_actual = lista_actual

        nombres = obtener_nombres_listas_favoritos()
        opciones = list(nombres) + ["[+] Crear nueva lista..."]

        sizer = wx.BoxSizer(wx.VERTICAL)

        info_text = f"Mover a otra lista:\n{video_title}"
        if lista_actual:
            info_text += f"\n(Lista actual: {lista_actual})"
        lbl_info = wx.StaticText(self, label=info_text)
        sizer.Add(lbl_info, 0, wx.ALL, 10)

        lbl_list = wx.StaticText(self, label="&Selecciona la lista de destino:")
        sizer.Add(lbl_list, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        self.listbox = wx.ListBox(self, choices=opciones, style=wx.LB_SINGLE)
        # Seleccionar la primera lista distinta a la actual si es posible
        sel_idx = 0
        if lista_actual and lista_actual in opciones:
            for idx, opc in enumerate(opciones):
                if opc != lista_actual:
                    sel_idx = idx
                    break
        self.listbox.SetSelection(sel_idx)
        self.listbox.Bind(wx.EVT_LISTBOX_DCLICK, self.on_ok)
        sizer.Add(self.listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        row_btn = wx.BoxSizer(wx.HORIZONTAL)
        btn_ok = wx.Button(self, wx.ID_OK, "&Mover")
        btn_ok.SetDefault()
        btn_ok.Bind(wx.EVT_BUTTON, self.on_ok)
        row_btn.Add(btn_ok, 0, wx.RIGHT, 8)

        btn_cancel = wx.Button(self, wx.ID_CANCEL, "&Cancelar")
        row_btn.Add(btn_cancel, 0)

        sizer.Add(row_btn, 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 10)

        self.SetSizer(sizer)
        self.SetSize((440, 340))
        self.CenterOnParent()

    def on_ok(self, event):
        sel_idx = self.listbox.GetSelection()
        if sel_idx == wx.NOT_FOUND:
            return

        total = self.listbox.GetCount()
        if sel_idx == total - 1:
            # Opción "[+] Crear nueva lista..."
            dlg = wx.TextEntryDialog(self, "Introduce el nombre de la nueva lista de favoritos:", "Nueva lista de favoritos")
            if dlg.ShowModal() == wx.ID_OK:
                nombre = dlg.GetValue().strip()
                dlg.Destroy()
                if not nombre:
                    wx.MessageBox("El nombre de la lista no puede estar vacío.", "Aviso", wx.OK | wx.ICON_WARNING, self)
                    return
                crear_lista_favoritos(nombre)
                self.selected_list_name = nombre
                self.EndModal(wx.ID_OK)
            else:
                dlg.Destroy()
                return
        else:
            self.selected_list_name = self.listbox.GetString(sel_idx)
            self.EndModal(wx.ID_OK)


class ViewFavoritesChoiceDialog(wx.Dialog):
    """Diálogo accesible para elegir qué lista de favoritos ver o reproducir."""
    def __init__(self, parent, action_label="Ver"):
        super().__init__(parent, title=f"{action_label} lista de Favoritos", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.selected_list = None
        
        nombres = obtener_nombres_listas_favoritos()
        opciones = ["Todas las listas"] + list(nombres)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        lbl = wx.StaticText(self, label=f"Elige la lista de favoritos que deseas {action_label.lower()}:")
        sizer.Add(lbl, 0, wx.ALL, 10)
        
        self.listbox = wx.ListBox(self, choices=opciones, style=wx.LB_SINGLE)
        self.listbox.SetSelection(0)
        self.listbox.Bind(wx.EVT_LISTBOX_DCLICK, self.on_ok)
        sizer.Add(self.listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        
        row_btn = wx.BoxSizer(wx.HORIZONTAL)
        btn_ok = wx.Button(self, wx.ID_OK, f"&{action_label}")
        btn_ok.SetDefault()
        btn_ok.Bind(wx.EVT_BUTTON, self.on_ok)
        row_btn.Add(btn_ok, 0, wx.RIGHT, 8)
        
        btn_cancel = wx.Button(self, wx.ID_CANCEL, "&Cancelar")
        row_btn.Add(btn_cancel, 0)
        
        sizer.Add(row_btn, 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 10)
        self.SetSizer(sizer)
        self.SetSize((400, 290))
        self.CenterOnParent()
        
    def on_ok(self, event):
        sel_idx = self.listbox.GetSelection()
        if sel_idx != wx.NOT_FOUND:
            self.selected_list = self.listbox.GetString(sel_idx)
            self.EndModal(wx.ID_OK)

