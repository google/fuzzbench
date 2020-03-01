---
layout: default
title: Custom analysis and reports
parent: Developing FuzzBench
nav_order: 2
permalink: /developing-fuzzbench/custom_analysis_and_reports
---

# Custom analysis and reports
{: .no_toc}

- TOC
{:toc}

---

## Custom analysis and reports

The [default report]({{site.baseurl}}/reference/report/) shows the results of an
experiment using plots, ranking methods, and statistical tests that are commonly
used in the literature. However, these defaults are not the only way to rank
fuzzers, visualize results, or determine statistical significance.

We encourage researchers to look at the data from different points of view as
well. We provide a library of alternative analysis, statistical tests and
plotting options under the
[`analysis/`](https://github.com/google/fuzzbench/tree/master/analysis)
directory.

We invite researchers to contribute their own scripts for various tests and
visualization of the data to the library.

## Generating reports

You can use the `generate_report.py` tool for creating reports. For example, you
can re-generate the report from the raw data of our [sample
experiment](https://www.fuzzbench.com/reports/sample/index.html) like this:

```bash
mkdir ~/my-report; cd ~/my-report
wget https://www.fuzzbench.com/reports/sample/data.csv.zip
PYTHONPATH=<fuzzbench_root> python3 experiment/generate_report.py \
  [experiment_name] \
  --report_dir ~/my-report \
  --from_cached_data
```

You can also create a custom report using a template of your own (see
`--report_type` option). See all command line options with:

```bash
PYTHONPATH=<fuzzbench_root> python3 experiment/generate_report.py --help
```
