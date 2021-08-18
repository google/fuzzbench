---
layout: default
title: FAQ
has_children: false
nav_order: 7
permalink: /faq/
---

# Frequently Asked Questions

- TOC
{:toc}
---

## Why do we need a fuzzer benchmarking platform?

Evaluating fuzz testing tools properly and rigorously is difficult, and
typically needs time and resources that most researchers do not have access to.
A study on
[Evaluating Fuzz Testing](https://dl.acm.org/doi/10.1145/3243734.3243804)
analyzed 32 fuzzing research papers and has
[found](http://www.pl-enthusiast.net/2018/08/23/evaluating-empirical-evaluations-for-fuzz-testing/)
that "_no paper adheres to a sufficiently high standard of evidence to justify
general claims of effectiveness_". This is a problem because it can lead to
[unreproducible](https://andreas-zeller.blogspot.com/2019/10/when-results-are-all-that-matters-case.html)
results.

We created FuzzBench, so that all researchers and developers can evaluate their
tools according to the
[best practices](https://andreas-zeller.blogspot.com/2019/10/when-results-are-all-that-matters.html)
and
[guidelines](http://www.sigplan.org/Resources/EmpiricalEvaluation),
with minimal effort and for free.

## Why are you measuring coverage? Isn't the point of fuzzing to find bugs?

We are planning to extend the system to measure bugs as well.

The most challenging part of fuzzing is generating inputs that exercise
different parts of the program. The effectiveness of a fuzzer doing this program
state discovery is best measured using a coverage metric -- this is why we
started with that. Measuring this with bugs would be difficult, because bugs are
typically sparse in a program. Coverage, on the other hand, is a great proxy
metric for bugs as well, as a fuzzer cannot find a bug in code that it's not
covering.

## Should I trust your results?

You don't have to. We made FuzzBench fully open source so that anybody can
reproduce the experiments. Also, we'd like FuzzBench to be a community driven
platform. Contributions and suggestions to make the platform better are welcome.

## How can I reproduce the results or run FuzzBench myself?

We are running the free FuzzBench service on Google Cloud, and the current
implementation has some Google Cloud specific bits in it. You can use the code
to run FuzzBench yourself on Google Cloud. Our docs explain how to do this
[here]({{ site.baseurl }}/running-your-own-experiment/running-an-experiment/).

We are also working on making it easier to run in other environments (local
cluster, other cloud providers, kubernetes, etc.). Community contributions for
making it easier to run on different platforms are more than welcome.

## Can I add my fuzzer?

Yes! In our initial launch, we have picked only a few fuzzers (e.g. AFL,
libFuzzer) to get things started. We welcome all researchers to add their tools
to the FuzzBench platform for automated, continuous, and free evaluation. Please
use the instructions provided [here]({{ site.baseurl}}/getting-started/adding-a-new-fuzzer/).

## Can I integrate someone else's fuzzer?

Sure. However, please make sure you have configured it properly. It's too easy
to misunderstand configuration details that can have an impact on the results.
If you can, please reach out to the authors to confirm your configuration looks
good to them.

## I'd like to get my fuzzer evaluated, but I don't want the results and/or code to be public yet. Can I use the FuzzBench service?

Probably yes. We run private experiments for this purpose.
Please reach out to us at fuzzbench@google.com. If we agree to benchmark your
fuzzer, please follow the guide on
[adding a new fuzzer]({{ site.baseurl }}/getting-started/adding-a-new-fuzzer/)
on how to integrate your fuzzer with FuzzBench.

You can ignore the sections on [Requesting an experiment]({{ site.baseurl }}/getting-started/adding-a-new-fuzzer/#requesting-an-experiment) and
[Submitting your integration]({{ site.baseurl }}/getting-started/adding-a-new-fuzzer/#submitting-your-integration).
Please test your fuzzer works with our benchmarks, we don't have CI to verify
this for private experiments.
Ideally, you should test all benchmarks using `make -j test-run-$FUZZER-all`.
This takes too long on most machines so you should at least test a few of them:
```
make test-run-$FUZZER-zlib_zlib_uncompress_fuzzer test-run-$FUZZER-libpng-1.2.56
```

You should also run `make presubmit` to validate the fuzzer's name and
integration code.
When your fuzzer is ready, send us a patch file that applies cleanly to
FuzzBench with `git apply <patch_file>`.

## How can you prevent researchers from optimizing their tools only for these benchmarks?

We have chosen a large and diverse set of real-world benchmarks precisely to
avoid technique over-fitting. These are some of the most widely used open source
projects that process a wide variety of input formats. We believe that the
evaluation results will generalize due to the size and diversity of our
benchmarks. However, we are always open to suggestions from the community to
improve it.

## What is your criteria for accepting a new benchmark?

We have picked a large and diverse set of real-world benchmarks. This includes
projects that are widely used and hence have a critical impact on infrastructure
and user security.

Many of these benchmarks come from the
[OSS projects](https://github.com/google/oss-fuzz/tree/master/projects) that are
integrated in our community fuzzing service
[OSS-Fuzz](https://github.com/google/oss-fuzz).

We welcome recommendations on adding a new benchmark on the FuzzBench platform.
It should satisfy these criteria:
* Should be a commonly used OSS project.
* Should have a non-trivial codebase (e.g. not a CRC32 implementation).

Please follow the instructions
[here]({{ site.baseurl }}/developing-fuzzbench/adding-a-new-benchmark/) to add
a new benchmark.

## I've found an issue with FuzzBench. What can I do?

Please [file an issue on GitHub](https://github.com/google/fuzzbench/issues/new)
or send a pull request fixing the problem.

## How can I cite FuzzBench in my paper?

You can use the following BibTeX entry:
{% raw %}
```
@inproceedings{FuzzBench,
  author = {Metzman, Jonathan and Szekeres, L\'{a}szl\'{o} and Maurice Romain Simon, Laurent and Trevelin Sprabery, Read and Arya, Abhishek},
  title = {{FuzzBench: An Open Fuzzer Benchmarking Platform and Service}},
  year = {2021},
  isbn = {9781450385626},
  publisher = {Association for Computing Machinery},
  address = {New York, NY, USA},
  url = {https://doi.org/10.1145/3468264.3473932},
  doi = {10.1145/3468264.3473932},
  booktitle = {Proceedings of the 29th ACM Joint Meeting on European Software Engineering Conference and Symposium on the Foundations of Software Engineering},
  pages = {1393–1403},
  numpages = {11},
  series = {ESEC/FSE 2021}
}
```
{% endraw %}
