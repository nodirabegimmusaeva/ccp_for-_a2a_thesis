import io
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

from tools.diagnose_cross_model_limit import capture_http, diagnostic, select_retry


class LimitDiagnosticTests(unittest.TestCase):
    def test_main_diagnostic_targets_only_saved_error_in_explicit_batch(self):
        manifest = {'spec': {'config': {'routes': {'qwen_only': ['q'] * 4},
                                      'models': {'q': {'provider': 'groq'}}}}}
        jobs = [{'id': 'job1', 'task_id': 'T1', 'repetition': 0, 'route': 'qwen_only'}]
        state = {'events': [], 'records': {'job1': {'status': 'api_error', 'hops': [{}]}}}
        with self.assertRaisesRegex(ValueError, 'explicit --batch'):
            select_retry(manifest, jobs, state)
        self.assertEqual(select_retry(manifest, jobs, state, 1), (jobs[0], 1))
        with self.assertRaisesRegex(ValueError, 'Requested batch'):
            select_retry(manifest, jobs, state, 2)
        state['records']['job1']['status'] = 'running'
        with self.assertRaisesRegex(ValueError, 'saved operational error'):
            select_retry(manifest, jobs, state, 1)

    def test_diagnostic_refuses_unknown_pending_attempt(self):
        with self.assertRaisesRegex(ValueError, 'unknown outcome'):
            select_retry({'spec': {}}, [], {'events': [{'status': 'pending'}]}, 1)

    def test_redacts_key_and_never_copies_authorization_header(self):
        secret = 'gsk_' + 'a' * 30
        body = json.dumps({'error': {'code': 'rate_limit_exceeded', 'message':
            'Tokens per day limit reached: ' + secret + ' Bearer something-private'}}).encode()
        result = diagnostic(429, {'Authorization': secret, 'x-ratelimit-limit-tokens': '8000'}, body, [secret])
        self.assertNotIn(secret, json.dumps(result))
        self.assertNotIn('something-private', json.dumps(result))
        self.assertNotIn('Authorization', result['rate_headers'])
        self.assertIn('Tokens per day', result['provider_error']['message'])

    def test_error_body_replayed_to_frozen_client_handler(self):
        body = b'{"error":{"code":"rate_limit_exceeded","message":"TPD reached"}}'
        error = urllib.error.HTTPError('https://api.groq.com', 429, 'limited',
                                       {'retry-after': '50'}, io.BytesIO(body))
        records = []
        with patch.object(urllib.request.OpenerDirector, 'open', side_effect=error):
            before = urllib.request.OpenerDirector.open
            with capture_http(records, []):
                opener = urllib.request.OpenerDirector()
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    opener.open('https://api.groq.com')
                self.assertEqual(raised.exception.read(16384), body)
            self.assertIs(urllib.request.OpenerDirector.open, before)
        self.assertEqual(records[0]['provider_error']['message'], 'TPD reached')


if __name__ == '__main__':
    unittest.main()
