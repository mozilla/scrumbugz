========
 README
========

This is the software that runs https://scrumbu.gs/ .

This allows you to manage sprints backed by Bugzilla data.


Project details
===============

Code:
    https://github.com/pmclanahan/scrumbugz

Issues:
    https://github.com/pmclanahan/scrumbugz/issues

CI:
    .. image:: https://secure.travis-ci.org/pmclanahan/scrumbugz.png
       :alt: Travis CI
       :target: http://travis-ci.org/pmclanahan/scrumbugz

IRC:
    #scrum on irc.mozilla.org


Setup for development
=====================

Requirements
------------

* Bugzilla 4
* a recent version of the Bugzilla API

Currently, scrumbugz uses Bugzilla search urls to define a sprint. It converts
the parameters in the search url to a form which it then uses with the Bugzilla
API.

Thus, in order to use scrumbugz, you need a Bugzilla instance that's running
a recent version of Bugzilla and the Bugzilla API. We think the minimum 
version is Bugzilla 4, but haven't verified this.


Get dependencies
----------------

Run::

    pip install -E ./venv/ -r requirements-dev.txt

That sets up all the dependencies required.


Configure
---------

Then you should create a local file. First, copy the template over::

    cp settings/local.py-dist settings/local.py

and edit it.

Activate virtual environment
----------------------------

After that, activate the virtual environment::

    . ./venv/bin/activate


Set up the db
-------------

Run::

    ./manage.py syncdb

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

Static media will be handled automatically by Django 1.3's built-in
handler.


Setting up a project
====================

Pull up the home page which should now be at http://localhost:8000/. Click
the `Admin` link on the right of the nav bar. Login with the admin account
you setup in during `syncdb`, then go back to the home page. Once you're
logged in you'll see buttons for creating and editing projects and sprints.

The bugzilla url for a sprint should be the url for a query defining the sprint. For
example, SUMO uses the target to define sprints, so the query url for our 2012.6 sprint
is::

    https://bugzilla.mozilla.org/buglist.cgi?quicksearch=ALL%20product%3Asupport%20milestone%3A2012.6
