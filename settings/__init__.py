from __future__ import absolute_import
import os

if 'DATABASE_URL' in os.environ:
    from .heroku import *
elif 'TRAVIS_CI' in os.environ:
    from .travis import *
else:
    try:
        from .local import *
    except ImportError:
        from .base import *
