import os
import json
import subprocess

def main():
    benchmark = os.getenv('BENCHMARK')
    doit(benchmark)

def doit(benchmark):
    SCRATCH = f'/tmp/scratch-{BENCHMARK}'
    COMBINED_DIR = '/tmp/combined'

    os.mkdir('/tmp/scratch')

    subprocess.run(
        ['gsutil', '-m', 'cp', f'gs://fuzzbench-data/batch/{benchmark}-*.json', SCRATCH],
    )

    data = []
    for filename in os.listdir(SCRATCH):
        file_path = os.path.join(SCRATCH, filename)

        with open(file_path, 'r') as fp:
            data.append(json.loads(fp.read()))

    COMBINED_NAME = f'{benchmark}.json'
    COMBINED = os.path.join(COMBINED_DIR, COMBINED_NAME)
    with open(COMBINED, 'w') as fp:
        fp.write(json.dumps(data))

    subprocess.run(
        ['gsutil', 'cp', '-m', COMBINED,
         f'gs://fuzzbench-data/batch-combined/{COMBINED_NAME}'],
    )


if __name__ == '__main__':
    main()
