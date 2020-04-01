# -*- coding: UTF-8 -*-
from pexpect import pxssh

from vlab_dataiq_api.lib import const


def configure_new_server(gateway_ip, ssh_port, logger):
    """
    :Returns: None or String
    """
    shell = pxssh.pxssh()
    shell.login(hostname=gateway_ip,
                username=const.VLAB_DATAIQ_ADMIN,
                password=const.VLAB_DATAIQ_ADMIN_PW,
                port=ssh_port)
    logger.info("Successfully connected to DataIQ via SSH")
    shell.sendline('/usr/bin/bash /home/administrator/dataiq_installer*.sh')
