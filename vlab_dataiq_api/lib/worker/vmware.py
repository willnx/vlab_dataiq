# -*- coding: UTF-8 -*-
"""Business logic for backend worker tasks"""
import time
import random
import os.path
import textwrap
from io import BytesIO

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
                  default_gateway, netmask, dns, disk_size, cpu_count, ram, logger):
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

    :param disk_size: The number of GB to allocate for the DataIQ database
    :type disk_size: Integer

    :param cpu_count: Thenumber of CPU cores to allocate to the DataIQ machine
    :type cpu_count: Integer

    :param ram: The number of GB of RAM to allocate to the VM
    :type ram: Integer

    :param logger: An object for logging messages
    :type logger: logging.LoggerAdapter
    """
    with vCenter(host=const.INF_VCENTER_SERVER, user=const.INF_VCENTER_USER,
                 password=const.INF_VCENTER_PASSWORD) as vcenter:
        image_name = convert_name(image)
        logger.info(image)
        ova = Ova(os.path.join(const.VLAB_DATAIQ_IMAGES_DIR, image_name))
        try:
            network_map = vim.OvfManager.NetworkMapping()
            network_map.name = ova.networks[0]
            try:
                network_map.network = vcenter.networks[network]
            except KeyError:
                raise ValueError('No such network named {}'.format(network))
            the_vm = virtual_machine.deploy_from_ova(vcenter=vcenter,
                                                     ova=ova,
                                                     network_map=[network_map],
                                                     username=username,
                                                     machine_name=machine_name,
                                                     logger=logger,
                                                     power_on=False)
        finally:
            ova.close()
        mb_of_ram = ram * 1024
        virtual_machine.adjust_ram(the_vm, mb_of_ram)
        virtual_machine.adjust_cpu(the_vm, cpu_count)
        virtual_machine.power(the_vm, state='on')
        meta_data = {'component' : "DataIQ",
                     'created' : time.time(),
                     'version' : image,
                     'configured' : False,
                     'generation' : 1}
        virtual_machine.set_meta(the_vm, meta_data)
        logger.info("Adding DB VMDK")
        _add_database_disk(the_vm, disk_size)
        logger.info("Configuring network")
        _config_network(vcenter, the_vm, static_ip, default_gateway, netmask, dns, logger)
        logger.info("Adding GUI")
        _add_gui(vcenter, the_vm, logger)
        logger.info("Acquiring machine info")
        info = virtual_machine.get_info(vcenter, the_vm, username, ensure_ip=True)
        return  {the_vm.name: info}


def list_images():
    """Obtain a list of available versions of DataIQ that can be created

    :Returns: List
    """
    images = os.listdir(const.VLAB_DATAIQ_IMAGES_DIR)
    images = [convert_name(x, to_version=True) for x in images]
    return images


def convert_name(name, to_version=False):
    """This function centralizes converting between the name of the OVA, and the
    version of software it contains.

    The DataIQ install script is named like this: dataiq_installer_1.0.0.10_202003090706_v1.sh
    The specific version is 1.0.0

    :param name: The name of the install script
    :type name: String

    :param to_version: Set to True to covert the name of an OVA to the version
    :type to_version: Boolean
    """
    if to_version:
        return name.split('-')[-1].replace('.ova', '')
    else:
        return 'dataiq-{}.ova'.format(name)


def _config_network(vcenter, the_vm, static_ip, default_gateway, netmask, dns, logger):
    """Configure the statis network on the VM

    :Returns: None

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
    nic_config_file = '/etc/sysconfig/network-scripts/ifcfg-eth0'
    cmd = '/bin/echo'
    config = """\
    TYPE=Ethernet
    ONBOOT=yes
    BOOTPROTO=static
    DEFROUTE=yes
    NAME=eth0
    DEVICE=eth0
    IPADDR={}
    GATEWAY={}
    NETMASK={}
    """.format(static_ip, default_gateway, netmask)
    nic_config = '{}\n{}'.format(textwrap.dedent(config), _format_dns(dns))
    _upload_nic_config(vcenter, the_vm, nic_config, os.path.basename(nic_config_file), logger)

    _run_cmd(vcenter, the_vm, '/bin/mv', '-f /home/administrator/{} {}'.format(os.path.basename(nic_config_file), nic_config_file), logger)
    _run_cmd(vcenter, the_vm, '/bin/systemctl', 'restart network', logger)
    _run_cmd(vcenter, the_vm, '/bin/hostnamectl', 'set-hostname {}'.format(the_vm.name), logger)


