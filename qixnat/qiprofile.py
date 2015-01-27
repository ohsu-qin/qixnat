"""
This module provides helper methods for updating the qiprofile
MongoDB database.
"""

# Absolute import (the default in a future Python release) resolves
# qiprofile as the qiprofile-rest qiprofile import rather than this
# module of the same name.
from __future__ import absolute_import
import qixnat
from qiprofile-rest import qiprofile

def sync():
    """
    Updates the qiprofile database from the XNAT database.
    The subjects, sessions and modeling results in the
    :meth:`qiutil.project.project` are added, if necessary,
    to the QuIP database.
    """
    prj = project()
    with qixnat.connect as xnat:
        criterion = "/project/%s/subjects" % prj
        for xnat_sbj in xnat.interface.select(criterion):
            prf_sbj = qiprofile.find_subject(prj, xnat_sbj.name, create=True)
            for xnat_sess in xnat_sbj.sessions():
                prf_sess = qiprofile.find_session(prj, xnat_sbj.name,
                                                  xnat_sess.name, create=True)
                # TODO - get image acquisition date from DICOM?
                # TODO - add modeling
