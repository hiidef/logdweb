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

try:
    import simplejson as json
except:
    import json

import redis
import msgpack
import logging
import urllib2

logd = settings.LOGD_REDIS_PREFIX

logger = logging.getLogger(__name__)

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
        def get_lines(limit=20):
            if level:
                lines = self.get_level_lines(path, level, limit=limit)
            elif logger:
                lines = self.get_logger_lines(path, logger, limit=limit)
            else:
                lines = self.get_lines(path, limit=limit)
            return lines
        lines = get_lines()
        if lines[-1]['id'] > latest:
            diff = latest - lines[-1]['id']
            diff += 50
            lines = get_lines(limit=diff)
        return [l for l in lines if l['id'] > latest]


class Graphite(object):
    def __init__(self, webhost=None, webport=None):
        self.host = webhost or settings.LOGD_GRAPHITE_WEB_HOST
        self.port = webport or settings.LOGD_GRAPHITE_WEB_PORT
        self.baseurl = 'http://%s:%s' % (self.host, self.port)

    def render(self, **kwargs):
        pass

    def get_stats(self):
        """Gets stats from Graphite.  These are cached for 30 seconds so
        that graphite isn't clobbered, since getting the stats requires a
        disk read."""
        ret = settings.cache.get('logd.graphite.get_stats')
        if ret: return ret
        url = '%s/api/stats/list/' % self.baseurl
        stats = json.loads(urllib2.urlopen(url).read())
        # from here we tailor the results for logd
        for key in stats.keys():
            if not key.startswith('stats'):
                del stats[key]
        buckets = {}
        for key, stat in stats.items():
            if key.startswith('stats.timers'):
                k = key.replace('stats.timers.', '')
                prefix, timer = k.split(':')
                buckets.setdefault(prefix, {'timers':{}, 'counts':{}, 'stats':{}})
                buckets[prefix]['timers'][timer] = stat
            elif key.startswith('stats.counts'):
                k = key.replace('stats.counts.', '')
                prefix, count = k.split(':')
                buckets.setdefault(prefix, {'timers':{}, 'counts':{}, 'stats':{}})
                buckets[prefix]['counts'][count] = stat
            elif ':' in key:
                k = key.replace('stats.', '')
                prefix, bucket = k.split(':')
                buckets.setdefault(prefix, {'timers':{}, 'counts':{}, 'stats':{}})
                buckets[prefix]['stats'][bucket] = stat
        # set for 30 seconds
        settings.cache.set('logd.graphite.get_stats', buckets, 30)
        return buckets

def stats_tree(keys):
    """Given a bunch of keys, make a tree such that similarly prefixed stats
    are at the same level underneath eachother."""
    keys = list(keys)
    keys.sort()

    def add_bit(d, key):
        parts = key.split('.')
        if len(parts) > 2:
            for part in parts[:-2]:
                if part in d and isinstance(d[part], basestring):
                    d[part] = {d[part]: {}}
                else:
                    d.setdefault(part, {})
                d = d[part]
            d.setdefault(parts[-2], []).append(parts[-1])
        elif len(parts) == 2:
            one, two = parts
            if one in d and isinstance(d[one], dict):
                d[one].setdefault(two, {})
            else:
                d[one] = two
        else:
            pass

    tree = {}
    for key in keys:
        add_bit(tree, key)

    # FIXME:
    # from here, we have to flatten keys that have zero or one values
    return tree




