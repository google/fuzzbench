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
        code_regions = coverage_utils.extract_covered_regions_from_summary_json(summary_json_file, 2)

        cmp_code_regions = code_regions.copy()
        # final list for JSON
        regions_info = []
        # keeping track reduces execution cycles
        # keep track of regions iterated over already
        keep_track = []

        for region in code_regions:

            region_arr = region[:7]
            trial_id = region[7]
            trial_hits = region[8]

            if region[:7] not in keep_track:
                trials_covered = []
                trials_uncovered = []
                # start trial count from 0.
                count = 0
                # Start trial Count from 1 if region's hits is greater than 1
                # and append [trial_id, hits] of the current specimen
                if region[8] > 0:
                    count += 1
                    trials_covered.append([region[7], region[8]])
                # Else start count from zero and add the
                else:
                    count = 0
                    trials_uncovered.append(region[7])
                # obtains all he trials in the region was hit and not hit
                # obtain count for distinct trials covering it
                c = 0
                for cmp_region in cmp_code_regions:
                    if cmp_region[:7] not in keep_track:
                        if region[:7] == cmp_region[:7] and \
                                region[7] != cmp_region[7]:
                            # append only trial_id if the region was not covered
                            if cmp_region[8] == 0:
                                trials_uncovered.append(cmp_region[7])
                            # append [trial_id, hits] if the region was
                            # covered in another trial
                            else:
                                trials_covered.append([cmp_region[7],
                                                       cmp_region[8]])
                                count += 1

                # Constructing Json object for the region
                obj = {"region_arr": region[:7],
                       "covered_trial_nums_hits": trials_covered,
                       "not_covered_trial_ids": trials_uncovered,
                       "num_unq_trials_covered": count}
                # Adding to the list of all region objects
                regions_info.append(obj)
                # Adding to keep track (Later te same region is not repeated)
                keep_track.append(region[:7])
        region_data = {"Coverage_Data": regions_info}
        print(region_data)
        # asserting the length of covered regions to not be 15
        # Just checking the the JSON output
        self.assertNotEqual(len(code_regions), 15, msg='did not pass assertion 1')


def check_if_duplicates(list_of_elems):
    """ Check if given list contains any duplicates """
    for elem in list_of_elems:
        if list_of_elems.count(elem) > 1:
            return True
    return False


if __name__ == '__main__':
    unittest.main()
