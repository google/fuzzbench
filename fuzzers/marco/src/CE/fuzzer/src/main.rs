#[macro_use]
extern crate clap;
use clap::{App, Arg};

//extern crate angora;
//extern crate angora_common;
use fastgen::fuzz_main::*;

fn main() {
    let matches = App::new("angora-fuzzer")
        .version(crate_version!())
        .about("Fastgen is a mutation-based fuzzer.")
        .arg(Arg::with_name("input_dir")
             .short("i")
             .long("input")
             .value_name("DIR")
             .help("Sets the directory of input seeds, use \"-\" to restart with existing output directory")
             .takes_value(true)
             .required(true))
        .arg(Arg::with_name("output_dir")
             .short("o")
             .long("output")
             .value_name("DIR")
             .help("Sets the directory of outputs")
             .takes_value(true)
             .required(true))
        .arg(Arg::with_name("track_target")
             .short("t")
             .long("track")
             .value_name("PROM")
             .help("Sets the target (USE_TRACK or USE_PIN) for tracking, including taints, cmps.  Only set in LLVM mode.")
             .takes_value(true))
        .arg(Arg::with_name("pargs")
            .help("Targeted program (USE_FAST) and arguments. Any \"@@\" will be substituted with the input filename from Angora.")
            .required(true)
            .multiple(true)
            .allow_hyphen_values(true)
            .last(true)
            .index(1))
        .arg(Arg::with_name("memory_limit")
             .short("M")
             .long("memory_limit")
             .value_name("MEM")
             .help("Memory limit for programs, default is 200(MB), set 0 for unlimit memory")
             .takes_value(true))
        .arg(Arg::with_name("time_limit")
             .short("T")
             .long("time_limit")
             .value_name("TIME")
             .help("time limit for programs, default is 1(s), the tracking timeout is 12 * TIME")
             .takes_value(true))
        .arg(Arg::with_name("thread_jobs")
             .short("j")
             .long("jobs")
             .value_name("JOB")
             .help("Sets the number of thread jobs, default is 1")
             .takes_value(true))
        .arg(Arg::with_name("sync_afl")
             .short("S")
             .long("sync_afl")
             .help("Sync the seeds with AFL. Output directory should be in AFL's directory structure."))
        .arg(Arg::with_name("brc_flip_strategy")
             .short("b")
             .long("brc_flip")
             .value_name("BRC_FLIP")
             .help("symbolic branch flippging strategy, 0 (default) for qsym-style; 1 for pplist;")
             .takes_value(true))
        .arg(Arg::with_name("do_fifo")
             .short("f")
             .long("do_fifo_sche")
             .value_name("DO_FIFO")
             .help("fifo execute the CE queue; 0 (default) for no; 1 for do fifo")
             .takes_value(true))
        .arg(Arg::with_name("initial_count")
             .short("c")
             .long("initial_corpus_count")
             .value_name("INI_COUNT")
             .help("count of initial seeds")
             .takes_value(true))
        .get_matches();

    fuzz_main_seq(
        matches.value_of("input_dir").unwrap(),
        matches.value_of("output_dir").unwrap(),
        matches.value_of("track_target").unwrap_or("-"),
        matches.values_of_lossy("pargs").unwrap(),
        value_t!(matches, "thread_jobs", usize).unwrap_or(1),
        value_t!(matches, "memory_limit", u64).unwrap_or(fastgen_common::config::MEM_LIMIT),
        value_t!(matches, "time_limit", u64).unwrap_or(fastgen_common::config::TIME_LIMIT),
        matches.occurrences_of("sync_afl") > 0,
        value_t!(matches, "brc_flip_strategy", u32).unwrap_or(0),
        value_t!(matches, "do_fifo", u32).unwrap_or(0),
        value_t!(matches, "initial_count", u32).unwrap_or(1),
    );
}
