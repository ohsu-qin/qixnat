import os
import re
from qiutil.logging import logger

"""
.. module:: helpers
    :synopsis: XNAT utility functions.
"""


def hierarchical_label(*names):
    """
    Returns the XNAT label for the given hierarchical name, qualified by
    a prefix if necessary.

    Example:

    >>> from qixnat.helpers import hierarchical_label
    >>> hierarchical_label('Breast003', 'Session01')
    'Breast003_Session01'
    >>> hierarchical_label('Breast003', 'Breast003_Session01')
    'Breast003_Session01'

    :param names: the object names
    :return: the corresponding XNAT label
    """
    names = list(names)
    if not all(names):
        raise ValueError("The XNAT label name hierarchy is invalid: %s" %
                         names)
    last = names.pop()
    if names:
        prefix = hierarchical_label(*names)
        if last.startswith(prefix):
            return last
        else:
            return "%s_%s" % (prefix, last)
    else:
        return last

def standardize_experiment_child_hierarchy(hierarchy):
    """
    Standardizes the given XNAT experiment hierarchy as a list of
    *(type, value)* or *container_method* items.

    Examples:

    >>> from qixnat.helpers import standardize_experiment_child_hierarchy
    >>> hiearchy = ['resource', 'reg_Qzu7R', 'files']
    >>> standardize_experiment_child_hierarchy(hiearchy)
    [('resource', 'reg_Qzu7R'), 'files']
    >>> hiearchy = ['analysis', 'pk_tYv4A', 'resource', 'k_trans', 'files']
    >>> standardize_experiment_child_hierarchy(hiearchy)
    [('assessor', 'pk_tYv4A'), ('resource', 'k_trans'), 'files']

    :param hierarchy: the XNAT path components
    :return: the path component list
    """
    out_path = []
    curr_type = None
    for item in hierarchy:
        if curr_type:
            out_path.append((curr_type, item))
            curr_type = None
        else:
            child_attr = standardize_child_attribute(item)
            if child_attr.endswith('s'):
                out_path.append(child_attr)
            else:
                curr_type = child_attr
    if curr_type:
        path = '/'.join(hierarchy)
        raise ValueError("The XNAT search path is not terminated with a"
                         " %s value" % curr_type)

    return out_path


def standardize_child_attribute(name):
    """
    Returns the standardized XNAT attribute for the given name.

    Examples:

    >>> from qixnat.helpers import standardize_child_attribute
    >>> standardize_child_attribute('assessment')
    'assessor'
    >>> standardize_child_attribute('analyses')
    'assessors'

    :param name: the attribute name
    :return: the standardized XNAT attribute
    """
    if name == 'analyses':
        return 'assessors'
    elif name in XNAT.ASSESSOR_SYNONYMS:
        return 'assessor'
    elif name.endswith('s'):
        return standardize_child_attribute(name[:-1]) + 's'
    elif name in XNAT.XNAT_CHILD_TYPES:
        return name
    else:
        raise ValueError("The XNAT path item %s is not recognized as an"
                         " XNAT object type" % name)


def parse_session_label(label):
    """
    Parses the given XNAT session label into *subject* and
    *session* based on the :meth:`hierarchical_label` naming
    standard.

    :param label: the label to parse
    :return: the *(subject, session)* tuple
    :raise ValueError: if there fewer than three hierarchical levels
    """
    names = label.split('_')
    if len(names) < 2:
        raise ValueError("The XNAT session label argument is not in"
                         " subject_session format: %s" % label)
    sess = names.pop()
    sbj = '_'.join(names)

    return (sbj, sess)
