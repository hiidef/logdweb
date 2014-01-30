#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""logdweb urls."""

import os
from django.conf.urls import patterns

moduledir = os.path.dirname(__file__)
docroot = os.path.abspath(os.path.join(moduledir, './static'))

urlpatterns = patterns('logdweb.views',
    (r'^$', 'index', {}, 'logd-index'),

    # dashboard
    (r'^dashboard/?$', 'dashboard_index', {}, 'logd-dashboard'),
    # config
    (r'^config/?$', 'config_index', {}, 'logd-config'),
    # stats
    (r'^stats/(?P<stat>[^/]+)/?$', 'stats_index', {}, 'logd-stat-index'),
    (r'^stats/(?P<stat>[^/]+)/(?P<bucket>[^/]+)/?$', 'stats_chart', {}, 'logd-stat-chart'),
    (r'^chart/(?P<path>[^/]+)/?$', 'chart_detail', {}, 'logd-chart-detail'),
    # logs
    (r'^(?P<path>[^/]+)/?$', 'path_index', {}, 'logd-path-index'),
    (r'^(?P<path>[^/]+)/search/?$', 'path_search', {}, 'logd-path-search'),
    (r'^(?P<path>[^/]+)/info/?$', 'path_info', {}, 'logd-path-info'),
    (r'^(?P<path>[^/]+)/delete/?$', 'path_delete', {}, 'logd-path-delete'),
    (r'^(?P<path>[^/]+)/line/(?P<line>\w+)', 'path_line', {}, 'logd-path-line'),
    (r'^(?P<path>[^/]+)/level/(?P<level>[^/]+)/?$', 'path_level', {}, 'logd-path-level'),
    (r'^(?P<path>[^/]+)/logger/(?P<logger>[^/]+)/?$', 'path_logger', {}, 'logd-path-logger'),
    # ajax updates
    (r'^(?P<path>[^/]+)/new/?$', 'path_new', {}, 'logd-path-new'),
    (r'^(?P<path>[^/]+)/level/(?P<level>[^/]+)/new/?$', 'path_new', {}, 'logd-path-level-new'),
    (r'^(?P<path>[^/]+)/logger/(?P<logger>[^/]+)/new/?$', 'path_new', {}, 'logd-path-logger-new'),
)

urlpatterns += patterns('django.views.static',
    (r'^_media/(?P<path>.*)$', 'serve', {'document_root': docroot}, 'logd-media'),
)
