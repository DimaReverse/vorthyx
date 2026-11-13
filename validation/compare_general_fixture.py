"""Isolated differential execution for the locally compiled fixture."""
import ast
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parent.parent
original = root / 'validation/fixtures/fixture_general_dispatch.py'
recovered = Path(sys.argv[1]) / 'dev/fixture_general_dispatch.py'


def same(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(same(left[k], right[k]) for k in left)
    if isinstance(left, (list, tuple)):
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    return left == right


def invoke(path, method, scenario):
    tree = ast.parse(path.read_text(encoding='utf8'))
    fn = next(node for node in tree.body
              if isinstance(node, ast.FunctionDef) and node.name == method)
    namespace = {}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), 'exec'), namespace)
    events = []
    class Product:
        def first(self):
            events.append('first')
            return 'left-result'
        def second(self, arg):
            events.append(('second', arg))
            return 'right-result'
    def factory(arg):
        events.append(('factory', arg))
        return Product()
    def provider(name):
        def call(arg):
            events.append((name, arg))
            if scenario.get('provider_error'):
                raise ValueError('provider failed')
            return ('source', scenario.get('result', 7))
        return call
    try:
        if method == 'build':
            result = namespace[method](factory, 'left', 'right')
        else:
            result = namespace[method](scenario['which'], provider('first'), provider('second'), 'input')
        result = {'value': result}
    except Exception as exc:
        result = {'exception': type(exc).__name__, 'detail': str(exc)}
    result['events'] = events
    return result


cases = []
for method, scenario in [
        ('build', {}),
        ('choose', {'which': 'first'}),
        ('choose', {'which': 'second'}),
        ('choose', {'which': 'unknown'}),
        ('choose', {'which': 'first', 'result': None}),
        ('choose', {'which': 'second', 'result': None}),
        ('choose', {'which': 'first', 'result': False}),
        ('choose', {'which': 'second', 'provider_error': True})]:
    before, after = (invoke(path, method, scenario) for path in (original, recovered))
    cases.append({'method': method, 'scenario': scenario, 'matches': same(before, after),
                  'original': before, 'recovered': after})
out = Path(sys.argv[1]) / 'fixture_behavior.json'
out.write_text(json.dumps(cases, indent=2), encoding='utf8')
print(f'{sum(c["matches"] for c in cases)}/{len(cases)} cases match; {out}')
