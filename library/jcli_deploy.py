#!/usr/bin/python
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule
import subprocess
from os import path

class JBossConnetionError(Exception):
    '''raise this cannot connect to JBoss contorller'''

class JBossNotFound(Exception):
    '''raise this when cannot find JBoss command line interface binary'''

def jbossCommand(data, cli):
    binaryExist = False
    remoteExists = False
    cmd = data['jboss_home'] + '/bin/jboss-cli.sh'
    no_cmd = path.isfile(cmd)
    if no_cmd is False:
        raise JBossNotFound('JBOSS command line binary ({}) is not found.'.format(cmd))
    controller = "--controller={}:{}".format(data['controller_host'],data['controller_port'])
    user = "-u={}".format(data['user'])
    password = "-p={}".format(data['password'])
    p = subprocess.Popen(["sh", cmd, "-c", cmd, controller, user, password], stdout=subprocess.PIPE)
    commandResult, err = p.communicate()
    if "WFLYPRT0053" in commandResult:
        raise JBossConnetionError('Could not connect http-remoting://{}:{}'.format(data['controller_host'],data['controller_port']))
    return commandResult

def isArtifactAlreadyDeployed(data):
    cli = "deployment-info --name={}".format(data['artifact'])
    result = jbossCommand(data, cli)
    if "WFLYCTL0216" in result:
        created = False
    else:
        created = True
    return created, result

def deployment_present(data):
    mode = data['server_mode']
    created, result = isArtifactAlreadyDeployed(data)
    isError = False
    hasChanged = True
    meta = {}
    result = ""
    if not created:
        if mode == 'standalone':
            cli = "deploy {}/{}".format(data['artifact_dir'],data['artifact'])
        else:
            cli = "deploy {}/{} --server-groups={}".format(data['artifact_dir'],data['artifact'],data['server_group_name'])
        res = jbossCommand(data, cli)
    else:
        cli = "deploy {}/{} --force".format(data['artifact_dir'],data['artifact']) #same behaviour between standalone and domain
        res = jbossCommand(data, cli)
        meta = {"status": "OK", "response": res}
        result = str(res)
        if "WFLYDC0074" in result:
            meta = {"status" : "Failed to deploy", "response" : result}
            isError = True
        else:
            meta = {"status" : "OK", "response" : result}
    return isError, hasChanged, meta

def deployment_absent(data):
    mode = data['server_mode']
    created, result = isArtifactAlreadyDeployed(data)
    isError = False
    hasChanged = True
    meta = {}
    if not created:
        hasChanged = False
        resp = "Deployment {} does not exist".format(data['artifact'])
        meta = {"status" : "OK", "response" : resp}
    else:
        if mode == 'standalone':
            cli = "undeploy {}".format(data['artifact'])
        else:
            cli = "undeploy {} --server-groups={}".format(data['artifact'],data['server_group_name'])
        res = jbossCommand(data, cli)
        result = str(res)
        if "WFLYDC0074" in result:
            meta = {"status" : "Failed to undeploy", "response" : result}
            isError = True
        else:
            meta = {"status": "OK", "response": result}
    return isError, hasChanged, meta

def main():
    fields = {
        "jboss_home" : {"required": True, "type": "str"},
        "server_group_name": {
            "required": True,
            "type": "str"
        },
        "artifact": {
            "required": True,
            "type": "str"
        },
        "artifact_dir": {
            "required": True,
            "type": "str"
        },
        "controller_host": {
            "required": False,
            "default": "localhost",
            "type": "str"
        },
        "controller_port": {
            "required": False,
            "default": 9990,
            "type": "int"
        },
        "server_mode" : {
            "required": True,
            "choices": ['standalone', 'domain'],
            "type": "str"
        },
        "user" : {
            "required": True,
            "type": "str"
        },
        "password" : {
            "required": True,
            "type": "str"
        },
        "state": {
            "default": "present",
            "choices": ['present', 'absent'],
            "type": 'str'
        },
    }

    choice_map = {
        "present": deployment_present,
        "absent": deployment_absent,
    }

    try:
        module = AnsibleModule(argument_spec=fields, supports_check_mode=False)
        is_error, has_changed, result = choice_map.get(module.params['state'])(module.params)
    except JBossNotFound as e:
        module.fail_json(msg=str(e))
    except JBossConnetionError as e:
        module.fail_json(msg=str(e))
    except Exception as e:
        module.fail_json(msg=str(e))

    if not is_error:
        module.exit_json(changed=has_changed, meta=result)
    else:
        module.fail_json(msg="Error creating server", meta=result)

if __name__ == '__main__':
    main()
