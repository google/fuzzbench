# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions andsss
# limitations under the License.
"""Plotting tests."""

import matplotlib.testing.compare as plt_cmp
import pandas as pd

from analysis import plotting


def test_pariwise_unique_coverage_heatmap_plot(tmp_path):
    """Tests that pairwise unique coverage heatmap looks as expected (even with
    a large number of fuzzers)."""
    fuzzer_num = 22

    fuzzers = [f'fuzzer-{i}' for i in range(fuzzer_num)]
    table_data = [range(1000, 1000 + fuzzer_num)] * fuzzer_num
    table_df = pd.DataFrame(table_data, index=fuzzers, columns=fuzzers)

    plotter = plotting.Plotter(fuzzers)
    image_path = tmp_path / 'out.png'
    plotter.write_pairwise_unique_coverage_heatmap_plot(table_df, image_path)

    golden_path = 'analysis/test_data/pairwise_unique_coverage_heatmap.png'
    plt_cmp.compare_images(image_path, golden_path, tol=0.01)


def test_unique_coverage_ranking_plot(tmp_path):
    """Tests that unique coverage ranking plot looks as expected (even with a
    large number of fuzzers)."""
    fuzzer_num = 22

    fuzzers = [f'fuzzer-{i}' for i in range(fuzzer_num)]
    unique_branchs = [10 * i for i in range(fuzzer_num)]
    total_branches = [1000] * fuzzer_num

    df = pd.DataFrame({
        'fuzzer': fuzzers,
        'unique_branches_covered': unique_branchs,
        'aggregated_edges_covered': total_branches
    })

    plotter = plotting.Plotter(fuzzers)
    image_path = tmp_path / 'out.png'
    plotter.write_unique_coverage_ranking_plot(df, image_path)

    golden_path = 'analysis/test_data/unique_coverage_ranking.png'
    plt_cmp.compare_images(image_path, golden_path, tol=0.01)
