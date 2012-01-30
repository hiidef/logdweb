#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""logdweb forms"""

from django.forms import *

class CreatePageForm(Form):
    name = CharField(max_length=50)

class ColorNameForm(Form):
    stat = CharField(max_length=30)
    color = CharField(max_length=10)

class ColorStatsForm(Form):
    name = CharField(max_length=30)
    color = CharField(max_length=30)

class ChartForm(Form):
    pass

