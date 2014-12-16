"""Command XNAT options."""

def add_options(parser):
    """
    Adds the ``--project`` and ``--config`` options to the given command
    line arugment parser.
    """
    # The XNAT project.
    parser.add_argument('-p', '--project',
                        help="the XNAT project (default is 'QIN')")
    
    # The XNAT configuration.
    parser.add_argument('-c', '--config', help='the XNAT configuration file',
                        metavar='FILE')
