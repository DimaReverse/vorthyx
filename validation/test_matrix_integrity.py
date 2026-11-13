"""Regression tests for coverage and isolation of matrix runs."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent


class MatrixIntegrityTests(unittest.TestCase):
    def test_unpack_comparator_covers_custom_exception_values(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / 'dev').mkdir()
            shutil.copyfile(ROOT / 'validation/fixtures/fixture_unpack_control.py',
                            output / 'dev/fixture_unpack_control.py')
            subprocess.run([sys.executable,str(ROOT / 'validation/compare_unpack_fixture.py'),
                            str(output)],check=True,capture_output=True,text=True)
            cases = json.loads((output / 'unpack_behavior.json').read_text(encoding='utf8'))
        self.assertEqual(len(cases),184)
        self.assertTrue(all(case['matches'] for case in cases))
        stop = next(case for case in cases if case.get('fault') == ['stop_value',1])
        self.assertEqual((stop['original']['exception'],stop['original']['detail']),
                         ('StopIteration','fixture-stop'))
        runtime = next(case for case in cases if case.get('fault') == ['runtime',2])
        self.assertEqual((runtime['original']['exception'],runtime['original']['detail']),
                         ('RuntimeError','fixture-runtime'))

    def test_tuple_comparator_exercises_element_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / 'dev').mkdir()
            shutil.copyfile(ROOT / 'validation/fixtures/fixture_tuple_control.py',
                            output / 'dev/fixture_tuple_control.py')
            subprocess.run([sys.executable, str(ROOT / 'validation/compare_tuple_fixture.py'),
                            str(output)], check=True, capture_output=True, text=True)
            cases = json.loads((output / 'tuple_behavior.json').read_text(encoding='utf8'))
        self.assertEqual(len(cases), 6)
        self.assertTrue(all(case['matches'] for case in cases))
        self.assertEqual([case['original']['events'] for case in cases if case['method'] == 'triple'],
                         [['first','middle','last'], ['first'], ['first','middle'],
                          ['first','middle','last']])

    def test_control_comparator_exercises_all_functions(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / 'dev').mkdir()
            shutil.copyfile(ROOT / 'validation/fixtures/fixture_core_control.py',
                            output / 'dev/fixture_core_control.py')
            subprocess.run([sys.executable, str(ROOT / 'validation/compare_core_fixture.py'),
                            str(output)], check=True, capture_output=True, text=True)
            cases = json.loads((output / 'control_behavior.json').read_text(encoding='utf8'))
        self.assertEqual(len(cases), 52)
        self.assertTrue(all(case['matches'] for case in cases))
        self.assertEqual({case['method'] for case in cases},
                         {'dispatch', 'identity_false', 'invert', 'pair'})
        self.assertEqual([case['original']['events'] for case in cases if case['method'] == 'pair'],
                         [['left', 'right'], ['left'], ['left', 'right']])
        truth = {case['scenario']: case['original'] for case in cases
                 if case['method'] == 'invert' and isinstance(case['scenario'], str)
                 and case['scenario'].startswith('bool_')}
        self.assertEqual(truth['bool_true'], {'value': 'yes', 'events': ['bool']})
        self.assertEqual(truth['bool_false'], {'value': 'no', 'events': ['bool']})
        self.assertEqual(truth['bool_error']['exception'], 'ValueError')
        length = {case['scenario']: case['original'] for case in cases
                  if case['method'] == 'invert' and isinstance(case['scenario'], str)
                  and case['scenario'].startswith('len_')}
        self.assertEqual(length['len_true'], {'value': 'yes', 'events': ['len']})
        self.assertEqual(length['len_false'], {'value': 'no', 'events': ['len']})
        self.assertEqual(length['len_error']['exception'], 'ValueError')
        selector = next(case for case in cases if case['method'] == 'dispatch'
                        and case.get('which') == 'selector_2')
        self.assertEqual(selector['original']['events'],
                         [['eq', 1], ['comparison_bool', False], ['eq', 2],
                          ['comparison_bool', True], ['second', 42]])

    def test_matrix_refuses_nonempty_output(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / 'keep.txt'
            marker.write_text('previous run', encoding='utf8')
            result = subprocess.run([sys.executable, str(ROOT / 'validation/run_matrix.py'),
                                     '--output', directory], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('new or empty directory', result.stderr)
            self.assertEqual(marker.read_text(encoding='utf8'), 'previous run')
            self.assertEqual(list(Path(directory).iterdir()), [marker])


if __name__ == '__main__':
    unittest.main()
