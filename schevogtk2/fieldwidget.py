"""Schevo specific field widget classes.

For copyright, license, and warranty, see bottom of file.
"""

import sys
from schevo.lib import optimize

from xml.sax.saxutils import escape
import os

if os.name == 'nt':
    import pywintypes
    import win32con
    import win32gui

import gtk

import schevo.field
from schevo.label import label
from schevo.base import Entity
from schevo.constant import UNASSIGNED

from schevogtk2 import icon
from schevogtk2.utils import gsignal, type_register


class EntityChooser(gtk.HBox):

    __gtype_name__ = 'EntityChooser'

    gsignal('create-clicked', object) # 'object' is list of allowable extents
    gsignal('update-clicked', object) # 'object' is entity to update
    gsignal('value-changed')

    def __init__(self, db, field, show_buttons=True):
        super(EntityChooser, self).__init__()
        self.db = db
        self.field = field
        # By default, there are no create and update buttons.
        self._create_button = None
        self._update_button = None
        # Always add the combobox.
        combobox = self._entity_combobox = EntityComboBox(db, field)
        self.add(combobox)
        combobox.show()
        combobox.connect('value-changed', self._on_value_changed)
        # Also create create/update buttons if the entity field allows.
        if show_buttons and isinstance(field, schevo.field.Entity):
            if field.allow_create:
                # Determine the allowed extents.
                if len(field.allow) == 0:
                    # Any extent that is not hidden, and whose create
                    # transaction is not hidden, is available.
                    allowed_extents = [
                        extent for extent in db.extents() if not extent.hidden]
                else:
                    allowed_extents = [
                        db.extent(name) for name in sorted(field.allow)]
                # Filter out extents where t.create is hidden.
                allowed_extents = self._create_button_allowed_extents = [
                    extent for extent in allowed_extents
                    if 'create' in extent.t
                    ]
                # Only create the button if there is at least one
                # allowed extent.
                if allowed_extents:
                    button = self._create_button = gtk.Button(label='+')
                    self.pack_end(button, expand=False, fill=False)
                    button.show()
                    button.connect('clicked', self._on_create_button__clicked)
            if field.allow_update:
                button = self._update_button = gtk.Button(label='U')
                self.pack_end(button, expand=False, fill=False)
                button.show()
                button.connect('clicked', self._on_update_button__clicked)
                self._reset_update_button_sensitivity()

    def get_selected(self):
        """Return the currently selected Schevo object."""
        return self._entity_combobox.get_selected()

    def _on_create_button__clicked(self, widget):
        db = self.db
        field = self.field
        self.emit('create-clicked', self._create_button_allowed_extents)

    def _on_update_button__clicked(self, widget):
        entity_to_update = self.get_selected()
        self.emit('update-clicked', entity_to_update)
    
    def _on_value_changed(self, widget):
        self.emit('value-changed')
        self._reset_update_button_sensitivity()

    def _reset_update_button_sensitivity(self):
        """Update the `_update_button` sensitivity based on whether or not the
        current value of the combobox is alowed to be updated."""
        button = self._update_button
        if button is not None:
            selected = self.get_selected()
            # UNASSIGNED.
            if selected is UNASSIGNED:
                button.set_sensitive(False)
            # Entity.
            elif isinstance(selected, Entity):
                button.set_sensitive('update' in selected.t)
        
type_register(EntityChooser)
        

class EntityComboBox(gtk.ComboBox):

    __gtype_name__ = 'EntityComboBox'

    gsignal('value-changed')

    def __init__(self, db, field):
        super(EntityComboBox, self).__init__()
        self.db = db
        self.field = field
        self.model = gtk.ListStore(str, object)
        self.set_row_separator_func(self.is_row_separator)
        self._populate()
        self.set_model(self.model)
##         self.set_text_column(0)
        cell = self.cell_pb = gtk.CellRendererPixbuf()
        self.pack_start(cell, False)
        self.set_cell_data_func(cell, self.cell_icon)
##         self.reorder(cell, 0)
        cell = self.cell_text = gtk.CellRendererText()
        self.pack_start(cell)
        self.add_attribute(cell, 'text', 0)
