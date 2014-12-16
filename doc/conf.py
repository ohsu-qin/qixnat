import os
import qixnat

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx.ext.todo']
autoclass_content = "both"
source_suffix = '.rst'
master_doc = 'index'
project = u'qixnat'
copyright = u'2014, OHSU Knight Cancer Institute'
version = qiutil.__version__
pygments_style = 'sphinx'
htmlhelp_basename = 'qxnatdoc'
html_title = "qixnat v%s" % version
