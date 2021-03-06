# -*- coding: UTF-8 -*-
"""
A suite of tests for the dataiq object
"""
import unittest
from unittest.mock import patch, MagicMock

import ujson
from flask import Flask
from vlab_api_common import flask_common
from vlab_api_common.http_auth import generate_v2_test_token


from vlab_dataiq_api.lib.views import dataiq


class TestDataIQView(unittest.TestCase):
    """A set of test cases for the DataIQView object"""
    @classmethod
    def setUpClass(cls):
        """Runs once for the whole test suite"""
        cls.token = generate_v2_test_token(username='bob')

    @classmethod
    def setUp(cls):
        """Runs before every test case"""
        app = Flask(__name__)
        dataiq.DataIQView.register(app)
        app.config['TESTING'] = True
        cls.app = app.test_client()
        # Mock Celery
        app.celery_app = MagicMock()
        cls.fake_task = MagicMock()
        cls.fake_task.id = 'asdf-asdf-asdf'
        app.celery_app.send_task.return_value = cls.fake_task

    def test_v1_deprecated(self):
        """DataIQView - GET on /api/1/inf/dataiq returns an HTTP 404"""
        resp = self.app.get('/api/1/inf/dataiq',
                            headers={'X-Auth': self.token})

        status = resp.status_code
        expected = 404

        self.assertEqual(status, expected)

    def test_get_task(self):
        """DataIQView - GET on /api/2/inf/dataiq returns a task-id"""
        resp = self.app.get('/api/2/inf/dataiq',
                            headers={'X-Auth': self.token})

        task_id = resp.json['content']['task-id']
        expected = 'asdf-asdf-asdf'

        self.assertEqual(task_id, expected)

    def test_get_task_link(self):
        """DataIQView - GET on /api/2/inf/dataiq sets the Link header"""
        resp = self.app.get('/api/2/inf/dataiq',
                            headers={'X-Auth': self.token})

        task_id = resp.headers['Link']
        expected = '<https://localhost/api/2/inf/dataiq/task/asdf-asdf-asdf>; rel=status'

        self.assertEqual(task_id, expected)

    def test_post_task(self):
        """DataIQView - POST on /api/2/inf/dataiq returns a task-id"""
        resp = self.app.post('/api/2/inf/dataiq',
                             headers={'X-Auth': self.token},
                             json={'network': "someLAN",
                                   'name': "myDataIQBox",
                                   'image': "someVersion",
                                   'static-ip': '192.168.1.2'})

        task_id = resp.json['content']['task-id']
        expected = 'asdf-asdf-asdf'

        self.assertEqual(task_id, expected)

    def test_post_task_link(self):
        """DataIQView - POST on /api/2/inf/dataiq sets the Link header"""
        resp = self.app.post('/api/2/inf/dataiq',
                             headers={'X-Auth': self.token},
                             json={'network': "someLAN",
                                   'name': "myDataIQBox",
                                   'image': "someVersion",
                                   'static-ip': '192.168.1.2'})

        task_id = resp.headers['Link']
        expected = '<https://localhost/api/2/inf/dataiq/task/asdf-asdf-asdf>; rel=status'

        self.assertEqual(task_id, expected)

    def test_post_bad_config(self):
        """DataIQView - POST on /api/2/inf/dataiq returns HTTP 400 when supplied with an invalid network config"""
        resp = self.app.post('/api/2/inf/dataiq',
                             headers={'X-Auth': self.token},
                             json={'network': "someLAN",
                                   'name': "myDataIQBox",
                                   'image': "someVersion",
                                   'static-ip': '10.7.1.2',
                                   'default-gateway': '192.168.1.1',
                                   'netmask': '255.255.255.0'})

        self.assertEqual(resp.status_code, 400)

    def test_post_bad_config_error(self):
        """DataIQView - POST on /api/2/inf/dataiq returns an error message when supplied with an invalid network config"""
        resp = self.app.post('/api/2/inf/dataiq',
                             headers={'X-Auth': self.token},
                             json={'network': "someLAN",
                                   'name': "myDataIQBox",
                                   'image': "someVersion",
                                   'static-ip': '10.7.1.2',
                                   'default-gateway': '192.168.1.1',
                                   'netmask': '255.255.255.0'})
        error = resp.json['error']
        expected = 'Static IP 10.7.1.2 is not part of network 192.168.1.0/24. Adjust your netmask and/or default gateway.'

        self.assertEqual(error, expected)

    def test_delete_task(self):
        """DataIQView - DELETE on /api/2/inf/dataiq returns a task-id"""
        resp = self.app.delete('/api/2/inf/dataiq',
                               headers={'X-Auth': self.token},
                               json={'name' : 'myDataIQBox'})

        task_id = resp.json['content']['task-id']
        expected = 'asdf-asdf-asdf'

        self.assertEqual(task_id, expected)

    def test_delete_task_link(self):
        """DataIQView - DELETE on /api/2/inf/dataiq sets the Link header"""
        resp = self.app.delete('/api/2/inf/dataiq',
                               headers={'X-Auth': self.token},
                               json={'name' : 'myDataIQBox'})

        task_id = resp.headers['Link']
        expected = '<https://localhost/api/2/inf/dataiq/task/asdf-asdf-asdf>; rel=status'

        self.assertEqual(task_id, expected)

    def test_image(self):
        """DataIQView - GET on the ./image end point returns the a task-id"""
        resp = self.app.get('/api/2/inf/dataiq/image',
                            headers={'X-Auth': self.token})

        task_id = resp.json['content']['task-id']
        expected = 'asdf-asdf-asdf'

        self.assertEqual(task_id, expected)

    def test_image(self):
        """DataIQView - GET on the ./image end point sets the Link header"""
        resp = self.app.get('/api/2/inf/dataiq/image',
                            headers={'X-Auth': self.token})

        task_id = resp.headers['Link']
        expected = '<https://localhost/api/2/inf/dataiq/task/asdf-asdf-asdf>; rel=status'

        self.assertEqual(task_id, expected)


if __name__ == '__main__':
    unittest.main()
