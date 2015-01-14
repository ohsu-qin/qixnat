"""XNAT object model constants."""

from pyxnat.core.resources import (Reconstruction, Reconstructions,
                                   Assessor, Assessors)

CONTAINER_TYPES = ['scan', 'reconstruction', 'assessor']
"""The XNAT resource container types."""

RESOURCE_TYPES = ['resource', 'in_resource', 'out_resource']
"""The XNAT resource types."""

CHILD_TYPES = set(CONTAINER_TYPES + RESOURCE_TYPES + ['file'])
"""The XNAT experiment or resource container child types."""

ASSESSOR_SYNONYMS = ['analysis', 'assessment']
"""Alternative designations for the XNAT ``assessor`` container type."""

INOUT_CONTAINER_TYPES = [Reconstruction, Reconstructions,
                         Assessor, Assessors]

HIERARCHICAL_LABEL_TYPES = ['experiment', 'assessor', 'reconstruction']
"""The XNAT types whose label is prefixed by the parent label."""