def _format_dns(dns):
    """Create the DNS section of the NIC config file.

    :Returns: String

    :param dns: A list of DNS servers to use.
    :type dns: List
    """
    tmp = []
    for idx, dns_server in enumerate(dns):
        server_num = idx + 1
        dns_config = 'DNS{}={}'.format(server_num, dns_server)
        tmp.append(dns_config)
    return '\n'.join(tmp)


def _run_cmd(vcenter, the_vm, cmd, args, logger, timeout=600, one_shot=False):
    shell = '/bin/bash'
    the_args = "-c '/bin/echo {} | /bin/sudo -S {} {}'".format(const.VLAB_DATAIQ_ADMIN_PW, cmd, args)
    result = virtual_machine.run_command(vcenter,
                                         the_vm,
                                         shell,
                                         user=const.VLAB_DATAIQ_ADMIN,
                                         password=const.VLAB_DATAIQ_ADMIN_PW,
                                         arguments=the_args,
                                         timeout=timeout,
                                         one_shot=one_shot,
                                         init_timeout=1200)
    if result.exitCode:
        logger.error("failed to execute: {} {}".format(shell, the_args))


def _upload_nic_config(vcenter, the_vm, nic_config, config_name, logger):
    """Upload the NIC config file to the new DataIQ machine. Works even if the
    machine has no external network configured.

    :Returns: None

    :param vcenter: The instantiated connection to vCenter
    :type vcenter: vlab_inf_common.vmware.vCenter

    :param the_vm: The new DataIQ machine
    :type the_vm: vim.VirtualMachine

    :param nic_config: The network configuration file contents
    :param nic_config: String

    :param config_name: The name of the config file
    :type config_name: String

    :param logger: An object for logging messages
    :type logger: logging.LoggerAdapter
    """
    nic_config_bytes = nic_config.encode()
    file_size = len(nic_config_bytes)
    logger.debug("Generating creds")
    creds = vim.vm.guest.NamePasswordAuthentication(username=const.VLAB_DATAIQ_ADMIN,
                                                     password=const.VLAB_DATAIQ_ADMIN_PW)
    logger.debug("Creating file attributes object")
    file_attributes = vim.vm.guest.FileManager.FileAttributes()
    logger.debug("Obtaining URL for uploading NIC config to new VM")
    upload_path = '/home/administrator/{}'.format(config_name)
    logger.info('Uploading NIC config: %s', upload_path)
    logger.debug('Uploading %s bytes', file_size)
    url = _get_upload_url(vcenter=vcenter,
                          the_vm=the_vm,
                          creds=creds,
                          upload_path=upload_path,
                          file_attributes=file_attributes,
                          file_size=file_size)
    logger.info('Uploading to URL %s', url)
    resp = requests.put(url, data=BytesIO(nic_config_bytes), verify=False)
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


