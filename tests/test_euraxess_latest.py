from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EuraxessLatestTests(unittest.TestCase):
    def test_mcp_accepts_future_build_and_rejects_missing_evidence(self):
        spec = importlib.util.spec_from_file_location('latest_smoke', ROOT / 'integrations/mcp/scripts/smoke_test.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        valid = {'buildId': 'futureImmutableBuild', 'buildNumber': '1.0.999'}
        module._require_build(valid, 'latest')
        for invalid in [{}, {'buildNumber': '1.0.999'}, {'buildId': 'x', 'buildNumber': 'latest'}, {'buildId': ' ', 'buildNumber': '1.0.999'}]:
            with self.subTest(invalid=invalid), self.assertRaises(RuntimeError):
                module._require_build(invalid, 'latest')
        with self.assertRaises(RuntimeError):
            module._require_build(valid, '1.0.2')

    def test_n8n_retains_build_identity_and_rejects_failed_or_unidentified_runs(self):
        workflow = json.loads((ROOT / 'integrations/n8n/euraxess-jobs-to-google-sheets.json').read_text())
        code = next(n['parameters']['jsCode'] for n in workflow['nodes'] if n['name'] == 'Validate terminal run')
        runner = "const p=JSON.parse(require('fs').readFileSync(0,'utf8')); const fn=new Function('$input','$',p.code); try {process.stdout.write(JSON.stringify(fn({first:()=>({json:p.run})},()=>({first:()=>({json:{actorBuild:'latest'}})}))));} catch(e) {process.stderr.write(String(e));process.exit(1);}"
        valid = {'id': 'run', 'status': 'SUCCEEDED', 'exitCode': 0, 'buildId': 'futureImmutableBuild', 'buildNumber': '1.0.999', 'defaultDatasetId': 'dataset'}
        def run(value):
            return subprocess.run(['node', '-e', runner], input=json.dumps({'code': code, 'run': value}), text=True, capture_output=True)
        result = run(valid)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)[0]['json']
        self.assertEqual(output['buildId'], valid['buildId'])
        self.assertEqual(output['buildNumber'], valid['buildNumber'])
        for delta in [{'buildId': ''}, {'buildNumber': 'latest'}, {'status': 'FAILED'}, {'exitCode': 1}]:
            with self.subTest(delta=delta):
                self.assertNotEqual(run({**valid, **delta}).returncode, 0)

    def test_make_checks_success_and_retains_immutable_fields(self):
        blueprint = json.loads((ROOT / 'integrations/make/euraxess-jobs-to-google-sheets.blueprint.json').read_text())
        modules = {m['id']: m for m in blueprint['flow']}
        variables = {v['name']: v['value'] for v in modules[2]['mapper']['variables']}
        self.assertEqual(variables['actorbuild'], 'latest')
        self.assertEqual(variables['resolvedbuildid'], '{{1.buildId}}')
        self.assertEqual(variables['resolvedbuildnumber'], '{{1.buildNumber}}')
        clause = modules[3]['filter']['conditions'][0]
        valid = {'{{1.status}}': 'SUCCEEDED', '{{1.buildNumber}}': '1.0.999', '{{1.buildId}}': 'futureImmutableBuild', '{{1.output.runSummary}}': 'https://example.com/summary', '{{1.exitCode}}': 0, '{{2.actorbuild}}': 'latest'}
        def matches(values):
            for condition in clause:
                expression = condition['a']
                if expression.startswith('{{length(trim('):
                    field = expression[len('{{length(trim('):-len('))}}')]
                    actual = len(str(values.get('{{' + field + '}}') or '').strip())
                elif expression.startswith('{{replace('):
                    field, pattern, replacement = re.fullmatch(r'\{\{replace\(([^;]+); "/(.*)/"; "(.*)"\)\}\}', expression).groups()
                    actual = re.sub(pattern, replacement, str(values.get('{{' + field + '}}') or ''))
                else:
                    actual = values.get(expression)
                op = condition['o']
                if op == 'exist':
                    ok = actual is not None
                elif op == 'number:equal':
                    ok = actual is not None and float(actual) == float(condition['b'])
                elif op == 'number:greater':
                    ok = actual is not None and float(actual) > float(condition['b'])
                elif op == 'text:equal':
                    ok = actual == condition['b']
                else:
                    raise AssertionError(op)
                if not ok:
                    return False
            return True
        self.assertTrue(matches(valid))
        for delta in [{'{{1.buildId}}': None}, {'{{1.buildNumber}}': None}, {'{{1.buildNumber}}': 'latest'}, {'{{1.buildNumber}}': ''}, {'{{1.buildId}}': '   '}, {'{{1.status}}': 'FAILED'}, {'{{1.exitCode}}': 1}, {'{{2.actorbuild}}': '1.0.999'}]:
            self.assertFalse(matches({**valid, **delta}))
