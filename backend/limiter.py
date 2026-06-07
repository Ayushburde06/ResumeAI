"""Shared SlowAPI rate limiter instance.

Import this module everywhere instead of creating a new Limiter()
so all decorators operate on the same in-memory store that is
registered with app.state.limiter in main.py.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