def _add_database_disk(the_vm, disk_size):
    """Add a VMDK to the new DataIQ instance to store it's database.

    :Returns: None

    :Rasies: RuntimeError

    :param the_vm: The new DataIQ machine
    :type the_vm: vim.VirtualMachine

    :param disk_size: The number of GB to make the disk
    :type disk_size: Integer
    """
    spec = vim.vm.ConfigSpec()
    unit_number = 0
    for dev in the_vm.config.hardware.device:
        if hasattr(dev.backing, 'fileName'):
            unit_number = int(dev.unitNumber) + 1
            # unitNumber 7 is reserved for the SCSI controller
            if unit_number == 7:
                unit_number += 1
            if unit_number >= 16:
                raise RuntimeError('VM cannot have 16 VMDKs')
    if unit_number == 0:
        raise RuntimeError('Unable to find any VMDKs for VM')

    dev_changes = []
    disk_spec = vim.vm.device.VirtualDeviceSpec()
    disk_spec.fileOperation = "create"
    disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    disk_spec.device = vim.vm.device.VirtualDisk()
    disk_spec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
    disk_spec.device.backing.thinProvisioned = True
    disk_spec.device.backing.diskMode = 'persistent'
    disk_spec.device.unitNumber = unit_number
    disk_spec.device.capacityInKB = int(disk_size) * 1024 * 1024
    disk_spec.device.controllerKey = 1000
    dev_changes.append(disk_spec)
    spec.deviceChange = dev_changes
    consume_task(the_vm.ReconfigVM_Task(spec=spec))

def _add_gui(vcenter, the_vm, logger):
    """Adds a GUI and RDP to the DataIQ machine

    :Returns: None

    :param vcenter: The instantiated connection to vCenter
    :type vcenter: vlab_inf_common.vmware.vCenter

    :param the_vm: The new DataIQ machine
    :type the_vm: vim.VirtualMachine

    :param logger: An object for logging messages
    :type logger: logging.LoggerAdapter
    """
    cmd = '/bin/echo {} | sudo -S'.format(const.VLAB_DATAIQ_ADMIN_PW)
    args1 = 'yum -y groupinstall "GNOME Desktop" "Graphical Administration Tools"'
    args2 = 'ln -sf /lib/systemd/system/runlevel5.target /etc/systemd/system/default.target'
    args3 = 'yum -y install epel-release'
    args4 = 'systemctl disable libvirtd'

    _handle_gui(vcenter, the_vm, cmd, args1, logger)

    most_args = [args2, args3, args4]
    for arg in most_args:
        logger.debug("Running: %s", arg)
        _run_cmd(vcenter, the_vm, cmd, arg, logger, timeout=1800)

    logger.info("Rebooting machine to enable GUI")
    _run_cmd(vcenter, the_vm, 'reboot', '', logger, one_shot=True)
    logger.info("Waiting 60 seconds for the machine to shutdown")
    time.sleep(60)

    rdp_args1 = 'yum -y install xrdp tigervnc-server'
    rdp_args2 = 'systemctl enable xrdp'
    rdp_args3 = 'systemctl start xrdp'
    rdp_args4 = 'firewall-cmd --permanent --add-port=3389/tcp'
    rdp_args5 = 'firewall-cmd --reload'
    rdp_args6 = 'chcon --type=bin_t /usr/sbin/xrdp'
    rdp_args7 = 'chcon --type=bin_t /usr/sbin/xrdp-sesman'
    rdp_args = [rdp_args1, rdp_args2, rdp_args3, rdp_args4, rdp_args5, rdp_args6, rdp_args7]
    logger.info("Adding RDP server")
    for rdp_arg in rdp_args:
        logger.debug("Running: %s", rdp_arg)
        _run_cmd(vcenter, the_vm, cmd, rdp_arg, logger, timeout=1800)


def _handle_gui(vcenter, the_vm, cmd, arg, logger):
    """No clue why, but PyVmomi poops the bed and loses the PID when installing
    the GUI. So manually check if the group got installed...
    """
    try:
        _run_cmd(vcenter, the_vm, cmd, arg, logger, timeout=1800)
    except IndexError:
        pass

    check_gnome = 'group list ids | grep "Installed Environment" | grep "GNOME Desktop"'
    check_admin_tools = 'group list ids | grep "Installed Groups" | grep "Graphfical Administration Tools"'
    _run_cmd(vcenter, the_vm, '/bin/yum', check_gnome, logger)
    _run_cmd(vcenter, the_vm, '/bin/yum', check_admin_tools, logger)
