"""Paired scenario-cluster bootstrap for fully scored condition comparisons."""
import argparse
import collections
import json
import random
import statistics
from pathlib import Path
from .study import CONDITIONS


def contrasts(rows, draws=2000, seed=42):
    rng=random.Random(seed); report=[]
    for model in sorted({r['model'] for r in rows}):
        for left,right in [('text','text_pinned'),('text','ccp_raw'),('ccp_raw','ccp_restored'),('text_pinned','ccp_restored')]:
            pairs=collections.defaultdict(dict)
            for row in rows:
                if row['model']==model and row['condition'] in (left,right):
                    key=(row['record_id'],row['repetition'])
                    if row['condition'] in pairs[key]: raise ValueError('Duplicate trial key')
                    pairs[key][row['condition']]=row['result']
            clusters=collections.defaultdict(list);excluded=0
            for (record,_),pair in pairs.items():
                evals=[pair.get(c,{}).get('evaluation',{}) for c in (left,right)]
                if any(e.get('status')!='scored' for e in evals):
                    excluded+=1;continue
                clusters[record].append(int(evals[1]['overall_success'])-int(evals[0]['overall_success']))
            values=[statistics.mean(v) for v in clusters.values()]
            ci=None
            if len(values)>=2:
                samples=sorted(statistics.mean(rng.choices(values,k=len(values))) for _ in range(draws))
                ci=[samples[int(.025*(draws-1))],samples[int(.975*(draws-1))]]
            report.append({'model':model,'contrast':right+' minus '+left,'scenario_count':len(values),
                'excluded_pairs':excluded,'success_rate_difference':statistics.mean(values) if values else None,
                'scenario_bootstrap_95_interval':ci,
                'note':'Exploratory complete-pair analysis, equal scenario weights. Review missingness; small scenario counts give unstable intervals. No universal format/restoration attribution.'})
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('results');a=p.parse_args()
    print(json.dumps(contrasts(json.loads(Path(a.results).read_text())['rows']),indent=2))
