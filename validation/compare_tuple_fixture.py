"""Compare tuple values, element order and exceptions in isolation."""
import ast
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent
PATHS = (ROOT / 'validation/fixtures/fixture_tuple_control.py',
         Path(sys.argv[1]) / 'dev/fixture_tuple_control.py')


def same(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(same(left[k], right[k]) for k in left)
    if isinstance(left, (list, tuple)):
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    return left == right


def invoke(path, method, failure):
    tree = ast.parse(path.read_text(encoding='utf8'))
    function = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == method)
    namespace = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
    events = []
    def callback(name):
        def call():
            events.append(name)
            if failure == name:
                raise ValueError(name + ' failed')
            return name + '_value'
        return call
    try:
        value = (namespace[method](callback('first'), callback('middle'), callback('last'))
                 if method == 'triple' else namespace[method](42, callback('produce')))
        return {'type': type(value).__name__, 'value': value, 'events': events}
    except Exception as exc:
        return {'exception': type(exc).__name__, 'detail': str(exc), 'events': events}


cases = []
for method, scenarios in (('triple', ('none','first','middle','last')),
                          ('mixed', ('none','produce'))):
    for scenario in scenarios:
        original, recovered = (invoke(path, method, scenario) for path in PATHS)
        cases.append({'method': method, 'scenario': scenario, 'original': original,
                      'recovered': recovered, 'matches': same(original, recovered)})
out = Path(sys.argv[1]) / 'tuple_behavior.json'
out.write_text(json.dumps(cases, indent=2), encoding='utf8')
print(f'{sum(case["matches"] for case in cases)}/{len(cases)} cases match; {out}')
