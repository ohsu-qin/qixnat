import os
import re
from contextlib import contextmanager
from .facade import XNAT
from qiutil.logging import logger

@contextmanager
def connect(config=None):
    """
    Yields a :class:`qixnat.facade.XNAT` instance.
    The XNAT connection is closed when the outermost connection
    block finishes.

    Example:

    >>> from qiutil import qixnat
    >>> with qixnat.connect() as xnat:
    ...    sbj = xnat.get_subject('QIN', 'Breast003')

    :yield: the XNAT instance
    """
    if not hasattr(connect, 'connect_cnt'):
        connect.connect_cnt = 0
    if not connect.connect_cnt:
        logger(__name__).debug('Connecting to XNAT...')
        connect.xnat = XNAT(config)
        logger(__name__).debug('Connected to XNAT.')
    connect.connect_cnt += 1
    try:
        yield connect.xnat
    finally:
        connect.connect_cnt -= 1
        if not connect.connect_cnt:
            connect.xnat.close()
            logger(__name__).debug('Closed thge XNAT connection.')
