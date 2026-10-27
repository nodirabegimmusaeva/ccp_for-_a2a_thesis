"""Checkpoint every attempted call; never silently repair, retry or switch providers."""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import time
import urllib.error
import urllib.request

from .core import (PROVIDERS, ROLES, COMMON, FINAL, atomic_json, build_request,
                   code_hash, digest, initial_handoff, load_materials, parse_final,
                   read_json, schedule, transform)


def now():
    return datetime.now(timezone.utc).isoformat()


class ProviderError(RuntimeError):
    pass


def safe_http_diagnostic(response_body):
    """Classify provider errors without persisting messages, headers or echoed keys."""
    try:
        data = json.loads(response_body)
    except (ValueError, TypeError, UnicodeError):
        return 'non-JSON error response (gateway or access policy may be involved)'
    error = data.get('error') if isinstance(data, dict) else None
    if not isinstance(error, dict):
        return 'unrecognized JSON error response'
    allowed_codes = {
        'model_permission_blocked_org', 'model_permission_blocked_project',
        'model_not_found', 'invalid_api_key', 'insufficient_quota',
        'rate_limit_exceeded', 'organization_restricted', 'access_denied',
    }
    allowed_types = {'permissions_error', 'invalid_request_error', 'authentication_error',
                     'rate_limit_error', 'server_error'}
    code = error.get('code')
    kind = error.get('type')
    return 'provider_code=' + (code if isinstance(code, str) and code in allowed_codes else 'unrecognized') + \
           '; provider_type=' + (kind if isinstance(kind, str) and kind in allowed_types else 'unrecognized')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProviderError('Provider redirect rejected; credentials were not forwarded.')


