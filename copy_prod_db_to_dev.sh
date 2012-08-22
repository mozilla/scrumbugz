#!/bin/sh

test -z "$1" && echo "usage: $0 <DB_ALIAS_NAME>" && exit 1

heroku pgbackups:capture -r prod
heroku pgbackups:restore "$1" `heroku pgbackups:url -r prod` -r dev
