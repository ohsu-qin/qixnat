"""
.. module:: helpers
    :synopsis: XNAT utility functions.
"""

import os
import re
from qiutil.logging import logger
try:
    from pyxnat.core.resources import Reconstruction
    from .constants import (XNAT_TYPES, UNLABELED_XNAT_TYPES, ASSESSOR_SYNONYMS)
except ImportError:
    # Ignore pyxnat import failure to allow ReadTheDocs auto-builds.
    # See the installation instructions for why auto-build fails.
    pass

def xnat_path(obj):
    """
    Returns the XNAT object path consisting of the :meth:`xnat_name`
    path components.

    :param obj: the XNAT object
    :return: the XNAT path
    """
    name = xnat_name(obj)
    parent = obj.parent()
    if parent:
        return '/'.join((xnat_path(parent), name))
    else:
        return '/' + name


def xnat_name(obj):
    """
    Returns the XNAT object name as follows:
    * If the object is a Reconstruction, then the XNAT id
    * Otherwise, the XNAT label

    :param obj: the XNAT object
    :return: the XNAT label or id
    """
    unlabeled = any((isinstance(obj, t) for t in UNLABELED_XNAT_TYPES))
    return obj.id() if unlabeled else obj.label()


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


def path_hierarchy(path):
    """
    Transforms the given XNAT path into a list of *(type, value)* tuples.

    The *path* string argument must consist of a sequence of slash-delimited
    XNAT object specifications, where each specification is either a singular
    XNAT type and value, e.g. 'subject/Breast003', or a pluralized XNAT type,
    e.g. 'resources'. If the path starts with a forward slash, then the first
    three components can elide the XNAT type. Thus, the following are
    equivalent::

          path_hierarchy('/project/QIN/subject/Breast003/experiment/Session02')
          path_hierarchy('/QIN/Breast003/Session02')

    The following XNAT object type synonyms are allowed:
    * ``session`` => ``experiment``
    * ``analysis`` or ``assessment`` => ``assessor``
    Pluralized type synonyms are standardized according to the singular form,
    e.g. ``analyses`` => ``assessors``.

    The path hierarchy is a list of *(type, value)* tuples. A pluralization
    value is a wild card.

    Examples:

    >>> from qixnat.helpers import path_hierarchy
    >>> path = 'session/Session03/resource/reg_Qzu7R/files'
    >>> path_hierarchy(path)
    [('experiment', 'Session03'), ('resource', 'reg_Qzu7R'), ('files', '*')]
    >>> path = '/project/QIN/subject/Breast*/session/*/resources'
    >>> path_hierarchy(path)
    [('project', 'QIN'), ('subjects', 'Breast*'), ('experiments', '*'), ('resources', '*')]

    :param path: the XNAT object path string or list
    :return: the path hierarchy list
    :rtype: list
    """
    # Remove the leading slash, if necessary, before splitting
    # the path items.
    if path.startswith('/'):
        relpath = path[1:]
    else:
        relpath = path
    # Allow but ignore a trailing slash.
    if relpath.endswith('/'):
        relpath = relpath[:-1]
    # There must be something left.
    if not relpath:
        raise ValueError("The path argument is empty.")
    # The path items list.
    items = relpath.split('/')

    # If the path starts with a '/', then the first three items are
    # /project/subject/experiment, and can elide the object type.
    if path.startswith('/'):
        prefix = []
        # Walk through the first three object specifications
        # to create a standard prefix.
        first = items.pop(0)
        if re.match(r"projects?$", first):
            prj = items.pop(0)
        else:
            prj = first
        prefix.extend(('project', prj))
        if items:
            first = items.pop(0)
            if re.match(r"subjects?$", first):
                sbj = items.pop(0) if items else '*'
            else:
                sbj = first
            prefix.extend(('subjects', sbj))
        if items:
            first = items.pop(0)
            if re.match(r"(session|experiment)s?$", first):
                sess = items.pop(0) if items else '*'
            else:
                sess = first
            prefix.extend(('experiments', sess))
        # Prepend the augmented prefix.
        items = prefix + items
    
    # A terminal type not followed by a value has a '*' value.
    if len(items) % 2:
        items.append('*')

    # Partition the items into (type, value) pairs.
    return [_standardize_attribute_value(items[i], items[i+1])
            for i in range(0, len(items), 2)]


def _standardize_attribute_value(name, value):
    """
    Returns the standardized XNAT (attribute, value) pair for the
    given attribute name and value.

    :param name: the attribute name
    :param value: the attribute value
    :return: the standardized XNAT (attribute, value) pair
    """
    attr = _standardize_attribute(name)
    # If the value is a wild card, then pluralize the attribute.
    if isinstance(value, str) and '*' in value:
        attr = attr + 's'
    
    return (attr, value)


def _standardize_attribute(name):
    """
    Returns the standardized XNAT attribute for the given name, with
    the following substitutions:
    * session => experiment
    * analysis or assessment => assessor
    * pluralizations => the singular standardization, e.g.
      analyses => assessor

    :param name: the attribute name
    :return: the standardized XNAT attribute
    """
    if name in XNAT_TYPES:
        return name
    elif name == 'session':
        return 'experiment'
    elif name == 'analyses':
        return 'assessor'
    elif name in ASSESSOR_SYNONYMS:
        return 'assessor'
    elif name.endswith('s'):
        return _standardize_attribute(name[:-1])
    else:
        raise ValueError("The XNAT path item %s is not recognized as an"
                         " XNAT object type" % name)
