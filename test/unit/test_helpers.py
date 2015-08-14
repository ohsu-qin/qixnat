import os
from nose.tools import (assert_equal, assert_true, assert_is_not_none,
                        assert_is_instance)
import qixnat
from qixnat.helpers import (hierarchical_label, path_hierarchy,
                            pluralize_type_designator, xnat_key, xnat_name,
                            xnat_path, xnat_children)
from qixnat.constants import TYPE_DESIGNATORS
from .. import PROJECT
# Borrow the facade hierarchy and file fixture.
from .test_facade import (PROJECT, SUBJECT, SESSION, SCAN, RESOURCE, FIXTURE)


class TestHelpers(object):
    def test_pluralize_type_designator(self):
        for xnat_type in TYPE_DESIGNATORS:
            expected = 'analyses' if xnat_type == 'analysis' else xnat_type + 's'
            actual = pluralize_type_designator(xnat_type)
            assert_equal(actual, expected, "The XNAT type name pluralization"
                                           " is incorrect: %s" % actual)

    def test_short_hierarchical_label(self):
        exp = 'Session01'
        expected = 'Breast003_Session01'
        actual = hierarchical_label('Breast003', exp)
        assert_equal(actual, expected, "The hierarchical label for experiment %s"
                                       " is incorrect: %s" % (exp, actual))

    def test_long_hierarchical_label(self):
        exp = 'Breast003_Session01'
        expected = 'Breast003_Session01'
        actual = hierarchical_label('Breast003', exp)
        assert_equal(actual, expected, "The hierarchical label for experiment %s"
                                       " is incorrect: %s" % (exp, actual))

    def test_path_hierarchy_with_leading_slash(self):
        path = '/project/QIN/subject/Breast003/experiment/Session01'
        expected = [('project', 'QIN'), ('subject', 'Breast003'),
                    ('experiment', 'Session01')]
        actual = path_hierarchy(path)
        assert_equal(actual, expected, "The path hierarchy for path %s is"
                                       " incorrect: %s" % (path, actual))

    def test_path_hierarchy_with_elided_types(self):
        path = '/QIN/Breast003/Session01'
        expected = [('project', 'QIN'), ('subject', 'Breast003'),
                    ('experiment', 'Session01')]
        actual = path_hierarchy(path)
        assert_equal(actual, expected, "The path hierarchy for path %s is"
                                       " incorrect: %s" % (path, actual))

    def test_relative_path_hierarchy(self):
        path = 'experiment/Session01/resource/pk_01'
        expected = [('experiment', 'Session01'), ('resource', 'pk_01')]
        actual = path_hierarchy(path)
        assert_equal(actual, expected, "The path hierarchy for path %s is"
                                       " incorrect: %s" % (path, actual))

    def test_relative_path_hierarchy_with_type_synonym(self):
        path = 'session/Session01/resource/pk_01'
        expected = [('experiment', 'Session01'), ('resource', 'pk_01')]
        actual = path_hierarchy(path)
        assert_equal(actual, expected, "The path hierarchy for path %s is"
                                       " incorrect: %s" % (path, actual))


    def test_path_hierarchy_with_wild_card(self):
        path = 'experiment/Session01/resource/*'
        expected = [('experiment', 'Session01'), ('resource', '*')]
        actual = path_hierarchy(path)
        assert_equal(actual, expected, "The path hierarchy for path %s is"
                                       " incorrect: %s" % (path, actual))

    def test_path_hierarchy_with_globs(self):
        path = '/QIN/Breast003/Session*/resources/pk*'
        expected = [('project', 'QIN'), ('subject', 'Breast003'),
                    ('experiment', 'Session*'), ('resource', 'pk*')]
        actual = path_hierarchy(path)
        assert_equal(actual, expected, "The path hierarchy for path %s is"
                                       " incorrect: %s" % (path, actual))

    def test_project_glob(self):
        path = '/QIN*/*/*/resources/pk*'
        expected = [('project', 'QIN*'), ('subject', '*'),('experiment', '*'),
                     ('resource', 'pk*')]
        actual = path_hierarchy(path)
        assert_equal(actual, expected, "The path hierarchy for path %s is"
                                       " incorrect: %s" % (path, actual))

    def test_path_hierarchy_with_missing_terminal_value(self):
        path = 'experiment/Session01/resources'
        expected = [('experiment', 'Session01'), ('resource', '*')]
        actual = path_hierarchy(path)
        assert_equal(actual, expected, "The path hierarchy for path %s is"
                                       " incorrect: %s" % (path, actual))

    def test_xnat_info(self):
        # The test file name without the directory.
        _, fname = os.path.split(FIXTURE)
        with qixnat.connect() as xnat:
            # Clear the XNAT test subject.
            xnat.delete(PROJECT, SUBJECT)
            # Make a resource.
            rsc = xnat.find_or_create(PROJECT, SUBJECT, SESSION,
                                      scan=SCAN, resource=RESOURCE,
                                      modality='MR')
            # Upload a file.
            xnat.upload(rsc, FIXTURE)

            # The XNAT file object.
            file = rsc.file(fname)
            # The ancestor scan.
            scan = rsc.parent()
            # The ancestor experiment.
            exp = scan.parent()
            # The ancestor subject.
            sbj = exp.parent()
            # The root project.
            prj = sbj.parent()

            # Test xnat_key.
            assert_equal(xnat_key(prj), prj.label(),
                         "The project key is incorrect: %s" % xnat_key(prj))
            assert_equal(xnat_key(sbj), sbj.label(),
                         "The subject key is incorrect: %s" % xnat_key(prj))
            assert_equal(xnat_key(exp), exp.label(),
                         "The experiment key is incorrect: %s" % xnat_key(exp))
            assert_equal(xnat_key(scan), scan.label(),
                         "The scan key is incorrect: %s" % xnat_key(scan))
            assert_equal(xnat_key(rsc), rsc.label(),
                         "The resource key is incorrect: %s" % xnat_key(rsc))
            assert_equal(xnat_key(file), file.label(),
                         "The file key is incorrect: %s" % xnat_key(file))

            # Test xnat_name.
            assert_equal(xnat_name(prj), PROJECT,
                         "The project name is incorrect: %s" % xnat_name(prj))
            assert_equal(xnat_name(sbj), SUBJECT,
                         "The subject name is incorrect: %s" % xnat_name(sbj))
            assert_equal(xnat_name(exp), SESSION,
                         "The experiment name is incorrect: %s" % xnat_name(exp))
            scan_name = xnat_name(scan)
            assert_is_instance(scan_name, int, "The scan name type is not an"
                                               " integer: %s" % scan_name.__class__)
            assert_equal(scan_name, SCAN,
                         "The scan name is incorrect: %s" % scan_name)
            assert_equal(xnat_name(rsc), RESOURCE,
                         "The resource name is incorrect: %s" % xnat_name(rsc))
            assert_equal(xnat_name(file), fname,
                         "The file name is incorrect: %s" % xnat_name(file))

            # Test xnat_path.
            assert_equal(xnat_path(prj), "/%s" % PROJECT,
                         "The XNAT project path is incorrect: %s" % xnat_path(prj))
            assert_equal(xnat_path(sbj), "/%s/%s" % (PROJECT, SUBJECT),
                         "The XNAT subject path is incorrect: %s" % xnat_path(sbj))
            assert_equal(xnat_path(exp), "/%s/%s/%s" % (PROJECT, SUBJECT, SESSION),
                         "The XNAT experiment path is incorrect: %s" % xnat_path(exp))
            assert_equal(xnat_path(scan), "/%s/%s/%s/scan/%d" %
                                          (PROJECT, SUBJECT, SESSION, SCAN),
                         "The XNAT scan path is incorrect: %s" % xnat_path(scan))
            assert_equal(xnat_path(rsc), "/%s/%s/%s/scan/%d/resource/%s" %
                                         (PROJECT, SUBJECT, SESSION, SCAN, RESOURCE),
                         "The XNAT resource path is incorrect: %s" % xnat_path(rsc))
            assert_equal(xnat_path(file), "/%s/%s/%s/scan/%d/resource/%s/file/%s" %
                                          (PROJECT, SUBJECT, SESSION, SCAN, RESOURCE,
                                           fname),
                         "The XNAT file path is incorrect: %s" % xnat_path(file))
            # Test xnat_children.
            # Note: project children is not tested, since there might be other 
            #subjects in the QIN_Test XNAT project.
            #
            # Note: Compare the XNAT object ids rather than the object directly,
            # due to the following pyxnat bug:
            # * pyxnat objects which resolve to the same XNAT database object
            #   are not equal.
            #
            assert_equal([obj.id() for obj in xnat_children(sbj)], [exp.id()],
                         "The XNAT subject children is incorrect: %s" % xnat_children(sbj))
            assert_equal([obj.id() for obj in xnat_children(exp)], [scan.id()],
                         "The XNAT experiment children is incorrect: %s" % xnat_children(exp))
            assert_equal([obj.id() for obj in xnat_children(scan)], [rsc.id()],
                         "The XNAT scan children is incorrect: %s" % xnat_children(scan))

            assert_equal([obj.id() for obj in xnat_children(rsc)], [file.id()],
                         "The XNAT resource children is incorrect: %s" % xnat_children(rsc))
            assert_equal(xnat_children(file), [],
                         "The XNAT file children is incorrect: %s" % xnat_children(file))


if __name__ == "__main__":
    import nose

    nose.main(defaultTest=__name__)
