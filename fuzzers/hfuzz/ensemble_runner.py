"""
Description: Ensemble runner for Cmplog, HFUZZ1, and HFuzz2 fuzzer modes.

Usage:
    python3 ensemble_runner.py -i [corpus_dir] -o [output_dir] -b [target_binary] -x [dicts]
        --hfuzz1_target_binary [hfuzz1_target_binary]
        --cmplog_target_binary [cmplog_target_binary]
        --hfuzz2_target_binary [hfuzz2_target_binary]

Note:
    - Input and output directories are managed per fuzzer instance.
    - Before each fuzzer runs, a new output directory is created.
    - The input for each subsequent fuzzer is the 'queue' directory from the previous fuzzer's output.
    - The 'queue' directory is searched within the fuzzer's output directory.
    - The environment variable 'AFL_AUTORESUME' is not set.

Alternatively, you can directly import the EnsembleFuzzer class and use it as follows:
    EnsembleFuzzer(corpus_dir, output_dir, dicts,
                   target_binary,
                   cmplog_target_binary,
                   hfuzz1_target_binary,
                   hfuzz2_target_binary).run()

Required fuzzer binaries in the current directory (names/paths modifiable in the script, see CMPLOG_FUZZ_BIN_NAME, HFUZZ1_FUZZ_BIN_NAME, and HFUZZ2_FUZZ_BIN_NAME):
    - hfuzz1_4.30c_hybrid_start
    - cmplog_4.30c_hybrid_start
    - hfuzz2_4.30c_hybrid_start

Environment variables touched:
    - None
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import time

from collections import deque
from typing import List, Deque

# Fuzzer-command specific constants
INT_MAX = '2147483647'
COMMON_ARGS = ['-m', 'none', '-d', '-t', '1000+']
CMPLOG_FUZZ_BIN_NAME = "./cmplog_4.30c_hybrid_start"
HFUZZ3_FUZZ_BIN_NAME = "./hfuzz3_4.30c_hybrid_start"
HFUZZ1_FUZZ_BIN_NAME = "./hfuzz1_4.30c_hybrid_start"
HFUZZ2_FUZZ_BIN_NAME = "./hfuzz2_4.30c_hybrid_start"

# Timeout strategies (in seconds)
TMOUT_CMPLOG = 60 * 60    # 90 minutes
TIMEOUT_HFUZZ3 = 60 * 60 
TMOUT_HFUZZ1 = 4 * 60 * 60      # 120 minutes
TMOUT_HFUZZ2 = 60 * 60   # 120 minutes
TIMEOUT_LIBAFL = 4 * 60 * 60       # 1 minute


def time_s():
    """Get the current time in seconds."""
    return int(time.time())


def run_command(command: List[str]):
    """Run a checked command."""
    subprocess.run(command, check=True)


class AbstractFuzzer:
    """Abstract class for a fuzzer."""
    name: str
    run_cnt: int
    corpus_dir: str
    output_dir: str
    command: List[str]
    dicts: List[str]
    target_binary: str
    args: List[str]

    def run(self):
        raise NotImplementedError()

    def build_command(self):
        raise NotImplementedError()

    def get_timeout(self):
        raise NotImplementedError()
    


# class LibAFLFuzzer(AbstractFuzzer):
#     """ lib afl fuzzer """
#     timeout: bool;
#     run_err: Exception
#     time_start: int
#     time_end: int
#     libafl_target_binary: str

#     def __init__(
#         self,
#         name,
#         corpus_dir,
#         output_dir,
#         dicts: List[str],
#         target_binary: str,
#         args: List[str]
#     ):
#         self.name = name
#         self.corpus_dir = corpus_dir
#         self.output_dir = output_dir
#         self.dicts = dicts
#         self.args = args
#         self.run_cnt = 0
#         self.command = None
#         self.timeout = False
#         self.run_err = None
#         self.libafl_target_binary = target_binary
    
#     def add_common_args(self):
#         """Add the common arguments to the command."""
#         self.command += ["-t", "1000"]
#         self.command += [
#             '--input', self.corpus_dir,
#             '--output', self.output_dir,
#         ]
    
#     def build_command(self):
#         self.command = [self.libafl_target_binary]
#         self.add_common_args()
    
#     def do_run(self):
#         """
#         Run the fuzzer with the specified command.
#         If self.timeout is True, enforce timeout using subprocess.
#         Handle exceptions appropriately.
#         """
#         try:
#             if self.timeout:
#                 subprocess.run(self.command, check=True, timeout=self.get_timeout())
#             else:
#                 subprocess.run(self.command, check=True)
#             self.run_err = None
#         except subprocess.TimeoutExpired:
#             logging.info(f"Fuzzer {self.name} timed out after {self.get_timeout()} seconds")
#             # Timeout is not considered an error; fuzzer can be re-queued
#             self.run_err = None
#         except subprocess.CalledProcessError as e:
#             logging.error(f"Unexpected error while running the fuzzer")
#             logging.exception(e)
#             self.run_err = e

