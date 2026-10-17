"""Run each Bruno scenario against a fresh, unchanged course API.

Exit 1 means a real request/assertion failed; exit 2 means setup failed.
The bundled API deliberately fails the business-rule tests.
"""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COLLECTION = ROOT / 'bruno'


def port_in_use():
    with socket.socket() as connection:
        return connection.connect_ex(('127.0.0.1', 5000)) == 0


def safe_body(body):
    if isinstance(body, dict):
        return {key: ('[redacted]' if key.lower() in {'accesstoken', 'authorization', 'password'} else safe_body(value)) for key, value in body.items()}
    if isinstance(body, list):
        return [safe_body(value) for value in body]
    if isinstance(body, str) and '<!doctype html>' in body.lower():
        return '[HTML error response omitted; see HTTP status]'
    return body


def report_requests(raw):
    if isinstance(raw, list):
        for entry in raw:
            yield from report_requests(entry)
    elif isinstance(raw, dict) and 'results' in raw:
        yield from report_requests(raw['results'])
    elif isinstance(raw, dict):
        yield raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', help='Run a single scenario folder')
    parser.add_argument('--collection', type=Path, default=DEFAULT_COLLECTION)
    parser.add_argument('--report-dir', type=Path, default=ROOT / 'reports')
    args = parser.parse_args()
    collection = args.collection.resolve()
    reports = args.report_dir.resolve()
    raw_dir = reports / 'raw'
    raw_dir.mkdir(parents=True, exist_ok=True)
    python = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    cli = ROOT / 'node_modules/@usebruno/cli/bin/bru.js'
    if not python.exists() or not cli.exists():
        raise RuntimeError('Create .venv, install requirements.txt, and run npm ci first.')
    if port_in_use():
        raise RuntimeError('Port 5000 is occupied. Stop the existing API; no existing process was stopped.')
    scenarios = sorted(path for path in collection.iterdir() if path.is_dir() and path.name[:2].isdigit())
    if args.scenario:
        scenarios = [path for path in scenarios if path.name == args.scenario]
    if not scenarios:
        raise RuntimeError('No matching scenario folders.')
    environment = collection / 'environments/local.bru'
    template = collection / 'environments/local.example.bru'
    if not template.exists():
        raise RuntimeError('The collection needs environments/local.example.bru.')
    template_text = template.read_text(encoding='utf-8')
    output = []
    failed = False
    opener = build_opener(ProxyHandler({}))
    for scenario in scenarios:
        if port_in_use():
            raise RuntimeError('Port 5000 became occupied between scenarios.')
        environment.write_text(template_text, encoding='utf-8')
        env = os.environ.copy()
        env.update({'FLASK_DEBUG': '0', 'PYTHONUNBUFFERED': '1', 'NO_PROXY': 'localhost,127.0.0.1', 'no_proxy': 'localhost,127.0.0.1'})
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        log_path = reports / f'server-{scenario.name}.log'
        print(f'\n=== {scenario.name}: fresh API ===', flush=True)
        with log_path.open('w', encoding='utf-8') as log:
            server = subprocess.Popen([str(python), '-m', 'flask', '--app', str(ROOT / 'auntie-som-noodle-api/app.py'), 'run', '--host', '127.0.0.1', '--port', '5000', '--no-debugger', '--no-reload'], cwd=ROOT, env=env, stdout=log, stderr=log, creationflags=flags)
            try:
                deadline = time.monotonic() + 20
                while True:
                    if server.poll() is not None:
                        raise RuntimeError(f'API failed to start; inspect {log_path}')
                    try:
                        with opener.open('http://127.0.0.1:5000/menu', timeout=1) as response:
                            menu = json.load(response)
                        if [(item['id'], item['stock']) for item in menu] != [(1, 2), (2, 1)]:
                            raise RuntimeError('API did not start with clean inventory.')
                        break
                    except OSError:
                        if time.monotonic() > deadline:
                            raise RuntimeError('API readiness timed out.')
                        time.sleep(0.1)
                raw_path = raw_dir / f'{scenario.name}.json'
                raw_path.unlink(missing_ok=True)
                # No --bail: all requests and assertions must execute.
                result = subprocess.run(['node', str(cli), 'run', scenario.name, '--env', 'local', '--reporter-json', str(raw_path), '--reporter-skip-all-headers'], cwd=collection, env=env, timeout=180)
                if result.returncode not in (0, 1) or not raw_path.exists():
                    raise RuntimeError(f'Bruno setup/execution failed with exit {result.returncode}.')
                failed |= result.returncode != 0
                requests = list(report_requests(json.loads(raw_path.read_text(encoding='utf-8'))))
                expected_requests = len([path for path in scenario.glob('*.bru') if path.name != 'folder.bru'])
                if len(requests) != expected_requests or any(request.get('error') or not request.get('testResults') for request in requests):
                    raise RuntimeError(f'{scenario.name}: missing requests, script failure, or transport error; inspect the raw report.')
                for request in requests:
                    response = request.get('response') or {}
                    tests = request.get('testResults') or []
                    assertions = request.get('assertionResults') or []
                    output.append({'scenario': scenario.name, 'name': request.get('name'), 'path': request.get('path'), 'status': response.get('status'), 'body': safe_body(response.get('data')), 'tests': tests, 'assertions': assertions, 'error': str(request.get('error')) if request.get('error') else None})
            finally:
                # Windows virtualenv's python.exe is a redirector; stop its owned
                # child process too, otherwise Flask survives between scenarios.
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(server.pid), '/T', '/F'], capture_output=True)
                else:
                    server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)
                environment.write_text(template_text, encoding='utf-8')
                deadline = time.monotonic() + 10
                while port_in_use() and time.monotonic() < deadline:
                    time.sleep(0.1)
    tests = [test for request in output for test in request['tests'] + request['assertions']]
    passing = sum(test.get('status') == 'pass' for test in tests)
    summary = {'requests': len(output), 'checks': len(tests), 'passed': passing, 'failed': len(tests) - passing, 'scenarios': len(scenarios), 'python': subprocess.check_output([str(python), '--version'], text=True).strip(), 'node': subprocess.check_output(['node', '--version'], text=True).strip(), 'brunoCli': json.loads((ROOT / 'node_modules/@usebruno/cli/package.json').read_text())['version'], 'results': output}
    (reports / 'audit-results.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    rows = ['# Bruno audit results', '', f"{summary['requests']} requests; {summary['checks']} checks; {summary['passed']} passed; {summary['failed']} failed.", '', 'Failures are preserved against the correct contract. Each scenario used a fresh API.', '', '| Scenario | Request | HTTP | Failing check |', '| --- | --- | --- | --- |']
    for request in output:
        for test in request['tests'] + request['assertions']:
            if test.get('status') != 'pass':
                rows.append(f"| {request['scenario']} | {request['name']} | {request['status']} | {test.get('description', test.get('name', 'unnamed'))} |")
    (reports / 'audit-results.md').write_text('\n'.join(rows) + '\n', encoding='utf-8')
    print(f"\nReport: {reports / 'audit-results.md'}")
    print(f"{len(output)} requests, {passing} passing checks, {len(tests) - passing} failing checks")
    return 1 if failed else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (RuntimeError, subprocess.SubprocessError) as error:
        print(f'Setup error: {error}', file=sys.stderr)
        sys.exit(2)
