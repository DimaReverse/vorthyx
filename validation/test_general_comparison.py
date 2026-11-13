"""Check that the differential scenarios exercise the intended paths."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent


class GeneralComparisonTests(unittest.TestCase):
    def test_original_matches_itself_for_all_scenarios(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / 'dev').mkdir()
            shutil.copyfile(ROOT / 'validation/fixtures/fixture_general_dispatch.py',
                            output / 'dev/fixture_general_dispatch.py')
            subprocess.run([sys.executable, str(ROOT / 'validation/compare_general_fixture.py'),
                            str(output)], check=True, capture_output=True, text=True)
            cases = json.loads((output / 'fixture_behavior.json').read_text(encoding='utf8'))
        self.assertEqual(len(cases), 8)
        self.assertTrue(all(case['matches'] for case in cases))
        values = [case['original'] for case in cases]
        self.assertEqual(values[4]['value'], 'failed')
        self.assertEqual(values[5]['value'], 'failed')
        self.assertIs(values[6]['value'], False)
        self.assertEqual(values[7]['exception'], 'ValueError')


if __name__ == '__main__':
    unittest.main()
