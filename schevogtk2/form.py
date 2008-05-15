"""Form classes.

For copyright, license, and warranty, see bottom of file.
"""

import sys
from schevo.lib import optimize

import gtk
from gtk import gdk

import schevo.base
from schevo.label import label

from schevogtk2.action import get_method_action
from schevogtk2.field import FieldLabel, DynamicField
from schevogtk2 import plugin
from schevogtk2.utils import gsignal


class FormBox(gtk.VBox):

    def __init__(self):
        super(FormBox, self).__init__()
        self.field_widgets = {}
        self.set_border_width(10)
        self.set_spacing(10)
        self.header = gtk.Label()
        self.pack_start(self.header, expand=False, fill=False, padding=0)
        self.header_sep = gtk.HSeparator()
        self.pack_start(self.header_sep, expand=False, fill=False, padding=0)
        self.table = None

    def set_fields(self, db, fields, get_value_handlers, set_field_handlers):
        field_count = len(fields)
        if field_count > 0:
            self.table = get_table(db, fields, self.field_widgets,
                                   get_value_handlers, set_field_handlers)
            self.table.show()
            self.pack_start(self.table, expand=True, fill=True, padding=0)

    def set_header_text(self, text):
        self.header.set_text(text)
        self.header.show()
        self.header_sep.show()


class FormWindow(gtk.Window):

    def __init__(self):
        super(FormWindow, self).__init__()
        self._bindings = {}
        self._db = None
        self._model = None
        self.tx_result = None
        self.vbox = vbox = gtk.VBox()
        vbox.set_spacing(5)
        vbox.set_border_width(5)
        self.set_default_size(400, -1)
        vbox.show()
        self.form_box = fbox = FormBox()
        fbox.show()
        self.footer_sep = fsep = gtk.HSeparator()
        fsep.show()
        self.button_box = bbox = gtk.HButtonBox()
        bbox.set_layout(gtk.BUTTONBOX_END)
        bbox.set_spacing(5)
        bbox.show()
        self.ok_button = button = gtk.Button(stock=gtk.STOCK_OK)
        button.connect('clicked', self.on_ok_button__clicked)
        self.button_box.add(button)
        self.cancel_button = button = gtk.Button(stock=gtk.STOCK_CANCEL)
        button.connect('clicked', self.on_cancel_button__clicked)
        self.button_box.add(button)
        self.close_button = button = gtk.Button(stock=gtk.STOCK_CLOSE)
        button.connect('clicked', self.on_close_button__clicked)
        self.button_box.add(button)
        vbox.pack_start(fbox, expand=True, fill=True, padding=0)
        vbox.pack_start(fsep, expand=False, fill=False, padding=0)
        vbox.pack_start(bbox, expand=False, fill=True, padding=0)
        self.add(vbox)
        self.connect('hide', self.quit)
        self.connect('key-press-event', self._on_key_press_event)
        self._set_bindings()

    def on_cancel_button__clicked(self, widget):
        self.hide()

    def on_close_button__clicked(self, widget):
        self.hide()

    def _on_key_press_event(self, window, event):
        keyval = event.keyval
        mask = event.state & gdk.MODIFIER_MASK
        binding = (keyval, mask)
        if binding in self._bindings:
            func = self._bindings[binding]
            func()

    def on_ok_button__clicked(self, widget):
        tx = self._model
        for name, widget in self.form_box.field_widgets.items():
            field = tx.f[name]
            if field.readonly:
                continue
            value = widget.get_value()
            try:
                setattr(tx, name, value)
            except Exception, e:
                show_error(self, Exception, e)
                return
        try:
            self.tx_result = self._db.execute(tx)
        except Exception, e:
            show_error(self, Exception, e)
            if not hasattr(sys, 'frozen'):
                raise
        except:
            raise
        else:
            self.hide()

    def quit(self, *args):
        gtk.main_quit()

    def run(self):
        self.show()
        gtk.main()

    def _set_bindings(self):
        items = [
            ('<Control>F4', self.hide),
            ('Escape', self.hide),
            ]
        self._bindings = dict([(gtk.accelerator_parse(name), func)
                               for name, func in items])
        # Hack to support these with CapsLock on.
        for name, func in items:
            keyval, mod = gtk.accelerator_parse(name)
            mod = mod | gtk.gdk.LOCK_MASK
            self._bindings[(keyval, mod)] = func

    def set_db(self, db):
        self._db = db

    def set_header_text(self, text):
        self.form_box.set_header_text(text)

    def set_fields(self, model, fields, get_value_handlers, set_field_handlers):
        self._model = model
        self.form_box.set_fields(self._db, fields,
                                 get_value_handlers, set_field_handlers)
        if isinstance(model, schevo.base.Transaction):
            self.ok_button.show()
            self.cancel_button.show()
            self.close_button.hide()
        else:
            self.ok_button.hide()
            self.cancel_button.hide()
            self.close_button.show()


