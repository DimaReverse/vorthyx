"""Differential unpack checks, including iterator effects and exceptions."""
import ast
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parent.parent
paths = [root / 'validation/fixtures/fixture_unpack_control.py',
         Path(sys.argv[1]) / 'dev/fixture_unpack_control.py']


def same(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(same(left[k], right[k]) for k in left)
    if isinstance(left, (list, tuple)):
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    return left == right


def run(path, name, values, fault):
    tree = ast.parse(path.read_text(encoding='utf8'))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    env = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), env)
    events = []
    class Items:
        def __iter__(self):
            events.append('iter')
            for index, value in enumerate(values):
                events.append(['next', index])
                if fault is not None and index == fault:
                    raise LookupError('fixture')
                yield value
            events.append('end')
    def fetch(value):
        events.append(['fetch', value])
        return Items()
    try:
        value = env[name](fetch, 'input') if name == 'unpacker' else env[name](Items())
        result = {'value': value}
    except Exception as exc:
        result = {'exception': type(exc).__name__, 'detail': str(exc)}
    result['events'] = events
    return result


cases = []
for name in ('unpack_direct', 'unpack_guard', 'unpacker', 'manual_next',
             'manual_two_iterators'):
    for values in ([], [1], [1, None], [1, False], [1, 2], [1, 2, 3], [1, 2, 3, 4]):
        for fault in (None, 0, 1, 2):
            before, after = (run(path, name, values, fault) for path in paths)
            cases.append({'name': name, 'values': values, 'fault': fault,
                          'matches': same(before, after), 'original': before, 'recovered': after})


def run_tracked(path, name, values, fault):
    tree = ast.parse(path.read_text(encoding='utf8'))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    env = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), env)
    events = []
    class Cursor:
        def __init__(self, number):
            self.number, self.index = number, 0
            events.append(['create', number])
        def __iter__(self):
            events.append(['cursor_iter', self.number])
            return self
        def __next__(self):
            index = self.index
            self.index += 1
            events.append(['next', self.number, index])
            if fault == index:
                raise LookupError('fixture')
            if isinstance(fault, tuple) and fault[1] == index:
                if fault[0] == 'stop_value':
                    raise StopIteration('fixture-stop')
                if fault[0] == 'runtime':
                    raise RuntimeError('fixture-runtime')
            if index >= len(values):
                raise StopIteration
            return values[index]
        def __del__(self):
            events.append(['destroy', self.number])
    class Items:
        def __init__(self):
            self.count = 0
        def __iter__(self):
            self.count += 1
            events.append(['iter', self.count])
            return Cursor(self.count)
    try:
        result = {'value': env[name](Items())}
    except Exception as exc:
        result = {'exception': type(exc).__name__, 'detail': str(exc)}
    result['events'] = events
    return result


for name in ('manual_next', 'manual_two_iterators'):
    for values in ([], [1, 2], [1, 2, 3], [1, 2, 3, 4]):
        for fault in (None, 0, 1, 2):
            before, after = (run_tracked(path, name, values, fault) for path in paths)
            cases.append({'name': name, 'values': values, 'fault': fault, 'tracked': True,
                          'matches': same(before, after), 'original': before, 'recovered': after})
    for kind in ('stop_value', 'runtime'):
        for position in (0, 1, 2):
            fault = (kind, position)
            before, after = (run_tracked(path, name, [1,2,3], fault) for path in paths)
            cases.append({'name': name, 'values': [1,2,3], 'fault': fault, 'tracked': True,
                          'matches': same(before, after), 'original': before, 'recovered': after})
out = Path(sys.argv[1]) / 'unpack_behavior.json'
out.write_text(json.dumps(cases, indent=2), encoding='utf8')
print(f'{sum(c["matches"] for c in cases)}/{len(cases)} cases match; {out}')
