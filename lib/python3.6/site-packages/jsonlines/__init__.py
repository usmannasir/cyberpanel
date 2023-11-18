"""
Module for the jsonlines data format.
"""

# expose only public api
from .jsonlines import (  # noqa
    Reader,
    Writer,
    open,
    Error,
    InvalidLineError,
)
