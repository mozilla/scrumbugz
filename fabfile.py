from fabric.api import local, env

def heroku(cmd):
    local("heroku run '{0}'".format(cmd))

def heroku_django(cmd):
    heroku("python manage.py {0}".format(cmd))

def deploy():
    local('git push heroku master')
    heroku_django('collectstatic --noinput')
    heroku_django('syncdb')
    #heroku_django('migrate')

