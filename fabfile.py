from fabric.api import local, env


env.git_remote = 'dev'


def prod():
    env.git_remote = 'prod'


def heroku(cmd):
    local("heroku run '{0}' --remote {1}".format(cmd, env.git_remote))


def heroku_django(cmd):
    heroku("python manage.py {0}".format(cmd))


def deploy():
    remote = ('prod master' if env.git_remote == 'prod'
              else 'dev next:master')
    local('git push ' + remote)
    heroku_django('collectstatic --noinput')
    heroku_django('syncdb')
    if env.git_remote == 'dev':
        heroku_django('migrate')
