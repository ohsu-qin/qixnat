from .project import project
from .connection import connect

__version__ = '2.1.2'
"""
The one-based major.minor.patch version.
The version numbering scheme loosely follows http://semver.org/.
The major version is incremented when there is an incompatible
public API change. The minor version is incremented when there
is a backward-compatible functionality change. The patch version
is incremented when there is a backward-compatible refactoring
or bug fix. All major, minor and patch version numbers begin at
1.
"""
