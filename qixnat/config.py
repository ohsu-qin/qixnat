import os

__all__ = ['configuration_file']

CWD_CFG = os.path.join(os.getcwd(), 'xnat.cfg')
"""The XNAT current directory configuration location."""

DOT_CFG = os.path.join(os.path.expanduser('~'), '.xnat', 'xnat.cfg')
"""The XNAT home ``.xnat`` subdirectory configuration location."""

HOME_CFG = os.path.join(os.path.expanduser('~'), 'xnat.cfg')
"""The XNAT home configuration location."""

ETC_CFG = os.path.join('/etc', 'xnat.cfg')
"""The Linux global ``/etc`` XNAT configuration location."""


def configuration_file():
    """
    Returns the XNAT configuration file location determined as the first file
    found in the following precedence order:

    1. The ``XNAT_CFG`` environment variable, if it is set.

    2. ``xnat.cfg`` in the current working directory

    3. ``xnat.cfg`` in the home ``.xnat`` subdirectory

    4. ``xnat.cfg`` in the home directory

    5. ``xnat.cfg`` in the ``/etc`` directory

    :return: the configuration location, if any
    """
    files = [CWD_CFG, DOT_CFG, HOME_CFG, ETC_CFG]
    env_cfg = os.getenv('XNAT_CFG')
    if env_cfg:
        files.insert(0, env_cfg)
    for fname in files:
        if os.path.exists(fname):
            return fname
