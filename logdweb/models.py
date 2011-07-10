#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Data models for logdweb.  These are general purpose abstractions over the
redis data storage format for logd, which can be seen on its readme:

    https://github.com/hiidef/logd

These aren't really models, they are more like functions that return data
from redis.
"""

# we can eventually have this attempt to get the right settings for the
# environment, but running in a django context is most important for us
# now so we'll assume django

from logdweb.django import settings

import redis
import msgpack

logd = settings.LOGD_REDIS_PREFIX

class Logd(object):
    def __init__(self):
        self.redis = redis.Redis(settings.LOGD_REDIS_HOST,
            settings.LOGD_REDIS_PORT)

    def server_info(self):
        """Return info about the server in general."""
        r = self.redis
        logfiles = []
        for path in list(sorted(r.smembers('%s:paths' % logd))):
            log = {
                'path': path,
                'length': r.llen('%s:log:%s' % (logd, path)),
            }
            logfiles.append(log)
        return {'logfiles': logfiles}

    def get_keys(self, path, key, limit=50):
        r = self.redis
        base = '%s:log:%s' % (logd, path)
        raw = reversed(r.sort(base, by='nosort', start=0, num=limit,
            get=['%s:*' % (base), '#']))


    def get_lines(self, path, limit=50):
        r = self.redis
        base = '%s:log:%s' % (logd, path)
        raw = reversed(r.sort(base, by='nosort', start=0, num=limit, get='%s:*' % base))
        return [msgpack.loads(r) for r in raw]

    def get_level_lines(self, path, level, limit=50):
        r = self.redis
        base = '%s:log:%s' % (logd, path)
        key = '%s:level:%s' % (base, level)
        raw = reversed(r.sort(key, by='nosort', start=0, num=limit, get='%s:*' % base))
        return [msgpack.loads(r) for r in raw]

    def get_logger_lines(self, path, logger, limit=50):
        r = self.redis
        base = '%s:log:%s' % (logd, path)
        key = '%s:name:%s' % (base, logger)
        raw = reversed(r.sort(key, by='nosort', start=0, num=limit, get='%s:*' % base))
        return [msgpack.loads(r) for r in raw]

    def get_new_lines(self, path, latest, level=None, logger=None):
        """Get new lines for a path and optional level/logger.  Only returns
        lines with an id newer than ``latest``."""
        r = self.redis
        if level:
            lines = self.get_level_lines(self, path, level)
        elif logger:
            lines = self.get_logger_lines(self, path, logger)
        else:
            lines = self.get_lines(path, limit=20)
        return [l for l in lines if l['id'] > latest]

