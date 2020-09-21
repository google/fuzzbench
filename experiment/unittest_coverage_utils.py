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
        # keep track of regions iterated
        regions_track = []
        json_count = 1
        for region in code_regions:
            trials_covered = []
            trials_uncovered = []
            # start trial count from 0.
            count = 0

            # Start trial Count from 1 if region's hits is greater than 1
            if region[8] > 0:
                count += 1
                trials_covered.append([region[7], region[8]])
            else:
                count = 0
                trials_uncovered.append(region[7])

            # obtains all he trails in the region was hit and not hit
            # obtain count for distinct trials covering it
            for cmp_region in cmp_code_regions:
                if region[:7] == cmp_region[:7] and \
                        region[7] != cmp_region[7]:
                    if cmp_region[8] == 0:
                        trials_uncovered.append(cmp_code_regions[7])
                    else:
                        # append [trial_id, hits] if the region was covered in another trial
                        trials_covered.append([cmp_code_regions[7], cmp_code_regions[8]])
                        count += 1

            if region[:7] not in regions_track:
                regions_track.append(region[:7])
                obj = {"region_arr": region[:7], "covered_trial_nums_hits": trials_covered,
                       "uncovered_trial_nums": trials_uncovered, "num_unq_trial_covering": count}

                reg = {"region_arr": region[:7]}
                unq_trials_covered = {"covered_trial_nums_hits": trials_covered}
                unq_trials_uncovered = {"uncovered_trial_nums": trials_uncovered}
                total_unique_trials_covering = {"num_unq_trial_covering": count}
                region_obj = {str(json_count): [reg, unq_trials_covered,
                              unq_trials_uncovered, total_unique_trials_covering]}

                regions_info.append(obj)
                json_count += 1
            else:
                continue

        region_data = {"Coverage_Data": regions_info}

        print(region_data)
        # asserting the length of covered regions to be 15
        self.assertNotEqual(len(code_regions), 15, msg='did not pass assertion 1')



def check_if_duplicates(list_of_elems):
    """ Check if given list contains any duplicates """
    for elem in list_of_elems:
        if list_of_elems.count(elem) > 1:
            return True
    return False


if __name__ == '__main__':
    unittest.main()
