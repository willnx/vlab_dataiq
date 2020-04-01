# -*- coding: UTF-8 -*-
"""
A suite of tests for the functions in vmware.py
"""
import builtins
import unittest
from unittest.mock import patch, MagicMock

from vlab_dataiq_api.lib.worker import vmware


class TestVMware(unittest.TestCase):
    """A set of test cases for the vmware.py module"""

    @patch.object(vmware.virtual_machine, 'get_info')
    @patch.object(vmware, 'consume_task')
    @patch.object(vmware, 'vCenter')
    def test_show_dataiq(self, fake_vCenter, fake_consume_task, fake_get_info):
        """``dataiq`` returns a dictionary when everything works as expected"""
        fake_vm = MagicMock()
        fake_vm.name = 'DataIQ'
        fake_folder = MagicMock()
        fake_folder.childEntity = [fake_vm]
        fake_vCenter.return_value.__enter__.return_value.get_by_name.return_value = fake_folder
        fake_get_info.return_value = {'meta': {'component': 'DataIQ',
                                               'created': 1234,
                                               'version': '1.0',
                                               'configured': False,
                                               'generation': 1}}

        output = vmware.show_dataiq(username='alice')
        expected = {'DataIQ': {'meta': {'component': 'DataIQ',
                                                             'created': 1234,
                                                             'version': '1.0',
                                                             'configured': False,
                                                             'generation': 1}}}
        self.assertEqual(output, expected)

    @patch.object(vmware.virtual_machine, 'get_info')
    @patch.object(vmware.virtual_machine, 'power')
    @patch.object(vmware, 'consume_task')
    @patch.object(vmware, 'vCenter')
    def test_delete_dataiq(self, fake_vCenter, fake_consume_task, fake_power, fake_get_info):
        """``delete_dataiq`` returns None when everything works as expected"""
        fake_logger = MagicMock()
        fake_vm = MagicMock()
        fake_vm.name = 'DataIQBox'
        fake_folder = MagicMock()
        fake_folder.childEntity = [fake_vm]
        fake_vCenter.return_value.__enter__.return_value.get_by_name.return_value = fake_folder
        fake_get_info.return_value = {'meta': {'component': 'DataIQ',
                                               'created': 1234,
                                               'version': '1.0',
                                               'configured': False,
                                               'generation': 1}}

        output = vmware.delete_dataiq(username='bob', machine_name='DataIQBox', logger=fake_logger)
        expected = None

        self.assertEqual(output, expected)

    @patch.object(vmware.virtual_machine, 'get_info')
    @patch.object(vmware.virtual_machine, 'power')
    @patch.object(vmware, 'consume_task')
    @patch.object(vmware, 'vCenter')
    def test_delete_dataiq_value_error(self, fake_vCenter, fake_consume_task, fake_power, fake_get_info):
        """``delete_dataiq`` raises ValueError when unable to find requested vm for deletion"""
        fake_logger = MagicMock()
        fake_vm = MagicMock()
        fake_vm.name = 'win10'
        fake_folder = MagicMock()
        fake_folder.childEntity = [fake_vm]
        fake_vCenter.return_value.__enter__.return_value.get_by_name.return_value = fake_folder
        fake_get_info.return_value = {'meta': {'component': 'DataIQ',
                                               'created': 1234,
                                               'version': '1.0',
                                               'configured': False,
                                               'generation': 1}}

        with self.assertRaises(ValueError):
            vmware.delete_dataiq(username='bob', machine_name='myOtherDataIQBox', logger=fake_logger)

    @patch.object(vmware, '_add_gui')
    @patch.object(vmware, '_config_network')
    @patch.object(vmware.virtual_machine, 'adjust_ram')
    @patch.object(vmware.virtual_machine, 'adjust_cpu')
    @patch.object(vmware, '_add_database_disk')
    @patch.object(vmware.virtual_machine, 'set_meta')
    @patch.object(vmware, 'Ova')
    @patch.object(vmware.virtual_machine, 'get_info')
    @patch.object(vmware.virtual_machine, 'deploy_from_ova')
    @patch.object(vmware, 'consume_task')
    @patch.object(vmware, 'vCenter')
    def test_create_dataiq(self, fake_vCenter, fake_consume_task, fake_deploy_from_ova,
                           fake_get_info, fake_Ova, fake_set_meta, fake_add_database_disk,
                           fake_adjust_cpu, fake_adjust_ram, fake_config_network,
                           fake_add_gui):
        """``create_dataiq`` returns a dictionary upon success"""
        fake_logger = MagicMock()
        fake_deploy_from_ova.return_value.name = 'myDataIQ'
        fake_get_info.return_value = {'worked': True}
        fake_Ova.return_value.networks = ['someLAN']
        fake_vCenter.return_value.__enter__.return_value.networks = {'someLAN' : vmware.vim.Network(moId='1')}


        output = vmware.create_dataiq(username='alice',
                                       machine_name='DataIQBox',
                                       image='1.0.0',
                                       network='someLAN',
                                       static_ip='10.7.7.2',
                                       default_gateway='10.7.7.1',
                                       netmask='255.255.255.0',
                                       dns=['10.7.7.1'],
                                       disk_size=250,
                                       cpu_count=4,
                                       ram=32,
                                       logger=fake_logger)
        expected = {'myDataIQ': {'worked': True}}

        self.assertEqual(output, expected)

    @patch.object(vmware, '_add_database_disk')
    @patch.object(vmware, 'Ova')
    @patch.object(vmware.virtual_machine, 'get_info')
    @patch.object(vmware.virtual_machine, 'deploy_from_ova')
    @patch.object(vmware, 'consume_task')
    @patch.object(vmware, 'vCenter')
    def test_create_dataiq_invalid_network(self, fake_vCenter, fake_consume_task,
                                           fake_deploy_from_ova, fake_get_info, fake_Ova,
                                           fake_add_database_disk):
        """``create_dataiq`` raises ValueError if supplied with a non-existing network"""
        fake_logger = MagicMock()
        fake_get_info.return_value = {'worked': True}
        fake_Ova.return_value.networks = ['someLAN']
        fake_vCenter.return_value.__enter__.return_value.networks = {'someLAN' : vmware.vim.Network(moId='1')}

        with self.assertRaises(ValueError):
            vmware.create_dataiq(username='alice',
                                  machine_name='DataIQBox',
                                  image='1.0.0',
                                  network='someOtherLAN',
                                  static_ip='10.7.7.2',
                                  default_gateway='10.7.7.1',
                                  netmask='255.255.255.0',
                                  dns=['10.7.7.1'],
                                  disk_size=250,
                                  cpu_count=4,
                                  ram=32,
                                  logger=fake_logger)

    @patch.object(vmware.os, 'listdir')
    def test_list_images(self, fake_listdir):
        """``list_images`` - Returns a list of available DataIQ versions that can be deployed"""
        fake_listdir.return_value = ['dataiq-1.0.0.ova']

        output = vmware.list_images()
        expected = ['1.0.0']

        # set() avoids ordering issue in test
        self.assertEqual(set(output), set(expected))

    def test_convert_name(self):
        """``convert_name`` - converts the install script name to a version"""
        output = vmware.convert_name(name='1.0.0')
        expected = 'dataiq-1.0.0.ova'

        self.assertEqual(output, expected)

    def test_convert_name_to_version(self):
        """``convert_name`` - converts the install script name to a version"""
        output = vmware.convert_name(name='dataiq-1.0.0.ova', to_version=True)
        expected = '1.0.0'

        self.assertEqual(output, expected)

    @patch.object(vmware, '_upload_nic_config')
    @patch.object(vmware, '_run_cmd')
    def test_config_network(self, fake_run_cmd, fake_upload_nic_config):
        """``_config_network`` calls ``_upload_nic_config`` to edit the network file"""
        fake_vcenter = MagicMock()
        fake_the_vm = MagicMock()
        fake_static_ip = '192.168.1.6'
        fake_default_gateway = '192.168.1.1'
        fake_netmask = '255.255.255.0'
        fake_dns = ['192.168.1.1']
        fake_logger = MagicMock()

        vmware._config_network(fake_vcenter,
                               fake_the_vm,
                               fake_static_ip,
                               fake_default_gateway,
                               fake_netmask,
                               fake_dns,
                               fake_logger)

        self.assertTrue(fake_upload_nic_config.called)

    @patch.object(vmware, '_upload_nic_config')
    @patch.object(vmware, '_run_cmd')
    def test_config_network_overwrites(self, fake_run_cmd, fake__upload_nic_config):
        """``_config_network`` overwrites the config file"""
        fake_vcenter = MagicMock()
        fake_the_vm = MagicMock()
        fake_static_ip = '192.168.1.6'
        fake_default_gateway = '192.168.1.1'
        fake_netmask = '255.255.255.0'
        fake_dns = ['192.168.1.1']
        fake_logger = MagicMock()

        vmware._config_network(fake_vcenter,
                               fake_the_vm,
                               fake_static_ip,
                               fake_default_gateway,
                               fake_netmask,
                               fake_dns,
                               fake_logger)

        command_args = fake_run_cmd.call_args_list[0][0][-2]
        expected = '-f /home/administrator/ifcfg-eth0 /etc/sysconfig/network-scripts/ifcfg-eth0'

        self.assertEqual(command_args, expected)

    @patch.object(vmware, '_upload_nic_config')
    @patch.object(vmware, '_run_cmd')
    def test_config_network_restarts_network(self, fake_run_cmd, fake_upload_nic_config):
        """``_config_network`` restarts the network after configuring it"""
        fake_vcenter = MagicMock()
        fake_the_vm = MagicMock()
        fake_static_ip = '192.168.1.6'
        fake_default_gateway = '192.168.1.1'
        fake_netmask = '255.255.255.0'
        fake_dns = ['192.168.1.1']
        fake_logger = MagicMock()

        vmware._config_network(fake_vcenter,
                               fake_the_vm,
                               fake_static_ip,
                               fake_default_gateway,
                               fake_netmask,
                               fake_dns,
                               fake_logger)

        command_args = fake_run_cmd.call_args_list[-2][0][-2]
        expected = 'restart network'

        self.assertEqual(command_args, expected)

    @patch.object(vmware, 'consume_task')
    def test_add_database_disk(self, fake_consume_task):
        """``_add_database_disk`` Blocks on adding an extra VMDK to the DataIQ machine"""
        fake_dev = MagicMock()
        fake_the_vm = MagicMock()
        fake_the_vm.config.hardware.device = [fake_dev]
        disk_size = 1

        vmware._add_database_disk(fake_the_vm, disk_size)

        self.assertTrue(fake_consume_task.called)

    @patch.object(vmware, 'consume_task')
    def test_add_database_disk_too_many_vmdks(self, fake_consume_task):
        """``_add_database_disk`` Raises RuntimeError if there are 16 or more VMDKs"""
        fake_dev = MagicMock()
        fake_dev.unitNumber = 15
        fake_the_vm = MagicMock()
        fake_the_vm.config.hardware.device = [fake_dev]
        disk_size = 1

        with self.assertRaises(RuntimeError):
            vmware._add_database_disk(fake_the_vm, disk_size)

    @patch.object(vmware, 'consume_task')
    def test_add_database_disk_no_vmdks(self, fake_consume_task):
        """``_add_database_disk`` Raises RuntimeError if there zero VMDKs"""
        fake_the_vm = MagicMock()
        fake_the_vm.config.hardware.device = []
        disk_size = 1

        with self.assertRaises(RuntimeError):
            vmware._add_database_disk(fake_the_vm, disk_size)

    @patch.object(vmware, 'consume_task')
    def test_add_database_disk_scsi_unit(self, fake_consume_task):
        """``_add_database_disk`` Doesn't use unitNumber 7"""
        fake_dev = MagicMock()
        fake_dev.unitNumber = 6
        fake_the_vm = MagicMock()
        fake_the_vm.config.hardware.device = [fake_dev]
        disk_size = 1

        vmware._add_database_disk(fake_the_vm, disk_size)
        unit = fake_the_vm.ReconfigVM_Task.call_args[1]['spec'].deviceChange[0].device.unitNumber
        expected = 8

        self.assertEqual(unit, expected)

    @patch.object(vmware, 'consume_task')
    def test_add_database_disk_thin(self, fake_consume_task):
        """``_add_database_disk`` Creates a thin-provisioned VMDK"""
        fake_dev = MagicMock()
        fake_dev.unitNumber = 6
        fake_the_vm = MagicMock()
        fake_the_vm.config.hardware.device = [fake_dev]
        disk_size = 1

        vmware._add_database_disk(fake_the_vm, disk_size)

        thin_provision = fake_the_vm.ReconfigVM_Task.call_args[1]['spec'].deviceChange[0].device.backing.thinProvisioned

        self.assertTrue(thin_provision)

    @patch.object(vmware.virtual_machine, 'run_command')
    def test_run_cmd_logs(self, fake_run_command):
        """``_run_cmd`` logs the command if it fails"""
        fake_vcenter = MagicMock()
        fake_the_vm = MagicMock()
        fake_logger = MagicMock()
        cmd = '/some/command'
        args = "and it's args"
        fake_logger = MagicMock()

        vmware._run_cmd(fake_vcenter, fake_the_vm, cmd, args, fake_logger)

        self.assertTrue(fake_logger.error.called)

    @patch.object(vmware.requests, 'put')
    @patch.object(builtins, "open")
    def test_upload_nic_config_http_put(self, fake_open, fake_put):
        """``_upload_nic_config`` Uploads the file via the PUT method"""
        fake_vcenter = MagicMock()
        fake_the_vm = MagicMock()
        fake_logger = MagicMock()
        nic_config = 'TYPE=Ethernet'
        config_name = 'eth0'

        vmware._upload_nic_config(fake_vcenter, fake_the_vm, nic_config, config_name, fake_logger)

        self.assertTrue(fake_put.called)

    @patch.object(vmware.requests, 'put')
    @patch.object(builtins, "open")
    def test_upload_nic_config_checks_http_status(self, fake_open, fake_put):
        """``_upload_nic_config`` Checks the HTTP response status of the upload"""
        fake_vcenter = MagicMock()
        fake_the_vm = MagicMock()
        fake_resp = MagicMock()
        fake_logger = MagicMock()
        nic_config = 'TYPE=Ethernet'
        config_name = 'eth0'
        fake_put.return_value = fake_resp

        vmware._upload_nic_config(fake_vcenter, fake_the_vm, nic_config, config_name, fake_logger)

        self.assertTrue(fake_resp.raise_for_status.called)

    @patch.object(vmware.time, 'sleep')
    def test_get_upload_url(self, fake_sleep):
        """``_get_upload_url`` retries while the VM is booting up"""
        fake_vm = MagicMock()
        fake_creds = MagicMock()
        fake_upload_path = '/home/foo.sh'
        fake_file_size = 9001
        fake_file_attributes = MagicMock()
        fake_vcenter = MagicMock()
        fake_vcenter.content.guestOperationsManager.fileManager.InitiateFileTransferToGuest.side_effect = [vmware.vim.fault.GuestOperationsUnavailable(),
                                                                                                           vmware.vim.fault.GuestOperationsUnavailable(),
                                                                                                           'https://some-url.org']
        vmware._get_upload_url(fake_vcenter,
                               fake_vm,
                               fake_creds,
                               fake_upload_path,
                               fake_file_size,
                               fake_file_attributes)

        # one for every vmware.vim.fault.GuestOperationsUnavailable() side_effect
        self.assertEqual(fake_sleep.call_count, 2)

    @patch.object(vmware.time, 'sleep')
    def test_get_upload_url(self, fake_sleep):
        """``_get_upload_url`` Raises ValueError if the VM is never ready for the file upload"""
        fake_vm = MagicMock()
        fake_creds = MagicMock()
        fake_upload_path = '/home/foo.sh'
        fake_file_size = 9001
        fake_file_attributes = MagicMock()
        fake_vcenter = MagicMock()
        fake_vcenter.content.guestOperationsManager.fileManager.InitiateFileTransferToGuest.side_effect = [vmware.vim.fault.GuestOperationsUnavailable(),
                                                                                                           vmware.vim.fault.GuestOperationsUnavailable(),
                                                                                                           vmware.vim.fault.GuestOperationsUnavailable(),
                                                                                                           vmware.vim.fault.GuestOperationsUnavailable(),
                                                                                                           vmware.vim.fault.GuestOperationsUnavailable(),
                                                                                                           vmware.vim.fault.GuestOperationsUnavailable(),
                                                                                                           vmware.vim.fault.GuestOperationsUnavailable(),
                                                                                                           vmware.vim.fault.GuestOperationsUnavailable(),
                                                                                                           vmware.vim.fault.GuestOperationsUnavailable(),
                                                                                                           vmware.vim.fault.GuestOperationsUnavailable(),]

        with self.assertRaises(ValueError):
            vmware._get_upload_url(fake_vcenter,
                                   fake_vm,
                                   fake_creds,
                                   fake_upload_path,
                                   fake_file_size,
                                   fake_file_attributes)

    @patch.object(vmware, '_run_cmd')
    @patch.object(vmware.time, 'sleep')
    def test_add_gui(self, fake_sleep, fake_run_cmd):
        """``_add_gui`` - installs GNOME Desktop"""
        fake_vcenter = MagicMock()
        fake_the_vm = MagicMock()
        fake_logger = MagicMock()

        vmware._add_gui(fake_vcenter, fake_the_vm, fake_logger)

        installed = fake_run_cmd.call_args_list[0][0][3]
        expected = 'yum -y groupinstall "GNOME Desktop" "Graphical Administration Tools"'

        self.assertEqual(installed, expected)

    @patch.object(vmware, '_run_cmd')
    @patch.object(vmware.time, 'sleep')
    def test_add_gui_sleeps_while_rebooting(self, fake_sleep, fake_run_cmd):
        """``_add_gui`` - Sleeps when rebooting VM"""
        fake_vcenter = MagicMock()
        fake_the_vm = MagicMock()
        fake_logger = MagicMock()

        vmware._add_gui(fake_vcenter, fake_the_vm, fake_logger)

        self.assertTrue(fake_sleep.called)

    @patch.object(vmware, '_run_cmd')
    @patch.object(vmware.time, 'sleep')
    def test_add_gui_rdp(self, fake_sleep, fake_run_cmd):
        """``_add_gui`` - installs an RDP server"""
        fake_vcenter = MagicMock()
        fake_the_vm = MagicMock()
        fake_logger = MagicMock()

        vmware._add_gui(fake_vcenter, fake_the_vm, fake_logger)
        installed = fake_run_cmd.call_args_list[4][0][3]
        expected = 'yum -y install xrdp tigervnc-server'

        self.assertEqual(installed, expected)


if __name__ == '__main__':
    unittest.main()
