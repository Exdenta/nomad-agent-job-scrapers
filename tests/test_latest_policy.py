"""Latest is a selector; every execution still has an immutable identity."""
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LatestPolicyTests(unittest.TestCase):
    def test_every_maintained_descriptor_selects_latest(self):
        for path in (ROOT / 'integrations/mcp/examples').glob('*.mcp.json'):
            with self.subTest(path=path.name):
                self.assertEqual(json.loads(path.read_text())['callOptions']['build'], 'latest')
        for path in (ROOT / 'integrations/n8n').glob('*.json'):
            value = json.loads(path.read_text())
            for node in value.get('nodes', []):
                for field in node.get('parameters', {}).get('assignments', {}).get('assignments', []):
                    if field['name'] == 'actorBuild':
                        self.assertEqual(field['value'], 'latest', path.name)

    def test_future_numeric_build_is_accepted_but_identity_drift_is_rejected(self):
        harness = r"""
const fs = require('fs');
const workflow = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));
const drift = process.argv[2] === 'drift';
const started = {actId:process.argv[1].includes('ai-job-fit')?'mBRj1sgHTWmoPJEcb':'kqIdAA2UQiPdOtzEB',id:'run-future',buildId:'build-future',buildNumber:'9.8.7'};
const run = {...started,status:'SUCCEEDED',exitCode:0,defaultDatasetId:'dataset-future',defaultKeyValueStoreId:'store-future'};
if (drift) run.buildId = 'another-build';
global.$runIndex = 0;
global.$input = {first:()=>({json:{data:run}})};
global.$ = name => ({first:()=>({json:['Configuration','Alert configuration'].includes(name) ? {actorBuild:'latest'} : {data:started}})});
const node = workflow.nodes.find(n => ['Validate terminal run','Validate alert run'].includes(n.name));
process.stdout.write(JSON.stringify(new Function(node.parameters.jsCode)()));
"""
        for name in ['linkedin-jobs-to-google-sheets.json', 'euraxess-jobs-to-google-sheets.json', 'ai-job-fit-scorer-to-google-sheets.json', 'linkedin-daily-job-alerts.json']:
            for mode in ['future', 'drift']:
                with self.subTest(workflow=name, mode=mode):
                    result = subprocess.run(['node','-e',harness,str(ROOT/'integrations/n8n'/name),mode],capture_output=True,text=True)
                    if mode == 'future':
                        self.assertEqual(result.returncode, 0, result.stderr)
                    else:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertRegex(result.stderr, 'changed execution identity|terminal receipt changed the started run or build')

    def test_mcp_requires_actual_identity_and_latest_selector(self):
        spec = importlib.util.spec_from_file_location('latest_smoke', ROOT/'integrations/mcp/scripts/smoke_test.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        valid = {'buildNumber':'9.8.7','buildId':'future-build','options':{'build':'latest'}}
        module._require_build(valid, 'latest')
        for invalid in [valid | {'buildNumber':'latest'}, valid | {'buildId':None}, valid | {'options':{'build':'1.0.2'}}]:
            with self.assertRaises(RuntimeError): module._require_build(invalid, 'latest')