#     def do_run_timed(self):
#         """Run the fuzzer, timing the execution, and save any error if it fails."""
#         self.time_start = time_s()
#         self.do_run()
#         self.time_end = time_s()
    
#     def get_timeout(self):
#         return TIMEOUT_LIBAFL;

#     def run(self):
#         """Build the command, run the fuzzer, and log the result."""
#         self.build_command()
#         self.do_run_timed()
#         logging.info(self.run_info())
#         self.run_cnt += 1

#     def run_info(self):
#         """Get the run info as a JSON string."""
#         return json.dumps({
#             'name': self.name,
#             'run_cnt': self.run_cnt,
#             'time_start': self.time_start,
#             'time_end': self.time_end,
#             'command': self.command,
#             'run_err': str(self.run_err)
#         })


class AFLFuzzer(AbstractFuzzer):
    """Base class for an AFL fuzzer."""
    timeout: bool
    run_err: Exception
    time_start: int
    time_end: int

    def __init__(
        self,
        name: str,
        corpus_dir: str,
        output_dir: str,
        dicts: List[str],
        target_binary: str,
        args: List[str]
    ):
        self.name = name
        self.corpus_dir = corpus_dir
        self.output_dir = output_dir
        self.dicts = dicts
        self.target_binary = target_binary
        self.args = args
        self.run_cnt = 0
        self.command = None
        self.timeout = False
        self.run_err = None

    def add_common_args(self):
        """Add the common arguments to the command."""
        self.command += COMMON_ARGS
        for dict_path in self.dicts:
            self.command += ['-x', dict_path]
        self.command += [
            '-i', self.corpus_dir,
            '-o', self.output_dir,
            '--',
            self.target_binary
        ] + self.args + [INT_MAX]

    def do_run(self):
        """
        Run the fuzzer with the specified command.
        If self.timeout is True, enforce timeout using subprocess.
        Handle exceptions appropriately.
        """
        try:
            if self.timeout:
                subprocess.run(self.command, check=True, timeout=self.get_timeout())
            else:
                subprocess.run(self.command, check=True)
            self.run_err = None
        except subprocess.TimeoutExpired:
            logging.info(f"Fuzzer {self.name} timed out after {self.get_timeout()} seconds")
            # Timeout is not considered an error; fuzzer can be re-queued
            self.run_err = None
        except subprocess.CalledProcessError as e:
            logging.error(f"Unexpected error while running the fuzzer")
            logging.exception(e)
            self.run_err = e

    def do_run_timed(self):
        """Run the fuzzer, timing the execution, and save any error if it fails."""
        self.time_start = time_s()
        self.do_run()
        self.time_end = time_s()

    def run(self):
        """Build the command, run the fuzzer, and log the result."""
        self.build_command()
        self.do_run_timed()
        logging.info(self.run_info())
        self.run_cnt += 1

    def run_info(self):
        """Get the run info as a JSON string."""
        return json.dumps({
            'name': self.name,
            'run_cnt': self.run_cnt,
            'time_start': self.time_start,
            'time_end': self.time_end,
            'command': self.command,
            'run_err': str(self.run_err)
        })

