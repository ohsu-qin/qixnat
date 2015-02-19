import os
import qixnat

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx.ext.todo']
autoclass_content = "both"
autodoc_default_flags= ['members', 'show-inheritance']
source_suffix = '.rst'
master_doc = 'index'
project = u'qixnat'
copyright = u'2014, OHSU Knight Cancer Institute'
version = qixnat.__version__
pygments_style = 'sphinx'
htmlhelp_basename = 'qxnatdoc'
html_title = "qixnat v%s" % version


def skip(app, what, name, obj, skip, options):
    """
    @return False if the name is __init__ or *skip* is set, True otherwise
    """
    return skip and name is not "__init__"


def setup(app):
    """
    Directs autodoc to call :meth:`skip` to determine whether to skip a member.
    """
    app.connect("autodoc-skip-member", skip)
