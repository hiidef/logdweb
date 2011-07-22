#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""logdweb admin views."""

try:
    import simplejson as json
except ImportError:
    import json

from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404

from logdweb.django.django_jinja2 import render_to_response, render_to_string
from logdweb import models

def make_context(**kwargs):
    global_context = {
        'logd_base_url' : reverse('logd-index'),
    }
    global_context.update(kwargs)
    return global_context

def index(request):
    logd = models.Logd()
    info = logd.server_info()
    context = make_context(info=info)
    return render_to_response('logdweb/index.jinja', context, request)

def path_index(request, path=""):
    logd = models.Logd()
    info = logd.server_info()
    lines = logd.get_lines(path)
    context = make_context(info=info, path=path, lines=lines)
    return render_to_response('logdweb/index.jinja', context, request)

def path_level(request, path="", level=""):
    logd = models.Logd()
    info = logd.server_info()
    lines = logd.get_level_lines(path, level)
    context = make_context(info=info, path=path, level=level, lines=lines)
    return render_to_response('logdweb/index.jinja', context, request)

def path_logger(request, path="", logger=""):
    logd = models.Logd()
    info = logd.server_info()
    lines = logd.get_logger_lines(path, logger)
    context = make_context(info=info, path=path, logger=logger, lines=lines)
    return render_to_response('logdweb/index.jinja', context, request)

def path_new(request, path="", level="", logger=""):
    """Fetch the new from a path."""
    try:
        from_id = int(request.GET['id'])
    except (ValueError, KeyError):
        raise Http404
    logd = models.Logd()
    new = logd.get_new_lines(path, from_id, level=level, logger=logger)
    for line in new:
        line['rendered'] = render_to_string('logdweb/single_line.jinja',
            {'path':path, 'line':line})
    return HttpResponse(json.dumps(new), mimetype='application/javascript')