class ExtentChoiceBox(gtk.VButtonBox):

    def __init__(self, allowed_extents):
        super(ExtentChoiceBox, self).__init__()
        group = None
        self.selected_extent = None
        for extent in allowed_extents:
            button = gtk.RadioButton(group, label(extent), use_underline=False)
            if group is None:
                # First in the list, so make it the group and the
                # selected extent.
                group = button
                self.selected_extent = extent
                button.props.active = True
            button.connect('toggled', self.on_radio_button__toggled, extent)
            button.show()
            self.add(button)

    def on_radio_button__toggled(self, button, extent):
        self.selected_extent = extent


class ExtentChoiceWindow(gtk.Window):

    def __init__(self, allowed_extents):
        super(ExtentChoiceWindow, self).__init__()
        self.set_default_size(300, -1)
        self.vbox = vbox = gtk.VBox()
        vbox.set_spacing(5)
        vbox.set_border_width(5)
        vbox.show()
        self.extent_choice_box = ecbox = ExtentChoiceBox(allowed_extents)
        ecbox.show()
        self.footer_sep = fsep = gtk.HSeparator()
        fsep.show()
        self.button_box = bbox = gtk.HButtonBox()
        bbox.set_layout(gtk.BUTTONBOX_END)
        bbox.set_spacing(5)
        bbox.show()
        self.ok_button = button = gtk.Button(stock=gtk.STOCK_OK)
        button.connect('clicked', self.on_ok_button__clicked)
        bbox.add(button)
        button.show()
        self.cancel_button = button = gtk.Button(stock=gtk.STOCK_CANCEL)
        button.connect('clicked', self.on_cancel_button__clicked)
        bbox.add(button)
        button.show()
        vbox.pack_start(ecbox, expand=True, fill=True, padding=0)
        vbox.pack_start(fsep, expand=False, fill=False, padding=0)
        vbox.pack_start(bbox, expand=False, fill=True, padding=0)
        self.add(vbox)
        self.connect('hide', self.quit)

    @property
    def selected_extent(self):
        return self.extent_choice_box.selected_extent
        
    def on_cancel_button__clicked(self, widget):
        # If cancelled or closed, even if the user selected an extent,
        # ignore it.
        self.extent_choice_box.selected_extent = None
        self.hide()

    def on_ok_button__clicked(self, widget):
        self.hide()

    def quit(self, *args):
        gtk.main_quit()

    def run(self):
        self.show()
        gtk.main()

        
def get_custom_tx_dialog(WindowClass, parent, db, tx):
    dialog = WindowClass(db, tx)
    window = dialog.toplevel
    window.set_modal(True)
    window.set_transient_for(parent)
    window.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
    return dialog

def get_default_tx_dialog(parent, db, tx,
                          get_value_handlers, set_field_handlers):
    extent_name = tx.sys.extent_name
    if extent_name is None:
        title = u'%s' % label(tx)
        text = u'%s' % label(tx)
    else:
        title = u'%s :: %s' % (label(tx), extent_name)
        text = u'%s :: %s' % (label(tx), extent_name)
    field_map = tx.sys.field_map()
    fields = field_map.values()
    fields = [field for field in fields if not field.hidden]
    dialog = get_dialog(title, parent, text, db, tx, fields,
                        get_value_handlers, set_field_handlers)
    return dialog

def get_dialog(title, parent, text, db, model, fields,
               get_value_handlers, set_field_handlers):
    # Create the form window and set its basic properties.
    window = FormWindow()
    window.set_db(db)
    window.set_modal(True)
    window.set_transient_for(parent)
    window.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
    window.set_title(title)
    window.set_header_text(text)
    # Populate its fields.
    fields = [field for field in fields if not field.hidden]
    fields_dict = dict((field.name, field) for field in fields)
    window.set_fields(model, fields, get_value_handlers, set_field_handlers)
    # Attach create-clicked and update-clicked handlers to each of its
    # fields.
    for name, widget in window.form_box.field_widgets.iteritems():
        def on_create_clicked(dynamic_field, allowed_extents,
                              name=name, widget=widget):
            if len(allowed_extents) == 1:
                # If only one extent, simply use that extent.
                extent = allowed_extents[0]
            else:
                # If >1 extent, ask the user for an extent first.
                dialog = ExtentChoiceWindow(allowed_extents)
                dialog.set_modal(True)
                dialog.set_transient_for(window)
                dialog.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
                dialog.run()
                extent = dialog.selected_extent
                dialog.destroy()
            # User may not have chosen an extent.  Only continue if
            # they have. Otherwise do nothing.
            if extent is not None:
                action = get_method_action(extent, 't', 'create')
                create_tx = action.method()
                dialog = get_tx_dialog(
                    parent = window,
                    db = db,
                    tx = create_tx,
                    action = action,
                    get_value_handlers = get_value_handlers,
                    set_field_handlers = set_field_handlers,
                    )
                dialog.run()
                tx_result = dialog.tx_result
                dialog.destroy()
                if tx_result is not None:
                    field = fields_dict[name]
                    field.set(tx_result)
                    widget.set_field(db, field)
        widget.connect('create-clicked', on_create_clicked)
        def on_update_clicked(dynamic_field, entity_to_update,
                              name=name, widget=widget):
            action = get_method_action(entity_to_update, 't', 'update')
            update_tx = action.method()
            dialog = get_tx_dialog(
                parent = window,
                db = db,
                tx = update_tx,
                action = action,
                get_value_handlers = get_value_handlers,
                set_field_handlers = set_field_handlers,
                )
            dialog.run()
            tx_result = dialog.tx_result
            dialog.destroy()
            if tx_result is not None:
                field = fields_dict[name]
                field.set(tx_result)
                widget.set_field(db, field)
        widget.connect('update-clicked', on_update_clicked)
    return window

