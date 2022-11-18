# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Utilities for running muttfuzz"""
from datetime import datetime
import os
import signal
import subprocess
from subprocess import CalledProcessError
import time
from contextlib import contextmanager

from fuzzers.aflplusplus_muttfuzz import mutate


class TimeoutException(Exception):
    """ "Exception thrown when timeouts occur"""


@contextmanager
def time_limit(seconds):
    """Method to define a time limit before throwing exception"""

    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


def restore_executable(executable, executable_code):
    """Method to restore the original executable"""
    # We do this because it could still be busy if fuzzer hasn't shut down yet
    with open("/tmp/new_executable", "wb") as f_name:
        f_name.write(executable_code)
    os.rename("/tmp/new_executable", executable)
    subprocess.check_call(["chmod", "+x", executable])


def silent_run_with_timeout(cmd, timeout):
    """Method to run command silently with timeout"""
    dnull = open(os.devnull, "w")
    start_p = time.time()
    try:
        with open("cmd_errors.txt", "w") as cmd_errors:
            process = subprocess.Popen(  # pylint: disable=subprocess-popen-preexec-fn
                cmd,
                shell=True,
                preexec_fn=os.setsid,
                stdout=dnull,
                stderr=cmd_errors,
            )
            while (process.poll() is None) and (
                (time.time() - start_p) < timeout):
                time.sleep(0.5)
            if process.poll() is None:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        with open("cmd_errors.txt", "r") as cmd_errors:
            cmd_errors_out = cmd_errors.read()
        if len(cmd_errors_out) > 0:
            print("ERRORS:")
            print(cmd_errors_out)
    finally:
        if process.poll() is None:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)


def fuzz_with_mutants(  # pylint: disable=too-many-locals,too-many-arguments
    fuzzer_cmd,
    executable,
    budget,
    time_per_mutant,
    fraction_mutant,
    initial_fuzz_cmd="",
    initial_budget=0,
    post_initial_cmd="",
    post_mutant_cmd="",
    status_cmd="",
    order=1,
):
    """Function to fuzz mutants from commands"""
    executable_code = mutate.get_code(executable)
    executable_jumps = mutate.get_jumps(executable)
    start_fuzz = time.time()
    mutant_no = 1
    try:
        if initial_fuzz_cmd != "":
            print(
                "=" * 10,
                datetime.utcfromtimestamp(
                    time.time()).strftime("%Y-%m-%d %H:%M:%S"),
                "=" * 10,
            )
            print("RUNNING INITIAL FUZZING...")
            silent_run_with_timeout(initial_fuzz_cmd, initial_budget)
            if status_cmd != "":
                print("INITIAL STATUS:")
                subprocess.call(status_cmd, shell=True)
            if post_initial_cmd != "":
                subprocess.call(post_initial_cmd, shell=True)

        while ((time.time() - start_fuzz) - initial_budget) < (budget *
                                                               fraction_mutant):
            print(
                "=" * 10,
                datetime.utcfromtimestamp(
                    time.time()).strftime("%Y-%m-%d %H:%M:%S"),
                "=" * 10,
            )
            print(
                round(time.time() - start_fuzz, 2),
                "ELAPSED: GENERATING MUTANT #" + str(mutant_no),
            )
            mutant_no += 1
            # make a new mutant of the executable; rename
            # avoids hitting a busy executable
            mutate.mutate_from(
                executable_code,
                executable_jumps,
                "/tmp/new_executable",
                order=order,
            )
            os.rename("/tmp/new_executable", executable)
            subprocess.check_call(["chmod", "+x", executable])
            print("FUZZING MUTANT...")
            start_run = time.time()
            silent_run_with_timeout(fuzzer_cmd, time_per_mutant)
            print(
                "FINISHED FUZZING IN",
                round(time.time() - start_run, 2),
                "SECONDS",
            )
            if post_mutant_cmd != "":
                subprocess.call(post_mutant_cmd, shell=True)
            if status_cmd != "":
                print("STATUS:")
                subprocess.call(status_cmd, shell=True)

        print(
            datetime.utcfromtimestamp(
                time.time()).strftime("%Y-%m-%d %H:%M:%S"))
        print(round(time.time() - start_fuzz, 2),
              "ELAPSED: STARTING FINAL FUZZ")
        restore_executable(executable, executable_code)
        silent_run_with_timeout(fuzzer_cmd, budget - (time.time() - start_fuzz))
        print(
            "COMPLETED ALL FUZZING AFTER",
            round(time.time() - start_fuzz, 2),
            "SECONDS",
        )
        if status_cmd != "":
            print("FINAL STATUS:")
            subprocess.call(status_cmd, shell=True)
    finally:
        # always restore the original binary!
        restore_executable(executable, executable_code)


