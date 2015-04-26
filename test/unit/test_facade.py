import os
import shutil
from nose.tools import (assert_equal, assert_true, assert_is_not_none)
from pyxnat.core.resources import (Experiment, Scan, Reconstruction,
                                   Resource, Assessor)
import qixnat
from test import (PROJECT, ROOT)
from ..helpers.logging import logger
from ..helpers.name_generator import generate_unique_name

FIXTURE = os.path.join(ROOT, 'fixtures', 'xnat', 'dummy.nii.gz')
"""The test fixture parent directory."""

RESULTS = os.path.join(ROOT, 'results', 'xnat')
"""The test results directory."""

SUBJECT = generate_unique_name(__name__)
"""The test subject name."""

SESSION = 'MR1'

SCAN = 1

RECONSTRUCTION = 'reco'

REGISTRATION = 'reg'

ASSESSOR = 'pk'


class TestFacade(object):
    """The XNAT helper unit tests."""

    def setUp(self):
        shutil.rmtree(RESULTS, True)
        with qixnat.connect() as xnat:
            xnat.delete_subjects(PROJECT, SUBJECT)

    def tearDown(self):
        shutil.rmtree(RESULTS, True)
        with qixnat.connect() as xnat:
            xnat.delete_subjects(PROJECT, SUBJECT)

    def test_find_subject(self):
        with qixnat.connect() as xnat:
            sbj = xnat.find(PROJECT, SUBJECT, modality='MR', create=True)
            assert_true(xnat.exists(sbj), "Subject not created: %s" % SUBJECT)
            sbj = xnat.find(PROJECT, SUBJECT)
            assert_is_not_none(sbj, "Subject not found: %s" % SUBJECT)
    
    def test_find_experiment(self):
        with qixnat.connect() as xnat:
            sbj = xnat.find(PROJECT, SUBJECT, SESSION, modality='MR',
                            create=True)
            assert_true(xnat.exists(sbj),
                        "Subject %s session not created: %s" %
                        (SUBJECT, SESSION))
            sbj = xnat.find(PROJECT, SUBJECT, SESSION)
            assert_is_not_none(sbj, "Subject %s session not found: %s" %
                                    (SUBJECT, SESSION))
    
    def test_find_scan(self):
        with qixnat.connect() as xnat:
            scan = xnat.find(PROJECT, SUBJECT, SESSION, scan=SCAN,
                             modality='MR', create=True)
            assert_true(xnat.exists(scan),
                        "Subject %s session %s scan not created: %s" %
                        (SUBJECT, SESSION, SCAN))
            scan = xnat.find(PROJECT, SUBJECT, SESSION, scan=SCAN)
            assert_is_not_none(scan, "Subject %s session %s scan not found:"
                                     " %s" % (SUBJECT, SESSION, SCAN))
    
    def test_create_scan_with_description(self):
        with qixnat.connect() as xnat:
            scan_opts = dict(number=SCAN, description='T1')
            scan = xnat.find(PROJECT, SUBJECT, SESSION, scan=scan_opts,
                             modality='MR', create=True)
            assert_true(xnat.exists(scan), "Subject %s session %s scan not"
                                           " created: %s" %
                                           (SUBJECT, SESSION, SCAN))
            scan = xnat.find(PROJECT, SUBJECT, SESSION, scan=SCAN)
            assert_is_not_none(scan, "Subject %s session %s scan not found:"
                                     " %s" % (SUBJECT, SESSION, SCAN))
            assert_equal(scan.attrs.get('series_description'), 'T1',
                        "Subject %s session %s scan %d description is"
                        " incorrect" % (SUBJECT, SESSION, SCAN))
    
    def test_find_resource(self):
        with qixnat.connect() as xnat:
            rsc = xnat.find(PROJECT, SUBJECT, SESSION, resource=REGISTRATION,
                            modality='MR', create=True)
            assert_true(xnat.exists(rsc),
                        "Subject %s session %s resource not created: %s" %
                        (SUBJECT, SESSION, REGISTRATION))
            assert_true(isinstance(rsc, Resource),
                        "Subject %s session %s resource %s class incorrect:"
                        " %s" % (SUBJECT, SESSION, REGISTRATION,
                                 rsc.__class__.__name__))
            rsc = xnat.find(PROJECT, SUBJECT, SESSION, resource=REGISTRATION)
            assert_is_not_none(rsc, "Subject %s session %s resource not"
                                    " found: %s" %
                                    (SUBJECT, SESSION, REGISTRATION))
    
    def test_find_reconstruction(self):
        with qixnat.connect() as xnat:
            reco = xnat.find(PROJECT, SUBJECT, SESSION,
                            reconstruction=RECONSTRUCTION, modality='MR',
                            create=True)
            assert_true(xnat.exists(reco),
                        "Subject %s session %s reconstruction not created:"
                        " %s" % (SUBJECT, SESSION, RECONSTRUCTION))
            reco = xnat.find(PROJECT, SUBJECT, SESSION,
                             reconstruction=RECONSTRUCTION, modality='MR',
                             create=True)
            assert_is_not_none(reco, "Subject %s session %s reconstruction"
                                     " not found: %s" %
                                     (SUBJECT, SESSION, RECONSTRUCTION))
    
    def test_find_assessor(self):
        with qixnat.connect() as xnat:
            anl = xnat.find(PROJECT, SUBJECT, SESSION, assessor=ASSESSOR,
                            modality='MR', create=True)
            assert_true(xnat.exists(anl),
                        "Subject %s session %s assessor not created: %s" %
                        (SUBJECT, SESSION, ASSESSOR))
            anl = xnat.find(PROJECT, SUBJECT, SESSION, assessor=ASSESSOR)
            assert_is_not_none(anl, "Subject %s session %s assessor not"
                                    " found: %s" %
                                    (SUBJECT, SESSION, ASSESSOR))
    
    
    def test_scan_round_trip(self):
        with qixnat.connect() as xnat:
            # Upload the file.
            xnat.upload(PROJECT, SUBJECT, SESSION, FIXTURE, scan=SCAN,
                        modality='MR')
            _, fname = os.path.split(FIXTURE)
            exp = xnat.get_session(PROJECT, SUBJECT, SESSION)
            assert_true(xnat.exists(exp),
                        "XNAT %s %s %s experiment does not exist." %
                        (PROJECT, SUBJECT, SESSION))
            scan_obj = xnat.get_scan(PROJECT, SUBJECT, SESSION, SCAN)
            assert_true(xnat.exists(scan_obj),
                        "XNAT %s %s %s %s scan does not exist." %
                        (PROJECT, SUBJECT, SESSION, SCAN))
            file_obj = scan_obj.resource('NIFTI').file(fname)
            assert_true(xnat.exists(file_obj), "File not uploaded: %s" % fname)
    
            # Download the single uploaded file.
            files = xnat.download(PROJECT, SUBJECT, SESSION, dest=RESULTS,
                                  scan=SCAN)
            # Download all scan files.
            all_files = xnat.download(PROJECT, SUBJECT, SESSION, dest=RESULTS,
                                      container_type='scan', force=True)
    
        # Verify the result.
        assert_equal(len(files), 1,
                     "The download file count is incorrect: %d" % len(files))
        f = files[0]
        assert_true(os.path.exists(f), "File not downloaded: %s" % f)
        assert_equal(set(files), set(all_files),
                     "The %s %s scan %d download differs from all scans"
                     " download: %s vs %s" %
                     (SUBJECT, SESSION, SCAN, files, all_files))
    
    def test_registration_round_trip(self):
        with qixnat.connect() as xnat:
            # Upload the file.
            xnat.upload(PROJECT, SUBJECT, SESSION, FIXTURE, scan=SCAN,
                        resource=REGISTRATION, modality='MR')
            _, fname = os.path.split(FIXTURE)
            exp = xnat.get_session(PROJECT, SUBJECT, SESSION)
            assert_true(xnat.exists(exp),
                        "The XNAT %s %s %s experiment does not exist." %
                        (PROJECT, SUBJECT, SESSION))
            rsc_obj = xnat.get_scan_resource(PROJECT, SUBJECT, SESSION,
                                             SCAN, REGISTRATION)
            assert_true(xnat.exists(rsc_obj),
                        "The XNAT %s %s %s scan %d %s resource does not exist." %
                        (PROJECT, SUBJECT, SESSION, SCAN, REGISTRATION))
            file_obj = rsc_obj.file(fname)
            assert_true(xnat.exists(file_obj), "File not uploaded: %s" % fname)
    
            # Download the uploaded file.
            files = xnat.download(PROJECT, SUBJECT, SESSION, scan=SCAN,
                                  resource=REGISTRATION, dest=RESULTS)
    
        # Verify the result.
        assert_equal(len(files), 1,
                     "The download file count is incorrect: %d" % len(files))
        f = files[0]
        assert_true(os.path.exists(f), "File not downloaded: %s" % f)


if __name__ == "__main__":
    import nose

    nose.main(defaultTest=__name__)
