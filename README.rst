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


Create virtual environment
--------------------------

Create and activate the virtual environment::

    virtualenv venv
    source venv/bin/activate


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

This also creates a superuser which you can use to log into the admin.


Set up Cache
------------

By default the settings/local.py file is setup for a local memory cache.
This should be fine for local testing and you shouldn't need to do anything
else. If you'd like to more closely mimic production, you can install
`memcached` or `Redis` and configure the `CACHES` setting in `settings/local.py`
accordingly.


Run it
------

    ./manage.py runserver

Static media will be handled automatically by Django 1.4's built-in
handler.


Setting up a project
====================

Pull up the home page which should now be at http://localhost:8000/. Click
the `Admin` link on the right of the nav bar. Login with the admin account
you setup in during `syncdb`, then go back to the home page. Once you're
logged in you'll see buttons for creating and editing projects and sprints.
