---
layout: default
title: Prerequisites
parent: Getting started
nav_order: 1
permalink: /getting-started/prerequisites/
---

# Prerequisites
{: .no_toc}

This page explains how to set up your environment for using FuzzBench.

- TOC
{:toc}

---

## Getting the code

Clone the FuzzBench repository to your machine by running the following command:

```bash
git clone https://github.com/google/fuzzbench
cd fuzzbench
git submodule update --init
```

## Installing prerequisites

### Docker

Install Docker using the instructions
[here](https://docs.docker.com/engine/installation).
Googlers can visit [go/installdocker](https://goto.google.com/installdocker).

If you want to run `docker` without `sudo`, you can
[create a docker group](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user).

**Note:** Docker images can consume significant disk space. Clean up unused
docker images periodically.

### Make

Install make for your linux distribution. E.g. for Ubuntu:

```bash
sudo apt-get install build-essential
```

### Python programming language

[Download Python 3.8](https://www.python.org/downloads/release/python-386/),
then install it.

If you already have Python installed, you can verify its version by running
`python3 --version`. The minimum required version is 3.8.

### Python package dependencies

Install the python dependencies by running the following command:

```bash
sudo apt-get install python3.8-dev python3.8-venv
make install-dependencies
```

This installs all the dependencies in a virtualenv `.venv`. Activate this
virtualenv before running further commands.

```bash
source .venv/bin/activate
```

You can exit from this virtualenv anytime using the `deactivate` command.

### Verification

You can verify that your local setup is working correctly by running the
presubmit checks.

```bash
make presubmit
```

### Formatting

You can format your changes using the following command:

```bash
make format
```

### Local Support

If you want to run FuzzBench [locally]({{ site.baseurl }}/running-a-local-experiment/#Running a local experiment)
on your own machine or servers, it needs `rsync` installed:
```bash
sudo apt-get install rsync
```
