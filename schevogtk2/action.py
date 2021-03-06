"""Action class and helper functions."""

# Copyright (c) 2001-2009 ElevenCraft Inc.
# See LICENSE for details.

import sys
from schevo.lib import optimize

from schevo.base import Entity, Extent, View
from schevo.introspect import commontype, isselectionmethod
from schevo.label import label


DEFAULT_T_METHODS = ['clone', 'create', 'delete', 'update']

LABELS_WITH_SHORTCUTS = {
    # 'Label': '_Label',
    'Clone...': '_Clone...',
    'Delete...': '_Delete...',
    'Edit...': '_Edit...',
    'New...': '_New...',
    'View...': '_View...',
    }


class Action(object):

    db = None
    instance = None
    label = ''
    method = None
    name = ''
    related = None
    selection = None
    type = ''

    @property
    def label_with_shortcut(self):
        if self.label in LABELS_WITH_SHORTCUTS:
            return LABELS_WITH_SHORTCUTS[self.label]
        else:
            return self.label

    def __cmp__(self, other):
        try:
            return cmp(self.label, other.label)
        except AttributeError:
            return cmp(hash(self), hash(other))


def get_method_action(db, instance, namespace_id, method_name, related=None):
    """Return action for method name."""
    namespace = getattr(instance, namespace_id)
    method = namespace[method_name]
    method_label = label(method)
    action = Action()
    action.db = db
    action.instance = instance
    # Default label.
    action.label = u'%s...' % method_label
    if namespace_id == 't' and method_name in DEFAULT_T_METHODS:
        # Determine if there are any custom methods whose labels start
        # with the same string.
        t = action.instance.t
        other_found = False
        for other_name in t:
            if other_name not in DEFAULT_T_METHODS:
                other_label = label(t[other_name])
                if other_label.startswith(method_label):
                    other_found = True
        if other_found:
            # Custom labels, since there are custom methods that share
            # prefixes.
            if isinstance(instance, Entity):
                action.label = u'%s %s...' % (
                    method_label, label(instance.s.extent))
            elif isinstance(instance, Extent):
                action.label = u'%s %s...' % (method_label, label(instance))
            elif isinstance(instance, View):
                action.label = u'%s %s...' % (
                    method_label, label(instance.s.entity.s.extent))
    action.method = method
    action.name = method_name
    action.related = related
    if namespace_id == 'q':
        action.type = 'query'
    elif namespace_id == 't':
        action.type = 'transaction'
    return action


def get_relationship_actions(db, entity):
    """Return list of relationship actions for an entity instance."""
    actions = []
    if entity is not None:
        items = []
        if entity.s.extent.relationships:
            items = [
                'Relationships...',
                ]
        for text in items:
            action = Action()
            action.db = db
            action.instance = entity
            action.label = text
            action.name = 'relationship'
            action.type = 'relationship'
            actions.append(action)
    return sorted(actions)


def get_tx_actions(db, instance, related=None):
    """Return list of actions for an extent or entity instance."""
    actions = []
    if instance is not None:
        t_methods = set(instance.t)
        for method_name in sorted(t_methods):
            action = get_method_action(db, instance, 't', method_name, related)
            actions.append(action)
    return sorted(actions)


def get_tx_selectionmethod_actions(db, selection):
    """Return list of selectionmethod transactions for an extent."""
    cls = commontype(selection)
    if cls is None:
        return []
    else:
        if getattr(cls, '_hidden_t_selectionmethods', None) is not None:
            hidden = cls._hidden_t_selectionmethods(selection) or []
        else:
            hidden = []
        actions = []
        for method_name in sorted(cls.t):
            if method_name not in hidden:
                action = get_method_action(db, cls, 't', method_name)
                action.selection = selection
                actions.append(action)
        return sorted(actions)


def get_view_actions(db, entity):
    """Return list of view actions for an entity instance."""
    actions = []
    if entity is not None:
        if (entity._hidden_views is not None
            and 'default' in entity._hidden_views
            ):
            return actions
        options = [False]
        for name, FieldClass in entity._field_spec.iteritems():
            if FieldClass.expensive:
                # XXX: Remove this and add support for View objects.
##                 options.append(True)
                break
        for include_expensive in options:
            action = get_view_action(db, entity, include_expensive)
            actions.append(action)
    return sorted(actions)


def get_view_action(db, entity, include_expensive):
    if include_expensive:
        text = u'View (including expensive fields)...'
    else:
        text = u'View...'
    action = Action()
    action.db = db
    action.include_expensive = include_expensive
    action.instance = entity
    action.label = text
    action.name = 'view'
    action.type = 'view'
    return action


optimize.bind_all(sys.modules[__name__])  # Last line of module.
