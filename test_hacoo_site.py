import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

import bot
from hacoo_publish import history, run_auto
from hacoo_site import Application, make_server


class Tests(unittest.TestCase):
    @patch('hacoo_publish.convert', return_value={'affiliate_url': 'https://c.onlyaff.app/NEW'})
    @patch('builtins.input', side_effect=AssertionError('No prompts in automatic mode'))
    def test_auto_publishes_random_match_and_blocks_duplicate(self, prompt, convert):
        original = {'source': 'channel/1', 'text': 'Saucony Jazz\n31 EUR',
                    'photos': ['https://cdn4.telesco.pe/a'], 'links': ['https://c.onlyaff.app/OLD']}
        api = Mock(destination=bot.DESTINATION)
        api.publish.return_value = {'message_id': 3}
        db = history(':memory:')
        result = run_auto('40125478, saucony jazz', Mock(), api, db, lambda name: [original], lambda msg: None)
        self.assertEqual(result['source'], 'channel/1')
        post = api.publish.call_args.args[0]
        self.assertEqual(post['photos'], original['photos'])
        self.assertEqual(post['links'], ['https://c.onlyaff.app/NEW'])
        self.assertIn('31 EUR', bot.announcement_text(post))
        with self.assertRaises(ValueError):
            run_auto('40125478, saucony jazz', Mock(), api, db, lambda name: [original])
        self.assertEqual(api.publish.call_count, 1)
        self.assertEqual(convert.call_count, 1)
        db.close()

    @patch('hacoo_publish.convert')
    def test_auto_no_match_has_no_effect(self, convert):
        api = Mock(destination=bot.DESTINATION)
        db = history(':memory:')
        with self.assertRaises(ValueError):
            run_auto('40125478, saucony jazz', Mock(), api, db, lambda name: [], lambda msg: None)
        convert.assert_not_called()
        api.publish.assert_not_called()
        db.close()

    @patch('hacoo_site.threading.Thread')
    def test_job_requires_ready_cache_and_serializes_requests(self, thread):
        app = Application(Mock(), Mock(), Path('/unused'))
        with self.assertRaises(ValueError):
            app.submit('40125478', 'saucony jazz')
        app.ready = True
        app.submit('40125478', 'saucony jazz')
        with self.assertRaises(ValueError):
            app.submit('40125479', 'saucony jazz')
        self.assertEqual(thread.call_count, 1)

    @patch('hacoo_site.history', side_effect=OSError('disk error'))
    def test_database_failure_releases_busy_state(self, history):
        app = Application(Mock(), Mock(), Path('/unused'))
        app.busy = True
        app.publish('40125478, saucony jazz')
        self.assertFalse(app.snapshot()['busy'])
        self.assertIn('interrompue', app.snapshot()['message'])

    def test_http_page_status_and_cross_origin_rejection(self):
        with tempfile.TemporaryDirectory() as folder:
            app = Application(Mock(), Mock(), Path(folder))
            app.submit = Mock()
            server = make_server(app)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
            origin = f'http://127.0.0.1:{server.server_port}'
            try:
                conn.request('GET', '/')
                response = conn.getresponse()
                self.assertEqual(response.status, 200)
                self.assertIn('Code Hacoo', response.read().decode())
                conn.request('GET', '/status')
                response = conn.getresponse()
                self.assertEqual(json.loads(response.read())['ready'], False)
                body = json.dumps({'code': '40125478', 'name': 'Saucony Jazz'})
                for headers in [{}, {'Origin': 'https://evil.example', 'X-Hacoo-Token': app.token},
                                {'Origin': origin, 'X-Hacoo-Token': 'wrong'},
                                {'Origin': origin, 'X-Hacoo-Token': app.token, 'Host': 'evil.example'}]:
                    conn.request('POST', '/publish', body, headers)
                    response = conn.getresponse()
                    self.assertEqual(response.status, 403)
                    response.read()
                app.submit.assert_not_called()
                conn.request('POST', '/publish', body, {'Origin': origin, 'X-Hacoo-Token': app.token})
                response = conn.getresponse()
                self.assertEqual(response.status, 202)
                response.read()
                app.submit.assert_called_once_with('40125478', 'Saucony Jazz')
            finally:
                conn.close()
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == '__main__':
    unittest.main()
