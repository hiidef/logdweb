#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""logdweb settings"""

import os
from django.conf import settings
from django.core.cache import cache

TEMPLATE_DIRS = getattr(settings, 'TEMPLATE_DIRS', tuple())
INSTALLED_APPS = getattr(settings, 'INSTALLED_APPS', tuple('logdweb'))

# some of these have defaults set by django

LOGD_HOST = getattr(settings, 'LOGD_HOST', 'localhost')
LOGD_PORT = getattr(settings, 'LOGD_PORT', 8126)
LOGD_REDIS_HOST = getattr(settings, 'LOGD_REDIS_HOST', 'localhost')
LOGD_REDIS_PORT = getattr(settings, 'LOGD_REDIS_PORT', 6379)
LOGD_REDIS_PREFIX = getattr(settings, 'LOGD_REDIS_PREFIX', 'logd')

LOGD_GRAPHITE_WEB_HOST = getattr(settings, 'LOGD_GRAPHITE_WEB_HOST', 'localhost')
LOGD_GRAPHITE_WEB_PORT = getattr(settings, 'LOGD_GRAPHITE_WEB_PORT', 3333)

LOGD_GRAPHITE_WEB_BASE = "http://%s:%s" % (LOGD_GRAPHITE_WEB_HOST, LOGD_GRAPHITE_WEB_PORT)

# jinja related;  these are not standard, but are pretty well adopted

JINJA_CACHE_SIZE = getattr(settings, 'JINJA_CACHE_SIZE', 0)
JINJA_BYTECODE_CACHE_DIR = getattr(settings, 'JINJA_BYTECODE_CACHE_DIR', None)

JINJA_EXTENSIONS = getattr(settings, 'JINJA_EXTENSIONS', tuple())
JINJA_FILTERS = getattr(settings, 'JINJA_FILTERS', tuple())
JINJA_TESTS = getattr(settings, 'JINJA_TESTS', tuple())
JINJA_GLOBALS = getattr(settings, 'JINJA_GLOBALS', tuple())

if JINJA_BYTECODE_CACHE_DIR is None:
    if os.path.exists('/dev/shm/'):
        JINJA_BYTECODE_CACHE_DIR = '/dev/shm/jinja_cache'
    else:
        JINJA_BYTECODE_CACHE_DIR = '/tmp/jinja_cache'

try: os.makedirs(JINJA_BYTECODE_CACHE_DIR)
except OSError: pass

DEFAULT_CONTENT_TYPE = settings.DEFAULT_CONTENT_TYPE

