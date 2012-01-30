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

from logdweb import models, settings, forms
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
    logd = models.Logd()
    global_context = {
        'logd_base_url' : reverse('logd-index'),
        'timers': timer.timers,
        'stats': models.Graphite().get_stats(),
        'info': models.Logd().server_info(),
    }
    path = kwargs.pop('path', None)
    if path:
        global_context['path'] = path
        global_context['current'] = path
        global_context['loggers'] = logd.get_loggers(path)
        if 'logger' not in kwargs:
            global_context['logger'] = None
    else:
        global_context['current'] = None
        global_context['logger'] = None

    global_context.update(kwargs)
    return global_context

@superuser_required
def dashboard_index(request):
    return render_to_response('logdweb/dashboard/index.jinja', make_context(), request)

@superuser_required
def config_index(request):
    color_map_form = forms.ColorNameForm()
    color_stats_form = forms.ColorStatsForm()
    color_name_map = models.ColorNameMap()
    color_stats_map = models.ColorStatsMap()
    return render_to_response('logdweb/config.jinja', make_context(**locals()), request)

@superuser_required
def index(request):
    timer.start('page-generation')
    context = make_context()
    timer.end('page-generation')
    return render_to_response('logdweb/index.jinja', context, request)

@superuser_required
def path_index(request, path=""):
    timer.start('page-generation')
    logd = models.Logd()
    lines = logd.get_lines(path)
    context = make_context(path=path, lines=lines)
    timer.end('page-generation')
    return render_to_response('logdweb/index.jinja', context, request)

@superuser_required
def path_search(request, path):
    term = request.GET.get('q', '')
    if not term:
        return HttpResponseRedirect(reverse('logd-path-index', kwargs={'path': path}))
    limit = int(request.GET.get('limit', 50))
    logd = models.Logd()
    lines = logd.search(path, term, limit)
    context = make_context(term=term, limit=limit, disable_update=True,
            lines=lines, path=path)
    return render_to_response('logdweb/index.jinja', context, request)

@superuser_required
def path_info(request, path=""):
    timer.start('page-generation')
    logd = models.Logd()
    path_info = logd.path_info(path)
    timer.end('page-generation')
    context = make_context(path_info=path_info, path=path)
    return render_to_response('logdweb/info.jinja', context, request)

@superuser_required
def path_line(request, path, line):
    logd = models.Logd()
    line = logd.get_line(path, line)
    context = make_context(path=path, lines=[line],
            details=True, disable_update=True)
    return render_to_response('logdweb/details.jinja', context, request)

@superuser_required
def path_level(request, path="", level=""):
    logd = models.Logd()
    lines = logd.get_level_lines(path, level)
    context = make_context(path=path, level=level, lines=lines)
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
    lines = logd.get_logger_lines(path, logger)
    context = make_context(path=path, logger=logger, lines=lines)
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
    graphite = models.Graphite()
    stats = models.Graphite().get_stats()
    for key in stats.keys():
        for bucket in stats[key].keys():
            stats[key][bucket] = models.stats_tree(stats[key][bucket])
    context = make_context(stats=stats, stat=stat)
    return render_to_response('logdweb/stats.jinja', context, request)

@superuser_required
def stats_chart(request, stat, bucket):
    time = request.GET.get("time", "-1hours")
    template = request.GET.get("template", "plain")
    graphite = models.Graphite()
    pref, bucket = bucket.split(".", 1)
    stats = models.Graphite().get_stats()
    chart = dict([(k,v) for k,v in stats[stat][pref].items() if k.startswith(bucket)])
    chart = models.Chart(chart, stat, pref, time=time, template=template)
    context = make_context(stat=stat, bucket=bucket, chart=chart)
    return render_to_response("logdweb/charts.jinja", context, request)

@superuser_required
def chart_detail(request, path):
    time = request.GET.get("time", "-1hours")
    template = request.GET.get("template", "plain")
    graphite = models.Graphite()
    name, bucket = path.split(":", 1)
    type, statpath = bucket.split(".", 1)
    stats = models.Graphite().get_stats()

    chart = dict([(k,v) for k,v in stats[name][type].items() if k.startswith(statpath)])
    chart = models.Chart(chart, name, type, time=time, template=template)
    context = make_context(stat=name, bucket=bucket, chart=chart)

    return render_to_response("logdweb/chart-detail.jinja", context, request)

