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
    
    :Note: If a shared *cachedir* is used in a cluster environment,
        then concurrency cache conflicts can arise because the
        pyxnat cache is non-reentrant and unsynchronized (cf.
        the :meth:`qixnat.facade.find` Note).
        
        The caller is required to either not set the *cachedir*
        option or set the *cachedir* to a location that is unique
        for each execution process. This practice ensures cache
        consistency in a cluster environment.
        
        This practice differs from the standard ``pyxnat``
        configuration file. ``pyxnat`` load of a configuration file
        without a *cachedir* option results in an error. By contrast,
        ``qixnat`` load of a configuration file without a *cachedir*
        option results in a new temp cache directory.

    Example:

    >>> import qixnat
    >>> with qixnat.connect() as xnat:
    ...    subject = xnat.find_one('QIN', 'Breast003')

    :param config: the XNAT configuration file, or None
        for the :meth:`qixnat.configuration.load` default
    :param opts: the :class:`qixnat.facade.XNAT`
        initialization options
    :yield: the XNAT instance
    """
    # The *counter* function variable holds the active connection
    # context reference count.
    if not hasattr(connect, 'counter'):
        # The connection count.
        connect.counter = 0
        # The connection cache directory.
        connect.cachedir = None
    # If there no active connections, then do a real XNAT connect.
    if not connect.counter:
        _connect(config, **opts)
    # Increment the connect reference counter.
    connect.counter += 1
    # Pass back the XNAT facade in an execution context with clean-up.
    try:
        yield connect.xnat
    finally:
        # Decrement the connection counter.
        connect.counter -= 1
        # If there are no more active connections, then disconnect.
        if not connect.counter:
            _disconnect()

def _connect(config=None, **opts):
    """
    Opens a XNAT connection.

    :param config: the XNAT configuration file, or None
        for the :meth:`qixnat.configuration.load` default
    :param opts: the :class:`qixnat.facade.XNAT`
        initialization options
    """
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
    """
    Closes the xnat connection and deletes the cache directory.
    """
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