def fuzz_with_mutants_via_function(  # pylint: disable=too-many-locals,too-many-statements,too-many-arguments,too-many-branches
    fuzzer_fn,
    executable,
    budget,
    time_per_mutant,
    fraction_mutant,
    initial_fn=None,
    initial_budget=0,
    post_initial_fn=None,
    post_mutant_fn=None,
    status_fn=None,
    order=1,
):
    """Fuzz mutants from initial and post mutant functions"""
    executable_code = mutate.get_code(executable)
    executable_jumps = mutate.get_jumps(executable)
    start_fuzz = time.time()
    mutant_no = 1
    try:
        if initial_fn is not None:
            print(
                "=" * 10,
                datetime.utcfromtimestamp(
                    time.time()).strftime("%Y-%m-%d %H:%M:%S"),
                "=" * 10,
            )
            print("RUNNING INITIAL FUZZING...")
            try:
                with time_limit(initial_budget):
                    initial_fn()
            except TimeoutException:
                pass
            if status_fn is not None:
                print("INITIAL STATUS:")
                status_fn()
            if post_initial_fn is not None:
                post_initial_fn()

        while ((time.time() - start_fuzz) - initial_budget) < (budget *
                                                               fraction_mutant):
            print(
                "=" * 10,
                datetime.utcfromtimestamp(
                    time.time()).strftime("%Y-%m-%d %H:%M:%S"),
                "=" * 10,
            )
            print(
                round(time.time() - start_fuzz, 2),
                "ELAPSED: GENERATING MUTANT #" + str(mutant_no),
            )
            mutant_no += 1
            # make a new mutant of the executable; rename avoids
            # hitting a busy executable
            mutate.mutate_from(
                executable_code,
                executable_jumps,
                "/tmp/new_executable",
                order=order,
            )
            os.rename("/tmp/new_executable", executable)
            subprocess.check_call(["chmod", "+x", executable])
            print("FUZZING MUTANT...")
            start_run = time.time()
            try:
                with time_limit(time_per_mutant):
                    fuzzer_fn()
            except TimeoutException:
                pass
            except CalledProcessError:
                pass
            print(
                "FINISHED FUZZING IN",
                round(time.time() - start_run, 2),
                "SECONDS",
            )
            if post_mutant_fn is not None:
                post_mutant_fn()
            if status_fn is not None:
                print("STATUS:")
                status_fn()

        print(
            datetime.utcfromtimestamp(
                time.time()).strftime("%Y-%m-%d %H:%M:%S"))
        print(round(time.time() - start_fuzz, 2),
              "ELAPSED: STARTING FINAL FUZZ")
        restore_executable(executable, executable_code)
        try:
            with time_limit(int(budget - (time.time() - start_fuzz))):
                fuzzer_fn()
        except TimeoutException:
            pass
        except CalledProcessError:
            pass
        print(
            "COMPLETED ALL FUZZING AFTER",
            round(time.time() - start_fuzz, 2),
            "SECONDS",
        )
        if status_fn is not None:
            print("FINAL STATUS:")
            status_fn()
    finally:
        # always restore the original binary!
        restore_executable(executable, executable_code)