def get_table(db, fields, field_widgets,
              get_value_handlers, set_field_handlers):
    """Return a gtk.Table widget containing labels and dynamic field widgets
    for each field given.
    
    - `db`: The database containing the fields.
    
    - `fields`: Sequence of Schevo field instances to create widgets for.
    
    - `field_widgets`: Dictionary that is updated to store
      field-name:field-widget pairs as the field widgets are created.

    - `get_value_handlers`: A list of handlers to use when calling the
      `get_value` method of a `DynamicField` widget.

    - `set_field_handlers`: A list of handlers to use when calling the
      `set_value` method of a `DynamicField` widget.
    """
    field_count = len(fields)
    table = gtk.Table(rows=field_count, columns=2)
    table.set_row_spacings(5)
    table.set_col_spacings(5)
    row = 0
    for field in fields:
        # Skip hidden fields.
        if field.hidden:
            continue
        # Label.
        label_box = FieldLabel()
        label_box.set_field(db, field)
        label_box.show()
        # Widget.
        widget_box = DynamicField(get_value_handlers, set_field_handlers)
        widget_box.set_field(db, field)
        widget_box.show()
        # Attach to table.
        xoptions = gtk.FILL
        yoptions = gtk.FILL
        table.attach(label_box, 0, 1, row, row+1, xoptions, yoptions)
        xoptions = gtk.EXPAND|gtk.FILL
        yoptions = gtk.FILL
        if widget_box.expand:
            yoptions = gtk.EXPAND|gtk.FILL
        table.attach(widget_box, 1, 2, row, row+1, xoptions, yoptions)
        field_widgets[field.name] = widget_box
        row += 1
    return table

def get_tx_dialog(parent, db, tx, action,
                  get_value_handlers, set_field_handlers):
    WindowClass = plugin.get_custom_tx_dialog_class(db, action)
    if WindowClass is None:
        dialog = get_default_tx_dialog(
            parent, db, tx,
            get_value_handlers, set_field_handlers,
            )
    else:
        dialog = get_custom_tx_dialog(WindowClass, parent, db, tx)
    return dialog

def get_view_dialog(parent, db, entity, action,
                    get_value_handlers, set_field_handlers):
    extent_text = label(entity.sys.extent)
    title = u'View :: %s' % (extent_text, )
    text = u'View :: %s :: %s' % (extent_text, entity)
    def include(field):
        if action.include_expensive:
            return True
        elif field.expensive:
            return False
        else:
            return True
    f_map = entity.sys.field_map(include)
    fields = f_map.values()
    dialog = get_dialog(title, parent, text, db, entity, fields,
                        get_value_handlers, set_field_handlers)
    return dialog

def show_error(parent, exception, e):
    flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT
    win = gtk.MessageDialog(parent=parent, flags=flags,
                            type=gtk.MESSAGE_ERROR,
                            buttons=gtk.BUTTONS_CLOSE,
                            message_format=str(e))
##     title = 'Error: %s' % (exception, )
##     win.set_title(title)
    win.run()
    win.destroy()


##         scrolled_window = gtk.ScrolledWindow()
##         scrolled_window.show()
##         vbox = gtk.VBox(spacing=4)
##         vbox.set_border_width(4)
##         vbox.show()
##         table = gtk.Table(rows=3, columns=2, homogeneous=False)
##         table.show()
##         vbox.pack_start(table, expand=False, fill=True, padding=0)
##         viewport = gtk.Viewport()
##         viewport.show()
##         viewport.set_shadow_type(gtk.SHADOW_NONE)
##         viewport.add(vbox)
##         scrolled_window.add(viewport)


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
