# -*- coding: UTF-8 -*-
"""
Defines the RESTful API for deploying/managing a DataIQ instance
"""
import ujson
from flask import current_app
from flask_classy import request, route, Response
from vlab_inf_common.views import MachineView
from vlab_inf_common.vmware import vCenter, vim
from vlab_inf_common.input_validators import network_config_ok
from vlab_api_common import describe, get_logger, requires, validate_input


from vlab_dataiq_api.lib import const


logger = get_logger(__name__, loglevel=const.VLAB_DATAIQ_LOG_LEVEL)


class DataIQView(MachineView):
    """API end point for DataIQ"""
    route_base = '/api/2/inf/dataiq'
    RESOURCE = 'dataiq'
    POST_SCHEMA = { "$schema": "http://json-schema.org/draft-04/schema#",
                    "type": "object",
                    "description": "Create a dataiq",
                    "properties": {
                        "name": {
                            "description": "The name to give your DataIQ instance",
                            "type": "string"
                        },
                        "image": {
                            "description": "The image/version of DataIQ to create",
                            "type": "string"
                        },
                        "network": {
                            "description": "The network to hook the DataIQ instance up to",
                            "type": "string"
                        },
                        "static-ip": {
                            "description": "The IPv4 address to assign to the DataIQ machine",
                            "type": "string"
                        },
                        "default-gateway": {
                            "description": "The IPv4 address of the network default gateway",
                            "type": "string",
                            "default": "192.168.1.1"
                        },
                        "netmask":  {
                            "description": "The subnet mask for the network",
                            "type": "string",
                            "default": "255.255.255.0"
                        },
                        "dns": {
                            "description": "The IPv4 address(es) of DNS servers",
                            "type": "array",
                            "default": ["192.168.1.1"]
                        }
                    },
                    "required": ["name", "image", "network", "static-ip"]
                  }
    DELETE_SCHEMA = {"$schema": "http://json-schema.org/draft-04/schema#",
                     "description": "Destroy a DataIQ",
                     "type": "object",
                     "properties": {
                        "name": {
                            "description": "The name of the DataIQ instance to destroy",
                            "type": "string"
                        }
                     },
                     "required": ["name"]
                    }
    GET_SCHEMA = {"$schema": "http://json-schema.org/draft-04/schema#",
                  "description": "Display the DataIQ instances you own"
                 }
    IMAGES_SCHEMA = {"$schema": "http://json-schema.org/draft-04/schema#",
                     "description": "View available versions of DataIQ that can be created"
                    }


    @requires(verify=const.VLAB_VERIFY_TOKEN, version=2)
    @describe(post=POST_SCHEMA, delete=DELETE_SCHEMA, get=GET_SCHEMA)
    def get(self, *args, **kwargs):
        """Display the DataIQ instances you own"""
        username = kwargs['token']['username']
        resp_data = {'user' : username}
        txn_id = request.headers.get('X-REQUEST-ID', 'noId')
        task = current_app.celery_app.send_task('dataiq.show', [username, txn_id])
        resp_data['content'] = {'task-id': task.id}
        resp = Response(ujson.dumps(resp_data))
        resp.status_code = 202
        resp.headers.add('Link', '<{0}{1}/task/{2}>; rel=status'.format(const.VLAB_URL, self.route_base, task.id))
        return resp

    @requires(verify=const.VLAB_VERIFY_TOKEN, version=2)
    @validate_input(schema=POST_SCHEMA)
    def post(self, *args, **kwargs):
        """Create a DataIQ"""
        username = kwargs['token']['username']
        resp_data = {'user' : username}
        txn_id = request.headers.get('X-REQUEST-ID', 'noId')
        body = kwargs['body']
        machine_name = body['name']
        image = body['image']
        static_ip = body['static-ip']
        default_gateway = body.get('default-gateway', '192.168.1.1')
        netmask = body.get('netmask', '255.255.255.0')
        dns = body.get('dns', ['192.168.1.1'])
        network = '{}_{}'.format(username, body['network'])
        config_error = network_config_ok(ip=static_ip,
                                         gateway=default_gateway,
                                         netmask=netmask)
        if config_error:
            resp_data['error'] = config_error
            resp = Response(ujson.dumps(resp_data))
            resp.status_code = 400
        else:
            task = current_app.celery_app.send_task('dataiq.create', [username,
                                                                      machine_name,
                                                                      image,
                                                                      network,
                                                                      static_ip,
                                                                      default_gateway,
                                                                      netmask,
                                                                      dns,
                                                                      txn_id])
            resp_data['content'] = {'task-id': task.id}
            resp = Response(ujson.dumps(resp_data))
            resp.status_code = 202
            resp.headers.add('Link', '<{0}{1}/task/{2}>; rel=status'.format(const.VLAB_URL, self.route_base, task.id))
        return resp

    @requires(verify=const.VLAB_VERIFY_TOKEN, version=2)
    @validate_input(schema=DELETE_SCHEMA)
    def delete(self, *args, **kwargs):
        """Destroy a DataIQ"""
        username = kwargs['token']['username']
        txn_id = request.headers.get('X-REQUEST-ID', 'noId')
        resp_data = {'user' : username}
        machine_name = kwargs['body']['name']
        task = current_app.celery_app.send_task('dataiq.delete', [username, machine_name, txn_id])
        resp_data['content'] = {'task-id': task.id}
        resp = Response(ujson.dumps(resp_data))
        resp.status_code = 202
        resp.headers.add('Link', '<{0}{1}/task/{2}>; rel=status'.format(const.VLAB_URL, self.route_base, task.id))
        return resp

    @route('/image', methods=["GET"])
    @requires(verify=const.VLAB_VERIFY_TOKEN, version=2)
    @describe(get=IMAGES_SCHEMA)
    def image(self, *args, **kwargs):
        """Show available versions of DataIQ that can be deployed"""
        username = kwargs['token']['username']
        txn_id = request.headers.get('X-REQUEST-ID', 'noId')
        resp_data = {'user' : username}
        task = current_app.celery_app.send_task('dataiq.image', [txn_id])
        resp_data['content'] = {'task-id': task.id}
        resp = Response(ujson.dumps(resp_data))
        resp.status_code = 202
        resp.headers.add('Link', '<{0}{1}/task/{2}>; rel=status'.format(const.VLAB_URL, self.route_base, task.id))
        return resp
