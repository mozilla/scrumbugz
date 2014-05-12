#!/bin/bash

APP_NAME="scrumbugz" # Name of the application

echo "Starting $APP_NAME"

# get the configuration
source /home/pmclanahan/www/scrumbugz/scrumbugz_env


# Activate the virtual environment
source ${VENV_PATH}/bin/activate
export PYTHONPATH=$PROJECT_DIR:$PYTHONPATH

cd $PROJECT_DIR

# Start your Celery daemon
# Programs meant to be run under supervisor should not daemonize themselves (do not use --daemon)
exec newrelic-admin run-program manage.py celery worker \
    -c $CELERY_CONCURRENCY \
    --loglevel=$LOG_LEVEL
