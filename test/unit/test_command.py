import os
import shutil
from nose.tools import (assert_equal, assert_true)
from qixnat import command



class TestCommand(object):
    def test_prefix(self):
        path = 'QIN/Breast003/Session01'
        expected = [('project', 'QIN'), ('subject', 'Breast003'), ('experiment', 'Session01')]
        actual = command.parse_path(path)
        assert_equal(actual, expected, "Parsed project/subject/session path incorrect")
    
    def test_leading_slash(self):
        path = '/QIN/Breast003/Session01'
        expected = [('project', 'QIN'), ('subject', 'Breast003'), ('experiment', 'Session01')]
        actual = command.parse_path(path)
        assert_equal(actual, expected, "Parsed leading slash path incorrect")
    
    def test_trailing_slash(self):
        path = '/QIN/Breast003/Session01/'
        expected = [('project', 'QIN'), ('subject', 'Breast003'), ('experiment', 'Session01')]
        actual = command.parse_path(path)
        assert_equal(actual, expected, "Parsed trailing slash path incorrect")
    
    def test_leading_types(self):
        path = '/project/QIN/subject/Breast003/session/Session01'
        expected = [('project', 'QIN'), ('subject', 'Breast003'), ('experiment', 'Session01')]
        actual = command.parse_path(path)
        assert_equal(actual, expected, "Parsed leading types path incorrect")

    def test_pluralized_type(self):
        path = '/QIN/Breast003/Session01/resource/pk_jR5ny/files'
        expected = [('project', 'QIN'), ('subject', 'Breast003'), ('experiment', 'Session01'),
                    ('resource', 'pk_jR5ny'), 'files']
        actual = command.parse_path(path)
        assert_equal(actual, expected, "Parsed pluralized type path incorrect")
    
