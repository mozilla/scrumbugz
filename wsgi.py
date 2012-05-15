#!/usr/bin/python
import sys, os

sys.path.append(os.path.dirname(__file__))

if "DJANGO_SETTINGS_MODULE" not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = "settings"

import django.core.handlers.wsgi

application = django.core.handlers.wsgi.WSGIHandler()
