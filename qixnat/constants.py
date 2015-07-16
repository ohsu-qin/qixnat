"""XNAT object model constants."""

EXPERIMENT_PATH_TYPES = ['project', 'subject', 'experiment']
"""The XNAT types in the experiment lineage."""

INOUT_CONTAINER_TYPES = ['reconstruction', 'assessor']
"""The XNAT ``in_resource`` and ``out_resource`` container types."""

CONTAINER_TYPES = ['scan'] + INOUT_CONTAINER_TYPES
"""The XNAT resource container types."""

RESOURCE_TYPES = ['resource', 'in_resource', 'out_resource']
"""The XNAT resource types."""

XNAT_TYPES = set(EXPERIMENT_PATH_TYPES + CONTAINER_TYPES + RESOURCE_TYPES +
                 ['file'])
"""The standard XNAT object types."""

ASSESSOR_SYNONYMS = ['analysis', 'assessment']
"""Alternative designations for the XNAT ``assessor`` container type."""

CONTAINER_DESIGNATIONS = CONTAINER_TYPES + ASSESSOR_SYNONYMS
"""The :const:`CONTAINER_TYPES` and :const:`ASSESSOR_SYNONYMS`."""

UNLABELED_TYPES = ['reconstruction']
"""The XNAT types which do not have a label attribute."""

HIERARCHICAL_LABEL_TYPES = ['experiment', 'assessor', 'reconstruction']
"""The XNAT types whose label is prefixed by the parent label."""

MODALITY_TYPES = ['experiment', 'scan']
"""The XNAT types which have modality subtypes."""

DATE_FMT = "%Y-%m-%d"
"""
The XML schema xs:date string format which pyxnat uses to represent
dates.
"""