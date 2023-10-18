import csv

from google.cloud import batch_v1
import multiprocessing
import multiprocessing.pool

def launch_batch_job(rows):
    # row = dict(row)
    # row['fuzzer'] = 'aflplusplus'
    # row['id'] = 2353324
    # row['benchmark'] = 'systemd_fuzz-link-parser'
    client = batch_v1.BatchServiceClient()
    runnables = []
    for row in rows:
        runnable = batch_v1.Runnable()
        runnable.container = batch_v1.Runnable.Container()
        runnable.container.image_uri = 'gcr.io/fuzzbench/batch'
        runnable.container.entrypoint = '/bin/bash'
        command = f'FUZZER={row["fuzzer"]} TRIAL={row["id"]} MAX_TOTAL_TIME=82800 EXPERIMENT_FILESTORE=gs://fuzzbench-data BENCHMARK={row["benchmark"]} WORK=/work EXPERIMENT=2023-03-06-sbft23-cov PYTHONPATH=/fuzzbench python /fuzzbench/experiment/measurer/batch_measure.py'
        print(command)
        runnable.container.commands = ['-c', command]
        runnables.append(runnable)
    task = batch_v1.TaskSpec()
    task.runnables = runnables
    resources = batch_v1.ComputeResource()
    resources.memory_mib = 2046 # MB
    task.compute_resource = resources
    task.max_run_duration = "3600s"
    task.max_retry_count = 0

    group = batch_v1.TaskGroup()
    group.task_spec = task

    allocation_policy = batch_v1.AllocationPolicy()
    allocation_policy.service_account.email = '1097086166031-compute@developer.gserviceaccount.com'
    network_interface = allocation_policy.NetworkInterface()
    network_interface.no_external_ip_address = True
    project = 'fuzzbench'
    network_name = 'default'
    subnet = 'default'
    network_interface.network = f'projects/{project}/global/networks/{network_name}'
    region = 'us-central1'
    subnetwork = 'default'
    subnetwork = f'projects/{project}/regions/{region}/subnetworks/{subnetwork}'
    network_interface.subnetwork = subnetwork
    allocation_policy.network.network_interfaces.append(network_interface)

    job = batch_v1.Job()
    job.task_groups = [group]
    job.allocation_policy = allocation_policy
    job.logs_policy = batch_v1.LogsPolicy()
    job.logs_policy.destination = batch_v1.LogsPolicy.Destination.CLOUD_LOGGING

    create_request = batch_v1.CreateJobRequest()
    create_request.job = job
    create_request.job_id = f'measure11-{row["id"]}'
    create_request.parent = 'projects/fuzzbench/locations/us-central1'
    client.create_job(create_request)

def main():
    multiprocessing.set_start_method('spawn')
    with open('/tmp/2023-03-06-sbft23-cov', 'r') as fp:
        reader = csv.DictReader(fp)
        rows = [row for row in reader]
        launch_batch_job(rows[:100])
        # list(map(launch_batch_job, rows[:200]))

if __name__ == '__main__':
    main()
