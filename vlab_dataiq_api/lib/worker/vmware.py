# -*- coding: UTF-8 -*-
"""Business logic for backend worker tasks"""
import time
import random
import os.path

import requests
from urllib3.exceptions import InsecureRequestWarning
from vlab_inf_common.vmware import vCenter, Ova, vim, virtual_machine, consume_task

from vlab_dataiq_api.lib import const

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


def show_dataiq(username):
    """Obtain basic information about DataIQ

    :Returns: Dictionary

    :param username: The user requesting info about their DataIQ
    :type username: String
    """
    info = {}
    with vCenter(host=const.INF_VCENTER_SERVER, user=const.INF_VCENTER_USER, \
                 password=const.INF_VCENTER_PASSWORD) as vcenter:
        folder = vcenter.get_by_name(name=username, vimtype=vim.Folder)
        dataiq_vms = {}
        for vm in folder.childEntity:
            info = virtual_machine.get_info(vcenter, vm, username)
            if info['meta']['component'] == 'DataIQ':
                dataiq_vms[vm.name] = info
    return dataiq_vms


def delete_dataiq(username, machine_name, logger):
    """Unregister and destroy a user's DataIQ

    :Returns: None

    :param username: The user who wants to delete their jumpbox
    :type username: String

    :param machine_name: The name of the VM to delete
    :type machine_name: String

    :param logger: An object for logging messages
    :type logger: logging.LoggerAdapter
    """
    with vCenter(host=const.INF_VCENTER_SERVER, user=const.INF_VCENTER_USER, \
                 password=const.INF_VCENTER_PASSWORD) as vcenter:
        folder = vcenter.get_by_name(name=username, vimtype=vim.Folder)
        for entity in folder.childEntity:
            if entity.name == machine_name:
                info = virtual_machine.get_info(vcenter, entity, username)
                if info['meta']['component'] == 'DataIQ':
                    logger.debug('powering off VM')
                    virtual_machine.power(entity, state='off')
                    delete_task = entity.Destroy_Task()
                    logger.debug('blocking while VM is being destroyed')
                    consume_task(delete_task)
                    break
        else:
            raise ValueError('No {} named {} found'.format('dataiq', machine_name))


