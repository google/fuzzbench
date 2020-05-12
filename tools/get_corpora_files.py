import argparse
import multiprocessing
import os
import itertools
import posixpath
import re
import tarfile
import tempfile

from common import experiment_utils
from common import filesystem
from common import gsutil


def get_program_args():
    parser = argparse.ArgumentParser(
        description='Get files from last corpus-archive of each AFL trial.')
    parser.add_arguments('-g',
                         '--gcs-dir',
                         help='The gcs directory of the experiment.')
    parser.add_arguments('-f',
                         '--fuzzer',
                         help='The name of the fuzzer.')
    parser.add_arguments('-i',
                         '--filename',
                         help='The name of the file to get from the corpus '
                         'archives.')
    parser.add_arguments('-m',
                         '--max-total-time',
                         help='The max_total_time of the experiment.')
    parser.add_arguments('-o',
                         '--output-directory',
                         help='The name of the directory to write the files to.'
    )
    return parser.parse_args()


def get_all_corpus_archives(experiment_gcs_dir, fuzzer):
    search_path = posixpath.join(experiment_gcs_dir, 'experiment-folders', '*-' + fuzzer, '*', 'corpus')
    retcode, results = gsutil.ls(search_path)
    assert retcode == 0
    return [result for result in results if result.endswith('.tar.gz')]

def find_last_corpus_archives(all_corpus_archives, experiment_gcs_dir, fuzzer, max_total_time):
    # On the runnner we make 1 extra corpus archive. Don't use this.
    # get_snapshot_seconds might not return the same value as it during the
    # experiment. Assume this won't happen.
    snapshot_seconds = experiment_utils.get_snapshot_seconds()
    max_last_corpus_num = int(max_total_time / snapshot_seconds)
    last_archive_regex = re.compile(posixpath.join(experiment_gcs_dir, 'experiment-folders', '.*-' + fuzzer, 'trial-(\d+)', 'corpus', 'corpus-archive-(\d+)\.tar.gz'))
    last_archives = []
    trial = None
    last_trial_corpus_num = None
    last_trial_corpus = None

    for archive in all_corpus_archives:
        result = last_archive_regex.match(archive)
        print(last_archive_regex.pattern, result.groups())
        this_trial = result.group(1)
        this_trial_corpus_num = int(result.group(2))
        if trial is None:
            trial = this_trial

        elif this_trial != trial:
            # Save the last archive from the previous trial.
            last_archives.append(last_trial_corpus)
            trial = this_trial

        if this_trial_corpus_num <= max_last_corpus_num:
            last_trial_corpus_num = this_trial_corpus_num
            last_trial_corpus = archive

    # Save the last archive from the last trial.
    last_archives.append(last_trial_corpus)

    return last_archives



def get_last_corpus_archives_gcs_paths(experiment_gcs_dir, fuzzer, max_total_time):
    all_corpus_archives = get_all_corpus_archives(experiment_gcs_dir, fuzzer)
    return find_last_corpus_archives(all_corpus_archives, experiment_gcs_dir, fuzzer, max_total_time)


def extract_file_from_archive_gcs_path(corpus_archive_gcs_path, needle_filename, experiment_gcs_dir, output_dir):
    base_gcs_path = posixpath.join(experiment_gcs_dir, 'experiment-folders') + '/'
    filename_for_gcs_path = corpus_archive_gcs_path[len(base_gcs_path):].replace('/', '-') + '-' + needle_filename
    output_path = os.path.join(output_dir, filename_for_gcs_path)

    # Copy archive to a temporary file.
    with tempfile.NamedTemporaryFile() as tmp_file:
        gsutil.cp(corpus_archive_gcs_path, tmp_file.name)
        # Extract archive, look for needle_filename, and extract it.
        with tarfile.open(tmp_file.name) as tar_archive:
            for member in tar_archive.getmembers():
                if member.name != os.path.join('corpus', needle_filename):
                    continue

                tar_archive.extract(member, output_path)
                break
            else:
                # If we reached this point, then we haven't found |needle_filename|.
                print('Couldn\'t find %s in %s.' % (needle_filename, corpus_archive_gcs_path))


def extract_files_from_archive_gcs_paths(corpus_archive_gcs_paths, filename, experiment_gcs_dir, output_dir):
    filesystem.create_directory(output_dir)
    pool = multiprocessing.Pool()
    args = itertools.product(corpus_archive_gcs_paths, [filename], [experiment_gcs_dir], [output_dir])
    pool.starmap(extract_file_from_archive_gcs_path, args)


def main():
    args = get_program_args()
    corpus_archive_gcs_paths = get_last_corpus_archives_gcs_paths(
        args.gcs_dir, args.fuzzer, args.max_total_time)
    extract_files_from_archive_gcs_paths(corpus_archive_gcs_paths, args.filename, args.experiment_gcs_dir, args.output_dir)





if __name__ == '__main__':
    main()
