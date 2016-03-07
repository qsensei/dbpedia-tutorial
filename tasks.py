from glob import glob
from urlparse import urlparse
import contextlib
import os
import tempfile
import time
import zipfile

from invoke import run, task
import docker
import requests

app_container = 'dbpedia-tutorial'


@task
def setup():
    if not is_container_created():
        cmd = 'docker run -dp 8000:8000'
        cmd += ' --name %s' % app_container
        cmd += ' docker.qsensei.com/fuse-free'
        run(cmd)
    else:
        print 'Warning: The docker container "%s" is already setup.' % (
            app_container,)
        print 'If you did not set this up or you want to start over, run:\n'
        print '    bin/inv teardown'
        print '    bin/inv setup\n'
    if not is_instance_running():
        try:
            setup_instance()
            start_instance()
        except Exception as e:
            print 'An error has occurred when trying to start the instance.'
            print 'Please make sure you have the latest fuse-free image:\n'
            print '    docker pull docker.qsensei.com/fuse-free\n'
            print 'Also make sure your repository is up to date:\n'
            print '    git pull'
            print '    python bootstrap.py'
            print '    bin/buildout\n'
            print 'If either were out of date, please teardown and try setting up again'  # noqa
            print '    bin/inv teardown'
            print '    bin/inv setup\n'
            print e
            exit(-3)
    else:
        print 'Warning: The Fuse instance is already running. We will skip setting it up.'  # noqa
        print 'If there are issues, try creating a container from scratch:\n'
        print '    bin/inv teardown'
        print '    bin/inv setup\n'
    run('bin/python scripts/upload_athletes.py')
    host = _get_server_host()
    print 'Setup complete! Visit http://%s:8000 in your browser.\n' % (
        host,)


@task
def setup_fuse():
    run('docker run -dp 8000:8000 --name %s docker.qsensei.com/fuse-free' % (
        app_container))
    setup_instance()
    start_instance()


@task
def reload_schema():
    stop_instance()
    setup_instance()
    start_instance()
    reindex()


def get_docker_client():
    kws = docker.utils.kwargs_from_env()
    try:
        kws['tls'].assert_hostname = False
    except KeyError:
        pass
    return docker.Client(**kws)


def is_container_created():
    client = get_docker_client()

    msg = 'The docker container "{container}" already has port 8000 bound.\n'
    msg += 'Please stop before running this script using\n\n'
    msg += '    docker stop {container}\n'
    containers = client.containers()
    for container in containers:
        ports = container['Ports']
        for port in ports:
            if port.get('PublicPort') == 8000:
                container = container['Names'][0][1:]
                if container == app_container:
                    return True
                print(msg.format(container=container))
                exit(-1)
    return False


def is_instance_running():
    host = _get_server_host()
    try:
        res = requests.get('http://%s:8000/api/admin/instance' % host)
        return res.json()['ready']
    except requests.ConnectionError:
        return False


def setup_instance():
    wait_for_container_ready()
    host = _get_server_host()
    with fuse_schema() as z:
        res = requests.put(
            'http://%s:8000/api/admin/instance' % host,
            headers={'content-type': 'application/zip'},
            data=z)
        if res.status_code == 200:
            pass
        elif res.status_code == 400:
            print res.json()
        else:
            pass
        res.raise_for_status()


def start_instance():
    host = _get_server_host()
    res = requests.post(
        'http://%s:8000/api/admin/instance' % host,
        json={'action': 'start'})
    res.raise_for_status()
    wait_for_ready()


def stop_instance():
    host = _get_server_host()
    res = requests.post(
        'http://%s:8000/api/admin/instance' % host,
        json={'action': 'stop'})
    res.raise_for_status()
    wait_for_stopped()


def wait_for_container_ready():
    url = 'http://%s:8000/api/admin/instance' % _get_server_host()
    for _ in xrange(20):
        try:
            res = requests.get(url)
            if res.status_code == 200:
                return
        except KeyboardInterrupt:
            raise
        except requests.ConnectionError:
            time.sleep(0.5)
    raise RuntimeError('Timeout waiting for container to start.')


def wait_for_ready():
    host = _get_server_host()
    for _ in xrange(20):
        res = requests.get(
            'http://%s:8000/api/admin/instance' % host)
        res.raise_for_status()
        if res.json()['ready']:
            return
        time.sleep(0.5)
    raise RuntimeError('Timeout while waiting for Fuse to be ready.')


def wait_for_stopped():
    host = _get_server_host()
    for _ in xrange(20):
        res = requests.get(
            'http://%s:8000/api/admin/instance' % host)
        res.raise_for_status()
        if res.json()['status'] == 'stopped':
            return
        time.sleep(0.5)
    raise RuntimeError('Timeout while waiting for Fuse to stop.')


@task
def reindex():
    host = _get_server_host()
    res = requests.post(
        'http://%s:8000/api/tasks/types/index' % host
    )
    res.raise_for_status()


@task
def teardown():
    run('docker rm -fv %s' % app_container)


def _get_server_host():
    docker_host = os.environ.get('DOCKER_HOST')
    if docker_host:
        return urlparse(docker_host).hostname
    return 'localhost'


@contextlib.contextmanager
def fuse_schema():
    with tempfile.TemporaryFile() as f:
        with zipfile.ZipFile(f, 'w') as z:
            for fn in glob('schema/*.json'):
                z.write(fn, os.path.basename(fn))
            for fn in glob('schema/*.py'):
                z.write(fn, os.path.basename(fn))
        f.flush()
        f.seek(0)
        yield f
