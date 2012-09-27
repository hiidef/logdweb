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

rev_natural = [('$natural', -1)]

class Logd(object):
    @timer.timeit('models.logd.server_info')
    def server_info(self):
        """Return info about the server in general."""
        system_collections = ('system.indexes', 'config', 'logdweb')
        logfiles = [name for name in db.collection_names() if
                name not in system_collections]
        info = []
        for l in logfiles:
            linfo = db.command({"collstats": l})
            linfo['path'] = l
            linfo['length'] = linfo['count']
            info.append(linfo)
        return {'logfiles': info}

    @timer.timeit('models.logd.search')
    def search(self, path, term, limit=50):
        col = db[path]
        if term.count('/') > 2: # assume it's a regex
            term = term.strip('/')
            lines = col.find({'msg': {'$regex': term}}, sort=rev_natural)
        else:
            lines = col.find({'msg': {'$regex': term}}, sort=rev_natural)
        if limit:
            lines = list(lines.limit(limit))
        else:
            lines = list(lines)
        lines.reverse()
        return lines

    @timer.timeit('models.logd.path_info')
    def path_info(self, path):
        """Return info about a particular path."""
        stats = db.command({'collstats': path})
        stats[u'path'] = path
        stats[u'length'] = stats[u'count']
        config = db.config.find_one({'name': path})
        stats[u'config'] = config
        return stats

    @timer.timeit('models.logd.get_loggers')
    def get_loggers(self, path):
        """Return a list of the logger names on a logfile."""
        loggers = db.config.find_one({'name':path})
        loggers = loggers.get('loggers', []) if loggers else []
        return list(sorted(loggers))

    @timer.timeit('models.logd.get_line')
    def get_line(self, path, line):
        try:
            from pymongo import objectid
        except ImportError:
            from bson import objectid
        # 'line' is no longer a monotonically increasing integer;  it's probably
        # a mongo _id object
        return db[path].find_one({'_id': objectid.ObjectId(line)})

    @timer.timeit('models.logd.get_lines')
    def get_lines(self, path, limit=50):
        log = db[path]
        ret = list(log.find(sort=rev_natural).limit(limit))
        ret = list(reversed(ret))
        return ret

    @timer.timeit('models.logd.level_lines')
    def get_level_lines(self, path, level, limit=50):
        log = db[path]
        ret = list(log.find({'level': level}, sort=rev_natural).limit(limit))
        ret = list(reversed(ret))
        return ret

    @timer.timeit('models.logd.logger_lines')
    def get_logger_lines(self, path, logger, limit=50):
        log = db[path]
        ret = list(log.find({'name': logger}, sort=rev_natural).limit(limit))
        ret = list(reversed(ret))
        return ret

    def get_new_lines(self, path, latest, level=None, logger=None):
        """Get new lines for a path and optional level/logger.  Only returns
        lines with an id newer than ``latest``."""
        # 'line' is no longer a monotonically increasing integer;  it's a str
        # representation of a mongo ObjectID obj
        def get_lines(limit=100):
            if level:
                lines = self.get_level_lines(path, level, limit=limit)
            elif logger:
                lines = self.get_logger_lines(path, logger, limit=limit)
            else:
                lines = self.get_lines(path, limit=limit)
            return lines
        lines = get_lines()
        ret = []
        for l in reversed(lines):
            if str(l['_id']) == latest:
                return list(reversed(ret))
            l['_id'] = str(l['_id'])
            ret.append(l)
        return list(reversed(ret))


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

    @timer.timeit('graphite.get_stats')
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
            else:
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


