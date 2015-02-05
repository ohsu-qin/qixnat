from nose.tools import (assert_equal, assert_true, assert_is_not_none)
from qixnat.helpers import (hierarchical_label, parse_session_label, path_hierarchy)

class TestHelpers(object):
    def test_short_hierarchical_label(self):
        sess = 'Session01'
        expected = 'Breast003_Session01'
        actual = hierarchical_label('Breast003', sess)
        assert_equal(actual, expected, "The hierarchical label for session %s"
                                       " is incorrect: %s" % (sess, actual))

    def test_long_hierarchical_label(self):
        sess = 'Breast003_Session01'
        expected = 'Breast003_Session01'
        actual = hierarchical_label('Breast003', sess)
        assert_equal(actual, expected, "The hierarchical label for session %s"
                                       " is incorrect: %s" % (sess, actual))

    def test_parse_session_label(self):
        sess = 'Breast003_Session01'
        expected = ('Breast003', 'Session01')
        actual = parse_session_label(sess)
        assert_equal(actual, expected, "The parsed label for session %s"
                                       " is incorrect: %s" % (sess, actual))

    def test_path_hierarchy_with_leading_slash(self):
        path = '/project/QIN/subject/Breast003/session/Session01'
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
        path = 'session/Session01/resource/pk_01'
        expected = [('experiment', 'Session01'), ('resource', 'pk_01')]
        actual = path_hierarchy(path)
        assert_equal(actual, expected, "The path hierarchy for path %s is"
                                       " incorrect: %s" % (path, actual))

    def test_path_hierarchy_with_wild_card(self):
        path = 'session/Session01/resource/*'
        expected = [('experiment', 'Session01'), ('resources', '*')]
        actual = path_hierarchy(path)
        assert_equal(actual, expected, "The path hierarchy for path %s is"
                                       " incorrect: %s" % (path, actual))

    def test_path_hierarchy_with_globs(self):
        path = '/QIN/Breast003/Session*/resources/pk*'
        expected = [('project', 'QIN'), ('subject', 'Breast003'),
                    ('experiments', 'Session*'), ('resources', 'pk*')]
        actual = path_hierarchy(path)
        assert_equal(actual, expected, "The path hierarchy for path %s is"
                                       " incorrect: %s" % (path, actual))

    def test_project_glob(self):
        path = '/QIN*/*/*/resources/pk*'
        expected = [('projects', 'QIN*'), ('subjects', '*'),
                    ('experiments', '*'), ('resources', 'pk*')]
        actual = path_hierarchy(path)
        assert_equal(actual, expected, "The path hierarchy for path %s is"
                                       " incorrect: %s" % (path, actual))

    def test_path_hierarchy_with_missing_terminal_value(self):
        path = 'session/Session01/resources'
        expected = [('experiment', 'Session01'), ('resources', '*')]
        actual = path_hierarchy(path)
        assert_equal(actual, expected, "The path hierarchy for path %s is"
                                       " incorrect: %s" % (path, actual))
