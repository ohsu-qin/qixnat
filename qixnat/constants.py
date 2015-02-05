"""XNAT object model constants."""

from pyxnat.core.resources import (Project, Projects,
                                   Reconstruction, Reconstructions,
                                   Assessor, Assessors)

EXPERIMENT_PATH_TYPES = ['project', 'subject', 'experiment']

CONTAINER_TYPES = ['scan', 'reconstruction', 'assessor']
"""The XNAT resource container types."""

RESOURCE_TYPES = ['resource', 'in_resource', 'out_resource']
"""The XNAT resource types."""

XNAT_TYPES = set(EXPERIMENT_PATH_TYPES + CONTAINER_TYPES + RESOURCE_TYPES +
                 ['file'])
"""The standardized XNAT object types."""

UNLABELED_XNAT_TYPES = [Reconstruction]
"""The XNAT object types which do not have a label attribute."""

ASSESSOR_SYNONYMS = ['analysis', 'assessment']
"""Alternative designations for the XNAT ``assessor`` container type."""

INOUT_CONTAINER_TYPES = [Reconstruction, Reconstructions,
                         Assessor, Assessors]

HIERARCHICAL_LABEL_TYPES = ['experiment', 'assessor', 'reconstruction']
"""The XNAT types whose label is prefixed by the parent label."""
