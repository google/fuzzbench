---
layout: default
title: Setting up a Google Cloud Project
parent: Running an experiment on your Cloud project
nav_order: 1
permalink: /running-a-cloud-experiment/setting-up-a-google-cloud-project/
---

# Setting up a Google Cloud Project

**NOTE**: Most users of FuzzBench should simply [add a fuzzer]({{ site.baseurl
}}/getting-started/adding-a-new-fuzzer/) and use the FuzzBench service. This
page isn't needed for using the FuzzBench service. This page explains
how to set up a Google Cloud project for running an [experiment]({{ site.baseurl
}}/reference/glossary/#Experiment) for the first time. We don't recommend
running experiments on your own for most users. Validating results from the
FuzzBench service is a good reason to run an experiment on your own.

Currently, FuzzBench requires Google Cloud to run experiments (though this may
change, see
[FAQ]({{ site.baseurl }}/faq/#how-can-i-reproduce-the-results-or-run-fuzzbench-myself)).

The rest of this page will assume all commands are run from the root of
FuzzBench.

## Create the Project

* [Create a new Google Cloud Project](https://console.cloud.google.com/projectcreate).

* Enable billing when prompted on the Google Cloud website.

* Set `$PROJECT_NAME` in the environment:

```bash
export PROJECT_NAME=<your-project-name>
```

For the rest of this page, replace `$PROJECT_NAME` with the name of the
project you created.

* [Install Google Cloud SDK](https://cloud.google.com/sdk/install).

* Set your default project using gcloud:

```bash
gcloud config set project $PROJECT_NAME
```

## Set up the database

* [Enable the Compute Engine API](https://console.cloud.google.com/apis/library/compute.googleapis.com?q=compute%20engine)

* Create a PostgreSQL (we use PostgreSQL 11) instance using
[Google Cloud SQL](https://console.cloud.google.com/sql/create-instance-postgres).
This will take a few minutes.
We recommend using "us-central1" as the region and "us-central1-a" as the zone.
Certain links provided in this page assume "us-central1".
Note that the region you choose should be the region you use later for running
experiments.

* For the rest of this page, we will use `$PROJECT_REGION`, `$PROJECT_ZONE`,
`$POSTGRES_INSTANCE`, and `$POSTGRES_PASSWORD` to refer to the region of the
PostgreSQL instance you created, its name, and its password. Set them in your
environment:

```bash
export PROJECT_REGION=<your-postgres-region>
export PROJECT_ZONE=<your-postgres-zone>
export POSTGRES_INSTANCE=<your-postgres-instance-name>
export POSTGRES_PASSWORD=<your-postgres-password>
```

* [Download and install cloud_sql_proxy](https://cloud.google.com/sql/docs/postgres/sql-proxy)

```bash
wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O cloud_sql_proxy
```

* Connect to your postgres instance using cloud_sql_proxy:

```bash
./cloud_sql_proxy -instances=$PROJECT_NAME:$PROJECT_REGION:$POSTGRES_INSTANCE=tcp:5432
```

* (optional, but recommended) Connect to your instance to ensure you
   have all of the details right:

```bash
psql "host=127.0.0.1 sslmode=disable user=postgres"
```

Use `$POSTGRES_PASSWORD` when prompted.

* Initialize the postgres database:

```bash
PYTHONPATH=. alembic upgrade head
```

If this command fails, double check you set `POSTGRES_PASSWORD` correctly.
At this point you can kill the `cloud_sql_proxy` process.

## Google Cloud Storage buckets

* Set up Google Cloud Storage Buckets by running the commands below:

```bash
# Bucket for storing experiment artifacts such as corpora, coverage binaries,
# crashes etc.
gsutil mb gs://$DATA_BUCKET_NAME

# Bucket for storing HTML reports.
gsutil mb gs://$REPORT_BUCKET_NAME
```

You can pick any (globally unique) names you'd like for `$DATA_BUCKET_NAME` and
`$REPORT_BUCKET_NAME`.

* Make the report bucket public so it can be viewed from your browser:

```bash
gsutil iam ch allUsers:objectViewer gs://$REPORT_BUCKET_NAME
```

## Dispatcher image and container registry setup

* Build the dispatcher image:

```bash
docker build -f docker/dispatcher-image/Dockerfile \
    -t gcr.io/$PROJECT_NAME/dispatcher-image docker/dispatcher-image/
```

FuzzBench uses an instance running this image to manage most of the experiment.

* [Enable Google Container Registry API](https://console.cloud.google.com/apis/api/containerregistry.googleapis.com/overview)
to use the container registry.

* Push `dispatcher-image` to the docker registry:

```bash
docker push gcr.io/$PROJECT_NAME/dispatcher-image
```

* [Switch the registry's visibility to public](https://console.cloud.google.com/gcr/settings).

## Enable required APIs

* [Enable the IAM API](https://console.cloud.google.com/apis/api/iam.googleapis.com/landing)
so that FuzzBench can authenticate to Google Cloud APIs and services.

* [Enable the error reporting API](https://console.cloud.google.com/apis/library/clouderrorreporting.googleapis.com)
so that FuzzBench can report errors to the
[Google Cloud error reporting dashboard](https://console.cloud.google.com/errors)

* [Enable Cloud Build API](https://console.cloud.google.com/apis/library/cloudbuild.googleapis.com)
so that FuzzBench can build docker images using Google Cloud Build, a platform
optimized for doing so.

* [Enable Cloud SQL Admin API](https://console.cloud.google.com/apis/library/sqladmin.googleapis.com)
so that FuzzBench can connect to the database.

* [Enable Secret Manager API](https://console.cloud.google.com/apis/library/secretmanager.googleapis.com)
so that FuzzBench can store service account keys.

## Configure networking

* Go to the networking page for the network you want to run your experiment in.
[This](https://console.cloud.google.com/networking/subnetworks/details/us-central1/default)
is the networking page for the default network in "us-central1". It is best if
you use `$POSTGRES_REGION` for this.

* Click the edit icon. Turn "Private Google access" to "On". Press "Save".

* This allows the trial runner instances to use Google Cloud APIs since they do
  not have external IP addresses.

## Request CPU quota increase

* FuzzBench uses a 96 core Google Compute Engine instance for measuring trials
and single core instances for each trial in your experiment.

* Go to the quotas page for the region you will use for experiments.
[This](https://console.cloud.google.com/iam-admin/quotas?location=us-central1)
is the quotas page for the "us-central1" region.

* Select the "Compute Engine API" "CPUs" quota, fill out contact details and
request a quota increase. We recommend requesting a quota limit of "1000" as
will probably be approved and is large enough for running experiments in a
reasonable amount of time.

* Wait until you receive an email confirming the quota increase.

## Run an experiment

* Follow the [guide on running an experiment]({{ site.baseurl }}/running-your-own-experiment/running-an-experiment/)
