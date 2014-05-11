#!/bin/bash
 
APP_NAME="scrumbugz" # Name of the application

echo "Starting $APP_NAME"

# Requires a file to populate the environment variables.
# Should look like the following:

## paths
#export PROJECT_DIR=/path/to/django/project
#export VENV_PATH=/path/to/virtualenv
#export SOCKET_FILE=/path/to/socket/file.sock
#
## app settings
#export DATABASE_URL='postgres://USER:PASSWORD@HOST:PORT/DB_NAME'
#export SECRET_KEY='random string of characters'
#export BUGMAIL_API_KEY='whatever is in settings'
#export STATIC_URL='CDN url'
#export BROKER_URL='redis://HOST:6379/'
#export SENTRY_DSN='config from the sentry interface if you have one'
#export NEW_RELIC_CONFIG_FILE=newrelic.ini
#export SERVER_ENV=prod
#
## gunicorn stuff
#export WEB_CONCURRENCY=4
#export GUNICORN_USER=server_user
#export GUNICORN_GROUP=server_group
#export LOG_LEVEL=info

# get the configuration
source /home/pmclanahan/www/scrumbugz/scrumbugz_env

# Activate the virtual environment
source ${VENV_PATH}/bin/activate
export PYTHONPATH=$PROJECT_DIR:$PYTHONPATH

cd $PROJECT_DIR

# Start your Django Unicorn
# Programs meant to be run under supervisor should not daemonize themselves (do not use --daemon)
exec newrelic-admin run-program gunicorn \
	--name $APP_NAME \
	--user=$GUNICORN_USER --group=$GUNICORN_GROUP \
	--log-level=$LOG_LEVEL \
	--bind=unix:$SOCKET_FILE wsgi:application
