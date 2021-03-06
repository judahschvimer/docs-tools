import os
import pwd
import sys
import datetime
import tarfile
import urllib2
import json

from contextlib import closing

from fabric.api import task, puts, abort, env

from fabfile.utils.serialization import ingest_yaml_list
from fabfile.utils.config import get_conf
from fabfile.utils.structures import conf_from_list, BuildConfiguration

from fabfile.make import runner
from fabfile.deploy import deploy_jobs

def get_build_metadata(conf=None):
    if conf is None:
        conf=get_conf()

    o = dict(push=dict(), conf=conf, meta=dict())

    for target in ingest_yaml_list(os.path.join(conf.paths.projectroot,
                                                conf.paths.builddata,
                                                'push.yaml')):
        o['push'][target['target']] = target

    o['meta']['user'] = pwd.getpwuid(os.getuid())[0]
    o['meta']['platform'] = sys.platform
    o['meta']['time'] = datetime.datetime.utcnow().isoformat()
    o['meta']['host'] = os.uname()[1]
    return o

def package_filename(archive_path, target, conf):
    fn = [conf.project.name ]

    if target is not None:
        tag = ''.join([ i if i not in ['push', 'stage'] else '' for i in target.split('-') ])
        if tag != '':
            fn.append(tag)

    fn.extend([ conf.git.branches.current,
                datetime.datetime.utcnow().strftime('%s'),
                conf.git.commit[:8] ])

    fn = os.path.join(archive_path, '-'.join(fn) + '.tar.gz')

    return fn

@task
def package(target=None, conf=None):
    "Builds a package from the current build output."

    if conf is None:
        conf = get_conf()

    archive_path = os.path.join(conf.paths.projectroot, conf.paths.buildarchive)
    fn = package_filename(archive_path, target, conf)

    pconf = conf_from_list('target', ingest_yaml_list(os.path.join(conf.paths.projectroot,
                                                                   conf.paths.builddata,
                                                                   'push.yaml')))
    if target is None:
        pconf = pconf[pconf.keys()[0]]
    else:
        pconf = pconf[target]

    if not os.path.exists(archive_path):
        os.makedirs(archive_path)
        puts('[deploy] [tarball]: creating {0} directory'.format(archive_path))
    else:
        if not os.path.isdir(archive_path):
            abort('[ERROR]: {0} exists and is not a directory.'.format(archive_path))

    arc_conf = os.path.join(conf.paths.projectroot,
                            conf.paths.branch_output,
                            'conf.json')

    with open(arc_conf, 'w') as f:
        json.dump(get_build_metadata(conf), f, indent=2)

    with tarfile.open(fn, 'w:gz') as t:
        if 'branched' in pconf.options:
            input_path = os.path.join(conf.paths.projectroot,
                                      conf.paths.output,
                                      pconf.paths.local,
                                      conf.git.branches.current)
            output_path_name = conf.git.branches.current
        else:
            input_path = os.path.join(conf.paths.projectroot,
                                      conf.paths.output,
                                      pconf.paths.local)
            output_path_name = os.path.split(pconf.paths.local)[-1]

        t.add(name=input_path,
              arcname=output_path_name)

        t.add(arc_conf, arcname='conf.json')

        if 'static' in pconf.paths:
            for path in pconf.paths.static:
                rendered_path = os.path.join(conf.paths.projectroot,
                                             conf.paths.public, path)
                if os.path.exists(rendered_path):
                    t.add(name=rendered_path,
                          arcname=path)

    puts('[deploy] [tarball]: created {0} as archive of current build artifacts.'.format(fn))

@task
def fetch(path, conf=None):
    "Downloads package from a URL if it doesn't exist locally."

    if conf is None:
        conf = get_conf()

    local_path = path.split('/')[-1]

    tar_path = os.path.join(conf.paths.projectroot,
                            conf.paths.buildarchive,
                            local_path)

    if not os.path.exists(tar_path):
        with closing(urllib2.urlopen(path)) as u:
            with open(tar_path, 'w') as f:
                f.write(u.read())
        puts('[deploy] [tarball]: downloaded {0}'.format(local_path))
    else:
        puts('[deploy] [tarball]: {0} exists locally, not downloading.'.format(local_path))

    return tar_path

@task
def unwind(path, conf=None):
    "Unpack a package into the 'build/public/' directory."

    if conf is None:
        conf = get_conf()

    if path.startswith('http'):
        tar_path = fetch(path, conf)
    else:
        tar_path = path

    with tarfile.open(tar_path, "r:gz") as t:
        t.extractall(os.path.join(conf.paths.projectroot, conf.paths.public))

    arc_file = os.path.join(conf.paths.projectroot,
                            conf.paths.public,
                            'conf.json')

    new_conf = BuildConfiguration(arc_file)

    new_conf.conf.paths.projectroot = conf.paths.projectroot

    os.remove(arc_file)

    puts('[deploy] [tarball]: extracted {0} archive into {1}.'.format(os.path.basename(tar_path), conf.paths.public))
    return tar_path, new_conf

env.deploy_target = None
@task
def target(target):
    "Specify the deployment target. Required for stage.upload()"
    env.deploy_target = target

@task
def upload(path, conf=None):
    "Downloads, unwinds and deploys the docs build in a package."

    if conf is None:
        conf = get_conf()

    if env.deploy_target is None:
        abort('[deploy] [tarball] [ERROR]: cannot deploy without a deploy target.')

    tar_path, meta_conf = unwind(path, conf)

    pconf = meta_conf.push[env.deploy_target]
    conf = meta_conf.conf

    puts("[deploy] [tarball]: deploying from archive now.")
    count = runner(deploy_jobs(env.deploy_target, conf, pconf), pool=2)
    puts('[deploy]: pushed {0} targets'.format(count))
    puts("[deploy] [tarball]: Deployed {0} from archive.".format(env.deploy_target))
