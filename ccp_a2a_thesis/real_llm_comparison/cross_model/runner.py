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
            'max_tokens': settings['max_output_tokens']}
        for name in ('temperature', 'reasoning_effort'):
            if settings[name] is not None:
                body[name] = settings[name]
        request = urllib.request.Request(PROVIDERS[provider]['endpoint'],
            data=json.dumps(body).encode(), headers={
                'Authorization': 'Bearer ' + self.keys[provider],
                'Content-Type': 'application/json'}, method='POST')
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
            raise ProviderError(f'HTTP {exc.code}; stopped without retry. Retry-After: {retry_after or "unspecified"}') from None
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
    atomic_json(directory / 'manifest.json', {'created_at': now(), 'spec': spec, 'spec_hash': digest(spec)})
    atomic_json(directory / 'state.json', {'spec_hash': digest(spec), 'records': {}, 'events': []})
    return {'runs': len(jobs), 'workflow_calls': len(jobs) * 4, 'mode': spec['mode']}


def load_run(directory):
    directory = Path(directory)
    manifest = read_json(directory / 'manifest.json')
    spec = manifest['spec']
    if digest(spec) != manifest['spec_hash'] or code_hash() != spec['code_hash']:
        raise ValueError('Manifest or implementation changed; create a new study snapshot.')
    participant, reference = load_materials(directory)
    jobs = read_json(directory / 'schedule.json')
    if digest(participant) != spec['participant_hash'] or digest(reference) != spec['reference_hash'] or digest(jobs) != spec['schedule_hash']:
        raise ValueError('Frozen materials or schedule changed.')
    state = read_json(directory / 'state.json')
    if state['spec_hash'] != manifest['spec_hash']:
        raise ValueError('State belongs to a different run.')
    return manifest, participant, reference, jobs, state


def execute(directory, client=None, max_calls=40, confirm_free_tier=False,
            retry_errors=False, abandon_pending=False):
    if type(max_calls) is not int or max_calls < 1:
        raise ValueError('max_calls must be positive.')
    directory = Path(directory)
    manifest, participant, _, jobs, state = load_run(directory)
    simulation = manifest['spec']['mode'] == 'simulation'
    if not simulation and not confirm_free_tier:
        raise ValueError('Live execution requires --confirm-free-tier. Billing eligibility is not verifiable by this program.')
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
                return {'reason': 'provider_error', 'calls_this_session': used, 'error': str(exc)}
            event.update(status='returned', raw=raw, metadata=metadata, completed_at=now())
            if hop < 3:
                audit = transform(task, job['condition'], raw)
                audit['alias'] = alias
                row['hops'].append(audit)
                forwarded = audit['forwarded']
            else:
                final, error = parse_final(raw)
                row.update(status='invalid_output' if error else 'completed', final=final,
                           final_parse_error=error, raw_final=raw, final_input=json.loads(user))
            atomic_json(directory / 'state.json', state)
    return {'reason': 'schedule_exhausted', 'calls_this_session': used,
            'statuses': {s: sum(r['status'] == s for r in state['records'].values())
                         for s in ('completed', 'invalid_output', 'api_error', 'running')}}
