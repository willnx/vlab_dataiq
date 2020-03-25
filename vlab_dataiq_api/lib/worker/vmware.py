# -*- coding: UTF-8 -*-
"""Business logic for backend worker tasks"""
import time
import random
import os.path

import requests
from vlab_inf_common.vmware import vCenter, Ova, vim, virtual_machine, consume_task

from vlab_dataiq_api.lib import const


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


def create_dataiq(username, machine_name, image, network, logger):
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

    :param logger: An object for logging messages
    :type logger: logging.LoggerAdapter
    """
    install_script = _get_install_script(image)
    with vCenter(host=const.INF_VCENTER_SERVER, user=const.INF_VCENTER_USER,
                 password=const.INF_VCENTER_PASSWORD) as vcenter:
        image_name = '{}/{}'.format(const.VLAB_DATAIQ_IMAGES_DIR, const.VLAB_DATAIQ_BASE_OVA)
        logger.info(image_name)
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

        _upload_install_script(vcenter, the_vm, install_script)
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
            return script
    else:
        raise ValueError('Supplied version {} does not exist'.format(image))


def _upload_install_script(vcenter, the_vm, install_script):
    """Copy the DataIQ install script onto the newly deployed virtual machine.
    Works even if the machine has no external network configured.

    :Returns: None

    :param vcenter: The instantiated connection to vCenter
    :type vcenter: vlab_inf_common.vmware.vCenter

    :param the_vm: The new DataIQ machine
    :type the_vm: vim.VirtualMachine
    """
    with open(install_script) as the_file:
        script_in_ram = the_file.read()

    creds = vim.vm.guest.NamePasswordAuthentication(username=const.VLAB_DATAIQ_ADMIN,
                                                     password=const.VLAB_DATAIQ_ADMIN_PW)
    file_attribute = vim.vm.guest.FileManager.FileAttributes()
    url = vcenter.content.guestOperationsManager.fileManager.InitiateFileTransferToGuest(vm=the_vm,
                                                                                         auth=creds,
                                                                                         guestFilePath='/home/administrator/{}'.format(install_script),
                                                                                         fileAttributes=file_attribute,
                                                                                         fileSize=len(script_in_ram),
                                                                                         overwrite=True)
    resp = requests.put(url, data=script_in_ram, verify=False)
    resp.raise_for_status()
