from __future__ import absolute_import
import os

if 'HEROKU' in os.environ:
    from .heroku import *
elif 'TRAVIS' in os.environ:
    from .travis import *
else:
    try:
        from .local import *
    except ImportError:
        from .base import *
