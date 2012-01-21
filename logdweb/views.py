#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""logdweb admin views."""

try:
    import simplejson as json
except ImportError:
    import json

import time

from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404, HttpResponseRedirect

from django_jinja2 import render_to_response, render_to_string

from logdweb import models, settings
from logdweb.settings import timer

from functools import wraps
from django.contrib.auth.decorators import login_required

def superuser_required(view):
    if settings.LOGD_REQUIRE_SUPERUSER:
        @wraps(view)
        @login_required
        def wrapped(request, *args, **kwargs):
            if not request.user.is_superuser:
                try: login_url = reverse('django.contrib.auth.views.login')
                except: login_url = u'/'
                return HttpResponseRedirect(login_url)
            return view(request, *args, **kwargs)
        return wrapped
    return login_required(view)

def make_context(**kwargs):
    global_context = {
        'logd_base_url' : reverse('logd-index'),
        'timers': timer.timers,
    }
    global_context.update(kwargs)
    return global_context

@superuser_required
def index(request):
    timer.start('page-generation')
    logd = models.Logd()
    info = logd.server_info()
    stats = models.Graphite().get_stats()
    timer.end('page-generation')
    context = make_context(info=info, stats=stats)
    return render_to_response('logdweb/index.jinja', context, request)

@superuser_required
def path_index(request, path=""):
    timer.start('page-generation')
    logd = models.Logd()
    info = logd.server_info()
    lines = logd.get_lines(path)
    stats = models.Graphite().get_stats()
    names = logd.get_loggers(path)
    timer.end('page-generation')
    context = make_context(info=info, names=names, path=path, lines=lines, stats=stats)
    return render_to_response('logdweb/index.jinja', context, request)

@superuser_required
def path_search(request, path):
    term = request.GET.get('q', '')
    if not term:
        return HttpResponseRedirect(reverse('logd-path-index', kwargs={'path': path}))
    limit = int(request.GET.get('limit', 50))
    logd = models.Logd()
    info = logd.server_info()
    stats = models.Graphite().get_stats()
    lines = logd.search(path, term, limit)
    names = logd.get_loggers(path)
    context = make_context(term=term, limit=limit, disable_update=True,
            lines=lines, stats=stats, info=info, path=path, names=names)
    return render_to_response('logdweb/index.jinja', context, request)

@superuser_required
def path_info(request, path=""):
    timer.start('page-generation')
    logd = models.Logd()
    info = logd.server_info()
    path_info = logd.path_info(path)
    stats = models.Graphite().get_stats()
    names = logd.get_loggers(path)
    timer.end('page-generation')
    context = make_context(info=info, path_info=path_info, names=names, path=path, stats=stats)
    return render_to_response('logdweb/info.jinja', context, request)

@superuser_required
def path_line(request, path, line):
    logd = models.Logd()
    info = logd.server_info()
    line = logd.get_line(path, line)
    stats = models.Graphite().get_stats()
    names = logd.get_loggers(path)
    context = make_context(info=info, names=names, path=path,
            lines=[line], details=True, stats=stats, disable_update=True)
    return render_to_response('logdweb/details.jinja', context, request)

@superuser_required
def path_level(request, path="", level=""):
    logd = models.Logd()
    info = logd.server_info()
    lines = logd.get_level_lines(path, level)
    stats = models.Graphite().get_stats()
    context = make_context(info=info, path=path, level=level, lines=lines, stats=stats)
    return render_to_response('logdweb/index.jinja', context, request)

@superuser_required
def path_delete(request, path=""):
    from pylogd import delete_log
    delete_log(path, settings.LOGD_LOGD['host'], settings.LOGD_LOGD['port'])
    # to increase the likelihood that the UDP message will "get there" by the
    # time that the next page is loaded and the log will be deleted, we sleep
    time.sleep(0.25)
    return HttpResponseRedirect(reverse('logd-index'))

@superuser_required
def path_logger(request, path="", logger=""):
    logd = models.Logd()
    info = logd.server_info()
    lines = logd.get_logger_lines(path, logger)
    stats = models.Graphite().get_stats()
    names = logd.get_loggers(path)
    context = make_context(info=info, path=path, names=names, logger=logger, lines=lines, stats=stats)
    return render_to_response('logdweb/index.jinja', context, request)

@superuser_required
def path_new(request, path="", level="", logger=""):
    """Fetch the new from a path."""
    try:
        from_id = str(request.GET['id'])
    except (ValueError, KeyError):
        raise Http404
    logd = models.Logd()
    new = logd.get_new_lines(path, from_id, level=level, logger=logger)
    for line in new:
        line['rendered'] = render_to_string('logdweb/single_line.jinja',
            {'path':path, 'line':line})
    response = json.dumps(new)
    return HttpResponse(response, mimetype='application/javascript')

@superuser_required
def stats_index(request, stat):
    logd = models.Logd()
    graphite = models.Graphite()
    info = logd.server_info()
    stats = graphite.get_stats()
    for key in stats.keys():
        for bucket in stats[key].keys():
            stats[key][bucket] = models.stats_tree(stats[key][bucket])
    context = make_context(info=info, stats=stats, stat=stat)
    return render_to_response('logdweb/stats.jinja', context, request)

@superuser_required
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