class LibAFLFuzzer(AFLFuzzer):
    """ lib afl fuzzer """
    timeout: bool;
    run_err: Exception
    time_start: int
    time_end: int
    libafl_target_binary: str

    def __init__(
        self,
        corpus_dir,
        output_dir,
        dicts: List[str],
        target_binary: str,
        libafl_target_binary: str,
        args: List[str]
    ):
        self.libafl_target_binary = libafl_target_binary
        super().__init__("libafl", corpus_dir, output_dir, dicts, target_binary, args)
    
    def add_common_args(self):
        """Add the common arguments to the command."""
        self.command += ["-t", "1000"]
        self.command += [
            '--input', self.corpus_dir,
            '--output', self.output_dir,
        ]
    
    def build_command(self):
        self.command = [self.libafl_target_binary]
        self.add_common_args()
    
    
    def get_timeout(self):
        """Get the timeout value for the LibAFL fuzzer (in seconds)."""
        return TIMEOUT_LIBAFL
    def do_run(self):
        """
        Override to set LD_PRELOAD for LibAFL-specific runs.
        """
        fuzzer_env = os.environ.copy()
        fuzzer_env['LD_PRELOAD'] = '/usr/lib/x86_64-linux-gnu/libjemalloc.so.2'
        try:
            if self.timeout:
                subprocess.run(self.command, check=True, timeout=self.get_timeout(), env=fuzzer_env)
            else:
                subprocess.run(self.command, check=True, env=fuzzer_env)
            self.run_err = None
        except subprocess.TimeoutExpired:
            logging.info(f"Fuzzer {self.name} timed out after {self.get_timeout()} seconds")
            self.run_err = None
        except subprocess.CalledProcessError as e:
            logging.error(f"Unexpected error while running the fuzzer")
            logging.exception(e)
            self.run_err = e


class HFuzz3Fuzzer(AFLFuzzer):
    hfuzz3_target_binary: str

    """
    Example usage:
    ./hfuzz3_fuzzer -H -c /out/hfuzz3_cms_transform_fuzzer -m none -d -t 1000+ \\
        -x /out/keyval.dict -x /out/cms_transform_fuzzer.dict \\
        -i /out/corpus/ensemble_fuzzer/hfuzz3_input_0 \\
        -o '/out/corpus/ensemble_fuzzer/hfuzz3_run_0' \\
        -- /out/cms_transform_fuzzer 2147483648
    """

    def __init__(
        self,
        corpus_dir: str,
        output_dir: str,
        dicts: List[str],
        target_binary: str,
        hfuzz3_target_binary: str,
        args: List[str]
    ):
        self.hfuzz3_target_binary = hfuzz3_target_binary
        super().__init__("hfuzz3", corpus_dir, output_dir, dicts, target_binary, args)

    def build_command(self):
        """
        Build the command for running the Cmplog fuzzer.
        The '-c' option specifies the cmplog-instrumented binary.
        """
        out_dir = os.getenv("OUT")
        fuzz_target = os.getenv("FUZZ_TARGET")
        self.command = [
            HFUZZ3_FUZZ_BIN_NAME,
            "-H", "-c",
            self.hfuzz3_target_binary
        ]
        self.add_common_args()

    def get_timeout(self):
        """Get the timeout value for the Cmplog fuzzer (in seconds)."""
        return TIMEOUT_HFUZZ3

class CmplogFuzzer(AFLFuzzer):
    """Fuzzer class for the Cmplog mode."""
    cmplog_target_binary: str

    def __init__(
        self,
        corpus_dir: str,
        output_dir: str,
        dicts: List[str],
        target_binary: str,
        cmplog_target_binary: str,
        args: List[str]
    ):
        self.cmplog_target_binary = cmplog_target_binary
        super().__init__("cmplog", corpus_dir, output_dir, dicts, target_binary, args)

    def build_command(self):
        """
        Build the command for running the Cmplog fuzzer.
        The '-c' option specifies the cmplog-instrumented binary.
        """
        self.command = [
            CMPLOG_FUZZ_BIN_NAME,
            '-c',
            self.cmplog_target_binary
        ]
        self.add_common_args()

    def get_timeout(self):
        """Get the timeout value for the Cmplog fuzzer (in seconds)."""
        return TMOUT_CMPLOG


