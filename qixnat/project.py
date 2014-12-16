def project(name=None):
    """
    Gets or sets the current XNAT project name.
    The default project name is ``QIN``.
    
    :param name: the XNAT project name to set, or None to get the
        current project name
    :return: the current XNAT project name
    """
    if name:
        project.name = name
    elif not hasattr(project, 'name'):
        project.name = None

    return project.name or 'QIN'
