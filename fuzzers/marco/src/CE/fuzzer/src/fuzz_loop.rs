extern crate redis;
//use redis::{Client, Commands, Connection, RedisResult};
use crate::{
  branches::GlobalBranches, command::CommandOpt, depot::Depot, depot::DepotSync,
    executor::Executor, executor::ExecutorSync,
};
use std::sync::{ atomic::{AtomicBool, Ordering, AtomicUsize, AtomicU32},
    Arc, //RwLock,
};
use std::fs;

use std::time::SystemTime;
use std::time;
use std::thread;
use crate::cpp_interface::*;
use crate::file::*;
use fastgen_common::config;
use std::path::{Path, PathBuf};

pub fn constraint_solver(brc_flip: u32, shmid: i32, id: usize, lastone: u32) {
  info!("lastone = {}", lastone); 
  unsafe { run_solver(shmid, id, brc_flip, lastone) };
}

// fifo & sage mode;
pub fn ce_loop_sync(
    seeds_dir: PathBuf,
    running: Arc<AtomicBool>,
    cmd_opt: CommandOpt,
    depot: Arc<DepotSync>,
    global_branches: Arc<GlobalBranches>,
    time_list: bool,
    brc_strategy: u32,
    do_fifo: u32,
    ) {
  let mut id: usize = 0;
  let executor_id = cmd_opt.id;
  let mut all_time = 0;
  let mut last_all_time = 0;
  let shmid = match executor_id {
    2 => unsafe {
      libc::shmget(
          0x9876,
          0xc00000000,
          0o644 | libc::IPC_CREAT | libc::SHM_NORESERVE
          )
    },
    3 => unsafe {
      libc::shmget(
          0x8765,
          0xc00000000,
          0o644 | libc::IPC_CREAT | libc::SHM_NORESERVE
          )
    },
    _ => 0,
  };

  let mut executor = ExecutorSync::new(
      cmd_opt,
      depot.clone(),
      shmid,
      );

  while running.load(Ordering::Relaxed) {
    // unsafe { wait_ce(); }
    let mut time_used: u32 = 0;
    let mut t_start = time::Instant::now();
    let mut flag:bool = false;

    if (do_fifo > 0) { // fifo sync from fifo/queue/ and afl-slave/queue
      for n in 0..2 { // n takes 0 1
        depot.sync_fz_cefifo(n);
      }
    } else { // sage config; tier sync
      for n in 0..3 { // n take values: 0, 1, 2
        depot.sync_new(n); // synchronize fuzzer seed, edge seed, control seed
      }
    }

    while let Some((buf, path, queue_id, seed_id, lastone)) = depot.get_next_input_rare() {
      
      let handle = thread::spawn(move || {
          constraint_solver(brc_strategy, shmid, executor_id, lastone);
        });

      // this is to run CE constraint collector
      executor.track(seed_id as usize, queue_id as usize, &buf);
        
      if handle.join().is_err() {
        error!("Error happened in listening thread!");
      }

      let used_t1 = t_start.elapsed();
      time_used = used_t1.as_secs() as u32;

      info!("{:?}: Done executing {:?} from queue_id {}, time since last print {:?}", SystemTime::now(), path.display(), queue_id, time_used);

      if (time_used > 30) {
        info!("time slice is used up");
        break;
      }    
      // depot.sync_fz_cefifo(0); // frequently check fzq; hold off ce solving until fz stuck. 
    }

    all_time += time_used;
    if (last_all_time != all_time) {
      info!("total ce_time {:?}, current epi cost: {:?}", all_time, time_used);
      last_all_time = all_time;
    }

    // unsafe { post_gra(); }
    time_used = 0;
  }
}

#[cfg(test)]
mod tests {
  use super::*;
  use std::fs;
  use std::path::PathBuf;
  use crate::depot;
  use crate::command;
  use crate::branches;


#[test]
  fn test_grading() {
    let angora_out_dir = PathBuf::from("/home/jie/fastgen/workdir/playground/output-grading");
    println!("{:?}", angora_out_dir);
    let seeds_dir = PathBuf::from("/home/jie/fastgen/workdir/playground/input-grading");
    println!("{:?}", seeds_dir);
    let args = vec!["/home/jie/fastgen/workdir/binutils-2.33.1-fast/binutils/objdump".to_string(), "-D".to_string(), "@@".to_string()];
    fs::create_dir(&angora_out_dir).expect("Output directory has existed!");

    let cmd_opt = command::CommandOpt::new("/home/jie/fastgen/work/binutils-2.33.1-taint/binutils/objdump", args, &angora_out_dir, 200, 1);

    let depot = Arc::new(depot::Depot::new(seeds_dir, &angora_out_dir));

    let global_branches = Arc::new(branches::GlobalBranches::new());

    let mut executor = Executor::new(
        cmd_opt.specify(1),
        global_branches.clone(),
        depot.clone(),
        2
        );

    let t_start = time::Instant::now();
    let mut fid = 1;
    let dirpath = Path::new("/home/jie/fastgen/workdir/playground/test");
    let mut count = 0;
    loop {
      let file_name = format!("id-{:08}", fid);
      let fpath = dirpath.join(file_name);
      if !fpath.exists() {
        break;
      }
      trace!("grading {:?}", &fpath);
      let buf = read_from_file(&fpath);
      executor.run_sync(&buf);
      fid = fid + 1;
      count = count + 1;
    }
    let used_t1 = t_start.elapsed();
    if used_t1.as_secs() as u32 !=0  {
      println!("throught put is {}", count / used_t1.as_secs() as u32);
    }
  }

#[test]
  fn test_scan() {
    let shmid = unsafe {
      libc::shmget(
          0x1234,
          0xc00000000,
          0o644 | libc::IPC_CREAT | libc::SHM_NORESERVE
          )
    };

    unsafe { init_core(true); }
    unsafe { run_solver(shmid, 2); }
  }
}