class HFuzz1Fuzzer(AFLFuzzer):
    """Fuzzer class for the HFUZZ1 mode."""

    def __init__(
        self,
        corpus_dir: str,
        output_dir: str,
        dicts: List[str],
        target_binary: str,
        args: List[str]
    ):
        super().__init__("hfuzz1", corpus_dir, output_dir, dicts, target_binary, args)

    def build_command(self):
        """Build the command for running the HFUZZ1 fuzzer."""
        self.command = [
            HFUZZ1_FUZZ_BIN_NAME,
            '-k',
            '-p',
            'wd_scheduler'
        ]
        self.add_common_args()

    def get_timeout(self):
        """Get the timeout value for the HFUZZ1 fuzzer (in seconds)."""
        return TMOUT_HFUZZ1


class HFuzz2Fuzzer(AFLFuzzer):
    """Fuzzer class for the HFuzz2 mode."""
    cmplog_target_binary: str

    def __init__(
        self,
        corpus_dir: str,
        output_dir: str,
        dicts: List[str],
        target_binary: str,
        cmplog_target_binary: str,
        args: List[str]
    ):
        """
        如果传入了 cmplog_target_binary，则在构造命令时加上 -c cmplog_target_binary。
        target_binary 为 HFuzz2 编译出的可执行文件。
        """
        self.cmplog_target_binary = cmplog_target_binary
        super().__init__("hfuzz2", corpus_dir, output_dir, dicts, target_binary, args)

    def build_command(self):
        """Build the command for running the HFuzz2 fuzzer."""
        if self.cmplog_target_binary:
            self.command = [HFUZZ2_FUZZ_BIN_NAME]
        else:
            self.command = [HFUZZ2_FUZZ_BIN_NAME]
        self.add_common_args()

    def get_timeout(self):
        """Get the timeout value for the HFuzz2 fuzzer (in seconds)."""
        return TMOUT_HFUZZ2


