"""
.. module:: helpers
    :synopsis: XNAT utility functions.
"""
import os
import re
import itertools
from datetime import datetime
from pyxnat.core.resources import Scan
from .constants import (XNAT_TYPES, UNLABELED_TYPES, ASSESSOR_SYNONYMS,
                        EXPERIMENT_SYNONYM, EXPERIMENT_PATH_TYPES,
                        TYPE_DESIGNATORS, MODALITY_TYPES, DATE_FMT)


class ParseError(Exception):
    pass


def xnat_path(obj):
    """
    Returns the XNAT object path in the canonical form:
    
    /<project>[/<subject>[/<session>[/type/<name>]*]]
    
    e.g.::
        
        /QIN/Breast003/Session02/scan/1/resource/NIFTI/file/volume001.nii.gz
    
    :param obj: the XNAT object
    :return: the XNAT path
    """
    name = xnat_name(obj)
    # The lower-case type name.
    xnat_type = obj.__class__.__name__.lower()
    # The types leading to and including experiment are unqualified
    # by the type in the path.
    if xnat_type in EXPERIMENT_PATH_TYPES:
        subpath = name
    else:
        subpath = "%s/%s" % (xnat_type, name)
    parent = obj.parent()
    # If there is a parent, then prepend the parent path to the
    # relative sub-path. Otherwise, the path is the absolute project
    # name.
    if parent:
        return "%s/%s" % (xnat_path(parent), subpath)
    else:
        return '/' + subpath


def xnat_name(obj):
    """
    Returns the canonical XNAT object name determined as the :meth:`xnat_key`
    with the parent key prefix removed, if necessary, e.g.::
    
    >> xnat_key(session)
    Breast003_Session01
    >> xnat_name(session)
    Session01
    
    The scan name is an integer, the other names are strings.
    
    :param obj: the XNAT object
    :return: the canonical XNAT name
    """
    key = xnat_key(obj)
    if isinstance(obj, Scan):
        return int(key)
    parent = obj.parent()
    if parent:
        prefix = xnat_key(parent) + '_'
        if key.startswith(prefix):
            return key[len(prefix):]
    
    return key


def xnat_key(obj):
    """
    Returns the XNAT object key unique within the parent scope,
    determined as follows:
    * If the object is a Reconstruction, then the XNAT id
    * Otherwise, the XNAT label
    
    :param obj: the XNAT object
    :return: the XNAT label or id
    """
    type_name = obj.__class__.__name__.lower()
    
    return obj.id() if type_name in UNLABELED_TYPES else obj.label()


def xnat_children(obj):
    """
    Returns the XNAT objects contained in the given parent object.
    
    :param obj: the XNAT parent object
    :return: the child objects
    :rtype: list
    """
    # pyxnat children() is oddly the child collection attributes
    # rather than objects.
    child_attrs = obj.children()
    # The children generators for each child type.
    nested = (getattr(obj, attr)() for attr in child_attrs)
    flattened = itertools.chain(*nested)
    
    return list(flattened)


def pluralize_type_designator(designator):
    """
    :param designator: the XNAT type name or synonym
    :return: the pluralized type designator
    """
    if designator == 'analysis':
        return 'analyses'
    elif designator.endswith('s'):
        # No examples of this (yet), but play it safe.
        return designator
    else:
        return designator + 's'


def is_pluralized_type_designator(designator):
    """
    :param designator: the XNAT type name or synonym
    :return: whether the designator is a pluralized XNAT type
        designator
    """
    return any(designator == pluralize_type_designator(xnat_type)
               for xnat_type in TYPE_DESIGNATORS)


