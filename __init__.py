from __future__ import absolute_import, unicode_literals
from fishing_game_backend import celery_app
from . import app as celery_app

__all__ = ('celery_app',)


