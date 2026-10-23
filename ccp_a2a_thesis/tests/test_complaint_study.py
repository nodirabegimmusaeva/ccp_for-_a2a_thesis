import copy
import json
from pathlib import Path
import tempfile
import unittest
from real_llm_comparison.study import trial, load_dataset, restore, evaluate, digest, CONDITIONS
from real_llm_comparison.study_tools import agreement, export_review

FIXTURE = Path(__file__).resolve().parents[1]/'real_llm_comparison/data/complaints_fixture.json'
FINAL={'issues':['roof leak'],'locations':[],'actions':['inspect'],'clarification_required':True,'clarification_notes':'location unknown','department':None,'summary':'Inspection requested'}
class Fake:
    def __init__(self,raw='{"source":{},"working_notes":"inspect"}'):
        self.api_call_log=[];self.inputs=[];self.raw=raw
    def complete_text(self,system,user,call_label=None):
        self.inputs.append(json.loads(user))
        return json.dumps(FINAL) if call_label['role']=='final' else self.raw

class StudyTests(unittest.TestCase):
    def setUp(self): self.data,self.records=load_dataset(FIXTURE,'development');self.record=self.records[0]
    def test_four_conditions_no_reference_leak(self):
        for c in CONDITIONS:
            f=Fake();r=trial(f,self.record,c,{},1)
            self.assertEqual(r['status'],'completed')
            self.assertNotIn('reference',json.dumps(f.inputs))
            user=f.inputs[-1]
            self.assertEqual('protected_original' in user,c=='text_pinned')
            if c=='ccp_restored': self.assertEqual(user['handoff']['source'],self.record['source'])
            if c=='ccp_raw': self.assertEqual(user['handoff']['source'],{})
    def test_malformed_raw_has_no_repair(self):
        f=Fake('broken JSON');r=trial(f,self.record,'ccp_raw',{},1)
        self.assertEqual(f.inputs[-1]['handoff'],'broken JSON')
        self.assertTrue(r['hops'][0]['parse_error'])
        self.assertFalse(r['hops'][0]['restored'])
    def test_restored_malformed_keeps_original(self):
        f=Fake('broken JSON');r=trial(f,self.record,'ccp_restored',{},1)
        self.assertEqual(f.inputs[-1]['handoff']['source'],self.record['source'])
        self.assertTrue(r['hops'][0]['restored'])
    def test_restoration_has_no_alias(self):
        original={'source':{'x':['a']}};r=restore(original,{})
        r['source']['x'].append('b');self.assertEqual(original['source']['x'],['a'])
    def test_split_leakage_rejected(self):
        data=copy.deepcopy(self.data);data['records'][1]['group_id']=data['records'][0]['group_id']
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'data.json';p.write_text(json.dumps(data))
            with self.assertRaises(ValueError):load_dataset(p,'development')
    def test_false_boolean_not_accepted(self):
        class Bad(Fake):
            def complete_text(self,*a,**kw):return json.dumps(dict(FINAL,clarification_required='false'))
        self.assertEqual(trial(Bad(),self.record,'text',{},1)['status'],'invalid_output')
    def test_bad_judge_not_zero_quality(self):
        f=Fake('[]');r=evaluate(f,self.record,{'raw_final':'x'})
        self.assertEqual(r['status'],'evaluation_error');self.assertNotIn('overall_success',r)
    def test_review_blind_and_agreement(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);r=trial(Fake(),self.record,'ccp_restored',{},1)
            (p/'results.json').write_text(json.dumps({'rows':[{'key':'k','record_id':self.record['id'],'model':'m','condition':'ccp_restored','result':r}]}))
            export_review(p/'results.json',FIXTURE,p/'review')
            self.assertNotIn('ccp_restored',(p/'review/review_packet.json').read_text())
            ratings='item_id,criterion,rating,evidence\nx,a,pass,quote\nx,b,fail,quote\n'
            (p/'a.csv').write_text(ratings);(p/'b.csv').write_text(ratings)
            self.assertEqual(agreement(p/'a.csv',p/'b.csv')['cohen_kappa'],1)
if __name__=='__main__':unittest.main()

class AnalysisTests(unittest.TestCase):
    def test_clustered_contrast_and_missingness(self):
        from real_llm_comparison.study_analysis import contrasts
        rows=[]
        for record in ('a','b'):
            for c,success in [('text',False),('ccp_raw',True)]:
                rows.append({'model':'m','record_id':record,'repetition':0,'condition':c,
                             'result':{'evaluation':{'status':'scored','overall_success':success}}})
        r=next(x for x in contrasts(rows,100) if x['contrast']=='ccp_raw minus text')
        self.assertEqual(r['success_rate_difference'],1)
        self.assertEqual(r['scenario_bootstrap_95_interval'],[1,1])

class DevelopmentDatasetTests(unittest.TestCase):
    def test_development_set_has_explicit_anchors_and_no_heldout_cases(self):
        path=FIXTURE.parent/'complaints_development.json'
        data,records=load_dataset(path,'development')
        self.assertEqual(len(records),8)
        self.assertEqual(data['provenance']['kind'],'synthetic')
        self.assertTrue(all(r['split']=='development' for r in records))
        for record in records:
            self.assertEqual(record['review_metadata']['independent_human_review'],'pending')
            for constraint in record['reference']['constraints']:
                self.assertTrue(constraint['retention_pass'])
                self.assertTrue(constraint['compliance_pass'])
                self.assertTrue(constraint['fail'])
        with self.assertRaises(ValueError):load_dataset(path,'heldout')
