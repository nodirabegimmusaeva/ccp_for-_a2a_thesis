"""One explicitly requested, normally checkpointed retry with redacted HTTP diagnostics.

This external diagnostic tool leaves the frozen experiment implementation unchanged.
It never retries automatically or changes the prompt, model, endpoint or request headers.
"""
import argparse
from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from real_llm_comparison.cross_model.core import atomic_json
from real_llm_comparison.cross_model.runner import batch_plan, execute, load_run, now

HEADER_NAMES = (
    'retry-after', 'x-ratelimit-limit-requests', 'x-ratelimit-remaining-requests',
    'x-ratelimit-reset-requests', 'x-ratelimit-limit-tokens',
    'x-ratelimit-remaining-tokens', 'x-ratelimit-reset-tokens',
)


def redact(value, secrets):
    text = str(value)
    for secret in secrets:
        if secret:
            text = text.replace(secret, '[REDACTED]')
    text = re.sub(r'(?:gsk_[A-Za-z0-9_-]+|AIza[A-Za-z0-9_-]+|sk-(?:proj-)?[A-Za-z0-9_-]+)',
                  '[REDACTED]', text)
    text = re.sub(r'(?i)Bearer\s+\S+', 'Bearer [REDACTED]', text)
    return text[:2000]


def diagnostic(status, headers, body, secrets):
    result = {'http_status': status, 'rate_headers': {
        name: redact(headers[name], secrets) for name in HEADER_NAMES if headers.get(name) is not None}}
    if body is not None:
        try:
            obj = json.loads(body)
            error = obj.get('error', {}) if isinstance(obj, dict) else {}
            if not isinstance(error, dict):
                error = {}
            result['provider_error'] = {name: redact(error[name], secrets)
                                        for name in ('code', 'type', 'message') if name in error}
        except (ValueError, UnicodeError):
            result['provider_error'] = {'format': 'non_json',
                                       'cloudflare_1010_marker': b'1010' in body}
    return result


@contextmanager
def capture_http(records, secrets):
    original = urllib.request.OpenerDirector.open

    def opened(opener, request, *args, **kwargs):
        try:
            response = original(opener, request, *args, **kwargs)
            records.append(diagnostic(response.status, response.headers, None, secrets))
            return response
        except urllib.error.HTTPError as error:
            body = error.read()
            records.append(diagnostic(error.code, error.headers, body, secrets))
            # Replay the same bytes to the unchanged client's existing safe error handler.
            error.fp = io.BytesIO(body)
            error.file = error.fp
            error.read = error.fp.read
            raise
    urllib.request.OpenerDirector.open = opened
    try:
        yield
    finally:
        urllib.request.OpenerDirector.open = original


def select_retry(manifest, jobs, state, batch=None):
    development = manifest['spec'].get('materials_purpose') == 'provider_and_handoff_compatibility_only'
    if not development and batch is None:
        raise ValueError('Main-study diagnostics require an explicit --batch number.')
    if any(e['status'] == 'pending' for e in state['events']):
        raise ValueError('A pending request has unknown outcome; inspect it before any retry.')
    unfinished = [j for j in jobs if state['records'].get(j['id'], {}).get('status') not in ('completed', 'invalid_output')]
    if not unfinished:
        raise ValueError('No unfinished call remains.')
    job = unfinished[0]
    row = state['records'].get(job['id'], {})
    if not development and row.get('status') != 'api_error':
        raise ValueError('Main-study diagnostics may only retry a saved operational error.')
    if batch is not None:
        batches = batch_plan(jobs)
        if not 1 <= batch <= len(batches) or job['id'] not in batches[batch - 1]['job_ids']:
            raise ValueError('Requested batch does not contain the first unfinished call.')
    hop = len(row.get('hops', []))
    alias = manifest['spec']['config']['routes'][job['route']][hop]
    if manifest['spec']['config']['models'][alias]['provider'] != 'groq':
        raise ValueError('Next unfinished call is not Groq; no diagnostic call made.')
    return job, hop


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--confirm-free-tier', action='store_true')
    parser.add_argument('--batch', type=int, help='Required for a main-study operational retry.')
    args = parser.parse_args()
    if not args.confirm_free_tier:
        parser.error('Confirm the account is still on the free tier before one retry.')
    manifest, _, _, jobs, state = load_run(args.run_dir, require_current_code=True)
    try:
        job, hop = select_retry(manifest, jobs, state, args.batch)
    except ValueError as exc:
        parser.error(str(exc))
    secrets = [os.environ.get(name, '') for name in ('GROQ_API_KEY', 'GEMINI_API_KEY')]
    records = []
    before = len(state['events'])
    destination = args.run_dir / f'transport_diagnostic_{before:05d}.json'
    if destination.exists():
        parser.error('Diagnostic file already exists; refusing overwrite before making a call.')
    with capture_http(records, secrets):
        result = execute(args.run_dir, max_calls=1, confirm_free_tier=True, retry_errors=True,
                         batch=args.batch,
                         progress=lambda event: print(json.dumps(event), file=sys.stderr, flush=True))
    output = {'captured_at': now(), 'spec_hash': manifest['spec_hash'],
              'diagnostic_tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'event_index': before, 'execution': result, 'http': records,
              'target': {'job_id': job['id'], 'hop': hop, 'batch': args.batch},
              'note': 'One requested retry through the unchanged frozen runner; only response metadata was observed. No automatic retry or provider substitution.'}
    atomic_json(destination, output)
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
