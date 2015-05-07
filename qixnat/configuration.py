import os
import json

__all__ = ['default', 'load']

CWD_CFG = os.path.join(os.getcwd(), 'xnat.cfg')
"""The XNAT current directory configuration location."""

DOT_CFG = os.path.join(os.path.expanduser('~'), '.xnat', 'xnat.cfg')
"""The XNAT home ``.xnat`` subdirectory configuration location."""

HOME_CFG = os.path.join(os.path.expanduser('~'), 'xnat.cfg')
"""The XNAT home configuration location."""

ETC_CFG = os.path.join('/etc', 'xnat.cfg')
"""The Linux global ``/etc`` XNAT configuration location."""


def load(config=None):
    """
    Loads the configuration as follows:
    
    * If the *config* parameter is set, then that file is loaded.
    
    * Otherwise, if there is a default configuration file as
      specified below, then the default file is loaded.
     
    * Otherwise, this method returns an empty dictionary

    The default configuration file is the first file found in the
    following precedence order:

    1. The ``XNAT_CFG`` environment variable, if it is set.

    2. ``xnat.cfg`` in the current working directory

    3. ``xnat.cfg`` in the home ``.xnat`` subdirectory

    4. ``xnat.cfg`` in the home directory

    5. ``xnat.cfg`` in the ``/etc`` directory
    
    :param config: the configuration file location
    :return: the configuration dictionary
    """
    if not config:
        config = _default_file()
        if not config:
            return {}
    with open(config, 'rb') as fp:
        return json.load(fp)


def _default_file():
    """
    Returns the default XNAT configuration file location as specified in
    :meth:`default`.

    :return: the configuration location, if any
    """
    files = [CWD_CFG, DOT_CFG, HOME_CFG, ETC_CFG]
    env_cfg = os.getenv('XNAT_CFG')
    if env_cfg:
        files.insert(0, env_cfg)
    for fname in files:
        if os.path.exists(fname):
            return fname
