"""Compare recovered control flow against the local fixture with stubs."""
import ast
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parent.parent
paths = [root / 'validation/fixtures/fixture_core_control.py',
         Path(sys.argv[1]) / 'dev/fixture_core_control.py']


def same(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(same(left[k], right[k]) for k in left)
    if isinstance(left, (list, tuple)):
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    return left == right


def invoke(path, method, which, value):
    tree = ast.parse(path.read_text(encoding='utf8'))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
              and n.name == method)
    namespace = {}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), 'exec'), namespace)
    events = []
    class EqualityResult:
        def __init__(self, answer):
            self.answer = answer
        def __bool__(self):
            events.append(('comparison_bool', self.answer))
            return self.answer
    class Selector:
        def __init__(self, answer):
            self.answer = answer
        def __eq__(self, other):
            events.append(('eq', other))
            return EqualityResult(self.answer == other)
        def __ne__(self, other):
            events.append(('ne', other))
            return False
    if isinstance(which, str) and which.startswith('selector_'):
        which = Selector(int(which[-1]))
    def make(name):
        def call(arg):
            events.append((name, arg))
            if value == 'raise-fixture':
                raise ValueError('fixture failure')
            return value
        return call
    try:
        result = {'value': namespace[method](which, make('first'), make('second'), 42)}
    except Exception as exc:
        result = {'exception': type(exc).__name__, 'detail': str(exc)}
    result['events'] = events
    return result


def invoke_simple(path, method, scenario):
    tree = ast.parse(path.read_text(encoding='utf8'))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == method)
    namespace = {}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), 'exec'), namespace)
    events = []
    class TruthValue:
        def __bool__(self):
            events.append('bool')
            if scenario == 'bool_error':
                raise ValueError('bool failed')
            return scenario == 'bool_true'
    class LengthValue:
        def __len__(self):
            events.append('len')
            if scenario == 'len_error':
                raise ValueError('len failed')
            return 1 if scenario == 'len_true' else 0
    def callback(name):
        def call():
            events.append(name)
            if scenario == name + '_error':
                raise ValueError(name + ' failed')
            return name + '_value'
        return call
    try:
        argument = (TruthValue() if scenario in ('bool_true', 'bool_false', 'bool_error') else
                    LengthValue() if scenario in ('len_true', 'len_false', 'len_error') else scenario)
        value = (namespace[method](argument) if method == 'invert' else
                 namespace[method](callback('left'), callback('right')))
        result = {'value': value}
    except Exception as exc:
        result = {'exception': type(exc).__name__, 'detail': str(exc)}
    result['events'] = events
    return result


cases = []
for method in ('dispatch', 'identity_false'):
    for which in (1, 2, 3):
        for value in (None, False, 0, 5, 'raise-fixture'):
            expected, actual = (invoke(path, method, which, value) for path in paths)
            cases.append({'method': method, 'which': which, 'input_result': value,
                          'original': expected, 'recovered': actual,
                          'matches': same(expected, actual)})
    for which in ('selector_1', 'selector_2', 'selector_3'):
        expected, actual = (invoke(path, method, which, 5) for path in paths)
        cases.append({'method': method, 'which': which, 'input_result': 5,
                      'original': expected, 'recovered': actual,
                      'matches': same(expected, actual)})
for method, scenarios in (('invert', [None, False, 0, '', [], 1, 'hello',
                                      'bool_true', 'bool_false', 'bool_error',
                                      'len_true', 'len_false', 'len_error']),
                          ('pair', ['normal', 'left_error', 'right_error'])):
    for scenario in scenarios:
        expected, actual = (invoke_simple(path, method, scenario) for path in paths)
        cases.append({'method': method, 'scenario': scenario, 'original': expected,
                      'recovered': actual, 'matches': same(expected, actual)})
out = Path(sys.argv[1]) / 'control_behavior.json'
out.write_text(json.dumps(cases, indent=2), encoding='utf8')
print(f'{sum(c["matches"] for c in cases)}/{len(cases)} cases match; {out}')