class EnsembleFuzzer:
    """
    EnsembleFuzzer orchestrates multiple fuzzers, running them in a coordinated manner.
    Before each fuzzer runs, a new output directory is created, and the input directory is set up by copying
    the previous fuzzer's queue into it.
    The 'queue' directory is searched within the previous fuzzer's output directory.
    The environment variable 'AFL_AUTORESUME' is not set, so each fuzzer starts fresh with the provided inputs.
    """
    output_dir: str
    fuzzer_queue: Deque[AFLFuzzer]
    initial_corpus_dir: str
    args: List[str]
    dicts: List[str]

    def __init__(
        self,
        corpus_dir: str,
        output_dir: str,
        dicts: List[str],
        target_binary: str,
        cmplog_target_binary: str,
        hfuzz1_target_binary: str,
        hfuzz2_target_binary: str,
        libafl_target_binary: str,
        hfuzz3_target_binary: str,
        args: List[str]
    ):
        self.output_dir = os.path.join(output_dir, "ensemble_fuzzer")
        self.initial_corpus_dir = corpus_dir  # Store initial corpus directory
        self.dicts = dicts  # Store dictionaries
        self.args = args    # Store target binary arguments
        self.fuzzer_queue = deque()

        if hfuzz1_target_binary:
            self.fuzzer_queue.append(
                HFuzz1Fuzzer(
                    corpus_dir=None,
                    output_dir=None,
                    dicts=self.dicts,
                    target_binary=hfuzz1_target_binary,
                    args=self.args
                )
            )
        if hfuzz2_target_binary:
            self.fuzzer_queue.append(
                HFuzz2Fuzzer(
                    corpus_dir=None,
                    output_dir=None,
                    dicts=self.dicts,
                    target_binary=hfuzz2_target_binary,
                    cmplog_target_binary=cmplog_target_binary,
                    args=self.args
                )
            )
        if cmplog_target_binary:
            self.fuzzer_queue.append(
                CmplogFuzzer(
                    corpus_dir=None,
                    output_dir=None,
                    dicts=self.dicts,
                    target_binary=target_binary,
                    cmplog_target_binary=cmplog_target_binary,
                    args=self.args
                )
            )
        if libafl_target_binary:
            self.fuzzer_queue.append(
                LibAFLFuzzer(
                    corpus_dir=None,
                    output_dir=None,
                    dicts=self.dicts,
                    target_binary=target_binary,
                    libafl_target_binary=libafl_target_binary,
                    args=self.args
                )
            )
 
        if hfuzz3_target_binary:
            self.fuzzer_queue.append(
                HFuzz3Fuzzer(
                    corpus_dir=None,
                    output_dir=None,
                    dicts=self.dicts,
                    target_binary=target_binary,
                    hfuzz3_target_binary=hfuzz3_target_binary,
                    args=self.args
                )
            )

    def find_queue_directory(self, output_dir):
        """
        Search the output directory recursively for a 'queue' directory.
        Return the path to the 'queue' directory if found, else None.
        """
        for root, dirs, files in os.walk(output_dir):
            if 'queue' in dirs:
                return os.path.join(root, 'queue')
        return None

    def copy_queue_to_input(self, queue_dir, input_dir):
        """
        Copy the contents of the queue directory to the new input directory.
        """
        if not os.path.exists(queue_dir):
            logging.warning(f"Queue directory {queue_dir} does not exist.")
            return
        for filename in os.listdir(queue_dir):
            src_path = os.path.join(queue_dir, filename)
            dst_path = os.path.join(input_dir, filename)
            if os.path.isfile(src_path):
                shutil.copy2(src_path, dst_path)

    def merge_queue_directories(self, src_queue_dir, dst_queue_dir):
        """
        Merge contents from src queue directory into dst queue directory.
        """
        if not os.path.exists(src_queue_dir) or not os.path.exists(dst_queue_dir):
            logging.warning(f"Cannot merge queues - source or destination directory does not exist")
            return
        
        # Copy all files from src to dst, skipping if file already exists
        for filename in os.listdir(src_queue_dir):
            src_path = os.path.join(src_queue_dir, filename)
            dst_path = os.path.join(dst_queue_dir, filename)
            if os.path.isfile(src_path) and not os.path.exists(dst_path):
                shutil.copy2(src_path, dst_path)

    def run(self):
        """
        Run the ensemble of fuzzers.
        Each fuzzer runs in a round-robin fashion.
        Each fuzzer uses the output from the previously successful run.
        If a fuzzer errors, its queue is merged back into the last successful queue.
        """
        os.makedirs(self.output_dir, exist_ok=True)
        prev_output_dir = None  # Keep track of previous successful fuzzer's output directory
        last_successful_output_dir = None  # Keep track of the last successful run

        while len(self.fuzzer_queue):
            fuzzer = self.fuzzer_queue.popleft()

            # Create unique output directory for this fuzzer run
            fuzzer_output_dir = os.path.join(
                self.output_dir,
                f"{fuzzer.name}_run_{fuzzer.run_cnt}"
            )
            os.makedirs(fuzzer_output_dir, exist_ok=True)

            # Set up the input directory
            # For all runs, use prev_output_dir if available, otherwise use initial corpus
            if prev_output_dir is None:
                fuzzer_input_dir = self.initial_corpus_dir
            else:
                queue_dir = self.find_queue_directory(prev_output_dir)
                if queue_dir is None:
                    logging.warning(f"No queue directory found in {prev_output_dir}. Using initial corpus.")
                    fuzzer_input_dir = self.initial_corpus_dir
                else:
                    fuzzer_input_dir = queue_dir

            # Prepare the input directory by copying files
            fuzzer_input_dir_prepared = os.path.join(
                self.output_dir,
                f"{fuzzer.name}_input_{fuzzer.run_cnt}"
            )
            os.makedirs(fuzzer_input_dir_prepared, exist_ok=True)
            self.copy_queue_to_input(fuzzer_input_dir, fuzzer_input_dir_prepared)

            # Update fuzzer's input and output directories
            fuzzer.corpus_dir = fuzzer_input_dir_prepared
            fuzzer.output_dir = fuzzer_output_dir

            # Decide on timeout
            fuzzer.timeout = len(self.fuzzer_queue) > 0

            # Run the fuzzer
            fuzzer.run()

            if isinstance(fuzzer.run_err, Exception):
                # If an error occurred:
                # 1. Try to merge any findings back into the last successful queue
                # 2. Do not update prev_output_dir
                # 3. Do not re-queue the fuzzer
                logging.error(f"Fuzzer {fuzzer.name} encountered an error and will not be re-queued.")
                
                if last_successful_output_dir:
                    current_queue = self.find_queue_directory(fuzzer_output_dir)
                    last_successful_queue = self.find_queue_directory(last_successful_output_dir)
                    
                    if current_queue and last_successful_queue:
                        logging.info(f"Merging findings from failed run into last successful queue")
                        self.merge_queue_directories(current_queue, last_successful_queue)
                    
                # Restore prev_output_dir to last successful directory
                prev_output_dir = last_successful_output_dir
            else:
                # Successful run
                # Update both prev_output_dir and last_successful_output_dir
                prev_output_dir = fuzzer_output_dir
                last_successful_output_dir = fuzzer_output_dir
                
                # Re-queue the fuzzer to run again
                self.fuzzer_queue.append(fuzzer)

        logging.info("Fuzzing completed: all fuzzers have been processed.")
        
