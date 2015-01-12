.. _index:

=========================================
qixnat - Quantitative Imaging XNAT helper
=========================================

********
Synopsis
********
qixnat provides a XNAT_ facade.

:API: http://qixnat.readthedocs.org/en/latest/api/index.html

:Git: github.com/ohsu-qin/qixnat


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
``qixnat`` installation cannot be performed using the customary Python_ pip_
command ``pip install qixnat`` alone. The following steps are suggested
instead:

1. On Linux only, install the ``libxslt`` dev package. For Ubuntu or other
   Debian-based systems, execute::

       sudo aptitude install libxslt-dev

   For Red Hat, execute::
   
       sudo yum install libxslt-dev

2. Install Anaconda_ in ``$HOME/anaconda`` on your workstation according to
   the `Anaconda Installation Instructions`_.

3. Add ``$HOME/anaconda/bin`` to your PATH::

       export PATH=$HOME/anaconda/bin:$PATH

4. Make an Anaconda virtual environment which initialized with pip and lxml,
   e.g.::

       conda create --name qin pip lxml

5. Install the ``qixnat`` dependencies hosted by Anaconda::

       cat requirements.txt | xargs -n 1 conda install -y

   Ignore ``No packages found`` messages for non-Anaconda packages. These
   packages will be installed in the next step.

6. Install the ``qixnat`` package::

       pip install qixnat


*****
Usage
*****
Run the following command for the utility options::

    qicp --help
    qils --help
    qirm --help


---------

.. container:: copyright

  Copyright (C) 2014 Oregon Health & Science University `Knight Cancer Institute`_.
  See the license_ for permissions.


.. Targets:

.. _Anaconda: http://docs.continuum.io/anaconda/

.. _Anaconda Installation Instructions: http://docs.continuum.io/anaconda/install.html

.. _Knight Cancer Institute: http://www.ohsu.edu/xd/health/services/cancer

.. _license: https://github.com/ohsu-qin/qixnat/blob/master/LICENSE.txt

.. _pip: https://pypi.python.org/pypi/pip

.. _Python: http://www.python.org

.. _pyxnat: https://pythonhosted.org/pyxnat/

.. _pyxnat installation guide: https://pythonhosted.org/pyxnat/installing.html 

.. _XNAT: http://www.xnat.org/

.. toctree::
  :hidden:

  api/index
