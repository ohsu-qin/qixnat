import os
import re
import tempfile
import shutil
from contextlib import contextmanager
from .facade import XNAT
from . import configuration 
from qiutil.logging import logger

class ConnectError(Exception):
    pass


@contextmanager
def connect(config=None, **opts):
    """
    Yields a :class:`qixnat.facade.XNAT` instance.
    
    If this is the first connect call, then this method yields
    a new XNAT instance which connects to the XNAT server.
    Otherwise, this method yields the existing XNAT instance.
    The XNAT connection is closed when the outermost connection
    block finishes.
    
    The new XNAT connection is established as follows:
    
    If the *config* parameter is set, then the configuration
    options in that file take precedence over the *opts* options.
    
    Unlike pyxnat, a configuration loaded from the *config* file
    only needs to specify the connection arguments which differ
    from the ``pyxnat.Interface`` default values.
    
    Furthermore, if the options do not include a *cachedir*, then
    this method sets the *cachedir* option to a new temp directory.
    When the connection is closed, this directory is deleted.
    
    :Note: It is recommended, but not required, that the caller
        not set the *cachedir* option. This practice ensures
        cache consistency in a cluster environment, as described
        below. This differs from the standard pyxnat configuration
        file. pyxnat load of a configuration file without a
        *cachedir* option results in an error. By contrast,
        qixnat load of a configuration file without a *cachedir*
        option results in more reliable pyxnat behavior in a
        cluster environment.
    
    :Note: If a shared *cachedir* is used in a cluster environment,
        then concurrency cache conflicts can arise because the
        pyxnat cache is non-reentrant and unsynchronized.

    Example:

    >>> from qiutil import qixnat
    >>> with qixnat.connect() as xnat:
    ...    sbj = xnat.get_subject('QIN', 'Breast003')

    :param config: the XNAT configuration file
    :param opts: the :class:`qixnat.facade.XNAT`
        initialization options
    :yield: the XNAT instance
    """
    if not hasattr(connect, 'connect_cnt'):
        # The connection count.
        connect.connect_cnt = 0
        # The connection cache directory.
        connect.cachedir = None
    if not connect.connect_cnt:
        _connect(config, **opts)
    connect.connect_cnt += 1
    try:
        yield connect.xnat
    finally:
        connect.connect_cnt -= 1
        if not connect.connect_cnt:
            _disconnect()

def _connect(config=None, **opts):
    # Load the configuration file or default.
    opts.update(configuration.load(config))

    # If the pyxnat cachedir is not set, then make a new temp
    # directory for the exclusive use of this execution process.
    cachedir = opts.get('cachedir')
    if not cachedir:
        cachedir = tempfile.mkdtemp()
        connect.cachedir = opts['cachedir'] = cachedir
        logger(__name__).debug("The XNAT cache directory is %s" % cachedir)

    logger(__name__).debug('Connecting to XNAT...')
    connect.xnat = XNAT(**opts)
    logger(__name__).debug('Connected to XNAT.')


def _disconnect():
    connect.xnat.close()
    cachedir = connect.cachedir
    # If this connection created a cache directory, then delete it.
    if cachedir:
        # Unset the cachedir first so that it can be safely deleted. 
        connect.cachedir = None
        # Delete the cache directory
        try:
            shutil.rmtree(cachedir)
        except Exception:
            # Issue a warning and move on.
            logger(__name__).warn("Could not delete the XNAT cache"
                                  " directory %s" % cachedir)
    logger(__name__).debug('Closed the XNAT connection.')