def create_dataiq(username, machine_name, image, network, static_ip,
                  default_gateway, netmask, dns,logger):
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

    :param logger: An object for logging messages
    :type logger: logging.LoggerAdapter
    """
    install_script = _get_install_script(image)
    with vCenter(host=const.INF_VCENTER_SERVER, user=const.INF_VCENTER_USER,
                 password=const.INF_VCENTER_PASSWORD) as vcenter:
        image_name = '{}/{}'.format(const.VLAB_DATAIQ_IMAGES_DIR, const.VLAB_DATAIQ_BASE_OVA)
        logger.info(image)
        ova = Ova(os.path.join(const.VLAB_DATAIQ_IMAGES_DIR, image_name))
        try:
            network_map = vim.OvfManager.NetworkMapping()
            network_map.name = ova.networks[0]
            try:
                network_map.network = vcenter.networks[network]
            except KeyError:
                raise ValueError('No such network named {}'.format(network))
            the_vm = virtual_machine.deploy_from_ova(vcenter, ova, [network_map],
                                                     username, machine_name, logger)
        finally:
            ova.close()

        _upload_install_script(vcenter, the_vm, install_script, logger)
        _config_network(vcenter, the_vm, static_ip, default_gateway, netmask, dns, logger)
        meta_data = {'component' : "DataIQ",
                     'created' : time.time(),
                     'version' : image,
                     'configured' : False,
                     'generation' : 1}
        virtual_machine.set_meta(the_vm, meta_data)
        info = virtual_machine.get_info(vcenter, the_vm, username, ensure_ip=True)
        return  {the_vm.name: info}


def list_images():
    """Obtain a list of available versions of DataIQ that can be created

    :Returns: List
    """
    images = [x for x in os.listdir(const.VLAB_DATAIQ_IMAGES_DIR) if not x.endswith('.ova')]
    images = [convert_name(x) for x in images]
    return images


def convert_name(name):
    """This function centralizes converting between the name of the OVA, and the
    version of software it contains.

    The DataIQ install script is named like this: dataiq_installer_1.0.0.10_202003090706_v1.sh
    The specific version is 1.0.0

    :param name: The name of the install script
    :type name: String
    """
    try:
        version = name.split('_')[2]
        if version.count('.') == 3:
            # the build number is in the version string...
            version = '.'.join(version.split('.')[:-1])
    except IndexError:
        raise ValueError('Unexpected DataIQ install script name: {}'.format(name))
    return version


def _get_install_script(image):
    """Locate the install script to copy onto the new DataIQ instance. If the
    supplied image/version does not exist, a ValueError is raised.

    :Returns: String

    :Raises: ValueError

    :param image: The image/version of DataIQ to create
    :type image: String
    """
    all_scripts = [x for x in os.listdir(const.VLAB_DATAIQ_IMAGES_DIR) if not x.endswith('.ova')]
    for script in all_scripts:
        if image ==  convert_name(script):
            return '{}/{}'.format(const.VLAB_DATAIQ_IMAGES_DIR, script)
    else:
        raise ValueError('Supplied version {} does not exist'.format(image))


def _upload_install_script(vcenter, the_vm, install_script, logger):
    """Copy the DataIQ install script onto the newly deployed virtual machine.
    Works even if the machine has no external network configured.

    :Returns: None

    :param vcenter: The instantiated connection to vCenter
    :type vcenter: vlab_inf_common.vmware.vCenter

    :param the_vm: The new DataIQ machine
    :type the_vm: vim.VirtualMachine

    :param logger: An object for logging messages
    :type logger: logging.LoggerAdapter
    """
    logger.info("Uploading install script %s", install_script)
    logger.debug("Reading file contents")
    with open(install_script, 'rb') as the_file:
        file_size = len(the_file.read())
        the_file.seek(0)

        logger.debug("Generating creds")
        creds = vim.vm.guest.NamePasswordAuthentication(username=const.VLAB_DATAIQ_ADMIN,
                                                         password=const.VLAB_DATAIQ_ADMIN_PW)
        logger.debug("Creating file attributes object")
        file_attributes = vim.vm.guest.FileManager.FileAttributes()
        logger.debug("Obtaining URL for uploading script to new VM")
        upload_path = '/home/administrator/{}'.format(os.path.basename(install_script))
        logger.info('Uploading script to: %s', upload_path)
        logger.debug('Uploading %s bytes', file_size)
        url = _get_upload_url(vcenter=vcenter,
                              the_vm=the_vm,
                              creds=creds,
                              upload_path=upload_path,
                              file_attributes=file_attributes,
                              file_size=file_size)
        logger.info('Uploading to URL %s', url)
        resp = requests.put(url, data=the_file, verify=False)
        resp.raise_for_status()



def _get_upload_url(vcenter, the_vm, creds, upload_path, file_size, file_attributes, overwrite=True):
    """Mostly to deal with race between the VM power on, and all of VMwareTools being ready.

    :Returns: String

    :param vcenter: The instantiated connection to vCenter
    :type vcenter: vlab_inf_common.vmware.vCenter

    :param the_vm: The new DataIQ machine
    :type the_vm: vim.VirtualMachine

    :param creds: The username & password to use when logging into the new VM
    :type creds: vim.vm.guest.NamePasswordAuthentication

    :param file_attributes: BS that pyVmomi requires...
    :type file_attributes: vim.vm.guest.FileManager.FileAttributes

    :param file_size: How many bytes are going to be uploaded
    :type file_size: Integer

    :param overwrite: If the file already exists, write over the existing content.
    :type overwrite: Boolean
    """
    # The VM just booted, this service can take some time to be ready
    for retry_sleep in range(10):
        try:
            url = vcenter.content.guestOperationsManager.fileManager.InitiateFileTransferToGuest(vm=the_vm,
                                                                                                 auth=creds,
                                                                                                 guestFilePath=upload_path,
                                                                                                 fileAttributes=file_attributes,
                                                                                                 fileSize=file_size,
                                                                                                 overwrite=overwrite)
        except vim.fault.GuestOperationsUnavailable:
            time.sleep(retry_sleep)
        else:
            return url
    else:
        error = 'Unable to upload DataIQ install script. Timed out waiting on GuestOperations to become available.'
        raise ValueError(error)


def _config_network(vcenter, the_vm, static_ip, default_gateway, netmask, dns, logger):
    """Configure the statis network on the VM

    :Raises RuntimeError

    :param vcenter: The instantiated connection to vCenter
    :type vcenter: vlab_inf_common.vmware.vCenter

    :param the_vm: The new DataIQ machine
    :type the_vm: vim.VirtualMachine

    :param static_ip: The IPv4 address to assign to the VM
    :type static_ip: String

    :param default_gateway: The IPv4 address of the network gateway
    :type default_gateway: String

    :param netmask: The subnet mask of the network, i.e. 255.255.255.0
    :type netmask: String

    :param dns: A list of DNS servers to use.
    :type dns: List

    :param logger: An object for logging messages
    :type logger: logging.LoggerAdapter
    """
    nic_config_file = '/etc/sysconfig/network-scripts/ifcfg-ens192'
    cmd = '/usr/bin/echo'
    addr_args = 'IPADDR={} >> {}'.format(static_ip, nic_config_file)
    gateway_args = 'GATEWAY={} >> {}'.format(default_gateway, nic_config_file)
    netmask_args = 'NETMASK={} >> {}'.format(netmask, nic_config_file)

    _run_cmd(vcenter, the_vm, cmd, addr_args, logger)
    _run_cmd(vcenter, the_vm, cmd, gateway_args, logger)
    _run_cmd(vcenter, the_vm, cmd, netmask_args, logger)
    _add_dns(vcenter, the_vm, dns, nic_config_file, logger)
    _run_cmd(vcenter, the_vm, '/bin/systemctl', 'restart network', logger)
    _run_cmd(vcenter, the_vm, '/usr/bin/hostnamectl', 'set-hostname {}'.format(the_vm.name), logger)


def _add_dns(vcenter, the_vm, dns, nic_config_file, logger):
    cmd = '/usr/bin/echo'
    for idx, dns_server in enumerate(dns):
        args = 'DNS{}={} >> {}'.format(idx, dns_server, nic_config_file)
        _run_cmd(vcenter, the_vm, cmd, args, logger)


def _run_cmd(vcenter, the_vm, cmd, args, logger):
    shell = '/usr/bin/bash'
    the_args = "-c '{} {}'".format(cmd, args)
    result = virtual_machine.run_command(vcenter,
                                         the_vm,
                                         shell,
                                         user=const.VLAB_DATAIQ_ADMIN,
                                         password=const.VLAB_DATAIQ_ADMIN_PW,
                                         arguments=the_args)
    if result.exitCode:
        logger.error("failed to execute: {} {}".format(shell, the_args))
