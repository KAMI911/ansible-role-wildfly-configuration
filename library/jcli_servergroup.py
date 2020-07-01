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

def isServerGroupAlreadyCreated(data):
    cli = "/server-group={}:query".format(data['server_group_name'])
    result = jbossCommand(data, cli)
    if "WFLYCTL0216" in result:
        created = False
    else:
        created = True
    return created, result

def server_group_present(data):
    created, result = isServerGroupAlreadyCreated(data)
    isError = False
    hasChanged = True
    meta = {}
    if not created:
        cli = "/server-group={}:add(profile={}, socket-binding-group={})".format(data['server_group_name'],data['server_group_profile'],data['socket_binding_group'])
        res = jbossCommand(data, cli)
        meta = {"status": "OK", "response": res}
    else:
        hasChanged = False
        resp = "Server group {} already created ({})".format(data['server_group_name'], result)
        meta = {"status" : "OK", "response" : resp}
    return isError, hasChanged, meta

def server_group_absent(data):
    created, result = isServerGroupAlreadyCreated(data)
    isError = False
    hasChanged = True
    meta = {}
    if not created:
        hasChanged = False
        resp = "Server group {} does not exist".format(data['server_group_name'])
        meta = {"status" : "OK", "response" : resp}
    else:
        cli = "/server-group={}:remove".format(data['server_group_name'])
        res = jbossCommand(data, cli)
        meta = {"status": "OK", "response": res}
    return isError, hasChanged, meta

def server_group_start(data):
    created, result = isServerGroupAlreadyCreated(data)
    isError = False
    hasChanged = True
    meta = {}
    if created:
        cli = "/server-group={}:start-servers".format(data['server_group_name'])
        res = jbossCommand(data, cli)
        meta = {"status": "OK", "response": res}
    else:
        hasChanged = False
        resp = "Server group {} does not exist".format(data['server_group_name'])
        meta = {"status" : "OK", "response" : resp}
    return isError, hasChanged, meta

def server_group_stop(data):
    created, result = isServerGroupAlreadyCreated(data)
    isError = False
    hasChanged = True
    meta = {}
    if created:
        cli = "/server-group={}:stop-servers".format(data['server_group_name'])
        res = jbossCommand(data, cli)
        meta = {"status": "OK", "response": res}
    else:
        hasChanged = False
        resp = "Server group {} does not exist".format(data['server_group_name'])
        meta = {"status" : "OK", "response" : resp}
    return isError, hasChanged, meta

def main():
    fields = {
        "jboss_home" : {"required": True, "type": "str"},
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
        "server_group_name": {"required": True, "type": "str"},
        "server_group_profile": {
            "required": False,
            "default": "default",
            "type": "str"
        },
        "socket_binding_group": {
            "required": False,
            "default": "standard-sockets",
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
            "choices": ['present', 'absent', 'start', 'stop'],
            "type": 'str'
        },
    }

    choice_map = {
        "present": server_group_present,
        "absent": server_group_absent,
        "start": server_group_start,
        "stop": server_group_stop
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
        module.fail_json(msg="Error creating server group", meta=result)

if __name__ == '__main__':
    main()
