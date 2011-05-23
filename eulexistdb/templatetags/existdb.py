# file eulexistdb/templatetags/existdb.py
#
#   Copyright 2010,2011 Emory University Libraries
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""
Custom template filter for converting eXist highlight match tags to HTML.

To use, add ``{% load existdb %}`` to your template and then use the exist_matches
filter when you output data, e.g.::

    {{ poem.title|exist_matches }}


You should add CSS for span.exist-match to style it for search-term highlighting.

The :meth:`exist_matches` template tag expects to be given an instance of an
:class:`~eulxml.xmlmap.XmlObject`  (either a top-level object or a sub-object
mapped via :class:`~eulxml.xmlmap.NodeField` or
:class:`~eulxml.xmlmap.NodeListField`).
"""

from lxml import etree

from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from eulexistdb.db import EXISTDB_NAMESPACE

__all__ = [ 'exist_matches' ]

register = template.Library()

@register.filter
def exist_matches(value, autoescape=None):
    """
    Custom django template filter to convert structured fields in xml returned
    by the eXist database to HTML. :class:`~eulxml.xmlmap.XmlObject` values are
    recursively processed, escaping text nodes and converting <exist:match> tags
    to <span> tags. Other values are simply converted to unicode and
    escaped.

    :param value: :class:`~eulxml.xmlmap.XmlObject` instance

    Currently performs the following conversions:
      * ``<exist:match>`` is converted to ``<span class="exist-match">``
      * other elements are stripped
      * text nodes are HTML escaped where the template context calls for it
    """
    if autoescape:
        escape = conditional_escape
    else:
        escape = lambda x: x

    if value is None:
        parts = []
    elif hasattr(value, 'node'):
        parts = node_parts(value.node, escape, include_tail=False)
    else:
        parts = [ escape(unicode(value)) ]

    result = ''.join(parts)
    return mark_safe(result)
exist_matches.needs_autoescape = True

# Precompile XPath expressions for use in node_parts below
_IS_EXIST_MATCH = etree.XPath('self::exist:match',
                  namespaces={'exist': EXISTDB_NAMESPACE})

def node_parts(node, escape, include_tail):
    """Recursively convert an xml node to HTML. This function is used
    internally by :func:`format_ead`. You probably want that function, not
    this one.

    This function returns an iterable over unicode chunks intended for easy
    joining by :func:`format_ead`.
    """

    # if current node contains text before the first node, pre-pend to list of parts
    text = node.text and escape(node.text)

    # if this node contains other nodes, start with a generator expression
    # to recurse into children, getting the node_parts for each.
    child_parts = ( part for child in node
                         for part in node_parts(child, escape, include_tail=True) )

    tail = include_tail and node.tail and escape(node.tail)

    # format the current node, and either wrap child parts in appropriate
    # fenceposts or return them directly.
    return _format_node(node, text, child_parts, tail)

def _format_node(node, text, contents, tail):
    # format a single node, wrapping any contents, and passing any 'tail' text content
    if _IS_EXIST_MATCH(node):
        return _wrap('<span class="exist-match">', text, contents, '</span>', tail)
    else:
        return _wrap(None, text, contents, None, tail)

def _wrap(begin, text, parts, end, tail):
    """Wrap some iterable parts in beginning and ending fenceposts. Simply
    yields begin, then each part, then end."""
    if begin:
        yield begin
    if text:
        yield text

    for part in parts:
        yield part

    if end:
        yield end
    if tail:
        yield tail
