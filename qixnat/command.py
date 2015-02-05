"""Command XNAT options."""

import qiutil
from qiutil import command
from .helpers import path_hierarchy

def add_options(parser):
    """
    Adds the logging, project and config options to the given command
    line arugment parser.
    
    :param parser: the Python ``argparse`` parser
    """
    # The logging options.
    qiutil.command.add_options(parser)
    
    # The XNAT project.
    parser.add_argument('-p', '--project',
                        help="the XNAT project (default is 'QIN')")
    
    # The XNAT configuration.
    parser.add_argument('-c', '--config', help='the XNAT configuration file',
                        metavar='FILE')


def parse_path(path):
    """
    Standardizes the given path string argument as a list of *(type, value)*
    or pluralized collection child method items.
    
    The path argument must start with the project, subject and session
    values, e.g. '/QIN/Breast003/Session01'. The leading slash is optional,
    as are the XNAT object types. Thus, the following three paths are
    equivalent::
    
        /project/QIN/subject/Breast003/session/Session01
        /QIN/Breast003/Session01
        QIN/Breast003/Session01
    
    The rest of the path argument must specify either of the following:
    * the XNAT object type (or its allowed synonym) and the object value,
      e.g. 'resource/pk_h5H3v'
    * the pluralized collection child method, e.g. 'resources'
    
    Example:
    
    >> from qixnat.command import parse_path
    >> parse_path('QIN/Breast003/Session01/resource/pk_jR5ny/files')
    [('project', 'QIN'), ('subject', 'Breast003'), ('experiment', 'Session01'),
     ('resource', 'pk_jR5ny'), 'files']
    
    :param path: the XNAT path
    :return: the standardized path array
    :throw ValueError if the path is invalid
    """
    # Add a leading slash.
    if path.startswith('/'):
        path = path[1:]
    # Allow but ignore a trailing slash.
    if path.endswith('/'):
        path = path[:-1]
    # Parse the XNAT hierarchy argument.
    items = path.split('/')
    if len(items) < 3:
        raise ValueError("The search path does not start with"
                         " project/subject/session: %s" % path)
    
    # The first three items are /project/subject/session, and
    # can elide the object type.
    first = items.pop(0)
    prj = items.pop(0) if first == 'project' else first
    first = items.pop(0)
    sbj = items.pop(0) if first == 'subject' else first
    first = items.pop(0)
    sess = items.pop(0) if first in ('session', 'experiment') else first
    prefix = ['project', prj, 'subject', sbj, 'session', sess]
    expanded_path = prefix + items
    
    return path_hierarchy(expanded_path)
