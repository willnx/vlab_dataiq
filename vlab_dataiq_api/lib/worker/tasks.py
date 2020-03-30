# -*- coding: UTF-8 -*-
"""
Entry point logic for available backend worker tasks
"""
from celery import Celery
from vlab_api_common import get_task_logger

from vlab_dataiq_api.lib import const
from vlab_dataiq_api.lib.worker import vmware

app = Celery('dataiq', backend='rpc://', broker=const.VLAB_MESSAGE_BROKER)


@app.task(name='dataiq.show', bind=True)
def show(self, username, txn_id):
    """Obtain basic information about DataIQ

    :Returns: Dictionary

    :param username: The name of the user who wants info about their default gateway
    :type username: String

    :param txn_id: A unique string supplied by the client to track the call through logs
    :type txn_id: String
    """
    logger = get_task_logger(txn_id=txn_id, task_id=self.request.id, loglevel=const.VLAB_DATAIQ_LOG_LEVEL.upper())
    resp = {'content' : {}, 'error': None, 'params': {}}
    logger.info('Task starting')
    try:
        info = vmware.show_dataiq(username)
    except ValueError as doh:
        logger.error('Task failed: {}'.format(doh))
        resp['error'] = '{}'.format(doh)
    else:
        logger.info('Task complete')
        resp['content'] = info
    return resp


@app.task(name='dataiq.create', bind=True)
def create(self, username, machine_name, image, network,static_ip, default_gateway,
           netmask, dns, txn_id):
    """Deploy a new instance of DataIQ

    :Returns: Dictionary

    :param username: The name of the user who wants to create a new DataIQ
    :type username: String

    :param machine_name: The name of the new instance of DataIQ
    :type machine_name: String

    :param image: The image/version of DataIQ to create
    :type image: String

    :param network: The name of the network to connect the new DataIQ instance up to
    :type network: String

    :param static_ip: The IPv4 address to assign to the VM
    :type static_ip: String

    :param default_gateway: The IPv4 address of the network gateway
    :type default_gateway: String

    :param netmask: The subnet mask of the network, i.e. 255.255.255.0
    :type netmask: String

    :param dns: A list of DNS servers to use.
    :type dns: List

    :param txn_id: A unique string supplied by the client to track the call through logs
    :type txn_id: String
    """
    logger = get_task_logger(txn_id=txn_id, task_id=self.request.id, loglevel=const.VLAB_DATAIQ_LOG_LEVEL.upper())
    resp = {'content' : {}, 'error': None, 'params': {}}
    logger.info('Task starting')
    try:
        resp['content'] = vmware.create_dataiq(username,
                                               machine_name,
                                               image,
                                               network,
                                               static_ip,
                                               default_gateway,
                                               netmask,
                                               dns,
                                               logger)
    except ValueError as doh:
        logger.error('Task failed: {}'.format(doh))
        resp['error'] = '{}'.format(doh)
    logger.info('Task complete')
    return resp


@app.task(name='dataiq.delete', bind=True)
def delete(self, username, machine_name, txn_id):
    """Destroy an instance of DataIQ

    :Returns: Dictionary

    :param username: The name of the user who wants to delete an instance of DataIQ
    :type username: String

    :param machine_name: The name of the instance of DataIQ
    :type machine_name: String

    :param txn_id: A unique string supplied by the client to track the call through logs
    :type txn_id: String
    """
    logger = get_task_logger(txn_id=txn_id, task_id=self.request.id, loglevel=const.VLAB_DATAIQ_LOG_LEVEL.upper())
    resp = {'content' : {}, 'error': None, 'params': {}}
    logger.info('Task starting')
    try:
        vmware.delete_dataiq(username, machine_name, logger)
    except ValueError as doh:
        logger.error('Task failed: {}'.format(doh))
        resp['error'] = '{}'.format(doh)
    else:
        logger.info('Task complete')
    return resp


@app.task(name='dataiq.image', bind=True)
def image(self, txn_id):
    """Obtain a list of available images/versions of DataIQ that can be created

    :Returns: Dictionary

    :param txn_id: A unique string supplied by the client to track the call through logs
    :type txn_id: String
    """
    logger = get_task_logger(txn_id=txn_id, task_id=self.request.id, loglevel=const.VLAB_DATAIQ_LOG_LEVEL.upper())
    resp = {'content' : {}, 'error': None, 'params': {}}
    logger.info('Task starting')
    resp['content'] = {'image': vmware.list_images()}
    logger.info('Task complete')
    return resp
