web: newrelic-admin run-program gunicorn wsgi:application -b 0.0.0.0:$PORT -w 5 -k gevent --max-requests 250
workerbeat: newrelic-admin run-program python manage.py celery worker -c 8 -B --loglevel=INFO
worker: newrelic-admin run-program python manage.py celery worker -c 8 --loglevel=INFO
