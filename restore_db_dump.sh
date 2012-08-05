#!/bin/sh

DB_NAME='scrumbugz'

if [ "x$1" != "x" ]; then
    DUMP_NAME="$1"
    if [ "x$2" != "x" ]; then
        DB_NAME="$2"
    fi
else
    echo "usage: restore_db_dump.sh dumpfile_name.dump [db_name]"
    exit 1
fi

dropdb $DB_NAME && \
    createdb $DB_NAME && \
    pg_restore --clean --no-acl --no-owner -d $DB_NAME "$DUMP_NAME"
./manage.py syncdb && ./manage.py migrate
