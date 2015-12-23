import os
import re
from qiutil.logging import logger
from qiutil.collections import (concat, is_nonstring_iterable)
from qiutil.file import splitexts
from .constants import (CONTAINER_DESIGNATIONS, CONTAINER_TYPES,
                        ASSESSOR_SYNONYMS, MODALITY_TYPES,
                        INOUT_CONTAINER_TYPES, HIERARCHICAL_LABEL_TYPES)
from .helpers import (xnat_key, path_hierarchy, hierarchical_label,
                      rest_type, rest_date, pluralize_type_designator)
try:
    import pyxnat
    from pyxnat.core.resources import (Project, File)
    from  pyxnat.core.errors import DatabaseError
except ImportError:
    # Ignore pyxnat import failure to allow ReadTheDocs auto-builds.
    # See the installation instructions for why auto-build fails.
    pass


class XNATError(Exception):
    pass


class XNAT(object):
    """
    XNAT is a pyxnat facade convenience class. An XNAT instance is
    created in a :meth:`connection`
    context, e.g.::

        from qiutil import qixnat
        with qixnat.connect() as xnat:
            sbj = xnat.find('QIN_Test', 'Breast003')

    This XNAT wrapper class implements methods to access XNAT objects
    in a hierarchical name space using a labeling convention. The
    access method parameters are XNAT hierarchy object name values.
    Here, the *name* refers to a designator for an XNAT object that
    is unique within the scope of the object parent. For non-scan
    XNAT objects, the name is the ending portion of the XNAT label
    that strips out the parent label. Since the XNAT scan label is
    conventionally the scan number as a string, the scan name
    converts the label to an integer, i.e. the scan name is the
    scan number designator.
    
    The name parameters are used to build the XNAT label, as shown in
    the following example:

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

    :Note: An XNAT id and label is a string. Although the scan label is
        customarily the scan number, pyxnat does not support an
        integer label. By contrast, this :class:`XNAT` class allows an
        integer name and converts it to a string to perform a XNAT
        search.

    The XNAT label is set by the user and conforms to the following
    uniqueness constraints:

    * the Project label is unique within the database.

    * the Subject, Experiment, Assessor and Reconstruction label is
      unique within the Project.

    * the Scan label is unique within the scope of the Experiment.

    * the Resource label is unique within the scope of its parent
      container.

    * the File label is unique within the scope of its parent Resource.

    All but one constraint violation results in a ``DatabaseError``
    with REST HTTP status 409 or 500. The one constraint
    violation which does not raise an exception results in the
    following data anomaly:

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

    The Project and opaque XNAT-generated identifiers are unique within
    the database. The Scan and File id is unique within its parent.

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
    follows:

    >>> import qixnat
    >>> with qixnat.connect() as xnat:
    ...     recon = xnat.find_one('QIN', 'Breast003', 'Session01',
    ...                       assessor='pk_4kbEv3r')

    XNAT files are always placed in an existing XNAT resource, e.g.::

        import qixnat
        with qixnat.connect() as xnat:
            rsc = xnat.find_or_create('QIN', 'Breast003', 'Session01',
                                      scan=1, resource='DICOM')
            xnat.upload(rsc, *dicom_files)
    """

    SUBJECT_QUERY_FMT = "/project/%s/subject/%s"
    """The subject query template."""

    def __init__(self, **opts):
        """
        :param opts: the XNAT configuration options
        """
        self._logger = logger(__name__)
        self.interface = pyxnat.Interface(**opts)

    def close(self):
        """Drops the XNAT connection."""
        self.interface.disconnect()
        self._logger.debug("Disconnected the XNAT client.")

    def find_path(self, path):
        """
        Returns the XNAT object children in the given XNAT object path.
        The *path* string argument must conform to the
        :meth:`qixnat.helpers.path_hierarchy` requirements.

        :param path: the path string
        :return: the XNAT child label list
        :raise: XNATError if there is no such child
        """
        # The hierarchy list.
        self._logger.debug("Expanding the path %s..." % path)
        hierarchy = path_hierarchy(path)
        opts = dict(hierarchy)
        result = self.find(**opts)
        self._logger.debug("Path %s results in %d objects." %
                           (path, len(result)))

        return result

    def download(self, *args, **opts):
        """
        Downloads the files contained in XNAT resource or resources.
        The parameters and options specify the target XNAT file
        search condition, as described in :meth:`find`, augmented
        as follows:
        - if there is no *resource* option, then all resources
          are included
        
        - if there is no *file* option, then all files in the
          selected resources are downloaded

        Example::

            download('QIN', 'Breast001', '*', scan=1, resource='reg_*')

        downloads the files for all ``QIN`` ``Breast001`` scan ``1``
        resources whose label begins with ``reg_``.

        :param project: the XNAT project id
        :param subject: the XNAT subject name
        :param experiment: the XNAT experiment name
        :param opts: the :meth:`find` hierarchy and :meth:`download_file`
            options, as well the following option:
        :keyword dest: the optional download location
            (default current directory)
        :raise XNATError: if the options do not specify a resource
        :return: the downloaded file names
        """
        # The default is all resources.
        if not (opts.get('resource') or opts.get('resources')):
            opts['resource'] = '*'
        # The default is all files.
        if not (opts.get('file') or opts.get('files')):
            opts['file'] = '*'
        # The file objects.
        files = self.find(*args, **opts)
        if not files:
            self._logger.debug("The query criterion does not contain any"
                               " files: %s %s" % (args, opts))
            return []

        # The download location.
        if 'dest' in opts:
            dest = opts.pop('dest')
            if os.path.exists(dest):
                # The target location must be a directory.
                if not os.path.isdir(dest):
                    raise XNATError("The download target is not a directory:"
                                    " %s" % dest)
            else:
                # Make the download directory.
                os.makedirs(dest)
        else:
            dest = os.getcwd()
        self._logger.debug("Downloading %d %s %s files to %s..." %
                           (len(files), args, opts, dest))

        # Download the files.
        return [self.download_file(file_obj, dest, **opts)
                for file_obj in files]

    def download_file(self, file_obj, dest, **opts):
        """
        Downloads the given XNAT file to the target directory.

        :param file_obj: the XNAT File object
        :param dest: the required target directory
        :param opts: the following option:
        :keyword skip_existing: ignore the source XNAT file if it a file of the same
            name already exists at the target location (default False)
        :keyword force: overwrite existing file (default False)
        :return: the downloaded file path
        :raise XNATError: if both the *skip_existing* *force* options are set
        :raise XNATError: if the XNAT file already exists and the *force* option
            is not set
        """
        # The target file name without directory is the XNAT file
        # object label, which must exist.
        fname = file_obj.label()
        if not fname:
            raise XNATError("The XNAT file object does not have a label: %s" %
                            file_obj)

        # The file location.
        location = os.path.join(dest, fname)
        if os.path.exists(location):
            # If we are directory to skip existing files, then ignore
            # the file but capture its location.
            # Otherwise, if the force option is set, then overwrite the
            # existing file.
            # Otherwise, complain.
            if opts.get('skip_existing'):
                # Can't both skip and overwrite.
                if opts.get('force'):
                    raise XNATError('The XNAT download option --skip_existing'
                                    ' is incompatible with the --force option')
                return location
            elif not opts.get('force'):
                raise XNATError("Download target file already exists: %s" %
                                location)

        # Download the file.
        self._logger.debug("Downloading the XNAT file %s to %s..." %
                           (fname, dest))
        # pyxnat File.get(location) uses unreliable cache trickery to copy
        # the file to the location. If the location is transitory, e.g. a
        # temporary directory on a cluster node, then subsequent File.get()
        # calls will raise an IOError. Work around this pyxnat defect by
        # calling pyxnat File.get_copy(location), which inefficiently but
        # safely copies the file to both the pyxnat cache and to the
        # specified location.
        file_obj.get_copy(location)
        self._logger.debug("Downloaded the XNAT file %s." % location)

        # Return the target location.
        return location

    def upload(self, resource, *in_files, **opts):
        """
        Imports the given files into XNAT. The parameters and options
        specify a target XNAT resource object in the XNAT object
        hierarchy, as described in :meth:`find`. The resource and its
        hierarchy ancestor objects are created as necessary by the
        :meth:`find` method.

        Example::

            from glob import glob
            from qiutil import qixnat
            in_files = glob('/path/to/images/*.nii.gz')
            with qixnat.connect() as xnat:
                rsc = xnat.find_or_create(
                    'QIN', 'Sarcoma003', 'Session01', scan=4,
                    resource='NIFTI', modality='MR'
                )
                xnat.upload(rsc, *in_files)

        :param resource: the existing XNAT resource object
        :param in_files: the input files to upload
        :param opts: the following  keyword options:
        :keyword name: the XNAT file object name
            (default is the input file base name without directory
            or extensions)
        :keyword skip_existing: flag indicating whether to forego
            overwriting an existing file (default False)
        :keyword force: flag indicating whether to replace an existing
            file (default False)
        :return: the new XNAT file names
        :raise XNATError: if there are no input files
        :raise XNATError: if the input file does not exist
        :raise XNATError: if both the *skip_existing* *force* options
            are set
        :raise XNATError: if the XNAT file already exists and neither
             the *skip_existing* nor the *force* option is set
        """
        # Upload the files.
        if not in_files:
            raise XNATError("Missing the file(s) to upload")
        self._logger.debug("Uploading %d files to %s..." %
                           (len(in_files), resource))
        xnat_files = [self._upload_file(resource, location, **opts)
                      for location in in_files]
        self._logger.debug("%d files uploaded to %s." %
                           (len(in_files), resource))

        return xnat_files

    def object(self, project, subject=None, experiment=None, **opts):
        """
        Return the XNAT object with the given search specification.
        The parameters and options specify a XNAT object in the
        `XNAT REST hierarchy`_. This hierarchy is summarized as
        follows::

            /project/PROJECT/
                [subject/SUBJECT/
                    [experiment/EXPERIMENT/
                        [<container type>/CONTAINER]]]
                            [resource/RESOURCE
                                [file/FILE]]

        where *container type* is the experiment child type, e.g.
        ``scan``. The brackets in the hierarchy specification
        above denote optionality, namely:
        - Only the project is required.
        - If there is an experiment, then there must be a subject.
        - If there is a container, then there must be an experiment.
        - A resource can be associated with any ancestor type.
        - A file requires a resource.

        The positional parameters specify the XNAT
        project/subject/experiment hierarchy from the root project
        down to and including the XNAT experiment object.
        The keyword arguments specify the object hierarchy below the
        experiment, e.g. ``scan=1``. The experiment child can be a
        ``scan``, ``reconstruction`` or ``assessment``. The
        ``assessment`` container type value corresponds to the XNAT
        ``assessor`` Image Assessment type. ``analysis``, ``assessment``
        and ``assessor`` are synonymous. A resource is specified by the
        *resource* keyword.

        The positional parameter and keyword option values are the
        XNAT object names, as described in the :class:`qixnat.facade.XNAT`
        class documentation. The names are prefixed, if necessary, by
        :meth:`qixnat.helpers.hierarchical_label` to form the standard
        XNAT label.

        The XNAT object need not exist in the database. By contrast, the
        :meth:`find_one` method returns an object if and only if it
        exists in the database.

        Examples:

        >>> from qiutil import qixnat
        >>> with qixnat.connect() as xnat:
        ...     subject = xnat.object('QIN', 'Sarcoma003')

        .. _XNAT REST hierarchy: https://pythonhosted.org/pyxnat/features/inspect.html#the-rest-hierarchy

        :param project: the XNAT project id or (id, {attribute: value}) tuple
        :param subject: the XNAT subject name or (name, {attribute: value})
            tuple
        :param experiment: the XNAT experiment name or (name, {attribute: value})
            tuple
        :param opts: the following container options:
        :keyword scan: the scan number or (number, {attribute: value}) tuple
        :keyword reconstruction: the reconstruction name or
            (name, {attribute: value}) tuple
        :keyword analysis: the analysis name or (name, {attribute: value}) tuple
        :keyword resource: the resource name or (name, {attribute: value}) tuple
        :keyword in_resource: the XNAT *in_resource* name or
            (name, {attribute: value}) tuple
        :keyword out_resource: the XNAT *out_resource* name or
            (name, {attribute: value}) tuple
        :keyword file: the file name
        :keyword inout: the resource direction (``in`` or ``out``)
        :return: the XNAT object, which may not exist
        """
        args = self._positional_hierarchy_arguments(project, subject, experiment)
        # The object [(type name, search key), ...] hierarchy.
        hierarchy = self._hierarchify(*args, **opts)
        # Qualify the search keys, if necessary.
        rest_hierarchy = self._rest_hierarchy(hierarchy)

        # Make the object.
        return self._hierarchy_xnat_object(rest_hierarchy)

    def find(self, *args, **opts):
        """
        Finds the XNAT objects which match the given search
        criteria.

        The positional parameters and keyword options extend the
        :meth:`object` interface to allow glob wildcards (``*``).
        A key in the hierarchy which contains a wildcard matches
        those XNAT objects whose :meth:`qixnat.helpers.xnat_name`
        match the wildcard expression.

        The return value is a list of those XNAT objects which
        match the specification and exist in the database.

        Examples:

        >>> from qiutil import qixnat
        >>> with qixnat.connect() as xnat:
        ...     subjects = xnat.find('QIN', 'Sarcoma*')
        ...     scan = xnat.find('QIN', 'Sarcoma003', '*', scan=1)

        :param args: the :meth:`object` positional search keys
        :param opts: the :meth:`object` keyword hierarchy options
            search key
        :return: the XNAT objects
        """
        hierarchy = self._hierarchify(*args, **opts)
        # Qualify the search keys, if necessary.
        rest_hierarchy = self._rest_hierarchy(hierarchy)
        # The length of a queryable prefix.
        qlen = next((i for i, spec in enumerate(rest_hierarchy)
                     if '*' in str(spec[1])),
                    len(rest_hierarchy))
        # The hierarchy from the root down to, and including, the
        # queryable object.
        up = rest_hierarchy[:qlen]
        # The starting XNAT object.
        parent = self._hierarchy_xnat_object(up)
        # The hierarchy leading from the starting object.
        down = rest_hierarchy[qlen:]
        # Recurse on the children.
        self._logger.debug("Expanding the %s descendant hierarchy %s..." %
                           (parent, down))
        result = self._find_descendant_hierarchy(parent, down)
        self._logger.debug("Found %d objects for the %s descendant hierarchy"
                           " %s." % (len(result), parent, down))

        return result

    def find_one(self, *args, **opts):
        """
        Finds the XNAT object which match the given search criteria.
        as described in :meth:`find`. Unlike :meth:`find`, this find_one
        method returns a single object, or None if there is no match.

        Examples::

            from qiutil import qixnat
            with qixnat.connect() as xnat:
                subject = xnat.find_one('QIN', 'Sarcoma003')
                scan = xnat.find_one('QIN', 'Sarcoma003', 'Session01', scan=1)
                file_obj = xnat.find_one('QIN', 'Sarcoma003', 'Session01',
                                         scan=1, resource='NIFTI',
                                         file='image12.nii.gz')

        :param args: the :meth:`find` positional search key
        :param opts: the :meth:`find` keyword hierarchy options
            search key
        :return: the matching XNAT object, or None if not found
        """
        create = opts.pop('create', None)
        modality = opts.pop('modality', None)
        # The  [(type name, value), ...] hierarchy list.
        hierarchy = self._hierarchify(*args, **opts)
        # Qualify the search keys, if necessary.
        rest_hierarchy = self._rest_hierarchy(hierarchy)
        # The target XNAT object.
        obj = self._hierarchy_xnat_object(rest_hierarchy)
        # If the object exists, then return it.
        # Otherwise, the default return value is None.
        if obj.exists():
            self._logger.debug("The XNAT object %s was found." % obj)
            return obj
        else:
            self._logger.debug("The XNAT object %s was not found." % obj)

    def find_or_create(self, *args, **opts):
        """
        Extends :meth:`find_one` to create the object if it doesn't
        exist. If the target object doesn't exist, then every
        non-existing object in the hierarchy leading to and including
        the target object is created.

        The :meth:`find` hierarchy keyword options are extended with
        the scan *modality* keyword option, e.g. ``MR`` or ``CT``.
        The modality argument is case-insensitive. Direct or indirect
        creation of an experiment or scan requires the *modality*
        option.

        The positional parameters and hierarchy keyword options
        extend the :meth:`find` interface to allow either the
        XNAT search key or a (search key, non-key {attribute: value})
        tuple. The non-key content is set if and only if the
        object in the hierarchy specified by the option is
        created.

        Examples::

            from qiutil import qixnat
            with qixnat.connect() as xnat:
                date = datetime(2004, 12, 3)
                exp_opt = (('Session01', dict(date=date))
                experiment = find_or_create('QIN', 'Breast003',
                                            exp_opt, modality='MR')

                scan_opt = (1, dict(series_description='T1'))
                resource = xnat.find_or_create(
                    'QIN', 'Sarcoma003', 'Session02', scan=scan_opt,
                    resource='NIFTI', modality='MR'
                )

        In the previous example, if the ancestor XNAT scan 1 and
        resource 'NIFTI' don't exist, then they are created. The
        *series_description* attribute is set if and only if the
        XNAT scan object is created.

        The supported non-key attributes are defined by the
        `XNAT schema`_. For example, the standard non-key scan
        attributes are as follows:
        * note
        * quality
        * condition
        * series_description
        * documentation

        This method accomodates the following pyxnat oddities:

        - The pyxnat convention is to specify a modality-specific
          subtype as a {pluralized type name: REST type} option, where
          the option key is pluralized, e.g. ``experiments``, and the
          option value is the :meth:`qixnat.helpers.rest_type`.

        - The pyxnat idiom is to set non-key attributes on a create
          by the options {<REST type>/<attribute>: value}.

        - The pyxnat date setter argument is a `XML Schema`_ xs:date
          string with format YYYY-MM-DD. pyxnat does not convert a
          date value to a Python datetime.

        This :meth:`find_or_create` method handles these and other
        pyxnat create  idiosyncracies described in the
        `pyxnat operations`_ guide.

        See the note below for important information about XNAT object
        creation in a cluster or other concurrent processing environment.

        It is an error to use this method to create a *file* object. The
        :meth:`upload` method is used for this purpose instead.

        :Note: Concurrent XNAT object find-or-create fails unpredictably,
            possibly arising from one of the following causes:
            * the pyxnat config in $HOME/.xnat/xnat.cfg specifies a temp
              directory that *is not* shared by all concurrent jobs,
              resulting in inconsistent cache content
            * the pyxnat config in $HOME/.xnat/xnat.cfg specifies a temp
              directory that *is* shared by some concurrent jobs,
              resulting in unsynchronized pyxnat write conflicts across
              jobs
            * the non-reentrant pyxnat's custom non-http2lib cache is
              corrupted
            * an XNAT archive directory access race condition

            Update 05/12/2015 - there are two potential failure points:
            * Concurrent pyxnat cache access corrupts the cache resulting in
              unpredictable errors, e.g. attempt to create an existing XNAT
              object
            * Concurrent XNAT resource file upload corrupts the archive such
              that the files are stored in the archive but are not recognized
              by XNAT

            Update 05/14/2015 - per https://github.com/pyxnat/pyxnat/issues/61,
            a shared pyxnat cache is a likely point of failure. However,
            sporadic failures also occur without a shared cache. The following
            practices are recommended:
            * set an isolated pyxnat cache_dir for each execution context
            * serialize common XNAT object find-or-create access across all
              concurrent execution contexts

        .. _pyxnat operations: https://pythonhosted.org/pyxnat/features/operations.html#basic-operations

        .. _XML Schema: http://www.w3.org/2001/XMLSchema

        :param args: the :meth:`find` positional search key or
            (search key, {attribute: value}) tuple
        :param opts: the :meth:`find` keyword hierarchy options
            search key or (search key, {attribute: value}), as well as the
            following create options:
        :keyword modality: the scan modality (default ``MR``)
        :raise XNATError: if the options specify a non-existing XNAT file
            object

        .. _XNAT schema: https://central.xnat.org/schemas/xnat/xnat.xsd
        """
        modality = opts.pop('modality', None)
        # The  [(type name, value), ...] hierarchy list.
        hierarchy = self._hierarchify(*args, **opts)
        # The [(type name, search key), ...] hierarchy list.
        search_hierarchy = [(type_name, self._extract_search_key(value))
                            for type_name, value in hierarchy]
        # Qualify the search keys, if necessary.
        rest_hierarchy = self._rest_hierarchy(search_hierarchy)
        # The target XNAT object.
        obj = self._hierarchy_xnat_object(rest_hierarchy)
        # If the object exists, then return it.
        # Otherwise, create the object and its non-existing ancestors.
        if obj.exists():
            return obj
        # The create {type name: {attribute: value}} keyword options.
        create_opts = {type_name: value[1]
                       for type_name, value in hierarchy
                       if isinstance(value, tuple)}
        if modality:
            create_opts['modality'] = modality
        # The type name hierarchy.
        path = [type_name for type_name, _ in hierarchy]
        self._create(obj, path, **create_opts)

        return obj

    def delete(self, *args, **opts):
        """
        Deletes the XNAT objects which match the given search criteria.
        The object search is described in :meth:`find`.
        
        :Note: XNAT project deletion is unsupported.
        
        :Note: pyxnat file object deletion is unsupported.

        :Note: XNAT delete is recursive. In particular, all files
            contained in the deletion target are deleted. Use this
            method with caution. 

        Examples::

            from qiutil import qixnat
            with qixnat.connect() as xnat:
                # Delete all resources which begin with 'pk_'.
                xnat.delete('QIN', 'Sarcoma003', 'Session01', scan=1,
                                   resource='pk_*')

        :param args: the :meth:`find` positional search key
        :param opts: the :meth:`find` keyword hierarchy options
            search key
        :raise XNATError: if a project or file object is specified
        """
        matching = self.find(*args, **opts)
        is_project_object = lambda obj: isinstance(obj, Project)
        if any(is_project_object(obj) for obj in matching):
            raise XNATError("XNAT does not support project object deletion")
        is_file_object = lambda obj: isinstance(obj, File)
        if any(is_file_object(obj) for obj in matching):
            raise XNATError("XNAT does not support file object deletion")
        for obj in matching:
            obj.delete()
            self._logger.debug("Deleted XNAT object %s." % obj)

    def _positional_hierarchy_arguments(self, project, subject, experiment):
        args = [project]
        if subject:
            args.append(subject)
        if experiment:
            if not subject:
                raise XNATError('The find specifies an experiment but not a'
                                'subject')
            args.append(experiment)
        
        return args

    def _extract_search_key(self, value):
        """
        :param value: the search key or (search key, {attribute: value})
            tuple
        :return: the search key
        """
        return value[0] if isinstance(value, tuple) else value

    def _extract_mod_dictionary(self, value):
        """
        :param value: the search key or (search key, {attribute: value})
            tuple
        :return: the {attribute: value} dictionary, or None if the value
            doesn't have one
        """
        return value[1] if isinstance(value, tuple) else None

    def _create(self, obj, path, **opts):
        """
        Creates the given object specified by the hierarchy.
        This method is used to insert the XNAT object into
        the database. File objects must be uploaded rather
        than using this method.

        :param obj: the object to create
        :param path: the type name path to the object
        :param opts: the non-key {type name: {attribute: value}}
            content as well as the following option:
        :option modality: the scan modality
        :raise XNATError: if the object is a XNAT file object
        """
        # Files can only be uploaded.
        if path[-1] == 'file':
            raise XNATError("Use upload rather than find_one to insert"
                            " a file into XNAT")
        # Walk up the hierarchy to the first existing object.
        nonexisting = self._nonexisting_lineage(obj)
        # The types to create.
        create_types = path[-len(nonexisting):]
        self._logger.debug("Creating the XNAT %s %s hierarchy..." %
                           (obj, create_types))
        # The XNAT REST call create options.
        create_opts = self._rest_create_options(create_types, **opts)
        # Create the object.
        self._logger.debug("Creating the XNAT objects %s with options"
                           " %s..." % (nonexisting, create_opts))
        try:
            obj.create(**create_opts)
        except DatabaseError, e:
            # XNAT has a useless error message, so add a little more
            # information to the log.
            self._logger.error("XNAT object create database error - object: %s"
                               " options: %s " % (obj, create_opts))
            raise e
        self._logger.debug("Created the XNAT objects %s." % nonexisting)

    def _nonexisting_lineage(self, obj):
        """
        :param obj: the target object to check
        :return: the list of nonexisting objects leading to the target
        """
        if obj.exists():
            return []
        parent = obj.parent()
        if not parent:
            # The root project should always exist.
            raise XNATError("The root object does not exist: %s" % obj)
        # Recurse.
        nonexisting = self._nonexisting_lineage(parent)
        # Tack the current object onto the end.
        nonexisting.append(obj)

        return nonexisting

    def _rest_create_options(self, path, **opts):
        """
        Makes the options necessary to create XNAT objects in the
        given type name path.

        Example::

        >>> import qixnat
        ...     date = datetime(2014, 3, 6)
        ...     with qixnat.connect() as xnat:
        ...         type_names = ['experiment', 'scan']
        ...         opts = dict(modality='MR',
        ...                     experiment=dict(date=date),
        ...                     scan=dict(series_description='T1'))
        ...         xnat._rest_create_options(type_names, modality**opts)
        {'experiments': 'mrSessionData',
         'scans': 'mrScanData',
         'mrSessionData/date': '06/03/14'
         'mrScanData/series_description': 'T1'}

        :param path: the type name path to the created object
        :param opts: the :meth:`find_or_create` options
        :return: the XNAT create options
        """
        rest_opts = {}
        modality = opts.get('modality')
        for type_name in path:
            rest_name = rest_type(type_name, modality)
            # The subtype option described in the find_or_create doc.
            if type_name in MODALITY_TYPES:
                key = pluralize_type_designator(type_name)
                rest_opts[key] = rest_name
            type_opts = opts.get(type_name)
            # The REST attribute:value option described in the
            # find_or_create doc.
            if type_opts:
                for attr, val in type_opts.iteritems():
                    key = '/'.join((rest_name, attr))
                    # Munge a date per the find_or_create doc.
                    if val and attr.endswith('date'):
                        val = val.strftime("%D")
                    rest_opts[key] = val

        return rest_opts

    def update(self, obj, **mods):
        """
        Sets the given attributes and saves the object.

        This method handles python datetime values correctly by
        working around the pyxnat date oddity described in
        :mneth:`find_or_create`.

        :param obj: the object to change
        :param mods: the {attribute, value} modifications
        """
        if not mods:
            return
        # The pyxnat date setter argument is a string.
        date_opts = (opt for opt in mods if opt.endswith('date'))
        for opt in date_opts:
            date = mods.get(opt)
            if date:
                date_s = date.strftime()
                mods[opt] = date_s
        # Apply the modifications and save the parent object.
        self._logger.debug("Modifying the XNAT %s with %s..." % (obj, mods))
        # attrs.mset is the odd pyxnat idiom for setting and saving
        # attribute modifications.
        obj.attrs.mset(mods)

    def _hierarchify(self, *args, **opts):
        """
        Collects the given :meth:`find` XNAT object specifications into
        a [(type, key), ...] hierarchy list, where:
        * *type* is the lower-case object type, qualified by
          the resource *inout* option if necessary, e.g. ``project``
          or ``in_resource``
        * *key* is the XNAT object id or label find search key

        The positional parameter and keyword option values are XNAT
        names, as described in :meth:`object`.

        :param args: the *project*, *subject* and *experiment* parameters
        :param opts: the additional {type name: value} options
        :return: the hierarchy list
        """
        # The leading hierarchy object types.
        arg_types = ['project', 'subject', 'experiment']
        if len(args) > len(arg_types):
            raise XNATError("Too many positional arguments - expected:"
                            " (project, subject, experiment), found: %s" %
                            list(args))
        # Convert the leading arguments to keyword options.
        for i, arg in enumerate(args):
            if arg:
                opts[arg_types[i]] = arg
        # There must be a parent.
        if not opts.get('project'):
            raise XNATError("The XNAT search arguments and options are"
                            " missing a project: %s" % opts)
        # The leading hierarchy items.
        hierarchy = [(k, opts[k]) for k in arg_types if k in opts]

        # The resource container option keywords.
        ctr_kws = [k for k in opts if k in CONTAINER_DESIGNATIONS]
        # There can be at most one resource container option.
        if len(ctr_kws) > 1:
            raise XNATError("Mutually exclusive resource container search"
                            "options: %s" % ctr_kws)
        if ctr_kws:
            ctr_kw = ctr_kws[0]
            ctr_opt = opts[ctr_kw]
            # A container must have an experiment.
            if len(hierarchy) < 3:
                raise XNATError("The container does not have an experiment"
                                " in the search options %s" % opts)
            ctr_type = 'assessor' if ctr_kw in ASSESSOR_SYNONYMS else ctr_kw
            ctr_spec = (ctr_type, ctr_opt)
            hierarchy.append(ctr_spec)

        # The resource option.
        rsc_keys = [key for key in opts if key.endswith('resource')]
        if len(rsc_keys) > 1:
            raise XNATErrors("The resource options are exclusive: %s" % opts)
        if rsc_keys:
            rsc_key = rsc_keys[0]
            parent_type = hierarchy[-1][0]
            if parent_type in INOUT_CONTAINER_TYPES:
                if rsc_key == 'resource':
                    inout = opts.get('inout')
                    if not inout:
                        raise XNATError("The %s container inout option was not"
                                        " found in the find options %s" %
                                        (ctr_type, opts))
                    if not inout in ('in', 'out'):
                        raise XNATError("The inout option is invalid: %s" % inout)
                    rsc_attr = "%s_resource" % inout
                else:
                    rsc_attr = rsc_key
            elif rsc_key == 'resource':
                rsc_attr = rsc_key
            else:
                raise XNATError("The %s option is unsupported for the resource"
                                " container %s" % (rsc_key, parent_type))
            rsc_opt = opts[rsc_key]
            rsc_spec = (rsc_attr, rsc_opt)
            hierarchy.append(rsc_spec)

        # The file option.
        file_opt = opts.get('file')
        if file_opt:
            if not rsc_opt:
                raise XNATError("The file does not have a resource in the"
                                " search options %s" % opts)
            file_spec = ('file', file_opt)
            hierarchy.append(file_spec)

        self._logger.debug("The XNAT hierarchy is %s." % hierarchy)

        return hierarchy

    def _find_descendant_hierarchy(self, parent, hierarchy):
        """
        :param parent: the starting object
        :param hierarchy: the descendant [(type name, key)] list
        :return: the XNAT objects specified by the hierarchy
        """
        # The easy cases.
        if not parent.exists():
            return []
        if not hierarchy:
            return [parent]
        # Recurse on the children.
        child_type, child_key = hierarchy[0]
        child_hierarchy = hierarchy[1:]
        # Recurse on the matching children.
        if '*' in child_key:
            attr = pluralize_type_designator(child_type)
            children = getattr(parent, attr)()
            # The regex pattern to compare against the fetched
            # child key value.
            pat = child_key.replace('*', '.*')
            descendants = (
                self._find_descendant_hierarchy(child, child_hierarchy)
                for child in children
                if re.match(pat, xnat_key(child))
            )
            return concat(*descendants)
        else:
            child = getattr(parent, child_type)(child_key)
            return self._find_descendant_hierarchy(child, hierarchy[1:])

    def _rest_hierarchy(self, hierarchy):
        """
        Qualifies the hierarchy as follows:
        * the scan value is a string
        * experiment and non-scan experiment child keys prepend the parent
          label, if necessary.
        
        Examples::
            >>> hierarchy = [('project', 'QIN'), ('subject', 'Breast001'),
                             ('experiment', 'Session01', 'scan', 1)]
            >>> self._rest_hierarchy(hierarchy)
            [('project', 'QIN'), ('subject', 'Breast001'),
             ('experiment', 'Breast001_Session01'), ('scan', '1')]
            >>> hierarchy = [('project', 'QIN'), ('subject', 'Breast001'),
                             ('experiment', 'Session01', 'assessor', 'modeling')
                             ('resource', 'pk_Zu3s')]
            >>> self._rest_hierarchy(hierarchy)
            [('project', 'QIN'), ('subject', 'Breast001'),
             ('experiment', 'Breast001_Session01'),
             ('assessor', 'Breast001_Session01_modeling')
             ('resource', 'pk_Zu3s')]
        """
        hierarchy_dict = dict(hierarchy)
        exp = hierarchy_dict.get('experiment')
        if exp:
            sbj = hierarchy_dict['subject']
            # Qualify the experiment.
            hierarchy_dict['experiment'] = hierarchical_label(sbj, exp)
            ctr_type = next((t for t in CONTAINER_TYPES if t in hierarchy_dict),
                            None)
            if ctr_type:
                # Qualify the experiment child.
                ctr_val = hierarchy_dict[ctr_type]
                if ctr_type in HIERARCHICAL_LABEL_TYPES:
                    std_ctr_val = hierarchical_label(sbj, exp, ctr_val)
                else:
                    std_ctr_val = str(ctr_val)
                hierarchy_dict[ctr_type] = std_ctr_val

        # Return the qualified [(type name, search key), ...] list.
        return [(type_name, hierarchy_dict[type_name])
                for type_name, _ in hierarchy]

    def _hierarchy_xnat_object(self, hierarchy):
        """
        Makes an XNAT object which satisfies the given search hierarchy.

        :param hierarchy: the [(type name, key)] list
        :return: the XNAT object specified by the hierarchy
        """
        # The query string. Integer arguments are converted to string.
        level = lambda spec: '/'.join(map(str, spec))
        query = '/' + '/'.join(level(spec) for spec in hierarchy)
        # Find the object.
        self._logger.debug("Submitting XNAT select %s..." % query)

        return self.interface.select(query)

    def _upload_file(self, resource, in_file, **opts):
        """
        Uploads the given file to XNAT.

        :param resource: the existing XNAT resource object that will
            contain the file
        :param in_file: the input file path
        :param opts: the ``pyxnat.core.resources.File.put`` options,
            as well as the following upload options:
        :keyword name: the XNAT file object name
            (default is the input file name without directory)
        :keyword skip_existing: forego the upload if the target XNAT
             file already exists (default False)
        :keyword force: replace an existing XNAT file (default False)
        :return: the XNAT file name
        :raise XNATError: if the input file does not exist
        :raise XNATError: if both the *skip_existing* *force* options
            are set
        :raise XNATError: if the XNAT file already exists and neither
             the *skip_existing* nor the *force* option is set
        """
        # The input file must exist.
        if not os.path.exists(in_file):
            raise XNATError("Input file does not exist: %s" % in_file)
        # The XNAT file name.
        fname = opts.pop('name', None)
        if not fname:
            _, fname = os.path.split(in_file)
        self._logger.debug("Uploading the XNAT file %s from %s..." %
                           (fname, in_file))
        # The XNAT file wrapper.
        file_obj = resource.file(fname)
        # The resource parent container.
        rsc_ctr = resource.parent()

        # Check for an existing file.
        skip = opts.pop('skip_existing', False)
        force = opts.pop('force', False)
        if file_obj and file_obj.exists():
            if skip:
                if force:
                    raise XNATError("The XNAT upload option --skip_existing is"
                                    " incompatible with the --force option")
                return fname
            elif force:
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
        self._logger.debug("Inserting the file %s into the XNAT %s %s %s"
                           " resource..." % (fname, rsc_ctr_type,
                                             rsc_ctr.label(),
                                             resource.label()))
        try:
            file_obj.put(in_file, **opts)
        except pyxnat.core.errors.DatabaseError:
            # One of the obscure XNAT errors occurs if uploading an empty file.
            # Print a useful error message in this case.
            if not os.stat(in_file).st_size:
                raise XNATError("XNAT does not support upload of the empty"
                                " file %s" % in_file)
            
            
        self._logger.debug("Uploaded the XNAT file %s." % fname)

        return fname
