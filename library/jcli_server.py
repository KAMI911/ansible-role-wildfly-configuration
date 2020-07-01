#!/usr/bin/python
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule
import subprocess
from os import path
import time

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

def isServerAlreadyCreated(data):
    cli = "/host={}/server={}:query".format(data['host'], data['server_config_name'])
    result = jbossCommand(data, cli)
    if "WFLYCTL0216" in result:
        created = False
    else:
        created = True
    return created, result

def server_present(data):
    created, result = isServerAlreadyCreated(data)
    isError = False
    hasChanged = True
    meta = {}
    if not created:
        cli = "/host={}/server-config={}:add(group={},socket-binding-port-offset={},socket-binding-group={})".format(data['host'],data['server_config_name'],data['server_group_name'],data['server_socket_binding_port_offset'],data['server_group_socket'])
        res = jbossCommand(data, cli)
        meta = {"status": "OK", "response": res}
    else:
        hasChanged = False
        resp = "Server {} already created".format(data['server_config_name'])
        meta = {"status" : "OK", "response" : resp}
    return isError, hasChanged, meta

def server_absent(data):
    created, result = isServerAlreadyCreated(data)
    isError = False
    hasChanged = True
    meta = {}
    if not created:
        hasChanged = False
        resp = "Server {} does not exist".format(data['server_config_name'])
        meta = {"status" : "OK", "response" : resp}
    else:
        cli = "/host={}/server-config={}:stop".format(data['host'],data['server_config_name'])
        res = jbossCommand(data, cli)
        res = str(res)
        while not "STOPPED" in res:
            time.sleep(0.5)
            cli = "/host={}/server-config={}:stop".format(data['host'],data['server_config_name'])
            res = jbossCommand(data, cli)
            res = str(res,'utf-8')
        cli = "/host={}/server-config={}:remove".format(data['host'],data['server_config_name'])
        res = jbossCommand(data, cli)
        meta = {"status": "OK", "response": res}
    return isError, hasChanged, meta

def server_start(data):
    created, result = isServerAlreadyCreated(data)
    isError = False
    hasChanged = True
    meta = {}
    if created:
        cli = "/host={}/server-config={}:start".format(data['host'],data['server_config_name'])
        res = jbossCommand(data, cli)
        meta = {"status": "OK", "response": res}
    else:
        hasChanged = False
        resp = "Server {} does not exist".format(data['server_config_name'])
        meta = {"status" : "OK", "response" : resp}
    return isError, hasChanged, meta

def server_stop(data):
    created, result = isServerAlreadyCreated(data)
    isError = False
    hasChanged = True
    meta = {}
    if created:
        cli = "/host={}/server-config={}:stop".format(data['host'],data['server_config_name'])
        res = jbossCommand(data, cli)
        meta = {"status": "OK", "response": res}
    else:
        hasChanged = False
        resp = "Server {} does not exist".format(data['server_config_name'])
        meta = {"status" : "OK", "response" : resp}
    return isError, hasChanged, meta

def main():
    fields = {
        "jboss_home" : {"required": True, "type": "str"},
        "host": {
            "required": False,
            "default": "master",
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
        "server_group_name": {
            "required": True,
            "type": "str"
        },
        "server_config_name": {
            "required": True,
            "type": "str"
        },
        "server_socket_binding_port_offset": {
            "required": False,
            "default": 0,
            "type": "int"
        },
        "server_group_socket": {
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
        "present": server_present,
        "absent": server_absent,
        "start": server_start,
        "stop": server_stop,
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
