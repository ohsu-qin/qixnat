import os
import shutil
from datetime import datetime
from nose.tools import (assert_equal, assert_true, assert_false,
                        assert_is_none, assert_is_not_none)
from pyxnat.core.resources import (Experiment, Scan, Reconstruction,
                                   Resource, Assessor)
import qixnat
from qixnat.helpers import parse_rest_date
from test import (PROJECT, ROOT)
from ..helpers.logging import logger
from ..helpers.name_generator import generate_unique_name

FIXTURE = os.path.join(ROOT, 'fixtures', 'xnat', 'dummy.nii.gz')
"""The test fixture parent directory."""

RESULTS = os.path.join(ROOT, 'results', 'xnat')
"""The test results directory."""

SUBJECT = generate_unique_name(__name__)
"""The test subject name."""

SESSION = generate_unique_name(__name__)
"""The test session name."""

SCAN = 1
"""The test scan number."""

REGISTRATION = 'reg'
"""The test scan registration resource name."""

RECONSTRUCTION = 'reco'
"""The test reconstruction name."""

ASSESSOR = 'pk'
"""The test assessor name."""

class TestFacade(object):
    """The XNAT helper unit tests."""

    def setUp(self):
        shutil.rmtree(RESULTS, True)
        with qixnat.connect() as xnat:
            xnat.delete(PROJECT, SUBJECT)

    def tearDown(self):
        shutil.rmtree(RESULTS, True)
        with qixnat.connect() as xnat:
            xnat.delete(PROJECT, SUBJECT)

    def test_project(self):
        with qixnat.connect() as xnat:
            prj = xnat.find_one(PROJECT)
            assert_is_not_none(prj, "XNAT project was not fetched: %s" % prj)
    
    def test_subject(self):
        with qixnat.connect() as xnat:
            self._validate_fetch(xnat, PROJECT, SUBJECT)
    
    def test_experiment(self):
        date = datetime(2014, 9, 3)
        exp_opt = (SESSION, dict(date=date))
        with qixnat.connect() as xnat:
            exp = self._validate_fetch(xnat, PROJECT, SUBJECT, exp_opt)
            self._validate_experiment_date(exp, date)
    
    def test_scan(self):
        scan_opt = (SCAN, dict(series_description='T1'))
        with qixnat.connect() as xnat:
            scan = self._validate_fetch(xnat, PROJECT, SUBJECT, SESSION,
                                        scan=scan_opt)
            actual_desc = scan.attrs.get('series_description')
            assert_is_not_none(actual_desc, "Scan description is not set")
            assert_equal(actual_desc, 'T1',
                         "Scan description is incorrect: %s" % actual_desc)
    
    def test_scan_resource(self):
        """
        Test create and find of a scan resource. This test case also
        verifies the content of the created ancestor objects.
        """
        date = datetime(2014, 4, 9)
        exp_opt = (SESSION, dict(date=date))
        scan_opt = (SCAN, dict(series_description='T1'))
        with qixnat.connect() as xnat:
            rsc = self._validate_fetch(xnat, PROJECT, SUBJECT, exp_opt,
                                       scan=SCAN, resource=REGISTRATION)
            scan = rsc.parent()
            assert_is_not_none(scan, "Resource scan is not found")
            actual_desc = scan.attrs.get('series_description')
            exp = scan.parent()
            assert_is_not_none(exp, "Resource experiment is not found")
            self._validate_experiment_date(exp, date)
    
    def test_reconstruction(self):
        with qixnat.connect() as xnat:
            self._validate_fetch(xnat, PROJECT, SUBJECT, SESSION,
                                 reconstruction=RECONSTRUCTION)
    
    def test_assessor(self):
        with qixnat.connect() as xnat:
            self._validate_fetch(xnat, PROJECT, SUBJECT, SESSION,
                                 assessor=ASSESSOR)
    
    def test_file_round_trip(self):
        # The test file name without the directory.
        _, fname = os.path.split(FIXTURE)
        with qixnat.connect() as xnat:
            # Make the resource.
            rsc = xnat.find_or_create(PROJECT, SUBJECT, SESSION,
                                      scan=SCAN, resource='NIFTI',
                                      modality='MR')
            # Upload the file.
            xnat.upload(rsc, FIXTURE)
            # The XNAT file object.
            obj = xnat.find_one(PROJECT, SUBJECT, SESSION, scan=SCAN,
                           resource='NIFTI', file=fname)
            assert_is_not_none(obj, "XNAT %s %s file object not found" %
                                    (rsc, fname))
            # Download the uploaded file.
            files = xnat.download(PROJECT, SUBJECT, SESSION, scan=SCAN,
                                  dest=RESULTS)
        # Verify the download.
        assert_equal(len(files), 1,
                     "The download file count is incorrect: %d" % len(files))
        location = files[0]
        assert_true(os.path.exists(location), "File not downloaded: %s" %
                                              location)
    
    def test_find(self):
        with qixnat.connect() as xnat:
            # Make some experiments and resources.
            x11 = xnat.find_or_create(PROJECT, SUBJECT, 'Session01', scan=1,
                                resource='DICOM', modality='MR')
            xnat.find_or_create(PROJECT, SUBJECT, 'Session01', scan=1,
                                resource='NIFTI')
            x12 = xnat.find_or_create(PROJECT, SUBJECT, 'Session01', scan=2,
                                resource='NIFTI', modality='MR')
            x21 = xnat.find_or_create(PROJECT, SUBJECT, 'Session02', scan=1,
                                resource='NIFTI', modality='MR')
            # Find the NIFTI resources.
            result = xnat.find(PROJECT, '*', 'Session*', scan='*',
                               resource='NIFTI')
            assert_equal(len(result), 3, "Find existing result is"
                                         " incorrect: %s" % result)
            # Find non-existing resources.
            result = xnat.find(PROJECT, SUBJECT, 'Session*', scan=2,
                               resource='DICOM')
            assert_equal(len(result), 0, "Find non-existing result is"
                                         " not empty: %s" % result)
    
    def test_delete(self):
        with qixnat.connect() as xnat:
            # Make a resource.
            rsc = xnat.find_or_create(PROJECT, SUBJECT, 'Session01', scan=1,
                                resource='DICOM', modality='MR')
            # Delete the resource.
            xnat.delete(PROJECT, SUBJECT, 'Session*', scan=1, resource='DICOM')
            assert_false(rsc.exists(), "%s was not deleted." % rsc)
            # Find again.
            rsc = xnat.find_one(PROJECT, SUBJECT, 'Session01', scan=1,
                       
                                resource='DICOM', modality='MR')
            assert_is_none(rsc, "Deleted resource was found: %s." % rsc)
    
    def _validate_experiment_date(self, exp, date):
        actual_date_s = exp.attrs.get('date')
        actual_date = parse_rest_date(actual_date_s)
        assert_is_not_none(actual_date, "Session date is not set")
        assert_equal(actual_date, date, "Session date is incorrect: %s" %
                                        actual_date)

    def _validate_fetch(self, xnat, *args, **opts):
        """
        Tests fetching an XNAT object with the given arguments and
        options. The following operations are tested:
        - :meth:`qixnat.facade.XNAT.get`
        - :meth:`qixnat.facade.XNAT.find_one`
        - :meth:`qixnat.facade.XNAT.find_or_create`
        
        :param xnat: the qixnat connection
        :param args: the :class:`qixnat.facade.XNAT` operation
            positional arguments
        :param opts: the :class:`qixnat.facade.XNAT` operation
            keyword options
        :return: the created XNAT object
        """
        # Cheat by piggy-backing off of a facade private method.
        find_args = [xnat._extract_search_key(arg) for arg in args]
        find_opts = {k: xnat._extract_search_key(v) for k, v in opts.iteritems()}
        obj = xnat.object(*find_args, **find_opts)
        assert_false(obj.exists(), "XNAT object inadvertently created: %s" % obj)
        fetched = xnat.find_one(*find_args, **find_opts)
        assert_is_none(fetched, "Found non-existing XNAT object %s:" % obj)
        fetched = xnat.find_or_create(*args, modality='MR', **opts)
        assert_is_not_none(fetched, "No create return value")
        assert_true(fetched.exists(), "XNAT object not created: %s" % obj)
        fetched = xnat.find_one(*find_args, **find_opts)
        assert_is_not_none(fetched, "XNAT object not found: %s" % obj)

        return obj


if __name__ == "__main__":
    import nose

    nose.main(defaultTest=__name__)
