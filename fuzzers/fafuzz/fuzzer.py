
from fuzzers.afl import fuzzer as afl_fuzzer


def build():
    """Build benchmark."""
    afl_fuzzer.build()


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    afl_fuzzer.prepare_fuzz_environment(input_corpus)

    afl_fuzzer.run_afl_fuzz(
        input_corpus,
        output_corpus,
        target_binary,
        additional_flags=[
            # Enable Mopt mutator with pacemaker fuzzing mode at first. This
            # is also recommended in a short-time scale evaluation.
            '-FA'
        ])
