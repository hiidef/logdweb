#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Data models for logdweb."""

# we can eventually have this attempt to get the right settings for the
# environment, but running in a django context is most important for us
# now so we'll assume django

from logdweb import settings
cache = settings.cache
timer = settings.timer
db = settings.logd_mongo

try:
    import simplejson as json
except:
    import json

import logging
import urllib
import urllib2

logger = logging.getLogger(__name__)

def mcsafe(key):
    """Return a safe representation of some key."""
    return key.encode('base64').replace('==\n', '')

rev_natural = [('$natural', -1)]

class Logd(object):
    @timer.timeit('models.logd.server_info')
    def server_info(self):
        """Return info about the server in general."""
        system_collections = ('system.indexes', 'config')
        logfiles = [name for name in db.collection_names() if
                name not in system_collections]
        info = []
        for l in logfiles:
            linfo = db.command({"collstats": l})
            linfo['path'] = l
            linfo['length'] = linfo['count']
            info.append(linfo)
        return {'logfiles': info}

    @timer.timeit('models.logd.get_loggers')
    def get_loggers(self, path):
        """Return a list of the logger names on a logfile."""
        cache_key = 'logd.%s.loggers' % mcsafe(path)
        ret = cache.get(cache_key)
        if ret:
            return ret
        ret = db[path].distinct('name')
        # this can be relatively expensive (~500msec), so save it to a cache
        # FIXME: we might want to keep a list of these in the config as we
        # did before, so that this is always fast out of mongo
        cache.set(cache_key, ret, 60)
        return ret

    @timer.timeit('models.logd.get_line')
    def get_line(self, path, line):
        # 'line' is no longer a monotonically increasing integer;  it's probably
        # a mongo _id object
        return {}

    @timer.timeit('models.logd.get_lines')
    def get_lines(self, path, limit=50):
        log = db[path]
        ret = list(log.find(sort=rev_natural).limit(limit))
        return ret

    @timer.timeit('models.logd.level_lines')
    def get_level_lines(self, path, level, limit=50):
        log = db[path]
        return list(log.find({'level': level}, sort=rev_natural).limit(limit))

    @timer.timeit('models.logd.logger_lines')
    def get_logger_lines(self, path, logger, limit=50):
        log = db[path]
        return list(log.find({'name': logger}, sort=rev_natural).limit(limit))

    def get_new_lines(self, path, latest, level=None, logger=None):
        """Get new lines for a path and optional level/logger.  Only returns
        lines with an id newer than ``latest``."""
        # 'line' is no longer a monotonically increasing integer;  it's probably
        # a mongo _id object
        return []
        def get_lines(limit=100):
            if level:
                lines = self.get_level_lines(path, level, limit=limit)
            elif logger:
                lines = self.get_logger_lines(path, logger, limit=limit)
            else:
                lines = self.get_lines(path, limit=limit)
            return lines
        lines = get_lines()
        return [l for l in lines if l['id'] > latest]


class Graphite(object):
    def __init__(self, webhost=None, webport=None):
        self.host = webhost or settings.LOGD_GRAPHITE_WEB['host']
        self.port = webport or settings.LOGD_GRAPHITE_WEB['port']
        if not any([webhost, webport]):
            self.baseurl = settings.LOGD_GRAPHITE_WEB_URL
        else:
            self.baseurl = 'http://%s:%s' % (self.host, self.port)

    def render(self, **kwargs):
        pass

    def get_stats(self, usecache=True):
        """Gets stats from Graphite.  These are cached for 30 seconds so
        that graphite isn't clobbered, since getting the stats requires a
        disk read."""
        if usecache:
            ret = cache.get('logd.graphite.get_stats')
            if ret:
                return ret
        url = '%s/api/stats/list/' % self.baseurl
        stats = json.loads(urllib2.urlopen(url).read())
        # from here we tailor the results for logd
        for key in stats.keys():
            if not key.startswith('stats'):
                del stats[key]
        buckets = {}
        def base():
            return dict({'timers': {}, 'counts':{}, 'mcounts':{}, 'stats':{}, 'meters':{}})
        def split_key(key):
            if ':' not in key:
                return 'default', key
            return key.split(':')
        for key, stat in stats.items():
            if key.startswith('stats.timers'):
                k = key.replace('stats.timers.', '')
                prefix, timer = split_key(k)
                buckets.setdefault(prefix, base())
                buckets[prefix]['timers'][timer] = stat
            elif key.startswith('stats.mcounts'):
                k = key.replace('stats.mcounts.', '')
                prefix, count = split_key(k)
                buckets.setdefault(prefix, base())
                buckets[prefix]['mcounts'][count] = stat
            elif key.startswith('stats.counts'):
                k = key.replace('stats.counts.', '')
                prefix, count = split_key(k)
                buckets.setdefault(prefix, base())
                buckets[prefix]['counts'][count] = stat
            elif key.startswith('stats.meters'):
                k = key.replace('stats.meters.', '')
                prefix, bucket = split_key(k)
                buckets.setdefault(prefix, base())
                buckets[prefix]['meters'][bucket] = stat
            elif ':' in key:
                k = key.replace('stats.', '')
                prefix, bucket = split_key(k)
                buckets.setdefault(prefix, base())
                buckets[prefix]['stats'][bucket] = stat

        # set for 30 seconds
        if usecache:
            cache.set('logd.graphite.get_stats', buckets, 300)
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

# these colors are from the Tomorrow-Theme:
#  https://github.com/ChrisKempson/Tomorrow-Theme
colors = {
    'blue': '5281be',
    'green': '71dd00',
    'yellow': 'fac700',
    'orange': 'f5871f',
    'red': 'c82829',
}

color_map = {
    'success': colors['green'],
    'queuetimeout': colors['orange'],
    'failure': colors['red'],
    'negcache': colors['blue'],
    'hit': colors['green'],
    'miss': colors['red'],
    'flush': colors['blue'],
}

class Chart(object):
    defaults = {'width':700, 'height': 280}
    def __init__(self, tree, bucket, prefix, time='-1hours', template='plain'):
        self.tree = tree
        self.bucket = bucket
        self.prefix = '' if prefix == 'stats' else prefix
        self.base = 'stats' + ('.%s' % (self.prefix) if self.prefix else '')
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
        base = settings.LOGD_GRAPHITE_WEB_URL
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
        target_keys = [t.rsplit('.',1)[1] for t in targets]
        if all([t in color_map for t in target_keys]):
            kws['colorList'] = ','.join([color_map[t] for t in target_keys])
        return base + '/render/?%s' % urllib.urlencode(kws, doseq=True)


