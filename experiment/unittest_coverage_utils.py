import unittest
import os
import sys
from pyfakefs.fake_filesystem_unittest import TestCase

file_dir = os.path.dirname('coverage_utils.py')
sys.path.append(file_dir)

from experiment import coverage_utils

TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'test_data')


def get_test_data_path(*subpaths):
    """Returns the path of |subpaths| relative to TEST_DATA_PATH."""
    return os.path.join(TEST_DATA_PATH, *subpaths)


class TestCoverageJson(TestCase):
    def setUp(self):
        self.setUpPyfakefs()

    def test_extract_covered_regions_from_summary_json(self):
        """Tests that extract_covered_regions_from_summary_json returns the covered
        regions from summary json file."""
        summary_json_file = get_test_data_path('cov_summary.json')
        self.fs.add_real_file(summary_json_file, read_only=False)
        covered_regions = coverage_utils.extract_covered_regions_from_summary_json(
            summary_json_file, 2)
        self.assertEqual(len(covered_regions), 15)


if __name__ == '__main__':
    unittest.main()