class LiveClient:
    def __init__(self, config):
        self.config = config
        self.keys = {}
        self.last_call = {}
        self.opener = urllib.request.build_opener(NoRedirect)
        for model in config['models'].values():
            provider = model['provider']
            env = PROVIDERS[provider]['key_env']
            value = os.environ.get(env, '').strip()
            if not value:
                raise ValueError(f'{env} is not loaded. No requests were made.')
            self.keys[provider] = value

    def restore_pacing(self, events):
        """Carry the provider cooldown across checkpointed process restarts."""
        wall_now = datetime.now(timezone.utc)
        monotonic_now = time.monotonic()
        for event in events:
            timestamp = event.get('completed_at') or event.get('started_at')
            if not timestamp:
                continue
            elapsed = max(0, (wall_now - datetime.fromisoformat(timestamp)).total_seconds())
            provider = self.config['models'][event['alias']]['provider']
            self.last_call[provider] = max(self.last_call.get(provider, float('-inf')),
                                           monotonic_now - elapsed)

    def complete(self, alias, system, user):
        model = self.config['models'][alias]
        provider = model['provider']
        settings = self.config['settings']
        wait = max(0, settings['request_interval_seconds'] -
                   (time.monotonic() - self.last_call.get(provider, 0)))
        if wait:
            time.sleep(wait)
        body = {'model': model['model'], 'messages': [
            {'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
            'max_tokens': model.get('max_output_tokens', settings['max_output_tokens'])}
        for name in ('temperature', 'reasoning_effort'):
            if settings[name] is not None:
                body[name] = settings[name]
        request = urllib.request.Request(PROVIDERS[provider]['endpoint'],
            data=json.dumps(body).encode(), headers={
                'Authorization': 'Bearer ' + self.keys[provider],
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': 'CCP-Thesis-Research/1.0'}, method='POST')
        started = time.monotonic()
        try:
            with self.opener.open(request, timeout=90) as response:
                data = json.loads(response.read())
                choice = data['choices'][0]
                text = choice['message'].get('content')
                if not isinstance(text, str):
                    raise ProviderError('Provider returned no text content.')
                # Never retain authorization headers or echoed error bodies.
                metadata = {'returned_model': data.get('model'), 'response_id': data.get('id'),
                            'usage': data.get('usage'), 'finish_reason': choice.get('finish_reason'),
                            'system_fingerprint': data.get('system_fingerprint'),
                            'api_seconds': time.monotonic() - started, 'pacing_seconds': wait}
                return text, metadata
        except urllib.error.HTTPError as exc:
            retry_after = exc.headers.get('retry-after')
            # Retry-After should be numeric; never echo arbitrary response-header content.
            retry_after = retry_after if retry_after and retry_after.isdigit() and len(retry_after) <= 10 else 'unspecified'
            try:
                diagnostic = safe_http_diagnostic(exc.read(16384))
            except OSError:
                diagnostic = 'error body unavailable'
            finally:
                exc.close()
            raise ProviderError(f'HTTP {exc.code}; {diagnostic}; stopped without retry. Retry-After: {retry_after}') from None
        except (urllib.error.URLError, socket.timeout, TimeoutError, ValueError, KeyError, IndexError, TypeError):
            raise ProviderError('Provider/network response failure; stopped without retry.') from None
        finally:
            self.last_call[provider] = time.monotonic()


class OfflineClient:
    """Transport fixture, never evidence of model quality."""
    def complete(self, alias, system, user):
        data = json.loads(user)
        if 'C: Produce' in system:
            raw = json.dumps({'answer': 'OFFLINE TRANSPORT FIXTURE. No model was evaluated.',
                              'received_requirements': []})
        else:
            handoff = data['handoff']
            if isinstance(handoff, dict):
                raw = json.dumps(handoff)
            else:
                raw = handoff
        return raw, {'returned_model': 'OFFLINE_FIXTURE', 'usage': None,
                     'api_seconds': 0, 'pacing_seconds': 0, 'finish_reason': 'stop'}


def prepare(directory, materials, config, repetitions=3, seed=42, simulation=False,
            approve_materials=False):
    if not simulation and not approve_materials:
        raise ValueError('Freeze requires --approve-materials after reviewing requests, keys and protocol.')
    participant, reference = load_materials(materials)
    jobs = schedule(participant['tasks'], config, repetitions, seed)
    spec = {'version': 'cross-model-v1', 'mode': 'simulation' if simulation else 'live',
            'materials_purpose': participant.get('purpose', 'benchmark_templates'),
            'config': config, 'repetitions': repetitions, 'seed': seed,
            'participant_hash': digest(participant), 'reference_hash': digest(reference),
            'code_hash': code_hash(), 'schedule_hash': digest(jobs),
            'prompts': {'common': COMMON, 'roles': ROLES, 'final': FINAL},
            'source_policy': 'Protect exact original request, not evaluator-authored constraint labels.',
            'materials_review_acknowledged': bool(approve_materials)}
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    atomic_json(directory / 'participant_tasks.json', participant)
    atomic_json(directory / 'researcher_scoring_keys.json', reference)
    atomic_json(directory / 'schedule.json', jobs)
    atomic_json(directory / 'code_snapshot.json', {
        p.name: p.read_text() for p in sorted(Path(__file__).parent.glob('*.py'))})
    atomic_json(directory / 'manifest.json', {'created_at': now(), 'spec': spec, 'spec_hash': digest(spec)})
    atomic_json(directory / 'state.json', {'spec_hash': digest(spec), 'records': {}, 'events': []})
    return {'runs': len(jobs), 'workflow_calls': len(jobs) * 4, 'mode': spec['mode']}


def load_run(directory, require_current_code=False):
    directory = Path(directory)
    manifest = read_json(directory / 'manifest.json')
    spec = manifest['spec']
    if digest(spec) != manifest['spec_hash']:
        raise ValueError('Manifest changed.')
    if digest(read_json(directory / 'code_snapshot.json')) != spec['code_hash']:
        raise ValueError('Frozen implementation snapshot changed.')
    if require_current_code and code_hash() != spec['code_hash']:
        raise ValueError('Implementation changed; create a new study snapshot.')
    participant, reference = load_materials(directory)
    jobs = read_json(directory / 'schedule.json')
    if digest(participant) != spec['participant_hash'] or digest(reference) != spec['reference_hash'] or digest(jobs) != spec['schedule_hash']:
        raise ValueError('Frozen materials or schedule changed.')
    state = read_json(directory / 'state.json')
    if state['spec_hash'] != manifest['spec_hash']:
        raise ValueError('State belongs to a different run.')
    return manifest, participant, reference, jobs, state


def batch_plan(jobs):
    """Consecutive task/repetition blocks; never reorder the frozen schedule."""
    batches = []
    for job in jobs:
        block = (job['task_id'], job['repetition'])
        if not batches or block != (batches[-1]['task_id'], batches[-1]['repetition']):
            batches.append({'batch': len(batches) + 1, 'task_id': block[0],
                            'repetition': block[1], 'job_ids': [], 'workflow_calls': 0})
        batches[-1]['job_ids'].append(job['id'])
        batches[-1]['workflow_calls'] += 4
    return batches


def execute(directory, client=None, max_calls=40, confirm_free_tier=False,
            retry_errors=False, abandon_pending=False, progress=None, batch=None):
    import fcntl
    with (Path(directory) / '.execution.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another executor holds this run lock.') from None
        try:
            return _execute(directory, client, max_calls, confirm_free_tier,
                            retry_errors, abandon_pending, progress, batch)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _execute(directory, client=None, max_calls=40, confirm_free_tier=False,
             retry_errors=False, abandon_pending=False, progress=None, batch=None):
    if type(max_calls) is not int or max_calls < 1:
        raise ValueError('max_calls must be positive.')
    directory = Path(directory)
    manifest, participant, _, jobs, state = load_run(directory, require_current_code=True)
    simulation = manifest['spec']['mode'] == 'simulation'
    if not simulation and not confirm_free_tier:
        raise ValueError('Live execution requires --confirm-free-tier. Billing eligibility is not verifiable by this program.')
    if batch is not None:
        batches = batch_plan(jobs)
        if type(batch) is not int or not 1 <= batch <= len(batches):
            raise ValueError(f'batch must be between 1 and {len(batches)}.')
        selected_ids = set(batches[batch - 1]['job_ids'])
        previous_ids = {jid for b in batches[:batch - 1] for jid in b['job_ids']}
        terminal = ('completed', 'invalid_output')
        if any(state['records'].get(jid, {}).get('status') not in terminal for jid in previous_ids):
            raise ValueError('Finish earlier batches first; operational errors must not be skipped.')
        jobs = [job for job in jobs if job['id'] in selected_ids]
        if not retry_errors and any(state['records'].get(jid, {}).get('status') == 'api_error' for jid in selected_ids):
            raise ValueError('Batch has a saved API error; explicitly use --retry-errors after checking quota/access.')
        if all(state['records'].get(jid, {}).get('status') in terminal for jid in selected_ids):
            return {'reason': 'batch_complete', 'batch': batch, 'calls_this_session': 0}
    pending = [e for e in state['events'] if e['status'] == 'pending']
    if pending and not abandon_pending:
        raise ValueError('An interrupted request has unknown outcome. Inspect it; --abandon-pending records it as unknown, without retrying.')
    for e in pending:
        e['status'] = 'unknown_outcome'
        state['records'][e['job_id']]['status'] = 'api_error'
    atomic_json(directory / 'state.json', state)
    # A live test client can only be injected in simulation snapshots.
    if client is not None and not simulation:
        raise ValueError('Injected clients are restricted to offline simulation snapshots.')
    client = client or (OfflineClient() if simulation else LiveClient(manifest['spec']['config']))
    if isinstance(client, LiveClient):
        client.restore_pacing(state['events'])
    tasks = {t['task_id']: t for t in participant['tasks']}
    used = 0
    for job in jobs:
        row = state['records'].setdefault(job['id'], {'status': 'running', 'hops': []})
        if row['status'] in ('completed', 'invalid_output'):
            continue
        if row['status'] == 'api_error' and not retry_errors:
            continue
        task = tasks[job['task_id']]
        forwarded = row['hops'][-1]['forwarded'] if row['hops'] else initial_handoff(task, job['condition'])
        for hop in range(len(row['hops']), 4):
            if used >= max_calls:
                atomic_json(directory / 'state.json', state)
                return {'reason': 'call_budget_reached', 'calls_this_session': used}
            alias = manifest['spec']['config']['routes'][job['route']][hop]
            system, user = build_request(task, job, forwarded, hop)
            event = {'job_id': job['id'], 'hop': hop, 'alias': alias, 'status': 'pending',
                     'started_at': now(), 'system': system, 'user': user}
            state['events'].append(event)
            row['status'] = 'running'
            atomic_json(directory / 'state.json', state)
            used += 1
            try:
                raw, metadata = client.complete(alias, system, user)
            except ProviderError as exc:
                event.update(status='api_error', error=str(exc), completed_at=now())
                row['status'] = 'api_error'
                atomic_json(directory / 'state.json', state)
                if progress:
                    progress({'task': job['task_id'], 'route': job['route'], 'condition': job['condition'],
                              'hop': ROLES[hop].split(':')[0], 'status': 'api_error', 'session_calls': used})
                return {'reason': 'provider_error', 'calls_this_session': used, 'error': str(exc)}
            event.update(status='returned', raw=raw, metadata=metadata, completed_at=now())
            processed_at = time.monotonic()
            if hop < 3:
                audit = transform(task, job['condition'], raw)
                audit['alias'] = alias
                audit['local_processing_seconds'] = time.monotonic() - processed_at
                row['hops'].append(audit)
                forwarded = audit['forwarded']
            else:
                final, error = parse_final(raw)
                row.update(status='invalid_output' if error else 'completed', final=final,
                           final_parse_error=error, raw_final=raw, final_input=json.loads(user),
                           final_local_processing_seconds=time.monotonic() - processed_at)
            atomic_json(directory / 'state.json', state)
            if progress:
                progress({'task': job['task_id'], 'route': job['route'], 'condition': job['condition'],
                          'hop': ROLES[hop].split(':')[0], 'status': row['status'] if hop == 3 else 'returned',
                          'session_calls': used, 'finish_reason': metadata.get('finish_reason')})
    return {'reason': 'batch_complete' if batch is not None else 'schedule_exhausted',
            **({'batch': batch} if batch is not None else {}), 'calls_this_session': used,
            'statuses': {s: sum(state['records'].get(j['id'], {}).get('status') == s for j in jobs)
                         for s in ('completed', 'invalid_output', 'api_error', 'running')}}
