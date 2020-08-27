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
wget https://www.fuzzbench.com/reports/sample/data.csv.gz
PYTHONPATH=<fuzzbench_root> python3 analysis/generate_report.py \
  [experiment_name] \
  --report-dir ~/my-report \
  --from-cached-data
```

You can find the link to the raw data file at the bottom of each [previously
published report](https://www.fuzzbench.com/reports/index.html).

You can generate different types of reports (see available
[templates](https://github.com/google/fuzzbench/tree/master/analysis/report_templates)).
For example, to generate a more detailed report with more analysis results
(i.e., multiple ranking methods and statistical tests), use the `--report_type
experimental` flag. We also encourage you to add your own templates and report
types to the library.

Check out the rest of the command line options of the tool with:

```bash
PYTHONPATH=<fuzzbench_root> python3 analysis/generate_report.py --help
```

## Notebooks

Another way to do custom analysis is to use Jupyter / Colab notebooks. You can
find some example notebooks
[here](https://github.com/google/fuzzbench/tree/master/analysis/notebooks).

_If you do some custom analysis that might be useful for others as well, please
consider adding it to the analysis library!_
