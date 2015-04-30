import os
import re
from qiutil.logging import logger
from qiutil.collections import is_nonstring_iterable
from .configuration import configuration_file
from .helpers import (xnat_name, path_hierarchy, hierarchical_label)
try:
    import pyxnat
    from pyxnat.core.resources import (Experiment, Scan, Reconstruction,
                                       Reconstructions, Assessor, Assessors,
                                       Resources)
    from .constants import (CONTAINER_TYPES, ASSESSOR_SYNONYMS,
                            INOUT_CONTAINER_TYPES, HIERARCHICAL_LABEL_TYPES)
except ImportError:
    # Ignore pyxnat import failure to allow ReadTheDocs auto-builds.
    # See the installation instructions for why auto-build fails.
    pass


class XNATError(Exception):
    pass


class ChildNotFoundError(Exception):
    pass


class XNAT(object):
    """
    XNAT is a pyxnat facade convenience class. An XNAT instance is
    created in a :meth:`connection`
    context, e.g.:

    >>> from qiutil import qixnat
    >>> with qixnat.connect() as xnat:
    ...     sbj = xnat.get_subject('QIN_Test', 'Breast003')

    This XNAT wrapper class implements methods to access XNAT objects in
    a hierarchical name space using a labeling convention. The access
    method parameters are XNAT hierarchy object name values. Here, the
    *name* refers to the ending portion of the XNAT label that strips
    out the parent label. The name parameters are used to build the
    XNAT label, as shown in the following example:

        +----------------+-------------+---------------------------------+
        | Class          | Name        | Label                           |
        +================+=============+=================================+
        | Project        | QIN         | QIN                             |
        +----------------+-------------+---------------------------------+
        | Subject        | Breast003   | Breast003                       |
        +----------------+-------------+---------------------------------+
        | Experiment     | Session01   | Breast003_Session01             |
        +----------------+-------------+---------------------------------+
        | Scan           | 1           | 1                               |
        +----------------+-------------+---------------------------------+
        | Reconstruction | reco_fTkr4Y | Breast003_Session01_reco_fTkr4Y |
        +----------------+-------------+---------------------------------+
        | Assessor       | pk_4kbEv3r  | Breast003_Session01_pk_4kbEv3r  |
        +----------------+-------------+---------------------------------+
        | Resource       | reg_zaK1Bd  | reg_zaK1Bd                      |
        +----------------+-------------+---------------------------------+
        | File           | volume3.nii | volume3.nii                     |
        +----------------+-------------+---------------------------------+

        Table 1. Example XNAT label generation.

    :Note: The XNAT Reconstruction data type is deprecated. An experiment
        or scan Resource should be used instead.

    The XNAT label is set by the user and conforms to the following
    uniqueness constraints:

    * the Project label is unique within the database.

    * the Subject, Experiment, Assessor and Reconstruction label is unique
      within the Project.

    * the Scan label is unique within the scope of the Experiment.

    * the Resource label is unique within the scope of its parent container.

    * the File label is unique within the scope of its parent Resource.

    A constraint violation results in a ``DatabaseError`` with REST
    HTTP status 409 or 500, with the following exception:

    * If a *subject1* Experiment is created with the same label as a
      *subject2* Experiment in the same Project, then the *subject1*
      Experiment is moved to *subject2*, e.g.:

      >>> from qixnat.facade import XNAT
      >>> xnat = XNAT().interface
      >>> sbj1 = xnat.select('/project/QIN_Test/subject/Breast003')
      >>> exp1 = sbj1.experiment('Session01').create()
      >>> sbj2 = xnat.select('/project/QIN_Test/subject/Breast004')
      >>> exp2 = sbj2.experiment('Session01').create()
      >>> exp1.exists()
      False

    The pyxnat access methods specify an *id* parameter, but in fact either
    the id or label can be used for the *id* parameter, consistent with the
    XNAT REST interface, e.g.:

    >>> from qixnat.facade import XNAT
    >>> xnat = XNAT().interface
    >>> sbj1 = xnat.select('/project/QIN_Test/subject/Breast003')
    >>> exp1 = sbj1.experiment('Breast003_Session01')
    >>> if exp1.exists():
    ...     exp1.delete()
    >>> exp1.id() == None
    True
    >>> exp1.label() == None
    True
    >>> exp1.create().id() == None
    False
    >>> exp1.label()
    'Breast003_Session01'
    >>> exp2 = sbj1.experiment(exp1.id())
    >>> exp1.label() == exp2.label()
    True

    XNAT generates the id as follows:

    * The Project, Scan and File id and label are identical

    * A Reconstruction does not have an XNAT id

    * The Subject id is an opaque XNAT-generated value starting with
      *project*\ _S.

    * The Experiment and Assessor id is an opaque XNAT-generated value
      starting with *project*\ _E.

    * The Resource is an opaque XNAT-generated string value consisting
      of digits.

    Each opaque XNAT-generated identifier is unique within the database.

    The following table shows example XNAT ids and labels:

        +----------------+------------+-------------------------------------+
        | Class          | Id         | Label                               |
        +================+============+=====================================+
        | Project        | QIN        | QIN                                 |
        +----------------+------------+-------------------------------------+
        | Subject        | QIN_S00580 | Breast003                           |
        +----------------+------------+-------------------------------------+
        | Experiment     | QIN_E00604 | Breast003_Session01                 |
        +----------------+------------+-------------------------------------+
        | Scan           | 1          | 1                                   |
        +----------------+------------+-------------------------------------+
        | Reconstruction | --         | Breast003_Session01_reco_fTkr4Y     |
        +----------------+------------+-------------------------------------+
        | Assessor       | QIN_E00868 | Breast003_Session01_pk_4kbEv3r      |
        +----------------+------------+-------------------------------------+
        | Resource       | 3187       | reg_zaK1Bd                          |
        +----------------+------------+-------------------------------------+
        | File           | image3.nii | image3.nii                          |
        +----------------+------------+-------------------------------------+

        Table 2. Example XNAT ids and labels.

    In the example above, the XNAT assessor object is obtained as
    follows::

        from qiutil import qixnat
        with qixnat.connect() as xnat:
             recon = xnat.get_assessor('QIN', 'Breast003', 'Session01',
                                       'pk_4kbEv3r')

    XNAT files are always placed in a XNAT *resource*, e.g.::

        xnat.upload('QIN', 'Breast003', 'Session01', scan=1,
                    resource='DICOM', *dicom_files)
    """

    SUBJECT_QUERY_FMT = "/project/%s/subject/%s"
    """The subject query template."""

    def __init__(self, config=None):
        """
        :param config: the configuration file, or None to connect with
            the :meth:`configuration_file`
        """
        self._logger = logger(__name__)
        self._connect(config)

    def _connect(self, config=None):
        if not config:
            config = configuration_file()
        self._logger.debug("Connecting to XNAT with config %s..." % config)
        self.interface = pyxnat.Interface(config=config)

    def close(self):
        """Drops the XNAT connection."""
        self.interface.disconnect()
        self._logger.debug("Closed the XNAT connection.")

    def exists(self, obj):
        """
        @return whether the given object is an existing XNAT object
        """
        return obj and obj.exists()

    def delete_subjects(self, project, *subjects):
        """
        Deletes the given XNAT subjects, if they exist.

        :Note: this function is intended primarily for testing purposes.
            Use with care.

        :param project: the XNAT project id
        :param subjects: the XNAT subject names
        """
        for sbj in subjects:
            sbj_obj = self.get_subject(project, sbj)
            if self.exists(sbj_obj):
                sbj_obj.delete()
                logger(__name__).debug("Deleted the %s subject %s." %
                                       (project, sbj))

    def children_methods(self, obj):
        """
        Returns the XNAT children accessor methods for the given XNAT object.

        This method works around the following pyxnat/XNAT bugs:

        * The pyxnat 0.9.1 Assessor resources accessor method raises the
          following exception::

              KeyError: 'xnat_abstractresource_id'

          The work-around is to ignore the Assessor resources method.

        * The pyxnat 0.9.1 children method sometimes incorrectly returns
          an empty list. This bug occurs when iterating over experiment
          children. For example, the first reconstruction returns::

                ['in_resources', 'out_resources']

          but the remaining reconstructions return an empty list. This occurs
          in the qiutil ``qils`` script *_collect_resources* method, but does
          not occur in ipython.

          The work-around is to replace the pyxnat empty list by the
          children accessor methods defined for Scan and Reconstruction.
        """
        # Always override the pyxnat children call on an Assessor, since
        # the pyxnat resources acessor method is crippled.
        if isinstance(obj, Assessor):
            return ['in_resources', 'out_resources']

        # Call pyxnat, for what that's worth.
        methods = obj.children()
        # If pyxnat returns a non-empty value, then use that value. Otherwise,
        # override pyxnat for Scan and Resource.
        if methods:
            return methods
        elif isinstance(obj, Scan):
            return ['resources']
        elif isinstance(obj, Reconstruction):
            return ['in_resources', 'out_resources']
        else:
            return methods

    def get_subject(self, project, subject):
        """
        Returns the XNAT subject object for the given XNAT lineage.

        :param project: the XNAT project id
        :param subject: the XNAT subject name
        :return: the corresponding XNAT subject (which may not exist)
        """
        # The query path.
        qpath = XNAT.SUBJECT_QUERY_FMT % (project, subject)

        return self.interface.select(qpath)

    def get_experiment(self, project, subject, experiment):
        """
        Returns the XNAT experiment object for the given XNAT lineage.
        The experiment name is qualified by the subject name prefix,
        if necessary.

        :param project: the XNAT project id
        :param subject: the XNAT subject label
        :param experiment: the XNAT experiment label
        :return: the corresponding XNAT experiment (which may not exist)
        """
        label = hierarchical_label(subject, experiment)

        return self.get_subject(project, subject).experiment(label)

    get_session = get_experiment

    def get_scan(self, project, subject, experiment, scan):
        """
        Returns the XNAT scan object for the given XNAT lineage.
        The lineage names are qualified by a prefix, if necessary,
        as described in :meth:`get_experiment`.

        :param project: the XNAT project id
        :param subject: the XNAT subject label
        :param experiment: the XNAT experiment label
        :param scan: the XNAT scan name or number
        :return: the corresponding XNAT scan object (which may not exist)
        """
        exp = self.get_experiment(project, subject, experiment)

        return exp.scan(str(scan))

    def get_reconstruction(self, project, subject, experiment, recon):
        """
        Returns the XNAT reconstruction object for the given XNAT lineage.
        The lineage names are qualified by a prefix, if necessary,
        as described in :meth:`get_experiment`.

        :Note: The XNAT reconstruction data type is deprecated. Use an
            experiment resource instead.

        :param project: the XNAT project id
        :param subject: the subject name
        :param experiment: the experiment name
        :param recon: the XNAT reconstruction name
        :return: the corresponding XNAT reconstruction object
            (which may not exist)
        """
        label = hierarchical_label(subject, experiment, recon)
        exp = self.get_experiment(project, subject, experiment)

        return exp.reconstruction(label)

    def get_scan_resource(self, project, subject, experiment, scan, resource):
        """
        Returns the XNAT resource object for the given XNAT lineage.
        The resource parent is the XNAT experiment experiment.
        The lineage names are qualified by a prefix, if necessary,
        as described in :meth:`get_experiment`.

        :param project: the XNAT project id
        :param subject: the subject name
        :param experiment: the experiment name
        :param scan: the scan number
        :param resource: the XNAT resource name
        :return: the corresponding XNAT resource object
            (which may not exist)
        """
        exp = self.get_scan(project, subject, experiment, scan)

        return exp.resource(resource)

    def get_assessor(self, project, subject, experiment, assessor):
        """
        Returns the XNAT assessor object for the given XNAT lineage.
        The lineage names are qualified by a prefix, if necessary,
        as described in :meth:`get_experiment`.

        :Note: an XNAT bug results in missing assessors if the accessing
          XNAT user has administrative priveleges, but is not a member
          or owner of the project. See the XNAT users forum
          `post <https://groups.google.com/forum/#!topic/xnat_discussion/w6M74PTqgi4>`__
          on this topic.

        :param project: the XNAT project id
        :param subject: the subject name
        :param experiment: the experiment name
        :param assessor: the assessor name
        :return: the corresponding XNAT assessor object
            (which may not exist)
        """
        label = hierarchical_label(subject, experiment, assessor)
        exp = self.get_experiment(project, subject, experiment)

        return exp.assessor(label)

    # Define the get_assessor function aliases.
    get_assessment = get_assessor
    get_analysis = get_assessor

    def download(self, project, subject, experiment, **opts):
        """
        Downloads the files for the specified XNAT experiment.

        The keyword arguments include the resource name and the experiment
        child container. The experiment child container option can be set
        to either a specific resource container, e.g. ``scan=1``, as
        described in :meth:`upload` or all resources of a given container
        type. In the latter case, the *container_type* parameter is set.
        The permissible container types are described in :meth:`upload`.

        The XNAT object labels are qualified, if necessary, e.g.::

            download('QIN', 'Breast001', 'Session03', scan=1,
                     resource='reg_jA4K')

        downloads the files for the XNAT experiment with label
        ``Breast001_Session03``, scan id 1 and resource label ``reg_jA4K``.

        :param project: the XNAT project id
        :param subject: the XNAT subject label
        :param experiment: the XNAT experiment label
        :param opts: the following keyword options:
        :keyword scan: the scan number
        :keyword reconstruction: the reconstruction name
        :keyword analysis: the analysis name
        :keyword container_type: the container type, if no specific
            container is specified (default ``scan``)
        :keyword resource: the resource name
            (scan default is ``NIFTI``)
        :keyword inout: the ``in``/``out`` container resource qualifier
            (default ``out`` for a container type that requires this option)
        :keyword file: the XNAT file name
            (default all files in the resource)
        :keyword dest: the optional download location
            (default current directory)
        :return: the downloaded file names
        """
        # The XNAT experiment, which must exist.
        exp = self.get_experiment(project, subject, experiment)
        if not self.exists(exp):
            raise XNATError("The XNAT download experiment was not found: %s" %
                            experiment)

        # The XNAT file name.
        fname = opts.pop('file', None)

        # The resource.
        rsc = self._infer_resource(exp, opts)

        # The XNAT file object list.
        if fname:
            file_obj = rsc.file(fname)
            # rsc might be a Resources collection rather than a Resource,
            # in which case the file method returns a Files collection.
            # If that occurs, then rsc_files is the collection. Otherwise,
            # make a singleton File list.
            if is_nonstring_iterable(file_obj):
                rsc_files = file_obj
            else:
                rsc_files = [file_obj]
        else:
            rsc_files = list(rsc.files())

        # The download location.
        dest = opts.pop('dest', None) or os.getcwd()
        # If there are files to download, then prepare the download directory.
        # Otherwise, issue a debug log message.
        if rsc_files:
            if fname:
                file_clause = "%s file" % fname
            else:
                file_clause = "%d files" % len(rsc_files)
            self._logger.debug("Downloading %s %s %s %s %s to %s..." %
                               (project, subject, experiment, opts, file_clause, dest))
            if not os.path.exists(dest):
                os.makedirs(dest)
        else:
            self._logger.debug("The %s %s %s %s resource does not contain any"
                               " files." % (project, subject, experiment, opts))

        return [self.download_file(file_obj, dest, **opts) for file_obj in rsc_files]

    def download_file(self, file_obj, dest, **opts):
        """
        :param file_obj: the XNAT File object
        :param dest: the target directory
        :param opts: the following option:
        :keyword force: overwrite existing file
        :return: the downloaded file path
        """
        fname = file_obj.label()
        if not fname:
            raise XNATError("XNAT file object does not have a name: %s" %
                            file_obj)
        tgt = os.path.join(dest, fname)
        if os.path.exists(tgt):
            if opts.get('skip_existing'):
                if opts.get('force'):
                    raise XNATError('The XNAT download option --skip_existing'
                                    ' is incompatible with the --force option')
                return tgt
            elif not opts.get('force'):
                raise ValueError("Download target file already exists: %s" % tgt)
        self._logger.debug("Downloading the XNAT file %s to %s..." %
                           (fname, dest))
        file_obj.get(tgt)
        self._logger.debug("Downloaded the XNAT file %s." % tgt)

        return tgt

    def upload(self, project, subject, experiment, *in_files, **opts):
        """
        Imports the given files into XNAT. The target XNAT resource has the
        following hierarchy::

            /project/PROJECT/
                subject/SUBJECT/
                    experiment/SESSION/
                        [CTR_TYPE/CONTAINER/]
                            resource/RESOURCE

        where:

        - the *experiment* parameter is the XNAT experiment name

        - CTR_TYPE is the experiment child type ``scan``, ``assessor``
          or ``reconstruction``

        - CONTAINER is the container name

        - the default scan RESOURCE is the file format, e.g. ``NIFTI`` or
          ``DICOM``

        - if ``CTR_TYPE/CONTAINER/`` is missing, then the resource parent
          is the experiment

        The keyword arguments include the experiment child container, scan
        *modality* and *resource* name. The required container keyword
        argument associates the container type to the container name,
        e.g. ``scan=1``. The container type is ``scan``, ``reconstruction``
        or ``analysis``. The ``analysis`` container type value corresponds
        to the XNAT ``assessor`` Image Assessment type. ``analysis``,
        ``assessment`` and ``assessor`` are synonymous. The container name
        can be a string or integer, e.g. the scan number.

        If the XNAT file extension is ``.nii``, ``.nii.gz``, ``.dcm`` or
        ``.dcm.gz``, then the default scan resource name ``NIFTI`` or
        ``DICOM`` is inferred from the extension.

        If an XNAT object in the hierarchy does not yet exist, then it is
        created. If the experiment does not yet exist as a XNAT experiment,
        then the modality keyword argument is required. The modality is any
        supported XNAT modality, e.g. ``MR`` or  or ``CT``. A capitalized
        modality value is a synonym for the XNAT experiment data type, e.g.
        ``MR`` is a synonym for ``xnat:mrSessionData``.

        Example::

            from qiutil import qixnat
            with qixnat.connect() as xnat:
                xnat.upload('QIN', 'Sarcoma003', 'Sarcoma003_Session01',
                    scan=4, modality='MR', '/path/to/image.nii.gz')

        :param project: the XNAT project id
        :param subject: the XNAT subject name
        :param experiment: the XNAT experiment name
        :param in_files: the input files to upload
        :param opts: the following experiment child container, file format,
            scan modality and optional additional XNAT file creation
            options:
        :keyword scan: the scan number
        :keyword reconstruction: the reconstruction name
        :keyword analysis: the analysis name
        :keyword modality: the experiment modality
        :keyword resource: the resource name (scan default is inferred from
            the file extension)
        :keyword inout: the container ``in``/``out`` option
            (default ``out`` for a container type that requires this option)
        :keyword force: flag indicating whether to replace an existing
            file (default False)
        :return: the new XNAT file names
        :raise XNATError: if the project does not exist
        :raise ValueError: if the experiment child resource container type
            option is missing
        :raise ValueError: if the XNAT experiment does not exist and the
            modality option is missing
        """
        # Validate that there is sufficient information to infer a resource
        # parent container.
        ctr_spec = self._infer_resource_container(opts)
        if ctr_spec:
            ctr_type, _ = ctr_spec
        else:
            ctr_type = None

        # Infer the scan resource, if necessary.
        rsc = opts.pop('resource', None)
        if not rsc:
            if ctr_type == 'scan':
                rsc = self._infer_format(*in_files)
                if not rsc:
                    raise ValueError("XNAT %s %s %s upload can not infer the"
                                     " scan resource from the options %s" %
                                     (project, subject, experiment, opts))
            else:
                raise ValueError("XNAT %s %s %s upload is missing the resource"
                                 " name" % (project, subject, experiment))

        # The XNAT resource parent container.
        rsc_obj = self.find(project, subject, experiment, create=True,
                            resource=rsc, **opts)

        # Upload the files.
        self._logger.debug("Uploading %d %s %s %s %s files to XNAT..." %
                           (len(in_files), project, subject, experiment,
                            rsc_obj.label()))
        xnat_files = [self._upload_file(rsc_obj, f, **opts) for f in in_files]
        self._logger.debug("%d %s %s %s files uploaded to XNAT." %
                           (len(in_files), project, subject, experiment))

        return xnat_files

    def find(self, project, subject, experiment=None, **opts):
        """
        Finds the given XNAT object in the following hierarchy::

            /project/PROJECT/
                subject/SUBJECT/
                    experiment/EXPERIMENT/
                        CTR_TYPE/CONTAINER

        where CTR_TYPE is the experiment child type, e.g. ``scan``.

        If the ``create`` flag is set, then the object is created if it
        does not yet exist.

        The keyword arguments specify the experiment child container and
        resource. The container keyword argument associates the container
        type to the container name, e.g. ``reconstruction=reg_zPa4R``.
        The container type is ``scan``, ``reconstruction`` or ``analysis``.
        The ``analysis`` container type value corresponds to the XNAT
        ``assessor`` Image Assessment type. ``analysis``, ``assessment``
        and ``assessor`` are synonymous. The container name can be a string
        or integer, e.g. the scan number. The resource is specified by the
        *resource* keyword.

        If the experiment does not yet exist as a XNAT experiment and the
        *create* option is set, then the *modality* keyword argument
        specifies a scan modality, e.g. ``MR`` or  or ``CT``. The modality
        argument can be one of the following forms:
        * The XNAT modality XML value prefixed by the ``xnat`` XML context,
            e.g. ``xnat:ctSessionData``
        * The unqualified XNAT modality XML value, e.g. `ctSessionData``
        * The case-insensitive XNAT modality XML value prefix, e.g. ``ct``
            or ``CT``

        A capitalized modality value is a synonym for the XNAT experiment
        data type, e.g. ``MR`` is a synonym for ``xnat:mrSessionData``.
        The default modality is ``MR``.

        The *scan* option value can be a number or a {attribute: value}
        dictionary. If the *scan* option value is a number, then the scan
        with that number is searched. Otherwise, if the *scan* option is
        a dictionary, then the dictionary must contain the *number* key.
        Other dictionarty items are assigned to the scan object. The
        scan attributes are defined by the XNAT schema. The standard
        scan attributes are as follows:
        * note
        * quality
        * condition
        * series_description
        * documentation
        The *scan* dictionary argument can include a *description* item
        which aliases *series_description*.

        The *file* option specifies a file name or existing file path.
        The *file* option is used in conjunction with a *resource* option.
        If the *file* option is set, then this method searches for an XNAT
        file object whose label matches the file name in the given resource.
        If there is no such file object and the *create* flag is set, then
        the file at the given path is uploaded to the specified resource.

        Example:

        >>> from qiutil import qixnat
        >>> with qixnat.connect() as xnat:
        ...     subject = xnat.find('QIN', 'Sarcoma003')
        ...     session = xnat.find('QIN', 'Sarcoma003', 'Session01', create=True)
        ...     scan = xnat.find('QIN', 'Sarcoma003', 'Session01', scan=1)
        ...     resource = xnat.find('QIN', 'Sarcoma003', 'Session01', scan=1)
        ...     scan_dict = dict(number=2, description='T1')
        ...     scan = xnat.find('QIN', 'Sarcoma003', 'Session01', scan=scan_dict)

        :param project: the XNAT project id
        :param subject: the XNAT subject name
        :param experiment: the XNAT experiment name
        :param opts: the following container options:
        :keyword scan: the scan number or attribute dictionary
        :keyword reconstruction: the reconstruction name
        :keyword analysis: the analysis name
        :keyword resource: the resource name
        :keyword file: the file name
        :keyword inout: the resource direction (``in`` or ``out``)
        :keyword modality: the experiment modality (default ``MR``)
        :keyword create: flag indicating whether to create the XNAT object
            if it does not yet exist
        :return: the XNAT object, if it exists, `None` otherwise
        :raise XNATError: if the project does not exist
        :raise ValueError: if the experiment child resource container type
            option is missing
        """
        create = opts.pop('create', False)

        # If no experiment is specified, then return the XNAT subject.
        if not experiment:
            sbj = self.get_subject(project, subject)
            if self.exists(sbj):
                return sbj
            elif create:
                self._logger.debug("Creating the XNAT %s %s subject..." %
                                   (project, subject))
                sbj.insert()
                self._logger.debug("Created the XNAT %s %s subject with"
                                   " id %s." % (project, subject, sbj.id()))
                return sbj
            else:
                return

        # The XNAT experiment.
        exp = self.get_experiment(project, subject, experiment)

        # If there is an experiment and we are not asked for a container,
        # then return the experiment.
        # Otherwise, if create is specified, then create the experiment.
        # Otherwise, bail.
        if not self.exists(exp):
            if create:
                # If the experiment must be created, then we need the
                # modality.
                modality = opts.pop('modality', None)
                if not modality:
                    raise ValueError("The modality argument is missing to"
                                     " create /%s/%s/%s" %
                                     (project, subject, experiment))
                std_modality = self._standardize_modality(modality)
                # The odd way pyxnat specifies the modality is the
                # experiments option.
                exp_opts = dict(experiments=std_modality)
                # Create the experiment.
                self._logger.debug("Creating the XNAT %s %s %s experiment..." %
                                   (project, subject, experiment))
                exp.insert(**opts)
                self._logger.debug("Created the XNAT %s %s %s experiment with"
                                   " id %s." %
                                   (project, subject, experiment, exp.id()))
            else:
                return

        # The scan value can be a dictionary.
        scan_value = opts.get('scan')
        if isinstance(scan_value, dict):
            ctr_opts = scan_value
            # Reset the scan option to the scan number.
            # The XNAT insert *scans* keyword will be set
            # to the remaining scan attributes dictionary.
            if 'number' not in ctr_opts:
                raise ValueError("The scan options must include the number:"
                                 " %s" % ctr_opts)
            opts['scan'] = ctr_opts.pop('number')
            # description is an alias for series_description.
            desc = ctr_opts.pop('description', None)
            if desc:
                ctr_opts['series_description'] = desc
        else:
            # No container options.
            ctr_opts = {}

        # The resource parent container.
        ctr_spec = self._infer_resource_container(opts)

        # If the container was specified, then obtain the container object.
        # Otherwise, the default resource parent is the experiment.
        if ctr_spec:
            ctr_type, ctr_id = ctr_spec
            if not ctr_id:
                raise ValueError("XNAT %s %s %s %s object id is missing" %
                                (project, subject, experiment, ctr_type))
            ctr = self._resource_parent(exp, ctr_type, ctr_id)
            if not self.exists(ctr):
                if create:
                    self._logger.debug("Creating the XNAT %s %s %s %s %s"
                                       " object..." %
                                       (project, subject, experiment, ctr_type,
                                        ctr_id))
                    # Insert the XNAT object.
                    ctr.insert()
                    # Set the optional attribute values.
                    if ctr_opts:
                        self._logger.debug("Setting the XNAT %s %s %s %s %s "
                                           " attributes %s..." %
                                           (project, subject, experiment, ctr_type,
                                            ctr_id,
                                            ctr_opts))
                        ctr.attrs.mset(ctr_opts)
                    self._logger.debug("Created the XNAT %s %s %s %s %s object"
                                       " with id %s" %
                                       (project, subject, experiment, ctr_type,
                                        ctr_id, ctr.id()))
                else:
                    return
        else:
            ctr_type = 'experiment'
            ctr = exp

        # Find the resource, if specified.
        resource = opts.get('resource')
        if not resource:
            return ctr

        rsc_obj = self._child_resource(ctr, resource, opts.get('inout'))
        if not self.exists(rsc_obj):
            if create:
                if ctr_spec:
                    self._logger.debug("Creating the XNAT %s %s %s %s %s %s"
                                       " resource..." %
                                       (project, subject, experiment, ctr_type,
                                        ctr_id, resource))
                else:
                    self._logger.debug("Creating the XNAT %s %s %s %s"
                                       " resource..." %
                                       (project, subject, experiment, resource))
                rsc_obj.insert()
                if ctr_spec:
                    self._logger.debug("Created the XNAT %s %s %s %s %s %s"
                                       " resource with id %s." %
                                       (project, subject, experiment, ctr_type,
                                        ctr_id, resource, rsc_obj.id()))
                else:
                    self._logger.debug("Created the XNAT %s %s %s %s"
                                       " resource with id %s." %
                                       (project, subject, experiment, resource,
                                        rsc_obj.id()))
            else:
                return

        if 'file' in opts:
            path = opts['file']
            _, fname = os.path.split(path)
            file_obj = rsc_obj.file(fname)
            if self.exists(file_obj):
                return file_obj
            elif create:
                file_obj.insert(path, **opts)
                self._logger.debug("Created the XNAT %s %s %s %s %s"
                                   " file with id %s." %
                                   (project, subject, experiment, resource,
                                    fname, file_obj.id()))
                return file_obj
            else:
                return
        else:
            return rsc_obj

    def expand_path(self, path):
        """
        Returns the XNAT object children in the given XNAT object path.
        The *path* string argument must conform to the
        :meth:`qixnat.helpers.path_hierarchy` requirements.

        :param path: the path string
        :return: the XNAT child label list
        :raise: ChildNotFoundError if there is no such child
        """
        # The hierarchy list.
        hierarchy = path_hierarchy(path)
        # The query path.
        prj_type, prj_label = hierarchy.pop(0)
        qpath = "/%s/%s" % (prj_type, prj_label)
        # The first XNAT object.
        logger(__name__).debug("Selecting the XNAT hierarchy parent %s..." %
                               qpath)
        qresult = self.interface.select(qpath)
        if '*' in prj_label:
            parents = sorted([prj for prj in qresult], None, xnat_name)
        else:
            parents = [qresult]

        # Expand the children.
        closures = [self._expand_child_hierarchy(parent, hierarchy)
                    for parent in parents]
        # Concatenate the children lists.
        children = reduce(lambda x, y: x + y, closures, [])
        if not children:
            raise ChildNotFoundError("%s: No such XNAT object" % path)

        return children


    def _expand_child_hierarchy(self, parent, hierarchy):
        """
        Returns the XNAT object children in the given hierarchy.
        The *hierarchy* consists of child path components as described in
        the :meth:`path_hierarchy` result.

        :param parent: the parent XNAT object
        :param hierarchy: the child hierarchy
        :return: the XNAT child label list
        """
        # The trivial case.
        if not hierarchy:
            return [parent]

        logger(__name__).debug("Expanding the %s XNAT child hierarchy %s..." %
                               (parent, hierarchy))
        # The immediate child attribute and match value.
        attr, val = hierarchy[0]
        # The children which match the attribute and value.
        children = self._xnat_children(parent, attr, val)
        # Sort the children on the XNAT name.
        sorted_children = sorted(children, None, xnat_name)
        # Recurse.
        closures = [self._expand_child_hierarchy(child, hierarchy[1:])
                    for child in sorted_children]

        # Concatenate the closures.
        return reduce(lambda x, y: x + y, closures, [])

    def _xnat_children(self, xnat_obj, attribute, value=None):
        """
        Returns the XNAT object children for the given child attribute
        and value. If the value includes a wild card, e.g.
        ``('resource', 'reg_*')``, then all XNAT objects whose label
        matches the value are returned. Otherwise, the value is
        a label or id search target.

        :param xnat_obj: the parent XNAT object
        :param attribute: the XNAT child attribute
        :param value: the value to match against the child XNAT label,
            or None for all children
        :return: the matching XNAT child objects
        """
        # Prepend the parent label, if necessary.
        if value:
            if (attribute in HIERARCHICAL_LABEL_TYPES and
                not value.startswith(xnat_obj.label())):
                value = '_'.join([xnat_obj.label(), value])

            # A wild card label => search on the children.
            if isinstance(value, str) and '*' in value:
                # Pluralize the attribute, if necessary, for a wild
                # card search.
                if attribute[-1] != 's':
                    attribute += 's'
                children = self._xnat_children(xnat_obj, attribute)
                # Simple asterisk => all children match.
                if value == '*':
                    return children
                # Convert a glob wild card (*) to an re match (.*).
                label_pat = re.escape(value).replace('\*', '.*') + '$'
                return [child for child in children
                        if re.match(label_pat, child.label())]

            # Not a wild card; get the child with the specified label.
            if attribute == 'assessor':
                # Work around XNAT assessor URI/label inconsistency.
                child = None
                if xnat.exists(xnat_obj):
                    for assr in xnat_obj.assessors():
                        if assr.label() == value:
                            child = assr
            elif isinstance(xnat_obj, Assessor) and attribute == 'resource':
                return (self._xnat_children(xnat_obj, ('in_resource', value)) or
                        self._xnat_children(xnat_obj, ('out_resource', value)))
            else:
                child = self._xnat_child(xnat_obj, attribute, value)
            return [child] if self.exists(child) else []
        elif isinstance(xnat_obj, Assessor) and attribute == 'resources':
            # Work around a pyxnat bug that fetches abstract resource objects
            # rather than the concrete objects.
            in_rscs = self._xnat_children(xnat_obj, 'in_resources')
            out_rscs = self._xnat_children(xnat_obj, 'out_resources')
            return [r for r in in_rscs] + [r for r in out_rscs]
        else:
            # Call the accessor.
            return getattr(xnat_obj, attribute)()

    def _xnat_child(self, parent, attribute, label):
        """
        Curries the given label into the parent accessor partial function.

        :param parent: the parent XNAT object
        :param attribute: the accessor attribute, e.g. ``resource``
        :param label: the child XNAT label
        """
        return getattr(parent, attribute)(label)

    def _standardize_modality(self, modality):
        """
        Standardizes the modality as described in :meth:`find`.
        Examples:

        >>> from qiutil import qixnat
        >>> with qixnat.connect() as xnat:
        ...     xnat._standardize_modality('ctSessionData')
        'xnat:ctSessionData'
        >>> with qixnat.connect() as xnat:
        ...     xnat._standardize_modality('MR')
        'xnat:mrSessionData'

        :param modality: the modality option described in
            :meth:`find`
        :return: the standard XNAT modality value
        """
        if modality.startswith('xnat:'):
            return modality
        elif modality.endswith('SessionData'):
            return 'xnat:' + modality
        else:
            long_modality = modality.lower() + 'SessionData'
            return self._standardize_modality(long_modality)

    def _infer_resource(self, experiment, opts):
        """
        Infers the XNAT resource type and value from the given options.
        The default scan resource is ``NIFTI``.

        :param experiment: the XNAT experiment object
        :param opts: the :meth:`download` options
        :return: the container *(type, value)* tuple
        """
        # The resource parent type and name.
        ctr_spec = self._infer_resource_container(opts)
        if ctr_spec:
            rsc_parent = self._resource_parent(experiment, *ctr_spec)
        else:
            rsc_parent = experiment

        # The resource name.
        rsc = opts.get('resource')
        # The resource.
        return self._child_resource(rsc_parent, rsc, opts.get('inout'))

    def _infer_resource_container(self, opts):
        """
        Determines the resource container item from the given options as
        follows:

        - If there is a *container_type* option, then that type is returned
          without a value.

        - Otherwise, if the options include a container type in
          :data:`qixnat.constants.CONTAINER_TYPES`,
          then the option type and value are returned.

        - Otherwise, if the options include a container type in
          :data:`qixnat.constants.ASSESSOR_SYNONYMS`,
          then the `assessor` container type and the option value are
          returned.

        - Otherwise, this method returns ``None``.

        :param opts: the options to check
        :return: the container (type, value) tuple, or None if no container
            was specified
        """
        if 'container_type' in opts:
            return (opts['container_type'], None)
        for t in CONTAINER_TYPES:
            if t in opts:
                return (t, opts[t])
        for t in ASSESSOR_SYNONYMS:
            if t in opts:
                return ('assessor', opts[t])

    def _container_type(self, name):
        """
        :param name: the L{qixnat.constants.CONTAINER_TYPES} or
            L{qixnat.constants.ASSESSOR_SYNONYMS} container designator
        :return: the standard XNAT designator in L{qixnat.constants.CONTAINER_TYPES}
        :raise XNATError: if the name does not designate a valid container
            type
        """
        if name in ASSESSOR_SYNONYMS:
            return 'assessor'
        elif name in CONTAINER_TYPES:
            return name
        else:
            raise XNATError("XNAT upload experiment child container not"
                            " recognized: %s" % name)

    def _resource_parent(self, experiment, container_type, name=None):
        """
        Returns the resource parent for the given experiment and container
        type. The resource parent is the experiment child with the given
        container type, e.g a MR experiment scan. The ``resource`` container
        type parent is the experiment.

        If there is a name, then the parent is the object with that name,
        e.g. a scan object. Otherwise, the parent is a container group, e.g.
        the experiment XNAT ``Scans`` instance.

        :param experiment: the XNAT experiment
        :param container_type: the container type in L{qixnat.constants.CONTAINER_TYPES}
        :param name: the optional container name
        :return: the XNAT resource parent object
        """
        if name:
            # Convert an integer name, e.g. scan number, to a string.
            name = str(name)
            # The parent is the experiment child for the given container type.
            if container_type == 'resource':
                return experiment
            elif container_type == 'scan':
                return experiment.scan(name)
            elif container_type == 'reconstruction':
                # The recon label is prefixed by the experiment label.
                label = hierarchical_label(experiment.label(), name)
                return experiment.reconstruction(label)
            elif container_type == 'assessor':
                # The assessor label is prefixed by the experiment label.
                label = hierarchical_label(experiment.label(), name)
                return experiment.assessor(label)
        elif container_type == 'scan':
            return experiment.scans()
        elif container_type == 'resource':
            return experiment.resources()
        elif container_type == 'reconstruction':
            return experiment.reconstructions()
        elif container_type == 'assessor':
            return experiment.assessors()
        raise XNATError("XNAT resource container type not recognized: %s" %
                        container_type)

    def _child_resource(self, parent, name=None, inout=None):
        """
        :param parent: the XNAT resource parent object
        :param name: the resource name, e.g. ``NIFTI``
        :param inout: the container in/out option described in
            :meth:`download`
            (default ``out`` for a container type that requires this option)
        :return: the XNAT resource object
        :raise XNATError: if the inout option is invalid
        """
        if name:
            if self._is_inout_container(parent):
                if inout == 'in':
                    rsc = parent.in_resource(name)
                elif inout in ['out', None]:
                    rsc = parent.out_resource(name)
                else:
                    raise XNATError("Unsupported resource inout option: %s" %
                                    inout)
                return rsc
            else:
                return parent.resource(name)
        elif isinstance(parent, Resources):
            return parent
        elif self._is_inout_container(parent):
            if inout == 'in':
                return parent.in_resources()
            elif inout in ['out', None]:
                return parent.out_resources()
            else:
                raise XNATError(
                    "Unsupported resource inout option: %s" % inout)
        else:
            return parent.resources()

    def _is_inout_container(self, container):
        """
        :param obj: the XNAT container object
        :return: whether the container resources are qualified as input or
            output
        """
        for ctr_type in INOUT_CONTAINER_TYPES:
            if isinstance(container, ctr_type):
                return True
        return False

    def _infer_format(self, *in_files):
        """
        Infers the given image file format from the file extension
        :param in_files: the input file paths
        :return: the image format, or None if the format could not be
            inferred
        :raise XNATError: if the input files don't have the same file
            extension
        """
        # A sample input file.
        in_file = in_files[0]
        # The XNAT file name.
        _, fname = os.path.split(in_file)
        # Infer the format from the extension.
        base, ext = os.path.splitext(fname)

        # Verify that all remaining input files have the same extension.
        if in_files:
            for f in in_files[1:]:
                _, other_ext = os.path.splitext(f)
                if ext != other_ext:
                    raise XNATError("Upload cannot determine a format from"
                                    " the heterogeneous file extensions: %s"
                                    " vs %f" % (fname, f))

        # Ignore .gz to get at the format extension.
        if ext == '.gz':
            _, ext = os.path.splitext(base)
        if ext == '.nii':
            return 'NIFTI'
        elif ext == '.dcm':
            return 'DICOM'

    def _upload_file(self, resource, in_file, **opts):
        """
        Uploads the given file to XNAT.

        :param resource: the existing XNAT resource object that will contain
          the file
        :param in_file: the input file path
        :param opts: the XNAT file options, as well as the following upload
          options:
        :keyword skip_existing: ignore if the file already exists
        :keyword force: replace an existing file
        :return: the XNAT file name
        :raise XNATError: if the XNAT file already exists and neither the
          *skip_existing* nor the *force* option is set
        """
        # The XNAT file name.
        _, fname = os.path.split(in_file)
        self._logger.debug("Uploading the XNAT file %s from %s..." %
                           (fname, in_file))

        # The XNAT file wrapper.
        file_obj = resource.file(fname)
        # The resource parent container.
        rsc_ctr = resource.parent()
        # Check for an existing file.
        if self.exists(file_obj):
            if opts.get('skip_existing'):
                if opts.get('force'):
                    raise XNATError('The XNAT upload option --skip_existing is'
                                    ' incompatible with the --force option')
                return fname
            elif opts.get('force'):
                # Delete the existing file before upload.
                file_obj.delete()
                # XNAT 1.6 pyxnat ignores file delete.
                if file_obj.exists():
                    raise XNATError("XNAT upload force option is not supported,"
                                    " since XNAT ignores file delete.")
            else:
                raise XNATError("The XNAT file object %s already exists in the"
                                " %s resource" % (fname, resource.label()))

        # Upload the file.
        rsc_ctr_type = rsc_ctr.__class__.__name__.lower()
        self._logger.debug("Inserting the XNAT file %s into the %s %s %s"
                           " resource..." % (fname, rsc_ctr.label(),
                                             rsc_ctr_type, resource.label()))
        file_obj.insert(in_file, **opts)
        self._logger.debug("Uploaded the XNAT file %s." % fname)

        return fname
