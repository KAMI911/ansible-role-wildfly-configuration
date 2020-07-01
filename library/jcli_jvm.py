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

def isJvmAlreadyCreated(data):
    cli = "/host={}/server-config={}/jvm={}:query".format(data['host'], data['server_config_name'], data['jvm_name'])
    result = jbossCommand(data, cli)
    if "WFLYCTL0216" in result:
        created = False
    else:
        created = True
    return created, result

def jvm_present(data):
    created, result = isJvmAlreadyCreated(data)
    isError = False
    hasChanged = True
    meta = {}
    result = []
    if not created:
        cli = "/host={}/server-config={}/jvm={}:add".format(data['host'],data['server_config_name'],data['jvm_name'])
        res = jbossCommand(data, cli)
        result.append(res)
        cli = "/host={}/server-config={}/jvm={}:write-attribute(name=heap-size,value={})".format(data['host'],data['server_config_name'],data['jvm_name'],data['heap_size'])
        res = jbossCommand(data, cli)
        result.append(res)
        cli = "/host={}/server-config={}/jvm={}:write-attribute(name=max-heap-size,value={})".format(data['host'],data['server_config_name'],data['jvm_name'],data['max_heap_size'])
        res = jbossCommand(data, cli)
        result.append(res)
        cli = "/host={}/server-config={}/jvm={}:write-attribute(name=permgen-size,value={})".format(data['host'],data['server_config_name'],data['jvm_name'],data['permgen_size'])
        res = jbossCommand(data, cli)
        result.append(res)
        cli = "/host={}/server-config={}/jvm={}:write-attribute(name=max-permgen-size,value={})".format(data['host'],data['server_config_name'],data['jvm_name'],data['max_permgen_size'])
        res = jbossCommand(data, cli)
        result.append(res)
        if data['jvm_options'] is not None:
            cli = "/host={}/server-config={}/jvm={}:add-jvm-option(jvm-option={})".format(data['host'],data['server_config_name'],data['jvm_name'],data['jvm_options'])
            res = jbossCommand(data, cli)
            result.append(res)
        cli = "reload --host={}".format(data['host'])
        res = jbossCommand(data, cli)
        result.append(res)
        meta = {"status": "OK", "response": res}
        else:
            hasChanged = False
            resp = "JVM {} already created".format(data['jvm_name'])
            meta = {"status" : "OK", "response" : resp}
    return isError, hasChanged, meta

def jvm_absent(data):
    created, result = isJvmAlreadyCreated(data)
    isError = False
    hasChanged = True
    meta = {}
    if not created:
        hasChanged = False
        resp = "JVM {} does not exist".format(data['jvm_name'])
        meta = {"status" : "OK", "response" : resp}
    else:
        cli = "/host={}/server-config={}/jvm={}:remove".format(data['host'],data['server_config_name'],data['jvm_name'])
        res = jbossCommand(data, cli)
        result.append(res)
        meta = {"status": "OK", "response": result}
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
        "server_config_name": {
            "required": True,
            "type": "str"
        },
        "jvm_name": {
            "required": True,
            "type": "str"
        },
        "heap_size": {
            "required": True,
            "type": "str"
        },
        "max_heap_size": {
            "required": True,
            "type": "str"
        },
        "permgen_size": {
            "required": True,
            "type": "str"
        },
        "max_permgen_size": {
            "required": True,
            "type": "str"
        },
        "jvm_options": {
            "required": False,
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
        "present": jvm_present,
        "absent": jvm_absent,
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
