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

    @patch.object(vmware, '_upload_install_script')
    @patch.object(vmware, '_get_install_script')
    @patch.object(vmware.virtual_machine, 'set_meta')
    @patch.object(vmware, 'Ova')
    @patch.object(vmware.virtual_machine, 'get_info')
    @patch.object(vmware.virtual_machine, 'deploy_from_ova')
    @patch.object(vmware, 'consume_task')
    @patch.object(vmware, 'vCenter')
    def test_create_dataiq(self, fake_vCenter, fake_consume_task, fake_deploy_from_ova, fake_get_info, fake_Ova, fake_set_meta, fake_get_install_script, fake_upload_install_script):
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
                                       logger=fake_logger)
        expected = {'myDataIQ': {'worked': True}}

        self.assertEqual(output, expected)

    @patch.object(vmware, '_upload_install_script')
    @patch.object(vmware, '_get_install_script')
    @patch.object(vmware, 'Ova')
    @patch.object(vmware.virtual_machine, 'get_info')
    @patch.object(vmware.virtual_machine, 'deploy_from_ova')
    @patch.object(vmware, 'consume_task')
    @patch.object(vmware, 'vCenter')
    def test_create_dataiq_invalid_network(self, fake_vCenter, fake_consume_task,
                                           fake_deploy_from_ova, fake_get_info, fake_Ova,
                                           fake_get_install_script, fake_upload_install_script):
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
                                  logger=fake_logger)

    @patch.object(vmware.os, 'listdir')
    def test_list_images(self, fake_listdir):
        """``list_images`` - Returns a list of available DataIQ versions that can be deployed"""
        fake_listdir.return_value = ['dataiq_installer_1.0.0.10_202003090706_v1.', 'BaseDataIQ.ova']

        output = vmware.list_images()
        expected = ['1.0.0']

        # set() avoids ordering issue in test
        self.assertEqual(set(output), set(expected))

    def test_convert_name(self):
        """``convert_name`` - converts the install script name to a version"""
        output = vmware.convert_name(name='dataiq_installer_1.0.0.10_202003090706_v1.sh')
        expected = '1.0.0'

        self.assertEqual(output, expected)

    def test_convert_name_error(self):
        """``convert_name`` - raises a ValueError if a an install script has an unexpected name"""
        with self.assertRaises(ValueError):
            vmware.convert_name(name='dfw;eiupof23iulkhas')

    @patch.object(vmware.os, 'listdir')
    def test_get_install_script(self, fake_listdir):
        """``_get_install_script`` - is able to find the install script given an image/version"""
        fake_listdir.return_value = ['dataiq_installer_1.0.0.10_202003090706_v1.sh']

        script_name = vmware._get_install_script('1.0.0')
        expected = '/images/dataiq_installer_1.0.0.10_202003090706_v1.sh'

        self.assertEqual(script_name, expected)

    @patch.object(vmware.os, 'listdir')
    def test_get_install_script_error(self, fake_listdir):
        """``_get_install_script`` - raises ValueError if unable to find an install script"""
        fake_listdir.return_value = ['dataiq_installer_1.0.0.10_202003090706_v1.sh']

        with self.assertRaises(ValueError):
            vmware._get_install_script('a.b.c')

    @patch.object(vmware.requests, 'put')
    @patch.object(builtins, "open")
    def test_upload_install_script_reads_script_into_ram(self, fake_open, fake_put):
        """``_upload_install_script`` Reads the script into RAM for uploading"""
        fake_vcenter = MagicMock()
        fake_the_vm = MagicMock()
        fake_logger = MagicMock()
        install_script = 'dataiq_installer_1.0.0.10_202003090706_v1.sh'

        vmware._upload_install_script(fake_vcenter, fake_the_vm, install_script, fake_logger)

        file_read = fake_open.call_args_list[0][0][0]
        self.assertEqual(file_read, install_script)

    @patch.object(vmware.requests, 'put')
    @patch.object(builtins, "open")
    def test_upload_install_script_http_put(self, fake_open, fake_put):
        """``_upload_install_script`` Uploads the file via the PUT method"""
        fake_vcenter = MagicMock()
        fake_the_vm = MagicMock()
        fake_logger = MagicMock()
        install_script = 'dataiq_installer_1.0.0.10_202003090706_v1.sh'

        vmware._upload_install_script(fake_vcenter, fake_the_vm, install_script, fake_logger)

        self.assertTrue(fake_put.called)

    @patch.object(vmware.requests, 'put')
    @patch.object(builtins, "open")
    def test_upload_install_script_checks_http_status(self, fake_open, fake_put):
        """``_upload_install_script`` Checks the HTTP response status of the upload"""
        fake_vcenter = MagicMock()
        fake_the_vm = MagicMock()
        fake_resp = MagicMock()
        fake_logger = MagicMock()
        fake_put.return_value = fake_resp
        install_script = 'dataiq_installer_1.0.0.10_202003090706_v1.sh'

        vmware._upload_install_script(fake_vcenter, fake_the_vm, install_script, fake_logger)

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



if __name__ == '__main__':
    unittest.main()