##         self.completion = comp = gtk.EntryCompletion()
##         comp.set_model(self.model)
##         cell = self.comp_pb = gtk.CellRendererPixbuf()
##         comp.pack_start(cell, False)
##         comp.set_cell_data_func(cell, self.cell_icon)
##         comp.set_text_column(0)
##         self.entry = entry = self.child
##         entry.set_completion(comp)
##         entry.set_text(str(field.get()))
##         entry.connect('activate', self._on_entry__activate)
##         entry.connect('changed', self._on_entry__changed)
        self.select_item_by_data(field.get())
        self.connect('changed', self._on_changed)

    def cell_icon(self, layout, cell, model, row):
        entity = model[row][1]
        if entity in (UNASSIGNED, None):
            cell.set_property('stock_id', gtk.STOCK_NO)
            cell.set_property('stock_size', gtk.ICON_SIZE_SMALL_TOOLBAR)
            cell.set_property('visible', False)
        else:
            extent = entity.sys.extent
            pixbuf = icon.small_pixbuf(self, extent)
            cell.set_property('pixbuf', pixbuf)
            cell.set_property('visible', True)

    def get_selected(self):
        """Return the currently selected Schevo object."""
        iter = self.get_active_iter()
        if iter:
            return self.model[iter][1]

    def is_row_separator(self, model, row):
        text, entity = model[row]
        if text is None and entity is None:
            return True
        return False

    def select_item_by_data(self, data):
        for row in self.model:
            if row[1] == data:
                self.set_active_iter(row.iter)
                break

    def _on_changed(self, widget):
        self.emit('value-changed')

##     def _on_entry__activate(self, entry):
##         self.emit('activate')

##     def _on_entry__changed(self, entry):
##         self.emit('value-changed')

    def _populate(self):
        db = self.db
        field = self.field
        allow = field.allow
        if len(allow) > 1:
            allow_multiple = True
        else:
            allow_multiple = False
        items = []
        values = []
        # Unassigned.
        items.append((u'<UNASSIGNED>', UNASSIGNED))
        values.append(UNASSIGNED)
        # Preferred values.
        preferred_values = field.preferred_values or []
        if preferred_values:
            values.extend(preferred_values)
            more = []
            for entity in sorted(preferred_values):
                if entity is UNASSIGNED:
                    continue
                if allow_multiple:
                    extent_text = label(entity.sys.extent)
                    text = u'%s :: %s' % (entity, extent_text)
                else:
                    text = u'%s' % (entity, )
                more.append((text, entity))
            items.extend(more)
            # Row separator.
            items.append((None, None))
        # Valid values.
        more = []
        valid_values = field.valid_values
        if valid_values is not None:
            # Specific valid values.
            values.extend(valid_values)
            for entity in sorted(valid_values):
                if entity is UNASSIGNED:
                    continue
                if entity in preferred_values:
                    continue
                if allow_multiple:
                    extent_text = label(entity.sys.extent)
                    text = u'%s :: %s' % (entity, extent_text)
                else:
                    text = u'%s' % (entity, )
                more.append((text, entity))
        else:
            # Other allowed values.
            for extent_name in field.allow:
                extent = db.extent(extent_name)
                for entity in sorted(extent):
                    if entity in preferred_values:
                        continue
                    values.append(entity)
                    if allow_multiple:
                        extent_text = label(extent)
                        text = u'%s :: %s' % (entity, extent_text)
                    else:
                        text = u'%s' % (entity, )
                    more.append((text, entity))
        items.extend(more)
        value = field.get()
        if value not in values:
            entity = value
            # Row separator.
            items.append((None, None))
            # Invalid, but current value.
            if allow_multiple:
                extent_text = label(entity.sys.extent)
                text = u'%s :: %s' % (entity, extent_text)
            else:
                text = u'%s' % (entity, )
            items.append((text, entity))
        # Update the model.
        model = self.model
        model.clear()
        for text, entity in items:
            model.append((text, entity))

type_register(EntityComboBox)


