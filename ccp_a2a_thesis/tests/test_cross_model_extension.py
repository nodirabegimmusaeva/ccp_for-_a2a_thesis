import copy
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from real_llm_comparison.cross_model.core import (
    CONDITIONS, DEFAULT_MATERIALS, atomic_json, build_request, digest,
    initial_handoff, load_materials, parse_final, read_json, schedule, transform,
    validate_config,
)
from real_llm_comparison.cross_model.runner import (
    LiveClient, OfflineClient, ProviderError, batch_plan, execute, load_run, prepare, safe_http_diagnostic,
)
from real_llm_comparison.cross_model.review import (
    agreement, analyze, export_review, import_ratings, publish,
)


def config():
    return {'models': {'g': {'provider': 'google', 'model': 'gemini-fixture'}},
            'routes': {'g_only': ['g'] * 4},
            'settings': {'temperature': None, 'reasoning_effort': None,
                         'max_output_tokens': 1800, 'request_interval_seconds': 0}}


class Corrupt(OfflineClient):
    def complete(self, alias, system, user):
        if 'C: Produce' in system:
            return super().complete(alias, system, user)
        return '{"source":{"request":"Prefer any meal"},"working_notes":"wrong shortlist"}', {
            'api_seconds': 0, 'pacing_seconds': 0, 'usage': None, 'finish_reason': 'stop'}


class CrossModelTests(unittest.TestCase):
    def test_smoke_development_is_separate_and_requires_32_calls(self):
        development, reference = load_materials(DEFAULT_MATERIALS / 'development')
        benchmark, _ = load_materials(DEFAULT_MATERIALS)
        self.assertFalse({t['task_id'] for t in development['tasks']} & {t['task_id'] for t in benchmark['tasks']})
        c = read_json(DEFAULT_MATERIALS / 'providers.example.json')
        self.assertEqual(len(schedule(development['tasks'], c, 1, 42)) * 4, 32)
        self.assertEqual(reference['task_keys'][0]['acceptable_selection_ids'], ['DEV-B'])
        items = development['tasks'][0]['evidence']['items']
        self.assertEqual([i['id'] for i in items if i['capacity'] >= 8 and i['video_conferencing'] and i['session_price'] <= 40], ['DEV-B'])

    def test_error_diagnostics_do_not_echo_provider_messages_or_arbitrary_codes(self):
        secret = 'gsk_' + 'x' * 30
        response = json.dumps({'error': {'message': secret, 'code': 'model_permission_blocked_org',
                                        'type': 'permissions_error'}})
        diagnostic = safe_http_diagnostic(response)
        self.assertIn('model_permission_blocked_org', diagnostic)
        self.assertNotIn(secret, diagnostic)
        self.assertNotIn(secret, safe_http_diagnostic(json.dumps({'error': {'code': secret, 'type': secret}})))
        self.assertIn('non-JSON', safe_http_diagnostic('<html>Forbidden ' + secret + '</html>'))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.materials = self.root / 'materials'
        self.materials.mkdir()
        participant, reference = load_materials(DEFAULT_MATERIALS)
        participant['tasks'] = participant['tasks'][:1]
        reference['task_keys'] = reference['task_keys'][:1]
        atomic_json(self.materials / 'participant_tasks.json', participant)
        atomic_json(self.materials / 'researcher_scoring_keys.json', reference)
        self.task = participant['tasks'][0]

    def frozen(self, name='run', simulation=True):
        run = self.root / name
        prepare(run, self.materials, config(), repetitions=1, simulation=simulation,
                approve_materials=not simulation)
        return run

    def test_inventory_and_main_call_count(self):
        participant, reference = load_materials(DEFAULT_MATERIALS)
        c = read_json(DEFAULT_MATERIALS / 'providers.example.json')
        jobs = schedule(participant['tasks'], c, 3, 42)
        self.assertEqual(len(jobs), 288)
        self.assertEqual(len(jobs) * 4, 1152)
        self.assertEqual(sum(len(k['requirements']) for k in reference['task_keys']), 42)
        self.assertEqual(sum(len(k['preferences']) for k in reference['task_keys']), 12)
        self.assertEqual(len({j['id'] for j in jobs}), len(jobs))
        for tid in ('F1', 'T1'):
            evidence = [j['evidence'] for j in jobs if j['task_id'] == tid and j['repetition'] == 0]
            self.assertTrue(all(x == evidence[0] for x in evidence))

    def test_main_batches_cover_every_pair_without_reordering(self):
        participant, _ = load_materials(DEFAULT_MATERIALS)
        c = read_json(DEFAULT_MATERIALS / 'providers.main-v1.json')
        jobs = schedule(participant['tasks'], c, 3, 42)
        batches = batch_plan(jobs)
        self.assertEqual(len(batches), 36)
        self.assertEqual([jid for b in batches for jid in b['job_ids']], [j['id'] for j in jobs])
        for b in batches:
            selected = [j for j in jobs if j['id'] in b['job_ids']]
            self.assertEqual(b['workflow_calls'], 32)
            self.assertEqual({(j['route'], j['condition']) for j in selected},
                             {(r, condition) for r in c['routes'] for condition in CONDITIONS})

    def test_batch_resume_stops_at_boundary_and_cannot_skip_earlier_batch(self):
        run = self.root / 'batched'
        prepare(run, self.materials, config(), repetitions=2, simulation=True)
        with self.assertRaisesRegex(ValueError, 'Finish earlier'):
            execute(run, batch=2)
        self.assertEqual(execute(run, batch=1, max_calls=5)['calls_this_session'], 5)
        result = execute(run, batch=1, max_calls=32)
        self.assertEqual(result['reason'], 'batch_complete')
        self.assertEqual(result['calls_this_session'], 11)
        self.assertEqual(execute(run, batch=1)['calls_this_session'], 0)
        self.assertEqual(len(load_run(run)[-1]['events']), 16)
        self.assertEqual(execute(run, batch=2)['calls_this_session'], 16)

    def test_batch_api_error_needs_explicit_retry(self):
        class Failing(OfflineClient):
            def complete(self, *args):
                raise ProviderError('fixture quota error')
        run = self.frozen()
        self.assertEqual(execute(run, client=Failing(), batch=1)['reason'], 'provider_error')
        with self.assertRaisesRegex(ValueError, '--retry-errors'):
            execute(run, batch=1)
        self.assertEqual(execute(run, batch=1, retry_errors=True)['reason'], 'batch_complete')
        self.assertEqual(len(load_run(run)[-1]['events']), 17)

    def test_restart_carries_forward_provider_cooldown(self):
        client = LiveClient.__new__(LiveClient)
        client.config = config()
        client.last_call = {}
        timestamp = datetime.now(timezone.utc).isoformat()
        with patch('real_llm_comparison.cross_model.runner.time.monotonic', return_value=1000):
            client.restore_pacing([{'alias': 'g', 'completed_at': timestamp}])
        self.assertGreater(client.last_call['google'], 999)
        self.assertLessEqual(client.last_call['google'], 1000)

    def test_no_key_or_original_request_leak_in_unprotected_handoffs(self):
        for c in CONDITIONS:
            job = {'condition': c, 'evidence': self.task['evidence']}
            system, user = build_request(self.task, job, 'degraded request', 3)
            obj = json.loads(user)
            self.assertEqual('protected_original' in obj, c == 'text_pinned')
            self.assertNotIn('acceptable_selection_ids', user)
            self.assertNotIn('F1-R1', user)
            if c != 'text_pinned':
                self.assertNotIn(self.task['user_request'], user)
            self.assertIn('received_requirements', system)
            self.assertIn('Do not use Markdown, code fences', system)

    def test_ccp_stages_explicitly_request_bare_json_without_parser_repair(self):
        for c in ('ccp_raw', 'ccp_restored'):
            for hop in range(3):
                system, _ = build_request(self.task, {'condition': c, 'evidence': self.task['evidence']},
                                          initial_handoff(self.task, c), hop)
                self.assertIn('Do not use Markdown, code fences', system)
        raw = '```json\n{"answer":"Studio","received_requirements":[]}\n```'
        self.assertIsNotNone(parse_final(raw)[1])

    def test_restoration_preserves_working_notes_but_restores_exact_request(self):
        raw = '{"source":{"request":"any meal"},"working_notes":"wrong shortlist"}'
        restored = transform(self.task, 'ccp_restored', raw)
        self.assertEqual(restored['forwarded']['source']['request'], self.task['user_request'])
        self.assertEqual(restored['forwarded']['working_notes'], 'wrong shortlist')
        self.assertTrue(restored['restoration_changed_source'])
        self.assertEqual(transform(self.task, 'ccp_raw', raw)['forwarded']['source']['request'], 'any meal')

    def test_malformed_ccp_is_not_hidden_repair_in_raw(self):
        for raw in ('broken JSON', '[]', 'null', '```json\n{}\n```', '{"source":42}'):
            self.assertEqual(transform(self.task, 'ccp_raw', raw)['forwarded'], raw)
            r = transform(self.task, 'ccp_restored', raw)
            self.assertEqual(r['forwarded']['source']['request'], self.task['user_request'])
            self.assertEqual(r['forwarded']['working_notes'], raw)

    def test_no_aliasing(self):
        a = initial_handoff(self.task, 'ccp_restored')
        a['source']['request'] = 'changed'
        self.assertNotEqual(self.task['user_request'], 'changed')

    def test_pause_resume_does_not_repeat_successful_calls(self):
        run = self.frozen()
        self.assertEqual(execute(run, client=Corrupt(), max_calls=2)['calls_this_session'], 2)
        self.assertEqual(execute(run, client=Corrupt(), max_calls=100)['calls_this_session'], 14)
        self.assertEqual(execute(run, client=Corrupt(), max_calls=100)['calls_this_session'], 0)
        _, _, _, jobs, state = load_run(run)
        self.assertEqual(len(state['events']), 16)
        for job in jobs:
            r = state['records'][job['id']]
            if job['condition'] == 'ccp_restored':
                self.assertTrue(all(h['restoration_changed_source'] for h in r['hops']))
            if job['condition'] == 'ccp_raw':
                self.assertEqual(r['final_input']['handoff']['source']['request'], 'Prefer any meal')

    def test_api_error_stops_and_explicit_retry_retains_failure(self):
        class Error(OfflineClient):
            def complete(self, *args):
                raise ProviderError('HTTP 429')
        run = self.frozen()
        result = execute(run, client=Error(), max_calls=10)
        self.assertEqual(result['reason'], 'provider_error')
        self.assertEqual(result['calls_this_session'], 1)
        execute(run, retry_errors=True, max_calls=100)
        state = read_json(run / 'state.json')
        self.assertEqual(len(state['events']), 17)
        self.assertEqual(state['events'][0]['status'], 'api_error')

    def test_pending_unknown_request_requires_explicit_resolution(self):
        class Interrupted(OfflineClient):
            def complete(self, *args):
                raise KeyboardInterrupt()
        run = self.frozen()
        with self.assertRaises(KeyboardInterrupt):
            execute(run, client=Interrupted())
        with self.assertRaisesRegex(ValueError, 'unknown outcome'):
            execute(run)
        execute(run, abandon_pending=True, retry_errors=True, max_calls=100)
        self.assertEqual(read_json(run / 'state.json')['events'][0]['status'], 'unknown_outcome')

    def test_resume_rejects_changed_materials_and_code(self):
        run = self.frozen()
        p = read_json(run / 'participant_tasks.json')
        p['tasks'][0]['user_request'] = 'changed'
        atomic_json(run / 'participant_tasks.json', p)
        with self.assertRaisesRegex(ValueError, 'materials'):
            execute(run)
        run = self.frozen('run2')
        with patch('real_llm_comparison.cross_model.runner.code_hash', return_value='changed'):
            with self.assertRaisesRegex(ValueError, 'Implementation changed'):
                execute(run)
            load_run(run)  # Historical analysis is still permitted.

    def test_live_never_runs_without_acknowledgement_or_provider_keys(self):
        run = self.frozen(simulation=False)
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaisesRegex(ValueError, 'confirm-free-tier'):
                execute(run)
            with self.assertRaisesRegex(ValueError, 'GEMINI_API_KEY'):
                execute(run, confirm_free_tier=True)
        bad = config()
        bad['models']['g'] = {'provider': 'openai', 'model': 'gpt-4.1-nano'}
        with self.assertRaises(ValueError):
            validate_config(bad)
        with self.assertRaises(ValueError):
            prepare(self.root / 'noapprove', self.materials, config())

    def test_credential_not_in_request_log_and_redirects_rejected(self):
        from real_llm_comparison.cross_model.runner import NoRedirect
        with self.assertRaises(ProviderError):
            NoRedirect().redirect_request(None, None, 302, '', {}, 'https://elsewhere.test')
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-secret'}):
            client = LiveClient(config())
            class Response:
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def read(self):
                    return json.dumps({'choices': [{'message': {'content': 'ok'}, 'finish_reason': 'stop'}],
                                       'model': 'returned-model', 'usage': {'total_tokens': 10}}).encode()
            with patch.object(client.opener, 'open', return_value=Response()) as opened:
                raw, metadata = client.complete('g', 'system', 'user')
            request = opened.call_args.args[0]
            self.assertEqual(request.get_header('User-agent'), 'CCP-Thesis-Research/1.0')
            self.assertEqual(request.get_header('Accept'), 'application/json')
            self.assertEqual(raw, 'ok')
            self.assertNotIn('test-secret', json.dumps(metadata))
            self.assertEqual(metadata['returned_model'], 'returned-model')

    def test_model_specific_output_cap_changes_groq_only_on_wire(self):
        c = config()
        c['models']['q'] = {'provider': 'groq', 'model': 'qwen/fixture', 'max_output_tokens': 900}
        c['routes']['q_only'] = ['q'] * 4
        validate_config(c)
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self):
                return b'{"choices":[{"message":{"content":"ok"},"finish_reason":"stop"}]}'
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'fixture-g', 'GROQ_API_KEY': 'fixture-q'}):
            client = LiveClient(c)
            with patch.object(client.opener, 'open', return_value=Response()) as opened:
                client.complete('q', 'system', 'user')
                self.assertEqual(json.loads(opened.call_args.args[0].data)['max_tokens'], 900)
                client.complete('g', 'system', 'user')
                self.assertEqual(json.loads(opened.call_args.args[0].data)['max_tokens'], 1800)
        for invalid in (True, None, '900', 127, 8193):
            c['models']['q']['max_output_tokens'] = invalid
            with self.assertRaisesRegex(ValueError, 'Model output budget'):
                validate_config(c)

    def test_output_validation_and_partial_review_coverage(self):
        for raw in ('[]', '{}', '{"answer":"x","received_requirements":"all"}',
                    '{"answer":"","received_requirements":[]}'):
            self.assertIsNotNone(parse_final(raw)[1])
        run = self.frozen()
        execute(run, max_calls=5)
        packet = self.root / 'review'
        self.assertEqual(export_review(run, packet)['items'], 1)
        p = read_json(packet / 'review_packet.json')
        self.assertEqual(p['coverage']['not_included'], 3)
        self.assertNotIn('g_only', json.dumps(p))
        self.assertNotIn('ccp_restored', json.dumps(p))

    def test_manual_scoring_uncertainty_and_publication(self):
        run = self.frozen()
        execute(run, max_calls=100)
        packet = self.root / 'review'
        export_review(run, packet)
        with (packet / 'ratings_template.csv').open(newline='') as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            row['rating'] = 'pass'
            row['evidence'] = 'Fixture label for testing score import only.'
        rows[0]['rating'] = 'uncertain'
        ratings = self.root / 'ratings.csv'
        def write(rows):
            with ratings.open('w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['item_id', 'kind', 'constraint_id', 'rating', 'evidence'])
                writer.writeheader(); writer.writerows(rows)
        write(rows[:-1])
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            import_ratings(run, packet, ratings, self.root / 'bad.json')
        write(rows + [rows[0]])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            import_ratings(run, packet, ratings, self.root / 'bad.json')
        write(rows)
        self.assertEqual(agreement(ratings, ratings)['pooled']['raw_agreement'], 1)
        scores = self.root / 'scores.json'
        import_ratings(run, packet, ratings, scores)
        report = analyze(run, scores, draws=100)
        self.assertTrue(report['simulation'])
        group = next(g for g in report['groups'] if g['reported_crs'][0] < 1)
        self.assertEqual(group['reported_crs'], [2/3, 1])
        destination = self.root / 'published'
        with self.assertRaises(ValueError):
            publish(run, destination, scores)
        publish(run, destination, scores, reviewed=True)
        self.assertFalse((destination / 'PRIVATE_mapping.json').exists())
        self.assertEqual(len(read_json(destination / 'schedule.json')), 4)
        self.assertEqual(len(read_json(destination / 'state.json')['events']), 16)

    def test_concurrent_executor_lock_is_rejected(self):
        import fcntl
        run = self.frozen()
        with (run / '.execution.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError, 'Another executor'):
                execute(run)

    def test_group_order_answer_key_matches_all_feasible_pairs(self):
        from itertools import product
        tasks, reference = load_materials(DEFAULT_MATERIALS)
        task = next(t for t in tasks['tasks'] if t['task_id'] == 'F2')
        key = next(k for k in reference['task_keys'] if k['task_id'] == 'F2')
        evidence = task['evidence']
        pairs = [[a['id'], b['id']] for a, b in product(evidence['items'], repeat=2)
                 if not a['contains_peanuts'] and not a['peanut_warning'] and b['vegan']
                 and a['price'] + b['price'] + evidence['delivery_fee_per_order'] <= 30]
        self.assertEqual(sorted(pairs), sorted(key['acceptable_assignment_pairs']))

    def test_publication_blocks_possible_secret(self):
        run = self.frozen()
        execute(run, max_calls=100)
        state = read_json(run / 'state.json')
        state['events'][0]['raw'] = 'gsk_' + 'x' * 25
        atomic_json(run / 'state.json', state)
        with self.assertRaisesRegex(ValueError, 'credential'):
            publish(run, self.root / 'blocked', reviewed=True)
        self.assertFalse((self.root / 'blocked').exists())


if __name__ == '__main__':
    unittest.main()
