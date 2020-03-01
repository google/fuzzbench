---
layout: default
title: The report
parent: Reference
nav_order: 2
permalink: /reference/report/
---

# The report
{: .no_toc}

- TOC
{:toc}

---

## The default report

The default report (see
[sample](https://www.fuzzbench.com/reports/sample/index.html)) consists of an
experiment summary at the top, followed by the summary of each benchmark.

### Experiment summary

At the [top of the
report](https://www.fuzzbench.com/reports/sample/index.html#summary) we use a
critical difference diagram to summarize the experiment. It compares fuzzers
over all benchmarks, visualizing average ranks and statistical significance.
This diagram and the underlying methodology was introduced by
[Demsar](http://www.jmlr.org/papers/volume7/demsar06a/demsar06a.pdf), and is
often used in the field of machine learning to compare algorithms over multiple
data sets.

The line in the diagram represents the axis on which the the average ranks of
the fuzzers are shown. The average ranks are computed from the medians of the
reached coverage of each fuzzer on each benchmarks. (You can see the medians by
expanding the "Median coverages on each benchmark" table under the graph.) Lower
number in average rank is better (closer to "1st place"). In other words,
fuzzers placed more on the left are better.

Groups of fuzzers that are connected with bold lines are *not* significantly
different from each other. The *critical difference* (CD) is also shown at the
top of the plot, representing how far two fuzzers need to be on the axis to be
statistically significantly different. The critical difference is computed based
on a post-hoc [Nemenyi test](https://en.wikipedia.org/wiki/Nemenyi_test)
performed after the [Friedman
test](https://en.wikipedia.org/wiki/Friedman_test).

The pivot table under the critifical difference diagram shows the median reached
coverage numbers.

### Per-benchmark summary

Below the experiment summary, the report shows the result of each benchmark. The
default report show three plots:

- Bar plot of the median reached coverage of each fuzzer in order.
- Violin plot of the distribution of the reached coverages (including min, 25%,
  75%, max).
- Coverage growth plot aggregating individual trials (error band shows 95%
  confidence interval around the mean coverage).

The table under the plots show a statistical summary of reached coverage samples
for each fuzzer. This includes the number of trials, mean, median, standard
deviation.

Under the table we show a graphical summary pairwise statistical tests. The
default report uses pairwise two-tailed [Mann-Whitney U
tests](https://en.wikipedia.org/wiki/Mann%E2%80%93Whitney_U_test), recommended
by [Arcuri et al.](https://dl.acm.org/doi/10.1145/1985793.1985795). Green cells
in the plot indicate that the reached coverage distribution of a given fuzzer
pair is statistically significantly different from each other (α=0.05).

See how to create your own reports under [Custom analysis and
reports]({{site.baseurl}}/developing-fuzzbench/custom_analysis_and_reports/).
