from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / '.agents/skills/ai-job-fit-scorer'
SCRIPTS = SKILL / 'scripts'
EXAMPLES = ROOT / 'docs/examples/ai-job-fit-scorer'


def cli(name, value, *args):
    return subprocess.run([sys.executable, str(SCRIPTS/name), *args],
                          input=json.dumps(value), capture_output=True, text=True)


class FitSkillTests(unittest.TestCase):
    def setUp(self):
        self.rows = json.loads((EXAMPLES/'dataset.example.json').read_text())
        self.summary = json.loads((EXAMPLES/'run-summary.example.json').read_text())

    def test_real_example_summary_and_dataset_reconcile(self):
        result = cli('validate_run_summary.py', self.summary, '--expected-build', '0.1.22')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('example candidate', result.stderr)
        result = cli('validate_fit_rows.py', self.rows, '--summary', str(EXAMPLES/'run-summary.example.json'), '--table')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(result.stdout.splitlines()), 4)

    def test_summary_rejects_invalid_contract_and_arithmetic(self):
        mutations = [
            lambda s: s.update(extra='resume leak'),
            lambda s: s.pop('cleanEmpty'),
            lambda s: s['candidate'].update(usedExampleProfile='false'),
            lambda s: s['candidate'].update(resumeText='private text'),
            lambda s: s['counts'].update(evaluatedJobs=True),
            lambda s: s['counts'].update(budgetAuthorizedJobs=1),
            lambda s: s['counts'].update(aiScored=2),
            lambda s: s['billing'].update(totalChargedUsd=float('nan')),
            lambda s: s['billing'].update(budgetAuthorizedCount=1),
            lambda s: s['ai'].update(providerCostUsd=-1),
            lambda s: s.update(cleanEmpty=True),
            lambda s: s.update(warnings=[{}]),
            lambda s: s.update(status='failed'),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                s=copy.deepcopy(self.summary);mutate(s)
                r=cli('validate_run_summary.py', s)
                self.assertNotEqual(r.returncode, 0)
                self.assertNotIn('Traceback', r.stderr)

    def test_row_rejects_missing_nested_contract_or_wrong_identity(self):
        mutations = [lambda r:r['scoring'].pop('sourceProvenance'),
                     lambda r:r['job'].pop('raw'),
                     lambda r:r['job'].update(data=[]),
                     lambda r:r.update(title=5),
                     lambda r:r.update(fitScore=True),
                     lambda r:r.update(jobKey='other:123'),
                     lambda r:r.update(evaluationStatus=[])]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                row=copy.deepcopy(self.rows[0]);mutate(row)
                result=cli('validate_fit_rows.py', [row])
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Traceback', result.stderr)

    def test_mismatched_candidate_timestamp_source_and_duplicate_are_rejected(self):
        for key, value in [('candidateHash','a'*64), ('candidateSnapshotHash','b'*64),('evaluatedAt','2020-01-01')]:
            rows=copy.deepcopy(self.rows);rows[0][key]=value
            self.assertNotEqual(cli('validate_fit_rows.py',rows,'--summary',str(EXAMPLES/'run-summary.example.json')).returncode,0)
        rows=copy.deepcopy(self.rows);rows[0]['scoring']['sourceProvenance']={}
        self.assertNotEqual(cli('validate_fit_rows.py',rows,'--summary',str(EXAMPLES/'run-summary.example.json')).returncode,0)
        self.assertNotEqual(cli('validate_fit_rows.py',[self.rows[0],self.rows[0]]).returncode,0)

    def test_audit_accepts_static_zero_and_unbilled_failure_then_rejects_count_drift(self):
        rows=copy.deepcopy(self.rows[:2]);s=copy.deepcopy(self.summary)
        rows[0].update(evaluationStatus='static_drop',fitScore=0,deliveryScore=0,recommendation='incompatible')
        rows[1].update(evaluationStatus='ai_failed',fitScore=None,deliveryScore=None,recommendation='unavailable')
        s['parameters']['resultMode']='audit'
        s['counts'].update(sourceJobs=2,budgetAuthorizedJobs=2,evaluatedJobs=2,staticDropped=1,staticHeld=0,aiAttempted=1,aiScored=0,aiFailed=1,resultFilteredOut=0,outputRows=2)
        s['billing'].update(chargedCount=1,totalChargedUsd=.02,budgetAuthorizedCount=2)
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'summary.json';p.write_text(json.dumps(s))
            r=cli('validate_fit_rows.py',rows,'--summary',str(p));self.assertEqual(r.returncode,0,r.stderr)
            rows[1].update(evaluationStatus='static_hold')
            self.assertNotEqual(cli('validate_fit_rows.py',rows,'--summary',str(p)).returncode,0)

    def test_empty_budget_limited_run_does_not_require_candidate_hash(self):
        s=copy.deepcopy(self.summary);s['status']='empty';s['counts']={k:0 for k in s['counts']}
        s['counts']['sourceJobs']=3;s['candidate'].update(candidateHash=None,candidateSnapshotHash=None)
        s['billing'].update(chargedCount=0,totalChargedUsd=0,budgetAuthorizedCount=0,budgetLimited=True)
        s['terminal']['reason']='budget_limit'
        self.assertEqual(cli('validate_run_summary.py',s).returncode,0)

    def test_wrong_build_and_run_charge_receipt_rejected(self):
        self.assertNotEqual(cli('validate_run_summary.py',self.summary,'--expected-build','0.1.23').returncode,0)
        a=self.summary['actor']
        run=dict(id=a['runId'],actId=a['id'],buildId=a['buildId'],buildNumber=a['buildNumber'],status='SUCCEEDED',exitCode=0,defaultDatasetId='dataset',defaultKeyValueStoreId='store',chargedEventCounts={'job-fit-result':3})
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'run.json';p.write_text(json.dumps({'data':run}))
            self.assertEqual(cli('validate_run_summary.py',self.summary,'--run',str(p)).returncode,0)
            for key,value in [('id','wrong-run'),('exitCode',True),('buildNumber','0.1.23'),('chargedEventCounts',{'job-fit-result':2})]:
                bad=dict(run);bad[key]=value;p.write_text(json.dumps(bad))
                self.assertNotEqual(cli('validate_run_summary.py',self.summary,'--run',str(p)).returncode,0)

    def test_missing_files_and_malformed_summary_fail_cleanly(self):
        result=cli('validate_fit_rows.py',self.rows,'--summary','/does-not-exist.json')
        self.assertNotEqual(result.returncode,0);self.assertNotIn('Traceback',result.stderr)
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'bad.json';p.write_text('{')
            result=cli('validate_fit_rows.py',self.rows,'--summary',str(p))
            self.assertNotEqual(result.returncode,0);self.assertNotIn('Traceback',result.stderr)

    def test_active_website_pins_and_historical_proof_agree(self):
        import re
        for page in (ROOT/'website/integrations').glob('*/index.html'):
            text=page.read_text()
            self.assertNotIn('0.1.12',text,str(page))
        for name in ['website/index.html','website/actors/ai-job-fit-scorer/index.html']:
            text=(ROOT/name).read_text()
            for paragraph in re.findall(r'<p[^>]*>(.*?)</p>',text,re.S):
                if '0.1.22' in paragraph:
                    self.assertNotIn('2026-09-03',paragraph)
                    self.assertNotIn('September 3, 2026',paragraph)
            self.assertIn('AkjZ6lVDultxapjdP',text)
        active_docs = ['README.md', 'docs/integration-compatibility.md', 'docs/implementation-plan.md',
                       'integrations/api/README.md', 'integrations/mcp/README.md',
                       'integrations/n8n/README.md', 'integrations/n8n/template-listing.md',
                       'integrations/make/README.md', 'integrations/make/template-listing.md',
                       'integrations/zapier/README.md']
        for name in active_docs:
            self.assertNotIn('0.1.12', (ROOT/name).read_text(), name)
        evidence=json.loads((ROOT/'integrations/evidence/ai-job-fit-scorer.json').read_text())
        self.assertEqual(evidence['currentActorRun']['resolvedBuildNumber'],'0.1.22')
        self.assertEqual(evidence['currentActorRun']['datasetRows'],len(self.rows))
        self.assertEqual(evidence['currentActorRun']['chargedEventCounts']['job-fit-result'],self.summary['billing']['chargedCount'])

    def test_bundled_schema_copies_match_public_contracts(self):
        for p in (SKILL/'references').glob('*.schema.json'):
            self.assertEqual(p.read_bytes(),(ROOT/'integrations/shared'/p.name).read_bytes())
            self.assertEqual(p.read_bytes(),(ROOT/'website/contracts'/p.name).read_bytes())

    def test_installed_skill_works_without_repository(self):
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)
            result=subprocess.run([sys.executable,str(ROOT/'scripts/install_skill.py'),'--skill','ai-job-fit-scorer','--client','both','--target',temp],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            for root in ['.agents','.claude']:
                skill=target/root/'skills/ai-job-fit-scorer'
                self.assertFalse(any(skill.rglob('*.pyc')))
                result=subprocess.run([sys.executable,str(skill/'scripts/validate_run_summary.py')],input=json.dumps(self.summary),capture_output=True,text=True,cwd=temp)
                self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__': unittest.main()
