import unittest
import os
import sys
from pyfakefs.fake_filesystem_unittest import TestCase
import pandas as pd

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
        # cmp_covered_regions = covered_regions.copy()
        cmp_covered_regions = [[7, 12, 12, 2, 0, 0, 0, 2],
                               [7, 12, 12, 2, 0, 0, 0, 54],
                               [7, 12, 12, 2, 0, 0, 0, 5],
                               [7, 12, 12, 2, 0, 0, 0, 2],
                               [2, 37, 6, 2, 0, 0, 0, 4],
                               [3, 24, 3, 30, 0, 0, 0, 4],
                               [3, 32, 3, 35, 0, 0, 0, 4],
                               [3, 37, 3, 48, 0, 0, 0, 4],
                               [1, 16, 1, 28, 1, 0, 0, 4],
                               [1, 17, 1, 20, 1, 0, 0, 4],
                               [1, 24, 1, 27, 1, 0, 0, 4],
                               [2, 37, 6, 2, 0, 0, 0, 2],
                               [3, 24, 3, 30, 0, 0, 0, 2],
                               [3, 32, 3, 35, 0, 0, 0, 2],
                               [3, 37, 3, 48, 0, 0, 0, 2],
                               [1, 16, 1, 28, 1, 0, 0, 2],
                               [1, 17, 1, 20, 1, 0, 0, 2],
                               [1, 24, 1, 27, 1, 0, 0, 2]]

        for coverage in covered_regions:
            count = 1
            for cmp_coverage in cmp_covered_regions:
                if coverage[:7] == cmp_coverage[:7] and coverage[7] != cmp_coverage[7]:
                    count += 1
                else:
                    continue
            coverage[7] = count

        print(covered_regions)

        distinct_covered_regions = []
        for region in covered_regions:
            if region not in distinct_covered_regions:
                distinct_covered_regions.append(region)

        # all the region are covered by 3 distinct trials, denoted by the [8] element in the array
        # output:
        #   0-6th element - region
        #   7th element - trial.id
        #   8th element - distinct trials covering the same region
        print(distinct_covered_regions)
        self.assertEqual(len(covered_regions), 15)


if __name__ == '__main__':
    unittest.main()
