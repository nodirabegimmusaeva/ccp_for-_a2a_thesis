"""Offline dataset audit, blinded review, and agreement tools."""
import argparse
import collections
import csv
import json
from pathlib import Path
import random
import re
from .study import atomic_write, digest


def audit_snapshot(path):
    data = json.loads(Path(path).read_text())
    features = data[0]['features']
    texts = [str(f.get('properties',{}).get('hintContent','')).strip() for f in features]
    normalized = [' '.join(t.casefold().split()) for t in texts]
    return {'features':len(features), 'nonempty_narratives':sum(bool(t) for t in texts),
            'duplicate_narratives':sum(n-1 for t,n in collections.Counter(normalized).items() if t),
            'possible_phone_records':sum(bool(re.search(r'\+?998[\s\d()-]{9,}',t)) for t in texts),
            'statuses':dict(collections.Counter(f['properties'].get('status') for f in features)),
            'note':'PII flags are incomplete heuristics. Human redaction and reference annotation required. No raw narratives included in this report.'}


def prepare_snapshot(path, output):
    data = json.loads(Path(path).read_text())
    records, seen = [], set()
    for f in data[0]['features']:
        p = f.get('properties',{})
        hint = str(p.get('hintContent','')).strip()
        if not hint:
            continue
        group = digest(' '.join(hint.casefold().split()))
        if group in seen:
            continue
        seen.add(group)
        records.append({'id':group[:16], 'group_id':group,
            'split':'heldout' if int(group[:8],16)%5 == 0 else 'development',
            'source':{'hintContent':hint,'balloonContent':p.get('balloonContent',''),
                      'category_id':p.get('category_id'),'subcategory_id':p.get('subcategory_id'),
                      'subsubcategory_id':p.get('subsubcategory_id')},
            'reference':{'constraints':[],'deliverables':[]},'review_status':'unreviewed'})
    atomic_write(output,{'version':'unreviewed-import-v1','provenance':{'source':'Xalq Nazorati public map',
                 'snapshot_sha256':digest(data),'reuse_status':'unconfirmed','privacy_review':'pending'},
                 'taxonomy':data[1],'routing_directory':{},'records':records})


def export_review(results, dataset, directory, seed=42):
    rows = json.loads(Path(results).read_text())['rows']
    records = {r['id']:r for r in json.loads(Path(dataset).read_text())['records']}
    rows = [r for r in rows if r['result']['status']=='completed']
    random.Random(seed).shuffle(rows)
    out = Path(directory);out.mkdir(parents=True,exist_ok=False)
    mapping, sheets = {}, []
    for i,row in enumerate(rows):
        blind = f'item-{i+1:05d}'
        record = records[row['record_id']]
        mapping[blind] = {'key':row['key'],'condition':row['condition'],'model':row['model'],'record_id':row['record_id']}
        sheets.append({'item_id':blind,'original':record['source'],'reference':record['reference'],
                       'work_order':row['result']['final'],
                       'rubric':'Score each constraint pass/fail/uncertain. Score completion separately. Quote evidence. Do not infer success from mentioning a requirement.'})
    atomic_write(out/'review_packet.json',sheets)
    atomic_write(out/'PRIVATE_condition_mapping.json',mapping)
    with (out/'ratings_template.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['item_id','criterion','rating','evidence'])
        for item in sheets:
            for c in item['reference']['constraints']:
                w.writerow([item['item_id'],c['id'],'',''])
            w.writerow([item['item_id'],'completion','',''])
    return {'items':len(sheets),'note':'Give each rater an independent copy. Do not distribute PRIVATE_condition_mapping.json. Packet evaluates final compliance, not handoff retention.'}


def agreement(a,b):
    def read(path):
        result={}
        for row in csv.DictReader(Path(path).read_text().splitlines()):
            key=(row['item_id'],row['criterion'])
            if key in result: raise ValueError('Duplicate rating')
            if row['rating'] not in ('pass','fail','uncertain'): raise ValueError('Incomplete or invalid rating')
            result[key]=row['rating']
        return result
    left,right=read(a),read(b)
    if not left or left.keys()!=right.keys(): raise ValueError('Raters must score the same nonempty item set')
    n=len(left); observed=sum(left[k]==right[k] for k in left)/n
    ca,cb=collections.Counter(left.values()),collections.Counter(right.values())
    expected=sum(ca[v]*cb[v] for v in ('pass','fail','uncertain'))/(n*n)
    return {'decisions':n,'raw_agreement':observed,'cohen_kappa':(observed-expected)/(1-expected) if expected<1 else None,
            'note':'Pre-adjudication pooled categorical agreement; inspect criterion-specific disagreements too.'}


def audit_legacy(path):
    data=json.loads(Path(path).read_text()); totals=collections.Counter(); fields=collections.Counter()
    conditions=data.get('conditions',[{'results':data}])
    for condition in conditions:
        for task in condition.get('results',{}).get('tasks',[]):
            for trial in task.get('trials',[]):
                ccp=trial.get('ccp',{}); original=ccp.get('agent_a_output',{})
                for raw in ccp.get('agent_b_raw_outputs',[]):
                    totals['raw_hops']+=1
                    changed=[]
                    for key in ('task_id','context','extended_context','request','constraints','metadata'):
                        if not isinstance(raw,dict) or raw.get(key)!=original.get(key):
                            changed.append(key);fields[key]+=1
                    totals['hops_with_canonical_difference']+=bool(changed)
    return {'counts':dict(totals),'field_counts':dict(fields),'note':'Structural differences are not semantic constraint losses; manually classify sampled changes.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    for name in ('audit','legacy-audit'):
        q=sub.add_parser(name);q.add_argument('input')
    q=sub.add_parser('prepare');q.add_argument('input');q.add_argument('output')
    q=sub.add_parser('export');q.add_argument('results');q.add_argument('dataset');q.add_argument('directory')
    q=sub.add_parser('agreement');q.add_argument('rater_a');q.add_argument('rater_b')
    a=p.parse_args()
    if a.command=='audit': result=audit_snapshot(a.input)
    elif a.command=='legacy-audit': result=audit_legacy(a.input)
    elif a.command=='prepare': result=prepare_snapshot(a.input,a.output)
    elif a.command=='export': result=export_review(a.results,a.dataset,a.directory)
    else: result=agreement(a.rater_a,a.rater_b)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