def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--corpus_dir", type=str, required=True,
                        help="Directory containing the corpus")
    parser.add_argument("-o", "--output_dir", type=str, required=True,
                        help="Directory to store output")
    parser.add_argument("-b", "--target_binary", type=str, required=True,
                        help="Path to the vanilla AFLplusplus-instrumented target binary")
    parser.add_argument("-a", "--args", type=str, nargs="*", default=[],
                        help="Arguments to pass to the target binary")
    parser.add_argument("-x", "--dicts", type=str, nargs="+", default=None,
                        help="Path to the dictionaries; if not provided, will use all .dict files in the current directory")
    parser.add_argument("--hfuzz1_target_binary", type=str, required=False,
                        help="Path to the HFuzz1-instrumented target binary (optional)")
    parser.add_argument("--cmplog_target_binary", type=str, required=False,
                        help="Path to the cmplog-instrumented target binary (optional)")
    parser.add_argument("--hfuzz2_target_binary", type=str, required=False,
                        help="Path to the HFuzz2-instrumented target binary (optional)")
    parser.add_argument("--libafl_target_binary", type=str, required=False,
                        help="Path to the LibAFL-instrumented target binary (optional)")
    parser.add_argument("--hfuzz3_target_binary", type=str, required=False,
                        help="Path to the HFuzz3-instrumented target binary (optional)")
    return parser.parse_args()


def main(args):
    """Main function to run the ensemble fuzzer."""
    os.makedirs(args.output_dir, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(args.output_dir, "ensemble_runner.log"),
        level=logging.DEBUG
    )

    if args.dicts is None:
        args.dicts = [os.path.abspath(f) for f in os.listdir('.') if f.endswith('.dict')]
        if not args.dicts:
            logging.warning("No dictionaries found; proceeding without any dictionaries.")
    else:
        args.dicts = [os.path.abspath(dict_path) for dict_path in args.dicts]

    fuzzer = EnsembleFuzzer(
        corpus_dir=args.corpus_dir,
        output_dir=args.output_dir,
        dicts=args.dicts,
        target_binary=args.target_binary,
        cmplog_target_binary=args.cmplog_target_binary,
        hfuzz1_target_binary=args.hfuzz1_target_binary,
        hfuzz2_target_binary=args.hfuzz2_target_binary,
        libafl_target_binary=args.libafl_target_binary,
        hfuzz3_target_binary=args.hfuzz3_target_binary,
        args=args.args
    )
    fuzzer.run()


if __name__ == "__main__":
    main(parse_args())