def hierarchical_label(*names):
    """
    Returns the XNAT label for the given hierarchical name, qualified
    by a prefix if necessary.
    
    Example:
    
    >>> from qixnat.helpers import hierarchical_label
    >>> hierarchical_label('Breast003', 'Session01')
    'Breast003_Session01'
    >>> hierarchical_label('Breast003', 'Breast003_Session01')
    'Breast003_Session01'
    >>> hierarchical_label(3)   # for scan number 3
    3
    
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


def rest_type(type_name, modality=None):
    """
    Qualifies the given type name with the modality, e.g.:
    
    >>> from qixnat.helpers import rest_type
    >>> rest_type('experiment', 'MR')
    'xnat:mrSessionData'
    
    :param type_name: the XNAT type name
    :param modality: the case-insensitive modality, e.g. ``MR`` or ``CT``
    :return: the full XNAT subtype designation
    :raise XNATError: if the type name is in
        :const:`qixnat.constants.MODALITY_TYPES`
        but modality is None
    """
    # XNAT subtypes an Experiment as Session.
    rest_name = 'session' if type_name == 'experiment' else type_name
    if type_name in MODALITY_TYPES:
        if type_name in MODALITY_TYPES:
            if not modality:
                raise ParseError("Modality is required to create a XNAT"
                                " %s" % type_name)
        return "xnat:%s%sData" % (modality.lower(), rest_name.capitalize())
    else:
        return "xnat:%sData" % rest_name


def rest_date(value):
    """
    :param value: the input ``datetime`` object or None
    :return: None, if the input is None, otherwise the input formatted
        as a string using the :const:`qixnat.constants.DATE_FMT`
    :rtype: str
    """
    return value.strftime(DATE_FMT) if value else None


def parse_xnat_date(value):
    """
    The XNAT REST client unfortunately returns date fields as a string.
     experiment must have a date. This method converts the string
     input to a datetime.

    :param value: the input string in :const:`qixnat.constants.DATE_FMT`
        format or None
    :return: None, if the input is None, otherwise the input parsed
        as a datetime object
    :rtype: datetime.datetime
    """
    return datetime.strptime(value, DATE_FMT) if value else None


def path_hierarchy(path):
    """
    Transforms the given XNAT path into a list of *(type, value)*
    tuples.
    
    The *path* string argument must consist of a sequence of
    slash-delimited XNAT object specifications, where each specification
    is either a singular XNAT type and value, e.g. ``subject/Breast003``,
    or a pluralized XNAT type, e.g. ``resources``.
    
    The path can include wildcards, e.g. ``/project/QIN/subject/Breast*``.
    
    If the path starts with a forward slash, then the first three
    components can elide the XNAT type. Thus, the following are
    equivalent::
          
          path_hierarchy('/project/QIN/subject/Breast003/experiment/Session02')
          path_hierarchy('/QIN/Breast003/Session02')
    
    The following XNAT object type synonyms are allowed:
    * ``session`` => ``experiment``
    * ``analysis`` or ``assessment`` => ``assessor``
    Pluralized type synonyms are standardized according to the singular
    form, e.g. ``analyses`` => ``assessors``.
    
    The path hierarchy result is a list of *(type, value)* tuples. A
    pluralization value is a wild card.
    
    Examples:
    
    >>> from qixnat.helpers import path_hierarchy
    >>> path_hierarchy('/QIN/Breast003/Session03/resource/reg_Qzu7R/files')
    [('project', 'QIN'), ('subject', 'Breast*'), ('project', 'QIN'),
     ('subject', 'Breast*'), ('experiment', 'Session03'),
     ('resource', 'reg_Qzu7R'), ('file', '*')]
    >>> path_hierarchy('/QIN/Breast*/*/resources')
    [('project', 'QIN'), ('subjects, 'Breast*'), ('experiments, '*'),
     ('resource', '*')]
    
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
    return [(_standardize_attribute(items[i]), items[i+1])
            for i in range(0, len(items), 2)]


def _standardize_attribute(name):
    """
    Returns the standardized XNAT attribute for the given name, with
    the following substitutions:
    * ``session`` => ``experiment``
    * ``analysis`` or ``assessment`` => ``assessor``
    * pluralizations => the singular standardization, e.g.
      ``analyses`` => ``assessor``
    
    :param name: the attribute name
    :return: the standardized XNAT attribute
    :raise ParseError: if the name is not recognized as an attribute
        designator
    """
    if name in XNAT_TYPES:
        return name
    elif name == EXPERIMENT_SYNONYM:
        return 'experiment'
    elif name == 'analyses':
        return 'assessor'
    elif name in ASSESSOR_SYNONYMS:
        return 'assessor'
    elif name.endswith('s'):
        return _standardize_attribute(name[:-1])
    else:
        raise ParseError("The XNAT path item %s is not recognized as an"
                         " XNAT object type" % name)
