========
 README
========

This is the software that runs https://scrumbu.gs/ .

This allows you to manage sprints backed by Bugzilla data.


Project details
===============

Code:
    https://github.com/mozilla/scrumbugz

Issues:
    https://github.com/mozilla/scrumbugz/issues

CI:
    .. image:: https://secure.travis-ci.org/mozilla/scrumbugz.png
       :alt: Travis CI
       :target: http://travis-ci.org/mozilla/scrumbugz

IRC:
    #scrum on irc.mozilla.org


Setup for development
=====================

Requirements
------------

* Bugzilla 4+
* The Bugzilla XMLRPC API.

Currently, scrumbugz uses Bugzilla searches for Product(s)/Component(s) and
bug IDs via the XMLRPC api (/xmlrpc.cgi).

Thus, in order to use Scrumbugz, you need a Bugzilla instance that's
running a recent version of Bugzilla and the Bugzilla API. We think
the minimum version is Bugzilla 4, but haven't verified this.

.. Note::

   You don't need to install Bugzilla on your machine. As long as you
   have access to a Bugzilla server, you're fine.


Create virtual environment
--------------------------

Create and activate the virtual environment::

    virtualenv venv
    source venv/bin/activate

.. Note::

   You don't have to put your virtual environment in ``./venv/``. Feel
   free to put it anywhere.


Get dependencies
----------------

Run::

    pip install -r requirements-dev.txt

That sets up all the dependencies required.


Configure
---------

Then you should create a local file. First, copy the template over::

    cp settings/local.py-dist settings/local.py

and edit it.


Set up the db
-------------

Run::

    ./manage.py syncdb
    ./manage.py migrate

This also creates a superuser which you can use to log into the Django admin
page at `<http://localhost:8000/admin>`_.


Set up Cache
------------

By default the `settings/local.py` file is set up for a local memory
cache.  This should be fine for local testing and you shouldn't need
to do anything else. If you'd like to more closely mimic production,
you can install `memcached` or `Redis` and configure the `CACHES`
setting in `settings/local.py` accordingly.


Run it
------

    ./manage.py runserver

Static media will be handled automatically by Django's built-in handler.


Setting up a project
====================

1. Pull up the Django admin page at `<http://localhost:8000/admin>`_.
2. Login with the admin account you setup during `syncdb`,
3. then go back to the home page at `<http://localhost:8000/>`_.

Once you're logged in, you'll see buttons for creating and editing projects
and sprints. If your superuser account's email address is registered with
Mozilla Persona, you can also login using the `Sign In` link on the right
of the nav bar.

The Bugzilla url for a sprint should be the url for a query defining
the sprint. For example, SUMO uses the target to define sprints, so
the query url for our 2012.6 sprint is::

    https://bugzilla.mozilla.org/buglist.cgi?quicksearch=ALL%20product%3Asupport%20milestone%3A2012.6
