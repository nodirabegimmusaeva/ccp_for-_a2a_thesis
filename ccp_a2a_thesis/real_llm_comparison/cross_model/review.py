"""Offline blinded packets, strict rating import, paired summaries and publication."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import random
import re
import statistics

from .core import CONDITIONS, atomic_json, digest, read_json
from .runner import load_run, now


def export_review(directory, output, seed=42):
    manifest, participant, reference, jobs, state = load_run(directory)
    tasks = {t['task_id']: t for t in participant['tasks']}
    keys = {k['task_id']: k for k in reference['task_keys']}
    rows = [(j, state['records'].get(j['id'], {})) for j in jobs]
    rows = [(j, r) for j, r in rows if r.get('status') in ('completed', 'invalid_output')]
    random.Random(seed).shuffle(rows)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    items, mapping, expected = [], {}, []
    for i, (job, row) in enumerate(rows):
        blind = f'item-{i+1:05d}'
        key = keys[job['task_id']]
        final = row.get('final')
        items.append({'item_id': blind, 'request': tasks[job['task_id']]['user_request'],
                      'evidence': job['evidence'], 'reference': key,
                      'answer': final['answer'] if final else row.get('raw_final', ''),
                      'received_requirements': final['received_requirements'] if final else None,
                      'format_valid': final is not None})
        mapping[blind] = job['id']
        for c in key['requirements'] + key['preferences']:
            expected.append([blind, 'retention', c['id'], '', ''])
            if c['mandatory']:
                expected.append([blind, 'compliance', c['id'], '', ''])
            else:
                expected.append([blind, 'preference', c['id'], '', ''])
        expected.append([blind, 'completion', '__completion__', '', ''])
    atomic_json(output / 'review_packet.json', {
        'spec_hash': manifest['spec_hash'], 'simulation': manifest['spec']['mode'] == 'simulation',
        'materials_purpose': manifest['spec'].get('materials_purpose'),
        'instructions': 'Score final behavior from answer; score reported retention only from received_requirements. Use pass/fail/uncertain and cite evidence. Only preference satisfaction may use not_applicable when no preference-compatible mandatory-compliant choice exists or the task requires withholding selection. Preferences never offset mandatory violations. Do not infer compliance from mentions. This packet does not assess raw-hop semantic changes.',
        'coverage': {'scheduled': len(jobs), 'included': len(rows),
                     'not_included': len(jobs) - len(rows)}, 'items': items})
    atomic_json(output / 'PRIVATE_mapping.json', {
        'spec_hash': manifest['spec_hash'], 'mapping': mapping,
        'items_hash': digest(items)})
    with (output / 'ratings_template.csv').open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['item_id', 'kind', 'constraint_id', 'rating', 'evidence'])
        writer.writerows(expected)
    # A separate packet preserves raw/forwarded data for semantic audit.
    atomic_json(output / 'raw_handoff_audit.json', {
        'instructions': 'Classify semantic omission, weakening, contradiction, ownership changes, harmless paraphrase and overrestriction. Formatting limits blinding. Structural differences are not semantic losses.',
        'items': [{'item_id': f'audit-{i+1:05d}', 'request': tasks[j['task_id']]['user_request'],
                   'hops': [{k: v for k, v in h.items() if k != 'alias'} for h in r['hops']]}
                  for i, (j, r) in enumerate(rows)]})
    return {'items': len(items), 'scheduled': len(jobs), 'rating_rows': len(expected),
            'simulation': manifest['spec']['mode'] == 'simulation'}


def import_ratings(directory, packet_dir, ratings_file, output):
    manifest, _, reference, jobs, state = load_run(directory)
    packet_dir = Path(packet_dir)
    packet = read_json(packet_dir / 'review_packet.json')
    mapping = read_json(packet_dir / 'PRIVATE_mapping.json')
    if (packet['spec_hash'] != manifest['spec_hash'] or mapping['spec_hash'] != manifest['spec_hash']
            or digest(packet['items']) != mapping['items_hash']):
        raise ValueError('Review packet/mapping mismatch.')
    job_map = {j['id']: j for j in jobs}
    keys = {k['task_id']: k for k in reference['task_keys']}
    expected = set()
    for blind, job_id in mapping['mapping'].items():
        if job_id not in job_map or state['records'][job_id]['status'] not in ('completed', 'invalid_output'):
            raise ValueError('Review mapping references an unavailable output.')
        key = keys[job_map[job_id]['task_id']]
        expected.update((blind, 'retention', c['id']) for c in key['requirements'] + key['preferences'])
        expected.update((blind, 'compliance', c['id']) for c in key['requirements'])
        expected.update((blind, 'preference', c['id']) for c in key['preferences'])
        expected.add((blind, 'completion', '__completion__'))
    ratings = {}
    with Path(ratings_file).open(newline='') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != ['item_id', 'kind', 'constraint_id', 'rating', 'evidence']:
            raise ValueError('Unexpected ratings columns.')
        for row in reader:
            identity = (row['item_id'], row['kind'], row['constraint_id'])
            if identity not in expected or identity in ratings:
                raise ValueError('Unexpected or duplicate rating.')
            allowed = ('pass', 'fail', 'uncertain', 'not_applicable') if row['kind'] == 'preference' else ('pass', 'fail', 'uncertain')
            if row['rating'] not in allowed or not row['evidence'].strip():
                raise ValueError('Every rating needs a valid label and evidence; not_applicable is allowed only for preference satisfaction.')
            ratings[identity] = row
    if set(ratings) != expected or not expected:
        raise ValueError('Incomplete or empty rating sheet. Missing labels are not zero-quality answers.')
    scored = []
    for blind, job_id in mapping['mapping'].items():
        job = job_map[job_id]
        key = keys[job['task_id']]
        compliance = {c['id']: ratings[(blind, 'compliance', c['id'])]['rating'] for c in key['requirements']}
        retention = {c['id']: ratings[(blind, 'retention', c['id'])]['rating']
                     for c in key['requirements'] + key['preferences']}
        completion = ratings[(blind, 'completion', '__completion__')]['rating']
        labels = list(compliance.values()) + [completion]
        if state['records'][job_id]['status'] == 'invalid_output':
            success = False
        else:
            success = False if 'fail' in labels else (None if 'uncertain' in labels else True)
        scored.append({'job_id': job_id, 'task_id': job['task_id'], 'route': job['route'],
                       'condition': job['condition'], 'repetition': job['repetition'],
                       'compliance': compliance, 'reported_retention': retention,
                       'preference_satisfaction': {c['id']: ratings[(blind, 'preference', c['id'])]['rating'] for c in key['preferences']},
                       'completion': completion, 'strict_success': success,
                       'rating_evidence': [r for identity, r in ratings.items() if identity[0] == blind]})
    result = {'spec_hash': manifest['spec_hash'], 'simulation': manifest['spec']['mode'] == 'simulation',
              'ratings_file_hash': digest(Path(ratings_file).read_text()),
              'note': 'One imported sheet; not proof of independent or adjudicated assessment.', 'rows': scored}
    output = Path(output)
    if output.exists():
        raise ValueError('Refusing to overwrite a scored sheet.')
    atomic_json(output, result)
    return {'scored': len(scored), 'unresolved_success': sum(r['strict_success'] is None for r in scored)}


def bounds(labels):
    labels = list(labels)
    n = len(labels)
    if not n:
        return None
    return [labels.count('pass') / n, (labels.count('pass') + labels.count('uncertain')) / n]


def analyze(directory, scores=None, draws=2000):
    manifest, _, reference, jobs, state = load_run(directory)
    score_data = read_json(scores) if scores else {'rows': []}
    if scores and score_data['spec_hash'] != manifest['spec_hash']:
        raise ValueError('Scores belong to another run.')
    scored = {r['job_id']: r for r in score_data['rows']}
    keys = {k['task_id']: k for k in reference['task_keys']}
    groups, contrasts = [], []
    for route in manifest['spec']['config']['routes']:
        for condition in CONDITIONS:
            selected = [j for j in jobs if j['route'] == route and j['condition'] == condition]
            records = [state['records'].get(j['id'], {}) for j in selected]
            ss = [scored[j['id']] for j in selected if j['id'] in scored]
            metric_bounds = {'reported_crs': [], 'mandatory_compliance': [],
                             'safety_retention': [], 'mandatory_retention': [], 'preference_retention': [],
                             'preference_satisfaction': []}
            for row in ss:
                key = keys[row['task_id']]
                metric_bounds['reported_crs'].append(bounds(row['reported_retention'].values()))
                metric_bounds['mandatory_compliance'].append(bounds(row['compliance'].values()))
                applicable = [v for v in row.get('preference_satisfaction', {}).values() if v != 'not_applicable']
                if row['strict_success'] is True and applicable:
                    metric_bounds['preference_satisfaction'].append(bounds(applicable))
                for name, cs in [('safety_retention', [c for c in key['requirements'] if c['safety_related']]),
                                 ('mandatory_retention', key['requirements']),
                                 ('preference_retention', key['preferences'])]:
                    b = bounds(row['reported_retention'][c['id']] for c in cs)
                    if b:
                        metric_bounds[name].append(b)
            metrics = {name: [statistics.mean(v[i] for v in values) for i in (0, 1)] if values else None
                       for name, values in metric_bounds.items()}
            events = [e for e in state['events'] if e['job_id'] in {j['id'] for j in selected}]
            returned = [e for e in events if e['status'] == 'returned']
            known_tokens = [e['metadata']['usage']['total_tokens'] for e in returned
                            if isinstance(e['metadata'].get('usage'), dict) and
                            isinstance(e['metadata']['usage'].get('total_tokens'), (int, float))]
            groups.append({'route': route, 'condition': condition, 'scheduled': len(selected),
                'attempted_runs': len({e['job_id'] for e in events}), 'completed': sum(r.get('status') == 'completed' for r in records),
                'invalid_outputs': sum(r.get('status') == 'invalid_output' for r in records),
                'api_error_runs': sum(r.get('status') == 'api_error' for r in records),
                'scored_runs': len(ss), 'successful_scored_runs': sum(r['strict_success'] is True for r in ss),
                'unresolved_scored_runs': sum(r['strict_success'] is None for r in ss),
                'structural_source_change_hops': sum(h['source_changed'] is True for r in records for h in r.get('hops', [])),
                'restored_source_hops': sum(h['restoration_changed_source'] for r in records for h in r.get('hops', [])),
                'parse_error_hops': sum(bool(h['parse_error']) for r in records for h in r.get('hops', [])),
                'call_attempts': len(events), 'known_token_total': sum(known_tokens) if known_tokens else None,
                'calls_with_known_total_tokens': len(known_tokens), 'returned_calls': len(returned),
                'truncated_calls': sum(e['metadata'].get('finish_reason') == 'length' for e in returned),
                'returned_call_api_seconds': sum(e['metadata'].get('api_seconds', 0) for e in returned),
                'pacing_seconds': sum(e['metadata'].get('pacing_seconds', 0) for e in returned),
                'local_processing_seconds': sum(sum(h.get('local_processing_seconds', 0) for h in r.get('hops', []))
                                                + r.get('final_local_processing_seconds', 0) for r in records), **metrics})
        for left, right in [('text', 'ccp_raw'), ('ccp_raw', 'ccp_restored'),
                            ('text', 'text_pinned'), ('text_pinned', 'ccp_restored')]:
            deltas, excluded = {}, 0
            for tid in keys:
                values = []
                reps = sorted({j['repetition'] for j in jobs if j['route'] == route and j['task_id'] == tid})
                for rep in reps:
                    pair = [scored.get(j['id']) for c in (left, right) for j in jobs
                            if j['route'] == route and j['task_id'] == tid and j['repetition'] == rep and j['condition'] == c]
                    if len(pair) != 2 or any(r is None or r['strict_success'] is None for r in pair):
                        excluded += 1
                        continue
                    values.append(int(pair[1]['strict_success']) - int(pair[0]['strict_success']))
                if values:
                    deltas[tid] = statistics.mean(values)
            values = list(deltas.values())
            interval = None
            if len(values) >= 2:
                rng = random.Random(42)
                sampled = sorted(statistics.mean(rng.choices(values, k=len(values))) for _ in range(draws))
                interval = [sampled[int(.025 * (draws - 1))], sampled[int(.975 * (draws - 1))]]
            contrasts.append({'route': route, 'contrast': right + ' minus ' + left,
                'paired_templates': len(values), 'excluded_pairs': excluded,
                'template_differences': deltas,
                'mean_success_difference': statistics.mean(values) if values else None,
                'exploratory_template_bootstrap_95_interval': interval})
    return {'spec_hash': manifest['spec_hash'], 'simulation': manifest['spec']['mode'] == 'simulation',
            'materials_purpose': manifest['spec'].get('materials_purpose'),
            'groups': groups, 'contrasts': contrasts,
            'limitations': 'Complete-pair contrasts exclude operational/unscored/unresolved outcomes; inspect coverage. Bootstrap resamples task templates, not independent repeated calls. Mixed routes remain separate. Structural equality is not semantic retention. Preference satisfaction is shown only for strictly successful outputs with applicable preferences; semantic raw-hop audit remains manual.'}


def agreement(left, right):
    def read(path):
        values = {}
        with Path(path).open(newline='') as f:
            for row in csv.DictReader(f):
                key = (row['item_id'], row['kind'], row['constraint_id'])
                allowed = ('pass', 'fail', 'uncertain', 'not_applicable') if row['kind'] == 'preference' else ('pass', 'fail', 'uncertain')
                if key in values or row['rating'] not in allowed:
                    raise ValueError('Duplicate or incomplete agreement rating.')
                values[key] = row['rating']
        return values
    a, b = read(left), read(right)
    if not a or a.keys() != b.keys():
        raise ValueError('Raters must independently score the same nonempty set.')
    def compare(identities):
        n = len(identities)
        observed = sum(a[k] == b[k] for k in identities) / n
        labels = set(a.values()) | set(b.values())
        expected = sum(sum(a[k] == v for k in identities) * sum(b[k] == v for k in identities)
                       for v in labels) / n**2
        return {'decisions': n, 'raw_agreement': observed,
                'cohen_kappa': (observed - expected) / (1 - expected) if expected < 1 else None}
    return {'pooled': compare(list(a)),
            'by_kind': {kind: compare([k for k in a if k[1] == kind]) for kind in sorted({k[1] for k in a})},
            'note': 'Pre-adjudication categorical agreement. Does not establish rater independence; document the sample and raters separately.'}


def publish(directory, destination, scores=None, reviewed=False):
    if not reviewed:
        raise ValueError('Publication requires --reviewed after checking outputs for credentials and confidential content.')
    manifest, _, _, _, _ = load_run(directory)
    payloads = {name: read_json(Path(directory) / name) for name in (
        'manifest.json', 'participant_tasks.json', 'researcher_scoring_keys.json',
        'schedule.json', 'state.json', 'code_snapshot.json')}
    if scores:
        payloads['scores.json'] = read_json(scores)
        if payloads['scores.json']['spec_hash'] != manifest['spec_hash']:
            raise ValueError('Scores belong to another run.')
    payloads['analysis.json'] = analyze(directory, scores)
    # Defense in depth, not a substitute for the explicit researcher review.
    joined = json.dumps(payloads)
    if re.search(r'(?:AIza[A-Za-z0-9_-]{25,}|gsk_[A-Za-z0-9]{20,}|sk-(?:proj-)?[A-Za-z0-9_-]{20,}|Bearer\s+[A-Za-z0-9_-]{20,})', joined):
        raise ValueError('Possible credential detected; publication blocked.')
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    for name, content in payloads.items():
        atomic_json(destination / name, content)
    atomic_json(destination / 'publication.json', {'exported_at': now(),
        'spec_hash': manifest['spec_hash'], 'researcher_review_acknowledged': True,
        'files': {n: digest(v) for n, v in payloads.items()},
        'note': 'Complete scheduled snapshot including failures and incomplete coverage; not a selected-success subset. Reviewer-private mappings and credentials excluded.'})
    return {'destination': str(destination), 'files': len(payloads) + 1,
            'simulation': manifest['spec']['mode'] == 'simulation'}
