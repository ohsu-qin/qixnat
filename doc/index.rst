.. _index:

=========================================
qixnat - XNAT facade
=========================================

********
Synopsis
********
qixnat provides a XNAT_ facade.

:API: http://qixnat.readthedocs.org/en/latest/api/index.html

:Git: https://github.com/ohsu-qin/qixnat


************
Feature List
************
1. XNAT_ facade API.

2. XNAT list, transfer and delete utilities.


************
Installation
************

``qixnat`` depends on the pyxnat_ module, which can in turn can be tricky to
install. Furthermore, the `pyxnat installation guide`_ is itself insufficient
to install pyxnat dependencies consistently in all environments. Consequently,
the following installation steps must be followed to ensure a correct build:

1. On Linux only, install the ``libxslt`` dev package. For Ubuntu or other
   Debian-based systems, execute::

       sudo aptitude install libxslt-dev

   For Red Hat, execute::
   
       sudo yum install libxslt-dev

2. Anaconda_ is recommended for ensuring package and library consistency.
   Install Anaconda in ``$HOME/anaconda`` on your workstation according to
   the `Anaconda Installation Instructions`_. Preferably, install the
   `Anaconda Accelerate`_ add-on as well. Note that a
   `Anaconda Accelerate Academic User License`_ is available.

3. Add ``$HOME/anaconda/bin`` to your PATH, if necessary::

       export PATH=$HOME/anaconda/bin:$PATH

4. Make an Anaconda virtual environment initialized with ``pip``, e.g.::

       conda create --name qin pip

5. Activate the Anaconda environment, e.g.::

       source activate qin

   As a convenience, you can initialize this environment at login by prepending
   Anaconda and your virtual environment to ``PATH`` in your shell
   login script. Open an editor on ``$HOME/.bashrc`` or ``$HOME/.bash_profile``
   and add the following lines::

       # Prepend the Anaconda base applications.
       export PATH=$HOME/anaconda/bin:$PATH
       # Prepend the virtual environment.
       source activate qin

6. Install the ``qixnat`` dependencies hosted by Anaconda::

       wget -q --no-check-certificate -O \
         - https://www.github.com/ohsu-qin/qixnat/raw/master/requirements_conda.txt \
         | xargs conda install --yes

7. On Mac only, reinstall the lxml package using the ``-f`` force option to
   work around a `lxml install issue`_::

       conda install -f lxml

8. Install the ``qixnat`` package::

       pip install qixnat


*****
Usage
*****
Run the following command for the utility options::

    cpxnat --help
    lsxnat --help
    rmxnat --help

The primary read API interface of interest is the `XNAT facade`_ class.


***********
Development
***********

Testing is performed with the nose_ package, which must be installed separately.

Documentation is built automatically by ReadTheDocs_ when the project is pushed
to GitHub. Documentation can be generated locally as follows:

* Install Sphinx_, if necessary.

* Run the following in the ``doc`` subdirectory::

    make html

---------

.. container:: copyright


.. Targets:

.. _Anaconda: http://docs.continuum.io/anaconda/

.. _Anaconda Accelerate: http://docs.continuum.io/accelerate/index

.. _Anaconda Accelerate Academic User License: https://store.continuum.io/cshop/academicanaconda

.. _Anaconda Installation Instructions: http://docs.continuum.io/anaconda/install.html

.. _Knight Cancer Institute: http://www.ohsu.edu/xd/health/services/cancer

.. _license: https://github.com/ohsu-qin/qixnat/blob/master/LICENSE.txt

.. _lxml install issue: http://stackoverflow.com/questions/23172384/lxml-runtime-error-reason-incompatible-library-version-etree-so-requires-vers

.. _nose: https://nose.readthedocs.org/en/latest/

.. _pip: https://pypi.python.org/pypi/pip

.. _Python: http://www.python.org

.. _pyxnat: https://pythonhosted.org/pyxnat/

.. _pyxnat installation guide: https://pythonhosted.org/pyxnat/installing.html 

.. _ReadTheDocs: https://www.readthedocs.org

.. _Sphinx: http://sphinx-doc.org/index.html

.. _XNAT: http://www.xnat.org/

.. _XNAT facade: http://qixnat.readthedocs.org/en/latest/api/index.html#module-qixnat.facade

.. toctree::
  :hidden:

  api/index