class FileChooser(gtk.EventBox):

    __gtype_name__ = 'FileChooser'

    gsignal('value-changed')

    def __init__(self, db, field):
        super(FileChooser, self).__init__()
        self.db = db
        self.field = field
        if os.name == 'nt':
            if field.file_only:
                stock_id = gtk.STOCK_FILE
            elif field.directory_only:
                stock_id = gtk.STOCK_DIRECTORY
            self._hbox = hbox = gtk.HBox()
            hbox.show()
            self._entry = entry = gtk.Entry()
            entry.show()
            self._button = button = gtk.Button()
            button.show()
            image = gtk.Image()
            image.show()
            image.set_from_stock(stock_id, gtk.ICON_SIZE_MENU)
            button.add(image)
            hbox.pack_start(entry)
            hbox.pack_start(button, expand=False)
            button.connect('clicked', self._on_clicked)
            entry.connect('activate', self._on_changed)
            self.add(hbox)
        else:
            self._filechooser = chooser = gtk.FileChooserButton()
            chooser.show()
            chooser.connect('selection-changed', self._on_changed)
            self.add(chooser)

    def get_filename(self):
        if os.name == 'nt':
            return self._entry.get_text()
        else:
            return self._filechooser.get_filename()

    def set_filename(self, filename):
        if os.name == 'nt':
            self._entry.set_text(filename)
        else:
            return self._filechooser.set_filename(filename)

    def _on_changed(self, widget):
        self.emit('value-changed')

    def _on_clicked(self, widget):
        field = self.field
        filename = None
        file_ext_filter = 'Schevo Database Files\0*.db;*.schevo\0'
        file_custom_filter = 'All Files\0*.*\0'
        file_open_title = 'Select File'
        if field.file_only:
            try:
                filename, custom_filter, flags = win32gui.GetSaveFileNameW(
                    InitialDir='.',
                    Flags=win32con.OFN_EXPLORER,
                    Title='Select'
##                     File='',
##                     DefExt='',
##                     Title=self.file_open_title,
##                     Filter=self.file_ext_filter,
##                     CustomFilter=self.file_custom_filter,
##                     FilterIndex=1,
                    )
            except pywintypes.error:
                # Cancel button raises an exception.
                pass
        elif field.directory_only:
            try:
                filename, custom_filter, flags = win32gui.GetSaveFileNameW(
                    InitialDir='.',
                    Flags=win32con.OFN_EXPLORER,
                    Title='Select'
##                     File='',
##                     DefExt='',
##                     Title=self.file_open_title,
##                     Filter=self.file_ext_filter,
##                     CustomFilter=self.file_custom_filter,
##                     FilterIndex=1,
                    )
            except pywintypes.error:
                # Cancel button raises an exception.
                pass
        if filename is not None:
            self.set_filename(filename)

type_register(FileChooser)


class ValueChooser(gtk.ComboBox):

    __gtype_name__ = 'ValueChooser'

    gsignal('value-changed')

    def __init__(self, db, field):
        super(ValueChooser, self).__init__()
        self.db = db
        self.field = field
        self.model = gtk.ListStore(str, object)
        self.set_row_separator_func(self.is_row_separator)
        self._populate()
        self.set_model(self.model)
##         cell = self.cell_pb = gtk.CellRendererPixbuf()
##         self.pack_start(cell, False)
##         self.set_cell_data_func(cell, self.cell_icon)
        cell = self.cell_text = gtk.CellRendererText()
        self.pack_start(cell)
        self.add_attribute(cell, 'text', 0)
        self.select_item_by_data(field.get())
        self.connect('changed', self._on_changed)

##     def cell_icon(self, layout, cell, model, row):
##         entity = model[row][1]
##         if entity in (UNASSIGNED, None):
##             cell.set_property('stock_id', gtk.STOCK_NO)
##             cell.set_property('stock_size', gtk.ICON_SIZE_SMALL_TOOLBAR)
##             cell.set_property('visible', False)
##         else:
##             extent = entity.sys.extent
##             pixbuf = icon.small_pixbuf(self, extent)
##             cell.set_property('pixbuf', pixbuf)
##             cell.set_property('visible', True)

    def get_selected(self):
        iter = self.get_active_iter()
        if iter:
            return self.model[iter][1]

    def is_row_separator(self, model, row):
        text, entity = model[row]
        if text is None and entity is None:
            return True
        return False

    def select_item_by_data(self, data):
        for row in self.model:
            if row[1] == data:
                self.set_active_iter(row.iter)
                break

    def _on_changed(self, widget):
        self.emit('value-changed')

##     def _on_entry__activate(self, entry):
##         self.emit('activate')

##     def _on_entry__changed(self, entry):
##         self.emit('value-changed')

    def _populate(self):
        db = self.db
        field = self.field
        items = []
        values = []
        # Unassigned.
        items.append((u'<UNASSIGNED>', UNASSIGNED))
        values.append(UNASSIGNED)
        # Preferred values.
        preferred_values = field.preferred_values or []
        if preferred_values:
            values.extend(preferred_values)
            more = []
            for value in sorted(preferred_values):
                if value is UNASSIGNED:
                    continue
                more.append((unicode(value), value))
            items.extend(more)
            # Row separator.
            items.append((None, None))
        # Valid values.
        more = []
        valid_values = field.valid_values
        values.extend(valid_values)
        for value in sorted(valid_values):
            if value is UNASSIGNED:
                continue
            if value in preferred_values:
                continue
            more.append((unicode(value), value))
        items.extend(more)
        value = field.get()
        if value not in values:
            # Row separator.
            items.append((None, None))
            # Invalid, but current value.
            items.append((unicode(value), value))
        # Update the model.
        model = self.model
        model.clear()
        for text, value in items:
            model.append((text, value))

type_register(ValueChooser)


optimize.bind_all(sys.modules[__name__])  # Last line of module.


# Copyright (C) 2001-2007 Orbtech, L.L.C.
#
# Schevo
# http://schevo.org/
#
# Orbtech
# Saint Louis, MO
# http://orbtech.com/
#
# This toolkit is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This toolkit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA