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

IRC:
    #scrum on irc.mozilla.org


Setup for development
=====================

Get dependencies
----------------

Run::

    pip install -E ./venv/ -r requirements.txt

That sets up all the dependencies required.


Configure
---------

You need to create a sekrit module that holds secret settings. First, copy
the template over::

    cp settings/sekrit.py.tmpl settings/sekrit.py

and edit it.

Then you should create a local file. First, copy the template over::

    cp settings/local.py.tmpl settings/local.py

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


Set up Redis
------------

Set up a Redis instance based on your Redis settings.


Collect static stuff and run
----------------------------

Then collect static stuff::

    ./manage.py collectstatic

Then::

    ./manage.py runserver


Setting up a project
====================

In the admin, click on "projects" and add a project.

Each project needs at least one sprint. So in the admin, click on "sprints" and add
a sprint.

The bugzilla url for a sprint should be the url for a query defining the sprint. For
example, SUMO uses the target to define sprints, so the query url for our 2012.6 sprint
is::

    https://bugzilla.mozilla.org/buglist.cgi?quicksearch=ALL%20product%3Asupport%20milestone%3A2012.6
