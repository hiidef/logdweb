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
    stats = models.Graphite().get_stats()
    context = make_context(info=info, stats=stats)
    return render_to_response('logdweb/index.jinja', context, request)

def path_index(request, path=""):
    logd = models.Logd()
    info = logd.server_info()
    lines = logd.get_lines(path)
    stats = models.Graphite().get_stats()
    names = logd.get_loggers(path)
    context = make_context(info=info, names=names, path=path, lines=lines, stats=stats)
    return render_to_response('logdweb/index.jinja', context, request)

def path_line(request, path, line):
    logd = models.Logd()
    info = logd.server_info()
    line = logd.get_line(path, line)
    stats = models.Graphite().get_stats()
    context = make_context(info=info, path=path, lines=[line], stats=stats)
    return render_to_response('logdweb/index.jinja', context, request)

def path_level(request, path="", level=""):
    logd = models.Logd()
    info = logd.server_info()
    lines = logd.get_level_lines(path, level)
    stats = models.Graphite().get_stats()
    context = make_context(info=info, path=path, level=level, lines=lines, stats=stats)
    return render_to_response('logdweb/index.jinja', context, request)

def path_logger(request, path="", logger=""):
    logd = models.Logd()
    info = logd.server_info()
    lines = logd.get_logger_lines(path, logger)
    stats = models.Graphite().get_stats()
    names = logd.get_loggers(path)
    context = make_context(info=info, path=path, names=names, logger=logger, lines=lines, stats=stats)
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

def stats_index(request, stat):
    logd = models.Logd()
    graphite = models.Graphite()
    info = logd.server_info()
    stats = graphite.get_stats()
    for stat in stats.keys():
        for bucket in stats[stat].keys():
            stats[stat][bucket] = models.stats_tree(stats[stat][bucket])
    context = make_context(info=info, stats=stats, stat=stat)
    return render_to_response('logdweb/stats.jinja', context, request)

def stats_chart(request, stat, bucket):
    time = request.GET.get('time', '-1hours')
    template = request.GET.get('template', 'plain')
    logd = models.Logd()
    graphite = models.Graphite()
    info = logd.server_info()
    stats = graphite.get_stats()
    pref, bucket = bucket.split('.', 1)
    chart = dict([(k,v) for k,v in stats[stat][pref].items() if k.startswith(bucket)])
    chart = models.Chart(chart, stat, pref, time=time, template=template)
    context = make_context(info=info, stats=stats, stat=stat, bucket=bucket, chart=chart)
    return render_to_response('logdweb/charts.jinja', context, request)

