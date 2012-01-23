#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""logdweb forms"""

from django.forms import *

class CreatePageForm(Form):
    name = CharField(max_length=50)

class ColorMapForm(Form):
    name = CharField(max_length=30)
    color = CharField(max_length=10)

class ChartForm(Form):
    pass

