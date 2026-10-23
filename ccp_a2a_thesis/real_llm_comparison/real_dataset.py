"""Build a local, traceable research draft from a saved public-map snapshot.

No network or LLM calls. Review flags intentionally remain pending. Feature offsets
are snapshot-local identifiers, never claimed to be portal complaint IDs.
"""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from .study import atomic_write, digest


def normalize(text):
    return ' '.join(re.findall(r'\w+', unicodedata.normalize('NFKC', text).casefold()))


def groups(features):
    """Conservative exact text/address and near-text connected components."""
    parent = list(range(len(features)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    def union(a, b):
        a, b = root(a), root(b)
        parent[max(a, b)] = min(a, b)
    texts, addresses, postings = {}, {}, defaultdict(list)
    shingles = []
    for i, feature in enumerate(features):
        p = feature['properties']
        text = normalize(str(p.get('hintContent', '')))
        if text:
            if text in texts:
                union(i, texts[text])
            texts[text] = i
        address = normalize(str(p.get('balloonContent', '')).partition('Адрес:')[2])
        # Broad city/district labels are not enough to assert a shared incident.
        if len(address.split()) >= 5 and re.search(r'\d', address):
            if address in addresses:
                union(i, addresses[address])
            addresses[address] = i
        words = text.split()
        grams = {tuple(words[j:j+4]) for j in range(len(words)-3)}
        candidates = set()
        for gram in grams:
            if len(postings[gram]) <= 100:
                candidates.update(postings[gram])
        for j in candidates:
            other = shingles[j]
            if grams and len(grams & other) / len(grams | other) >= .8:
                union(i, j)
        shingles.append(grams)
        for gram in grams:
            postings[gram].append(i)
    components = defaultdict(list)
    for i in range(len(features)):
        components[root(i)].append(i)
    result = {}
    for indices in components.values():
        key = digest(sorted({normalize(features[i]['properties'].get('hintContent', '')) for i in indices}))
        for i in indices:
            result[i] = key
    return result


def build(snapshot, annotations, output, retrieved_at, reserve_count=24):
    raw = Path(snapshot).read_bytes()
    data = json.loads(raw)
    features = data[0]['features']
    spec = json.loads(Path(annotations).read_text())
    fingerprint = hashlib.sha256(raw).hexdigest()
    if spec['snapshot_sha256'] != fingerprint:
        raise ValueError('Annotations refer to a different snapshot')
    grouped = groups(features)
    exposed = {grouped[i] for i in spec['exposed_feature_indices']}
    selected = spec['development']
    if len({grouped[a['feature_index']] for a in selected}) != len(selected):
        raise ValueError('Selected development records share a duplicate/location group')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    provenance = {
        'kind': 'real-public-complaints',
        'source_url': 'https://xalqnazorati.uz/ru/map/points?status=processing',
        'retrieved_at': retrieved_at, 'snapshot_sha256': fingerprint,
        'snapshot_records': len(features), 'privacy_review': 'pending',
        'reuse_status': 'unconfirmed',
        'note': 'Public accessibility does not document a reuse license. Local research draft only.',
        'scope': 'Complaint-to-draft-work-order and clarification; no verified routing ground truth.',
        'sampling': 'Purposive development sample; deterministic diverse reserve, not representative prevalence evidence.',
        'split_policy': 'Every inspected candidate and its related group is development-only. Reserve chosen before prompt tuning.',
        'grouping': 'Exact normalized text, same detailed recorded address, or 4-token shingle Jaccard >=0.8; manual review still required.',
        'translation': 'Original language is the generating-agent input. English gloss is reviewer-only and needs bilingual review.',
    }
    def record(index, split):
        p = features[index]['properties']
        return {'id': 'xalq-' + digest({'snapshot': fingerprint, 'index': index})[:16],
                'group_id': grouped[index], 'split': split,
                'source': {key: p.get(key, '') for key in ('hintContent', 'balloonContent')},
                'source_trace': {'feature_index_zero_based': index,
                                 'feature_sha256': digest(features[index]),
                                 'portal_complaint_id': None,
                                 'observed_status': p.get('status'),
                                 'category_ids': [p.get(k) for k in ('category_id', 'subcategory_id', 'subsubcategory_id')]},
                'reference': {'constraints': [], 'deliverables': []},
                'review_status': 'unreviewed',
                'review_metadata': {'independent_human_review': 'pending', 'privacy_review': 'pending'}}
    development = []
    for annotation in selected:
        r = record(annotation['feature_index'], 'development')
        edits = annotation.get('redactions', [])
        for edit in edits:
            field = edit['field']
            if r['source'][field].count(edit['original']) != 1:
                raise ValueError('Redaction must match exactly once')
            r['source'][field] = r['source'][field].replace(edit['original'], edit['replacement'])
        r['transformations'] = edits
        r['review_metadata']['author_review'] = 'assistant draft; not independent validation'
        r['reviewer_english_gloss'] = annotation['english_gloss']
        r['reference'] = annotation['reference']
        development.append(r)
    # No reserve narrative is printed or put into the development review sheet.
    eligible = defaultdict(list)
    used = set(exposed)
    for i, f in enumerate(features):
        p = f['properties']; text = p.get('hintContent', '')
        if (grouped[i] not in used and p.get('category_id') in (18, 19, 20)
                and 120 <= len(text) <= 650
                and not re.search(r'\+?998[\s\d()-]{9,}|\b\d{9}\b|@|https?://', text)):
            eligible[p.get('subcategory_id')].append(i)
    for bucket in eligible.values():
        bucket.sort(key=lambda i: digest({'seed': 42, 'group': grouped[i], 'index': i}))
    reserve = []
    while len(reserve) < reserve_count:
        progress = False
        for category in sorted(eligible):
            bucket = eligible[category]
            while bucket and grouped[bucket[0]] in used:
                bucket.pop(0)
            if bucket and len(reserve) < reserve_count:
                i = bucket.pop(0); used.add(grouped[i])
                reserve.append(record(i, 'heldout')); progress = True
        if not progress:
            break
    if len(reserve) != reserve_count:
        raise ValueError('Insufficient distinct reserve groups')
    base = {'version': 'xalq-real-draft-v1', 'provenance': provenance, 'routing_directory': {}}
    atomic_write(output/'development.draft.json', dict(base, records=development))
    atomic_write(output/'heldout_reserve.UNREVIEWED.json', dict(base, records=reserve))
    manifest = {'snapshot_sha256': fingerprint, 'retrieved_at': retrieved_at,
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'development': [{'id': r['id'], 'group_id': r['group_id']} for r in development],
                'reserve': [{'id': r['id'], 'group_id': r['group_id']} for r in reserve],
                'exposed_groups': sorted(exposed),
                'development_sha256': digest(dict(base, records=development)),
                'reserve_sha256': digest(dict(base, records=reserve)),
                'independent_review': 'pending; reserve may not be used for prompt tuning'}
    atomic_write(output/'split_manifest.json', manifest)
    lines = ['# Real complaint development review', '',
             'Draft references: verify against original text before running models.',
             'For each case: check translation, privacy, every criterion, and missing criteria.',
             'Record reviewer/date and corrections; do not score model outputs yet.', '']
    for r in development:
        lines += ['## '+r['id'], '', 'Snapshot feature: '+str(r['source_trace']['feature_index_zero_based']), '',
                  '**Original narrative**', '', r['source']['hintContent'], '',
                  '**Recorded category/address**', '', r['source']['balloonContent'], '',
                  '**English reading aid (unverified)**', '', r['reviewer_english_gloss'], '',
                  '**Draft criteria**', '']
        for c in r['reference']['constraints']:
            lines += ['- '+c['id']+': '+c['requirement']]
        lines += ['', 'Reviewer / date / corrections: __________________', '']
    (output/'development_review.md').write_text('\n'.join(lines))
    return {'snapshot_records': len(features), 'development': len(development),
            'heldout_reserve': len(reserve), 'output': str(output),
            'status': 'draft; no live LLM calls; independent review pending'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot', required=True); p.add_argument('--annotations', required=True)
    p.add_argument('--output', required=True); p.add_argument('--retrieved-at', required=True)
    p.add_argument('--reserve-count', type=int, default=24)
    a = p.parse_args()
    print(json.dumps(build(a.snapshot, a.annotations, a.output, a.retrieved_at, a.reserve_count), indent=2))


if __name__ == '__main__':
    main()
