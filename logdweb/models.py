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
import urllib
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
        raw = reversed(r.sort(key, desc=True, start=0, num=limit, get='%s:*' % base))
        return [msgpack.loads(r) for r in raw]

    def get_logger_lines(self, path, logger, limit=50):
        r = self.redis
        base = '%s:log:%s' % (logd, path)
        key = '%s:name:%s' % (base, logger)
        raw = reversed(r.sort(key, desc=True, start=0, num=limit, get='%s:*' % base))
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

    def get_stats(self, usecache=True):
        """Gets stats from Graphite.  These are cached for 30 seconds so
        that graphite isn't clobbered, since getting the stats requires a
        disk read."""
        if usecache:
            ret = settings.cache.get('logd.graphite.get_stats')
            if ret:
                return ret
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
        if usecache:
            settings.cache.set('logd.graphite.get_stats', buckets, 300)
        return buckets

def stats_tree(keys):
    """Given a bunch of keys, make a tree such that similarly prefixed stats
    are at the same level underneath eachother."""
    keys = list(keys)

    def reduce_tree(tree):
        keys = list(sorted(tree.keys()))
        for k,v in tree.items():
            if '.' not in k and not v:
                tree[k] = []
        if len(tree) == 1 and not tree.values()[0]:
            return tree.keys()
        prefixes = [k.split('.', 1)[0] for k in tree.keys() if '.' in k]
        if len(prefixes) == len(list(set(prefixes))):
            return tree.keys()
        for key in keys:
            if '.' not in key:
                continue
            p,k = key.split('.', 1)
            tree.setdefault(p, {})
            if isinstance(tree[p], dict):
                tree[p][k] = {}
            elif not tree[p]:
                tree[p] = {k:{}}
            del tree[key]

        for k,v in tree.items():
            if v and isinstance(v, dict):
                tree[k] = reduce_tree(v)
        return tree

    tree = dict([(k,{}) for k in keys])
    reduce_tree(tree)
    return tree

class Chart(object):
    defaults = {'width':700, 'height': 280}
    def __init__(self, tree, bucket, prefix, time='-1hours', template='plain'):
        self.tree = tree
        self.bucket = bucket
        self.prefix = '' if prefix == 'stats' else prefix
        self.base = 'stats' + '.%s' % (self.prefix) if self.prefix else ''
        self.chartmap = {}
        self.charts = []
        for key,value in tree.iteritems():
            chart = ['%s:%s.%s' % (bucket, key, db) for db in value]
            self.charts.append(chart)
            self.chartmap[key] = chart
        self.time = time
        self.template = template

    def url(self, key, time=None, template=None):
        """Create a chart image URL for the key."""
        base = settings.LOGD_GRAPHITE_WEB_BASE
        targets = list(sorted(self.chartmap[key]))
        kws = dict(self.defaults)
        time = time or self.time
        template = template or self.template
        kws.update({'template': template, 'from': time})
        final_targets = []
        for target in targets:
            final = '%s.%s' % (self.base, target)
            func = 'alias(keepLastValue(%s),"%s")' % (final, target.rsplit('.',1)[1])
            if 'timers' in self.base and target.endswith('mean'):
                final_targets.insert(0, func)
            else:
                final_targets.append(func)
        kws['target'] = final_targets
        kws['title'] = key
        return base + '/render/?%s' % urllib.urlencode(kws, doseq=True)


