"""Prove CI partitioning keeps every collected test exactly once."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

RUNNER = Path(__file__).resolve().parents[1] / "ci_pytest.py"
spec = importlib.util.spec_from_file_location("ci_pytest", RUNNER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ShardingTests(unittest.TestCase):
    def test_complete_disjoint_and_order_independent(self):
        ids = [f"tests/test_{i}.py::test_case[{j}]" for i in range(17) for j in range(i + 1)]
        assignments = module.assign_files(ids, 3)
        self.assertEqual(assignments, module.assign_files(list(reversed(ids)), 3))
        partitions = [{n for n in ids if assignments[n.split('::')[0]] == shard} for shard in range(3)]
        self.assertEqual(set.union(*partitions), set(ids))
        self.assertEqual(sum(map(len, partitions)), len(ids))
        self.assertTrue(all(partitions))
        self.assertLessEqual(max(map(len, partitions)) - min(map(len, partitions)), 17)

    def test_actual_pytest_collection_includes_parameters_and_preserves_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for i in range(3):
                (root / f"test_{i}.py").write_text(
                    "import pytest\n"
                    "@pytest.mark.parametrize('value', [1, 2])\n"
                    f"def test_value(value):\n    assert {i} != 1\n"
                )
            seen = []
            codes = []
            for shard in range(1, 4):
                command = [sys.executable, str(RUNNER), '--shard', f'{shard}/3', '-q', str(root)]
                collected = subprocess.run(command + ['--collect-only'], cwd=root, capture_output=True, text=True)
                self.assertEqual(collected.returncode, 0, collected.stdout + collected.stderr)
                seen.extend(line for line in collected.stdout.splitlines() if '::test_value[' in line)
                result = subprocess.run(command, cwd=root, capture_output=True, text=True)
                codes.append(result.returncode)
            self.assertEqual(len(seen), 6)
            self.assertEqual(len(set(seen)), 6)
            self.assertEqual(sorted(codes), [0, 0, 1])

    def test_collection_failure_and_empty_shard_stay_nonzero(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            test = root / "test_sample.py"
            test.write_text("def test_ok(): assert True\n")
            command = [sys.executable, str(RUNNER), '--shard', '2/2', '-q', str(root)]
            empty = subprocess.run(command, cwd=root, capture_output=True, text=True)
            self.assertEqual(empty.returncode, 5, empty.stdout + empty.stderr)
            test.write_text("raise RuntimeError('broken collection')\n")
            broken = subprocess.run(command, cwd=root, capture_output=True, text=True)
            self.assertEqual(broken.returncode, 2, broken.stdout + broken.stderr)

    def test_invalid_shard_is_an_error(self):
        for value in ('0/3', '4/3', '1/0', 'bad'):
            result = subprocess.run([sys.executable, str(RUNNER), '--shard', value], capture_output=True)
            self.assertEqual(result.returncode, 2)


if __name__ == '__main__':
    unittest.main()