class ColorNameMap(object):
    """Manage a map of names -> colors."""
    def __init__(self):
        self.items = self.update()
        if self.items is None:
            self.initialize_defaults()
            self.items = self.update()

    def lookup(self, name, theme="default"):
        """Return the color for a name, if it's found, or the name itself
        if it isn't."""
        theme = self.items.get(theme, {})
        return theme.get(name, name)

    def update(self):
        self.items = db.logdweb.find_one({"name": "color-name-map"})
        return dict(self.items) if self.items else self.items

    def initialize_defaults(self):
        mapping = {
            "dkgray" : "#2d2d2d",
            "ltgray" : "#cccccc",
            "mdgray" : "#999999",
            "red": "#f2777a",
            "orange": "#f99157",
            "yellow": "#ffcc66",
            "green": "#99cc99",
            "aqua": "#66cccc",
            "blue": "#6699cc",
            "purple": "#cc99cc",
        }
        db.logdweb.insert({
            "name": "color-name-map",
            "default": mapping,
            "current": "default"
        })

    def themes(self):
        return dict([(k,v) for k,v in self.items.items() if k not in ("_id", "name", "current")])

    def delete_color(self, name, theme="default"):
        themes = self.themes()
        if theme in themes:
            themes[theme].pop(name, None)
            db.logdweb.update({"name": "color-name-map"}, {"$set" : {theme: themes[theme]}})

    def set_color(self, name, color, theme="default"):
        """Set a name to a color in a theme."""
        themes = self.themes()
        if theme in themes:
            themes[theme][name] = color
        else:
            themes[theme] = {name:color}
        db.logdweb.update({"name": "color-name-map"}, {"$set" : {theme: themes[theme]}})


class ColorStatsMap(object):
    """Manage a map of stats -> color names (or colors)."""
    def __init__(self):
        self.items = self.update()
        if not self.items:
            self.initialize_defaults()
            self.items = self.update()

    def update(self):
        self.items = db.logdweb.find_one({'name': 'color-stats-map'})
        return dict(self.items) if self.items else self.items

    def initialize_defaults(self):
        default = {
            'name': 'color-stats-map',
            'success': 'green',
            'failure': 'red',
            'warning': 'orange',
            'hit': 'green',
            'miss': 'red',
            'good': 'green',
            'bad': 'red'
        }
        db.logdweb.insert(default)

    def mapping(self):
        system_names = ["_id", "name"]
        return dict([(k,v) for k,v in self.items.items() if k not in system_names])

    def set_stat(self, stat, color):
        if stat != 'name':
            self.items[stat] = color
            db.logdweb.update({'name': 'color-stats-map'}, {'$set': {stat: color}})

    def delete_stat(self, stat):
        if stat != 'name':
            self.items.pop('stat', None)
            db.logdweb.update({'name': 'color-stats-map'}, {'$unset': stat})


# these colors are from the Tomorrow-Theme:
#  https://github.com/ChrisKempson/Tomorrow-Theme
colors = {
    "blue": "5281be",
    "green": "71dd00",
    "yellow": "fac700",
    "orange": "f5871f",
    "red": "c82829",
}

color_map = {
    "success": colors["green"],
    "queuetimeout": colors["orange"],
    "failure": colors["red"],
    "negcache": colors["blue"],
    "hit": colors["green"],
    "miss": colors["red"],
    "flush": colors["blue"],
}

class Chart(object):
    defaults = {"width":700, "height": 280}
    def __init__(self, tree, bucket, prefix, time="-1hours", template="plain"):
        self.tree = tree
        self.bucket = bucket
        self.prefix = "" if prefix == "stats" else prefix
        self.base = "stats" + (".%s" % (self.prefix) if self.prefix else "")
        self.chartmap = {}
        self.charts = []
        bucketstr = "%s:" % bucket if bucket != "default" else ""
        for key,value in tree.iteritems():
            chart = ["%s%s.%s" % (bucketstr, key, db) for db in value]
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
        kws.update({"template": template, "from": time})
        final_targets = []
        for target in targets:
            final = "%s.%s" % (self.base, target)
            func = 'alias(keepLastValue(%s),"%s")' % (final, target.rsplit(".",1)[1])
            if "timers" in self.base and target.endswith("mean"):
                final_targets.insert(0, func)
            else:
                final_targets.append(func)
        kws["target"] = final_targets
        kws["title"] = key
        target_keys = [t.rsplit(".",1)[1] for t in targets]
        if all([t in color_map for t in target_keys]):
            kws["colorList"] = ",".join([color_map[t] for t in target_keys])
        return base + "/render/?%s" % urllib.urlencode(kws, doseq=True)


