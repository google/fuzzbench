use fastgen_common::defs;
use chrono::prelude::Local;
use std::{
    fs,
    path::{PathBuf, Path},
    sync::{
      atomic::{AtomicBool, Ordering},
      Arc, //RwLock,
    },
    thread,
};

use std::time; use crate::{branches, check_dep, command, depot, sync, executor}; use ctrlc; use pretty_env_logger;
use crate::fuzz_loop;
use crate::cpp_interface::*;
use fastgen_common::config;
use std::collections::HashMap;

pub fn fuzz_main_seq(
    in_dir: &str,
    out_dir: &str,
    track_target: &str,
    pargs: Vec<String>,
    //TODO jobs
    _num_jobs: usize,
    mem_limit: u64,
    time_limit: u64,
    sync_afl: bool,
    brc_strategy:u32,
    do_fifo:u32,
    initial_count:u32,
    ) {
  pretty_env_logger::init();

  let (seeds_dir, angora_out_dir) = initialize_directories_sync(in_dir, out_dir);

  let command_option = command::CommandOpt::new(
      track_target,
      pargs,
      &angora_out_dir,
      mem_limit,
      time_limit,
      );
  info!("{:?}", command_option);

  check_dep::check_dep(in_dir, out_dir, &command_option);

  let depot = Arc::new(depot::DepotSync::new(&angora_out_dir));
  info!("{:?}", depot.dirs);

  let global_branches = Arc::new(branches::GlobalBranches::new());
  let running = Arc::new(AtomicBool::new(true));
  set_sigint_handler(running.clone());

  let mut executor = executor::ExecutorSync::new(
      command_option.specify(0),
      depot.clone(),
      0);

  unsafe { init_core(config::SAVING_WHOLE, initial_count); }
  fuzz_loop::ce_loop_sync(seeds_dir, running.clone(), command_option.specify(2), depot.clone(), global_branches.clone(), false, brc_strategy, do_fifo);
}

fn initialize_directories_sync(in_dir: &str, out_dir: &str) -> (PathBuf, PathBuf) {
  let angora_out_dir = PathBuf::from(out_dir);
  let seeds_dir = PathBuf::from(in_dir);

  (seeds_dir, angora_out_dir)
}

fn set_sigint_handler(r: Arc<AtomicBool>) {
  ctrlc::set_handler(move || {
      warn!("Ending Fuzzing.");
      r.store(false, Ordering::SeqCst);
      })
  .expect("Error setting SIGINT handler!");
}