---
layout: default
title: Setting up a Google Cloud Project
parent: Advanced topics
nav_order: 2
permalink: /advanced-topics/setting-up-a-google-cloud-project/
---

Currently, fuzzbench requires Google Cloud to run (though this
may change, see
[FAQ]({{ site.baseurl }}faq/#how-can-i-reproduce-the-results-or-run-fuzzbench-myself)).
This page will walk you through how to set up a Google Cloud Project to run an
experiment for the first time.

## Create the Project

* [Create a new Google Cloud Project](https://console.cloud.google.com/projectcreate).

* Set $PROJECT_NAME in the enviornment:

```bash
export PROJECT_NAME=<your-project-name>
```

For the rest of this document, replace $PROJECT_NAME with the name of the
project you created.

* [Install Google Cloud SDK](https://console.cloud.google.com/sdk/install).

* Set your default project using gcloud:

```bash
gcloud config set project $PROJECT_NAME
```

## Set up the database

* [Enable the Compute Engine API](https://bconsole.cloud.google.com/apis/library/compute.googleapis.com?q=compute%20engine)

* Create a PostgreSQL (we use PostgreSQL 11) instance using
[Google Cloud SQL](https://console.cloud.google.com/sql/create-instance-postgres).
This will take a few minutes.
Note that the region you choose should be the region you use later for running
experiments.

* For the rest of this document, we will use $POSTGRES_INSTANCE,
$POSTGRES_REGION, and $POSTGRES_PASSWORD to refer to the name of the PostgreSQL
instance you created, its region and its password. Set them in your environment:

```bash
export POSTGRES_INSTANCE=<your-postgres-instance-name>
export POSTGRES_REGION=<your-postgres-region>
export POSTGRES_PASSWORD=<your-postgress-password>
```

* [Download and install cloud_sql_proxy](https://console.cloud.google.com/sql/docs/postgres/sql-proxy)

```bash
wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O cloud_sql_proxy
```

* Connect to your postgres instance using cloud_sql_proxy:

```bash
./cloud_sql_proxy -instances=$PROJECT_NAME:$POSTGRES_REGION:$POSTGRES_NAME=tcp:5432
```

* (optional, but recommended) Connect to your instance to ensure you
   have all of the details right:

```bash
psql "host=127.0.0.1 sslmode=disable user=postgres"
```

Use $POSTGRES_PASSWORD when prompted.

* Initialize the postgres database:

```bash
PYTHONPATH=. alembic upgrade head
```

If this command fails, double check you set `POSTGRES_PASSWORD`.

## Google Cloud Storage Buckets

* Set up Google Cloud Storage Buckets:

```bash
gsutil mb gs://$DATA_BUCKET_NAME
gsutil mb gs://$REPORT_BUCKET_NAME
```

## Dispatcher Image

* Build dispatcher image:

```bash
docker build -f docker/dispatcher-image/Dockerfile -t gcr.io/$PROJECT_NAME/dispatcher-image docker/dispatcher-image/
```

* [Enable Google Container Registry API](https://console.console.cloud.google.com/apis/api/containerregistry.googleapis.com/overview)

* Push `dispatcher-image` to the docker registry:

```bash
docker push gcr.io/$PROJECT_NAME/dispatcher-image
```

* [Make the registry's visibility public](https://console.cloud.google.com/gcr/settings).

## Enable APIs

* [Enable the IAM API](https://console.cloud.google.com/apis/api/iam.googleapis.com/landing)

* [Enable the error reporting API](https://console.cloud.google.com/apis/library/clouderrorreporting.googleapis.com)

## Run an experiment

* Follow the [guide on running an experiment]({{ site.baseurl }}/advanced-topics/running-an-experiment/)
