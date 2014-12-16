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

1. On Linux only, install the ``libxslt`` dev package. For Ubuntu or other
   Debian-based systems, execute::

       sudo aptitude install libxslt-dev

   For Red Hat, execute::
   
       sudo yum install libxslt-dev

2. On Mac only, install the ``lxml`` Python package with statically bound
   libraries::

       (STATIC_DEPS=true; pip install lxml)

3. Install the ``qixnat`` package using the Python_ pip_ command::

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

.. _Knight Cancer Institute: http://www.ohsu.edu/xd/health/services/cancer

.. _license: https://github.com/ohsu-qin/qixnat/blob/master/LICENSE.txt

.. _pip: https://pypi.python.org/pypi/pip

.. _Python: http://www.python.org

.. _XNAT: http://www.xnat.org/

.. toctree::
  :hidden:

  api/index
