#!/bin/sh

usage(){
    echo "usage: restore_db_dump.sh <dumpfile_name.dump> <db_name>"
    exit 1
}

test $# -lt 2 && usage

DUMP_NAME="$1"
DB_NAME="$2"

dropdb $DB_NAME && \
    createdb $DB_NAME && \
    pg_restore --clean --no-acl --no-owner -d $DB_NAME "$DUMP_NAME"
./manage.py syncdb && ./manage.py migrate
