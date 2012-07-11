from fabric.api import local, env


env.app = 'scrumbugz-dev'


def prod():
    env.app = 'scrumbugz'


def heroku(cmd):
    local("heroku run '{0}' --app {1}".format(cmd, env.app))


def heroku_django(cmd):
    heroku("python manage.py {0}".format(cmd))


def deploy():
    remote = ('heroku master' if env.app == 'scrumbugz'
              else 'heroku-dev next:master')
    local('git push ' + remote)
    heroku_django('collectstatic --noinput')
    heroku_django('syncdb')
    if env.app == 'scrumbugz-dev':
        heroku_django('migrate')
