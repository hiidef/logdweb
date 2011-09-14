#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" """

import re

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

tbre = re.compile('(?P<tb>Traceback \(most recent call last\):.*)', re.MULTILINE | re.DOTALL)

def safe_unicode(s):
    """Try to decode a string."""
    try: return s.decode('utf-8')
    except:
        try: return s.decode('latin-1')
        except:
            try: return s.decode('utf-8', 'replace')
            except: return u"(Unicode Decode Error)"

def render_msg(msg):
    """Used on each message, can do things like escape html, linkify things,
    highlight tracebacks, etc."""
    if isinstance(msg, dict):
        msg = str(msg)
    msg = safe_unicode(msg)
    msg = pygmentize_tb(msg)
    return msg


def pygmentize_tb(msg):
    """Highlight tracebacks within a message."""
    tb = tbre.search(msg)
    if tb:
        code = tb.groups()[0]
        msg = msg.replace(code, pygmentize(code))
    return msg


def pygmentize(code, lang=None, cssclass='source'):
    """Highlight some code in language 'lang' using pygments.  The class name
    in `cssclass` is attributed to the resultant code div."""
    formatter = HtmlFormatter(cssclass=cssclass)
    lexer = get_lexer_by_name('pytb', stripnl=True, ecnoding='UTF-8')
    highlighted = highlight(code, lexer, formatter)
    return highlighted
