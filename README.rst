logdweb
--------

This is a web front-end to the logging data persisted to redis by `logd`_.  The
initial verison is going to be a django app you can run within an existing django
stack, but long-term plans include a standalone wsgi app based on Flask.

To install, simply add ``logdweb`` to your ``INSTALLED_APPS``, and add something
like this to your ``urls.py``::

    (r'^admin/logd/', include('logdweb.django.urls')),


