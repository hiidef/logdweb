#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" """

import re
import time

from jinja2.filters import escape, do_truncate, do_mark_safe

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

try:
    import simplejson as json
except:
    import json

trunc = lambda s, length=255, end='...': do_truncate(s, length, True, end)
safe = do_mark_safe

tbre = re.compile('(?P<tb>Traceback \(most recent call last\):.*)', re.MULTILINE | re.DOTALL)
url_re = re.compile(r"""(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))""")

class SimpleTimer(object):
    def __init__(self):
        self.timers = {}

    def start(self, name):
        self.timers[name] = time.time()

    def end(self, name):
        if name in self.timers:
            self.timers[name] = time.time() - self.timers[name]

    def timeit(self, key=None):
        def wrapper(function):
            name = key or function.__name__
            def f(*args, **kwargs):
                self.start(name)
                ret = function(*args, **kwargs)
                self.end(name)
                return ret
            return f
        return wrapper

    def clear(self):
        self.timers = {}

def safe_unicode(s):
    """Try to decode a string."""
    try: return s.decode('utf-8')
    except:
        try: return s.decode('latin-1')
        except:
            try: return s.decode('utf-8', 'replace')
            except: return u"(Unicode Decode Error)"

def parse_dict_or_json(msg):
    """If we find some matched brackets, we just assume it's json or python
    dict literals, and parse them out and highlight it with python."""
    start = 0
    end = 0
    imbalance = 0
    for i,c in enumerate(msg):
        if c == '{' and not start:
            start = i
            continue
        elif c == '{':
            imbalance += 1
        elif c == '}' and not imbalance:
            end = i
            break
        elif c == '}':
            imbalance -= 1
    if start and end:
        return ''.join(filter(None, [escape(msg[:start]), pygmentize(msg[start:end+1], 'python'), escape(msg[end+1:])]))
    return str(escape(msg))

def render_msg(msg):
    """Used on each message, can do things like escape html, linkify things,
    highlight tracebacks, etc."""
    if isinstance(msg, dict):
        msg = str(msg)
    msg = safe_unicode(msg)
    match = tbre.search(msg)
    if match:
        code = match.groups()[0]
        msgs = filter(None, tbre.split(msg))
        for i,m in enumerate(msgs):
            if m != code:
                m = parse_dict_or_json(m)
                msgs[i] = m
        msg = ''.join(msgs)
        msg = pygmentize_tb(msg)
    else:
        msg = parse_dict_or_json(msg)
    msg = url_re.sub(lambda x: '<a href="%s">%s</a>' % (x.group(0), trunc(x.group(0), 100)), msg)
    msg = msg.strip()
    return safe(msg)


def pygmentize_tb(msg):
    """Highlight tracebacks within a message."""
    tb = tbre.search(msg)
    if tb:
        code = tb.groups()[0]
        msg = msg.replace(code, pygmentize(code, 'pytb'))
    return msg


def pygmentize(code, lang=None, cssclass='source'):
    """Highlight some code in language 'lang' using pygments.  The class name
    in `cssclass` is attributed to the resultant code div."""
    formatter = HtmlFormatter(cssclass=cssclass)
    lexer = get_lexer_by_name(lang or 'pytb', stripnl=True, ecnoding='UTF-8')
    highlighted = highlight(code, lexer, formatter)
    return highlighted

