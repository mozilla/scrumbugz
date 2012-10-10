from fabric.api import local, env


env.git_remote = 'dev'


def prod():
    env.git_remote = 'prod'


def heroku(cmd):
    local("heroku run '{0}' --remote {1}".format(cmd, env.git_remote))


def heroku_django(cmd):
    heroku("python manage.py {0}".format(cmd))


def deploy():
    push()
    collect_static()
    syncdb()


def push():
    local('git push {0} master'.format(env.git_remote))


def collect_static():
    heroku_django('collectstatic --noinput')


def syncdb():
    heroku_django('syncdb')
    heroku_django('migrate')


def cron(command):
    heroku_django('cron {0}'.format(command))


def clear_cache():
    cron('clear_cache')
