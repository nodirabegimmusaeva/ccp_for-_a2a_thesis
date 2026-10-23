"""Build a self-contained Apps Script from a blinded review packet (no private mapping)."""
import argparse
import json
from pathlib import Path

def build(packet, template, output):
    items=json.loads(Path(packet).read_text())
    if len({x['item_id'] for x in items})!=len(items): raise ValueError('Duplicate item IDs')
    for item in items:
        if set(item)-{'item_id','original','reference','work_order','rubric'}:
            raise ValueError('Unexpected metadata: use only the blinded packet')
    source=Path(template).read_text().replace('/* REVIEW_DATA */',json.dumps(items,ensure_ascii=False))
    Path(output).write_text(source)
    return len(items)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('packet');p.add_argument('output');a=p.parse_args()
    print('Embedded cases:',build(a.packet,Path(__file__).with_name('template.gs'),a.output))
