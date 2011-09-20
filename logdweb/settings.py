#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Logdweb settings.

The default settings for logdweb are listed here to make deploying this as the
only django application a bit easier with the standard ``settings.py`` provided
by ``django-admin.py``.
"""

import os

from django.conf import settings
from django.core.cache import cache

import logging
logger = logging.getLogger("logdweb")

def default(name, value):
    return getattr(settings, name, value)

def update(name, default):
    """Update a default configuration dictionary with the values in the
    customized version from settings.py"""
    ret = default.copy()
    ret.update(getattr(settings, name, {}))
    return ret


TEMPLATE_DIRS = default('TEMPLATE_DIRS', tuple())
INSTALLED_APPS = default('INSTALLED_APPS', ('logdweb',))

# by default, logd access requires superuser privs

LOGD_REQUIRE_SUPERUSER = default('LOGD_REQUIRE_SUPERUSER', True)

# some of these have defaults set by django

LOGD_LOGD = update('LOGD_LOGD', {
    'host': 'localhost',
    'port': 8126,
})

LOGD_MONGO = update('LOGD_MONGO', {
    'host': 'localhost',
    'port': 27017,
    'db': 'logd',
})

LOGD_GRAPHITE_WEB = update('LOGD_GRAPHITE_WEB', {
    'host': 'localhost',
    'port': 3333,
})

LOGD_GRAPHITE_WEB_URL = default('LOGD_GRAPHITE_WEB_URL',
    "http://%(host)s:%(port)s" % LOGD_GRAPHITE_WEB)

# jinja related;  these are not standard, but are pretty well adopted

JINJA_CACHE_SIZE = default('JINJA_CACHE_SIZE', 0)
JINJA_BYTECODE_CACHE_DIR = default('JINJA_BYTECODE_CACHE_DIR', None)

JINJA_EXTENSIONS = default('JINJA_EXTENSIONS', tuple())
JINJA_FILTERS = default('JINJA_FILTERS', tuple())
JINJA_TESTS = default('JINJA_TESTS', tuple())
JINJA_GLOBALS = default('JINJA_GLOBALS', tuple())

# attempt to set a jinja bytecode cache directory to shared mem

if JINJA_BYTECODE_CACHE_DIR is None:
    if os.path.exists('/dev/shm/'):
        JINJA_BYTECODE_CACHE_DIR = '/dev/shm/jinja_cache'
    else:
        JINJA_BYTECODE_CACHE_DIR = '/tmp/jinja_cache'

try: os.makedirs(JINJA_BYTECODE_CACHE_DIR)
except OSError: pass

DEFAULT_CONTENT_TYPE = settings.DEFAULT_CONTENT_TYPE

# create a database cursor here so it can be shared among views.
# these cursors utilize a connection pool and are thread safe.

import pymongo

try:
    logd_mongo = pymongo.Connection(LOGD_MONGO['host'], LOGD_MONGO['port'])[LOGD_MONGO['db']]
except:
    logd_mongo = None
    logger.error("mongodb connection failed, logdweb will not work!")

import util

timer = util.SimpleTimer()

