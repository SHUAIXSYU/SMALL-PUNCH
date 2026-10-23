"""Explicit synthetic test allowlist; no optimizer or solver calls."""
from datetime import datetime
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT),str(Path(__file__).resolve().parent)]
suite=unittest.TestSuite()
paths=['run/run_015/artifacts/test_fd_loss.py','run/run_016/artifacts/test_loss_qualification.py',
       'run/run_017/artifacts/test_sensitivity_analysis.py']
for i,rel in enumerate(paths):
    spec=importlib.util.spec_from_file_location('synthetic_'+str(i),ROOT/rel)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
stream=io.StringIO()
result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
out=ROOT/'run/run_017/artifacts'
with (out/'test_log.txt').open('x',encoding='utf8') as f:f.write(stream.getvalue())
data=dict(observed_at=datetime.now().astimezone().isoformat(),interpreter=sys.executable,python=sys.version,
          tests_run=result.testsRun,successful=result.wasSuccessful(),failures=len(result.failures),
          errors=len(result.errors),scope='19 Loss + 9 sensitivity synthetic tests; no new FE',test_files=paths)
with (out/'test_results.json').open('x',encoding='utf8') as f:json.dump(data,f,indent=2)
print(json.dumps(data,indent=2))
if not result.wasSuccessful():raise SystemExit(1)
