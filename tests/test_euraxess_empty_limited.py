"""Exercise the published zero-result limit outcome across consumers."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
SKILL=ROOT/'.agents/skills/euraxess-enrich-translate-normalize-scraper'


def summary():
    return {'schemaVersion':'nomad-agent-run-summary-v4','status':'empty-limited','startedAt':'2026-09-05T10:00:00Z','finishedAt':'2026-09-05T10:00:01Z','resultsLimited':True,'delivered':0,'retry':{'recommended':False,'afterSeconds':None}}


def invalid_cases():
    for field,value in [('delivered',1),('resultsLimited',False),('retry',{'recommended':True,'afterSeconds':5}),('retry',{'recommended':False,'afterSeconds':5})]:
        x=summary();x[field]=value;yield x


class EmptyLimitedTests(unittest.TestCase):
    def test_python_consumers_accept_limited_zero_and_reject_inconsistent_states(self):
        for path in [ROOT/'integrations/shared/validate_run_summary.py',SKILL/'scripts/validate_run_summary.py']:
            spec=importlib.util.spec_from_file_location('summary_validator',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            self.assertEqual(module.validate_run_summary(summary()),summary())
            for item in invalid_cases():
                with self.subTest(path=path,value=item), self.assertRaises(ValueError):module.validate_run_summary(item)

    def test_n8n_executes_limited_zero_without_retry(self):
        workflow=json.loads((ROOT/'integrations/n8n/euraxess-jobs-to-google-sheets.json').read_text())
        code=next(n['parameters']['jsCode'] for n in workflow['nodes'] if n['name']=='Validate run status')
        runner='''const p=JSON.parse(require('fs').readFileSync(0,'utf8')); const fn=new Function('$input','$','$runIndex',p.code); const input={first:()=>({json:p.summary})}; const query=name=>({first:()=>({json:name==='Configuration'?{maxRescheduleRetries:1}:{}})}); try{process.stdout.write(JSON.stringify(fn(input,query,0)));}catch(e){process.stderr.write(String(e));process.exit(1);}'''
        def run(value):return subprocess.run(['node','-e',runner],input=json.dumps({'code':code,'summary':value}),text=True,capture_output=True)
        result=run(summary());self.assertEqual(result.returncode,0,result.stderr);out=json.loads(result.stdout)[0]['json'];self.assertFalse(out['retryRecommended']);self.assertTrue(out['searchIncomplete']);self.assertEqual(out['runSummary']['delivered'],0)
        for value in invalid_cases():self.assertNotEqual(run(value).returncode,0)

    def test_make_zero_limited_route_is_bounded_and_has_no_retry(self):
        blueprint=json.loads((ROOT/'integrations/make/euraxess-jobs-to-google-sheets.blueprint.json').read_text())
        clauses=blueprint['flow'][3]['routes'][1]['flow'][0]['filter']['conditions']
        clause=next(c for c in clauses if any(x.get('b')=='empty-limited' for x in c))
        def matches(value,count=0):
            values={'{{3.statusCode}}':200,'{{3.data.schemaVersion}}':value['schemaVersion'],'{{3.data.status}}':value['status'],'{{3.data.delivered}}':value['delivered'],'{{3.data.resultsLimited}}':value['resultsLimited'],'{{3.data.retry.recommended}}':value['retry']['recommended'],'{{3.data.retry.afterSeconds}}':value['retry']['afterSeconds'],'{{1.stats.datasetItems}}':count}
            for c in clause:
                actual=values[c['a']];op=c['o'];expected=c.get('b')
                if op=='notexist':ok=actual is None
                elif op=='number:equal':ok=float(actual)==float(expected)
                elif op=='boolean:equal':ok=actual is expected
                elif op=='text:equal':ok=actual==expected
                else:raise AssertionError(op)
                if not ok:return False
            return True
        self.assertTrue(matches(summary()))
        self.assertFalse(matches(summary(),count=1))
        for value in invalid_cases():self.assertFalse(matches(value))
        retry=blueprint['flow'][3]['routes'][0]['flow'][0]['filter']['conditions']
        self.assertTrue(all(any(x.get('a')=='{{3.data.status}}' and x.get('b')=='partial' for x in c) for c in retry))
