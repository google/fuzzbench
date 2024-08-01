use crate::command::CommandOpt;
use memmap;
use std::{fs::File, io::prelude::*, path::Path};
use twoway;

static CHECK_CRASH_MSG: &str = r#"
If your system is configured to send core dump, there will be an
extended delay after the program crash, which might makes crash to
misinterpreted as timeouts.
You can modify /proc/sys/kernel/core_pattern to disable it by:
# echo core | sudo tee /proc/sys/kernel/core_pattern
"#;

static CORE_PATTERN_FILE: &str = "/proc/sys/kernel/core_pattern";

fn check_crash_handling() {
    let mut f = File::open(CORE_PATTERN_FILE).unwrap();
    let mut buffer = String::new();
    f.read_to_string(&mut buffer).unwrap();
    // if buffer.trim() != "core" {
    if buffer.starts_with('|') {
        panic!(CHECK_CRASH_MSG);
    }
}

fn check_target_binary(target: &str) {
    let program_path = Path::new(target);
    if !program_path.exists() || !program_path.is_file() {
        panic!("Invalid executable file! {:?}", target);
    }
}

fn mmap_file(target: &str) -> memmap::Mmap {
    println!("target is {}", target);
    let file = File::open(target).expect("Unable to open file");
    unsafe {
        memmap::MmapOptions::new()
            .map(&file)
            .expect("unable to mmap file")
    }
}

fn containt_string(f_data: &memmap::Mmap, s: &str) -> bool {
    twoway::find_bytes(&f_data[..], s.as_bytes()).is_some()
}

pub fn check_asan(target: &str) -> bool {
    let f_data = mmap_file(target);
    containt_string(&f_data, "libasan.so") || containt_string(&f_data, "__msan_init")
}

fn check_fast(target: &str) {
    check_target_binary(target);
    let f_data = mmap_file(target);
    if !containt_string(&f_data, "__angora_cond_cmpid") {
        panic!("The program is not complied by Angora");
    }
}

fn check_track_llvm(target: &str) {
    check_target_binary(target);
    let f_data = mmap_file(target);
    if !containt_string(&f_data, "__taint_trace_cmp") {
        panic!("The program is not complied by Angora with taint tracking");
    }
}

fn check_io_dir(in_dir: &str, out_dir: &str) {
    let in_dir_p = Path::new(in_dir);
    let out_dir_p = Path::new(out_dir);

    if in_dir == "-" {
        if !out_dir_p.exists() {
            panic!("Original output directory is required to resume fuzzing.");
        }
    } else {
        if !in_dir_p.exists() || !in_dir_p.is_dir() {
            panic!("Input dir does not exist or is not a directory!");
        }
    }
}

pub fn check_dep(in_dir: &str, out_dir: &str, cmd: &CommandOpt) {
    check_io_dir(in_dir, out_dir);
    check_crash_handling();
    //check_fast(&cmd.main.0);
    check_track_llvm(&cmd.track.0);
}
