Fuse Athlete Search Using DBpedia Tutorial
##########################################

.. image:: https://travis-ci.org/qsensei/dbpedia-tutorial.svg?branch=master
    :target: https://travis-ci.org/qsensei/dbpedia-tutorial

This is a quick tutorial on how to setup a Fuse instance to quickly search
through athletes pulled from `DBpedia`_.

Links
=====

- `Documentation`_
- `Support`_
- `Fuse Docs`_

Quickstart
==========

Make sure you have a `Free Fuse Key`_ and review the `Requirements`_.

.. sourcecode:: bash

  docker login -u token -p $FREE_FUSE_KEY -e me@mycompany.com docker.qsensei.com
  git clone https://github.com/qsensei/dbpedia-tutorial.git
  cd dbpedia-tutorial
  python bootstrap.py
  bin/buildout
  bin/inv setup

Once you're done, remove the containers.

.. sourcecode:: bash

  bin/inv teardown

Or do this manually.

.. sourcecode:: bash

  docker rm -fv dbpedia-tutorial

See the full `Documentation`_ for additional details.

.. _DBpedia: http://dbpedia.org
.. _Documentation: http://www.qsensei.com/docs/fuse/current/tutorials/dbpedia/index.html
.. _Free Fuse Key: https://www.qsensei.com/member-download-page/
.. _Fuse Docs: http://www.qsensei.com/docs/fuse/current/
.. _Requirements: https://www.qsensei.com/docs/fuse/current/tutorials/dbpedia/index.html#requirements
.. _Support: https://www.qsensei.com/support/
