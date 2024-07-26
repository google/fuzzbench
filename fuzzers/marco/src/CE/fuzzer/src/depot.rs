use crate::job_queue::*;
use crate::bcount_queue::*;
use crate::bcount_queue::*;
use crate::file::*;
use crate::depot_dir::*;
use crate::status_type::StatusType;
use rand;
use std::{
    fs,
    io::prelude::*,
    path::{Path, PathBuf},
    sync::{
        atomic::{AtomicUsize, Ordering},
        Mutex,
    },
};
use min_max_heap::MinMaxHeap;
use priority_queue::PriorityQueue;
extern crate glob;
use self::glob::glob;
//use std::process;
// https://crates.io/crates/priority-queue

pub struct DepotSync {
  pub dirs: DepotSyncDir,
  pub next_afl_id: AtomicUsize,
  pub next_grader_q_id: AtomicUsize,
  pub next_ce_queue_id: AtomicUsize,
  pub next_grader_path_id: AtomicUsize,
  pub next_sample_afl_id: AtomicUsize,
  pub next_sample_grader_q_id: AtomicUsize,
  pub next_sample_grader_ctl_id: AtomicUsize,
  pub afl_gen_count: AtomicUsize,
  pub graderq_gen_count: AtomicUsize,
  pub graderc_gen_count: AtomicUsize,
  //pub input_queue: Mutex<PriorityQueue<PathBuf, BcountPriorityValue>>,
  pub input_queue: Mutex<MinMaxHeap<BcountPriorityValue>>,
  pub num_inputs: AtomicUsize,
}

impl DepotSync {
  pub fn new(out_dir: &Path) -> Self {
    Self {
      dirs: DepotSyncDir::new(out_dir),
      next_afl_id: AtomicUsize::new(0),
      next_grader_q_id: AtomicUsize::new(0),
      next_ce_queue_id: AtomicUsize::new(0),
      next_grader_path_id: AtomicUsize::new(0),
      next_sample_afl_id: AtomicUsize::new(0),
      next_sample_grader_q_id: AtomicUsize::new(0),
      next_sample_grader_ctl_id: AtomicUsize::new(0),
      afl_gen_count: AtomicUsize::new(1),
      graderq_gen_count: AtomicUsize::new(1),
      graderc_gen_count: AtomicUsize::new(1),
      // input_queue: Mutex::new(PriorityQueue::new()),
      input_queue: Mutex::new(MinMaxHeap::new()),
      num_inputs: AtomicUsize::new(0),
    }
  }

  fn check_seed(&self, category: i32) -> Option<PathBuf> {
    let mut seed_id = 0;
    let mut query = String::new();
    let mut rpath = PathBuf::new();
    let mut found = false;
    match category {
      0 => {
              seed_id = self.next_afl_id.load(Ordering::Relaxed);
              query = format!("{}/id:{:06}*", self.dirs.afl_queue_dir.display(), seed_id);
           },
      1 => {
              seed_id = self.next_grader_q_id.load(Ordering::Relaxed);
              query = format!("{}/id:{:06}*", self.dirs.grader_queue_dir.display(), seed_id);
           },
      2 => {
              seed_id = self.next_grader_path_id.load(Ordering::Relaxed);
              query = format!("{}/id:{:06}*", self.dirs.grader_path_dir.display(), seed_id);
           },
      _ => (),
    }
    for entry in glob(&query).expect("Failed to read glob pattern") {
      match entry {
        Ok(path) => {
          found = true;
          rpath = path;
          break;
        },
        Err(e) => println!("{:?}", e),
      }
    }
    if found {
      seed_id = seed_id + 1;
      match category {
        0 => { self.next_afl_id.store(seed_id, Ordering::Relaxed); },
        1 => { self.next_grader_q_id.store(seed_id, Ordering::Relaxed); },
        2 => { self.next_grader_path_id.store(seed_id, Ordering::Relaxed); },
        _ => (),
      }
    }
    if found {
      info!("Execute {:?}", rpath.display());
      return Some(rpath);
    }
    None
  }

  pub fn enqueue(&self, path: PathBuf, rare: u32,  queue_id: u32, seed_id: u32) {
    let mut q = match self.input_queue.lock() {
      Ok(guard) => guard,
        Err(poisoned) => {
          warn!("Mutex for input queue posioned");
          poisoned.into_inner()
        },
    };

    // println!("enqueue: queueid: {}, rarescore: {}, seed_id: {}, path: {}", queue_id, rare, seed_id, path.display());

    q.push(BcountPriorityValue{queue_id: queue_id,
                                rare_score: rare,
                                seed_id: seed_id,
                                path: path});
  }

  pub fn isempty(&self) -> bool {
    self.num_inputs.load(Ordering::Relaxed) == 0
    // let mut q = match self.input_queue.lock() {
    //   Ok(guard) => guard,
    //     Err(poisoned) => {
    //       warn!("Mutex for input queue posioned");
    //       poisoned.into_inner()
    //     },
    // };
    // q.is_empty()
  }

  pub fn qlen(&self) -> usize {
    self.num_inputs.load(Ordering::Relaxed)
    // let mut q = match self.input_queue.lock() {
    //   Ok(guard) => guard,
    //     Err(poisoned) => {
    //       warn!("Mutex for input queue posioned");
    //       poisoned.into_inner()
    //     },
    // };
    // q.len()
  }

  pub fn greenlights2v(&self) {
    let mut f = fs::File::create(self.dirs.greenlight.as_path()).expect("Could not save new input file.");
  }

  pub fn sync_fz_cefifo(&self, category: i32) {
    let mut totalnum = self.num_inputs.load(Ordering::Relaxed);
    // synchronize fzq and then ce_output0 queue
    let mut seed_id = 0;
    match category {
      0 => { seed_id = self.next_afl_id.load(Ordering::Relaxed); },
      1 => { seed_id = self.next_ce_queue_id.load(Ordering::Relaxed); },
      _ => (),
    }
    loop { // loop to sync all new seeds inside the directory
      let mut query = String::new();
      let mut prefixfmt = String::new();
      let mut rpath = PathBuf::new();
      let mut found = false;

      match category {
        0 => { query = format!("{}/id:{:06}*", self.dirs.afl_queue_dir.display(), seed_id);
                prefixfmt = format!("{}", self.dirs.afl_queue_dir.display()); },
        1 => { query = format!("{}/id:{:06}*", self.dirs.ce_queue_dir.display(), seed_id);
                prefixfmt = format!("{}", self.dirs.ce_queue_dir.display()); },
        _ => (),
      }

      for entry in glob(&query).expect("Failed to read glob pattern") {
        match entry {
          Ok(path) => {
            found = true;
            rpath = path;
            // println!("find next seed here: {}", rpath.display());
            break;
          },
          Err(e) =>  {
            println!("{:?}", e);
          },
        }
      }
      if  (!found || self.qlen() > 0)  { // never found the nextid
        match category {
          0 => { 
            self.next_afl_id.store(seed_id, Ordering::Relaxed); 
            self.num_inputs.store(totalnum, Ordering::Relaxed);},
          1 => { 
            self.next_ce_queue_id.store(seed_id, Ordering::Relaxed); 
            self.num_inputs.store(totalnum, Ordering::Relaxed);},
          _ => (),
        }
        break;
      }
      let mut rarevalue: u32 = 0;
      if (category > 0 ) {
        rarevalue = 999999 - (seed_id as u32);
      }

      if (category > 0 || 
        (category == 0 && (rpath.as_path().display().to_string().contains("orig") || rpath.as_path().display().to_string().contains("+cov")))) {
          println!("enqueue: {}", rpath.display());
          self.enqueue(rpath, rarevalue, category as u32, seed_id as u32);
          totalnum += 1;
      }
      
      // move on to next
      seed_id = seed_id + 1;      
    }
  }

  // helper func of rareness based priority queue
  pub fn sync_new(&self, category: i32) -> bool {
    // scan 3 queues for new seeds and enqueue
    let mut seed_id = 0;
    let mut res:bool = false;

    match category { // load checkpoint first
      0 => { seed_id = self.next_afl_id.load(Ordering::Relaxed); },
      1 => { seed_id = self.next_grader_q_id.load(Ordering::Relaxed); },
      2 => { seed_id = self.next_grader_path_id.load(Ordering::Relaxed); },
      _ => (),
    }

    loop { // loop to sync all new seeds inside the directory
      let mut query = String::new();
      let mut prefixfmt = String::new();
      let mut rpath = PathBuf::new();
      let mut found = false;

      match category {
        0 => { query = format!("{}/id:{:06}*", self.dirs.afl_queue_dir.display(), seed_id);
                prefixfmt = format!("{}", self.dirs.afl_queue_dir.display()); },
        1 => { query = format!("{}/id:{:06}*", self.dirs.grader_queue_dir.display(), seed_id);
                prefixfmt = format!("{}", self.dirs.grader_queue_dir.display()); },
        2 => { query = format!("{}/id:{:06}*", self.dirs.grader_path_dir.display(), seed_id);
                prefixfmt = format!("{}", self.dirs.grader_path_dir.display()); },
        _ => (),
      }
      // println!("making query to {}", query);
      for entry in glob(&query).expect("Failed to read glob pattern") {
        match entry {
          Ok(path) => {
            found = true;
            rpath = path;
            res = true;
            // println!("find next seed here: {}", rpath.display());
            break;
          },
          Err(e) =>  {
            println!("{:?}", e);
          },
        }
      }
      if  (!found)  { // never found the nextid
        match category {
          0 => { self.next_afl_id.store(seed_id, Ordering::Relaxed); },
          1 => { self.next_grader_q_id.store(seed_id, Ordering::Relaxed); },
          2 => { self.next_grader_path_id.store(seed_id, Ordering::Relaxed); },
          _ => (),
        }
        break;
      }
      let mut rarevalue: u32 = 0;
      if (category > 0 ) { // grader queue, not inf inside name

        let fname = rpath.strip_prefix(prefixfmt).unwrap().to_str().unwrap();
        if (!fname.contains("inf")) {
          let v: Vec<&str> = fname.split('_').collect();
          let raref: f32 = v.get(1).unwrap_or(&"0.00").parse().unwrap();
          rarevalue = (100.0 * raref) as u32;
        }
      // } else { // fzq, continue to next id if the file is not "+cov"
      //   let fname = rpath.strip_prefix(prefixfmt).unwrap().to_str().unwrap();
        // println("enqueue fzq seed {:?}", rpath);
        // if (!fname.contains("+cov")) {
        //   seed_id = seed_id + 1;
        //   continue;
        // }
      }

      // now push the seed into the job queue
      // println!("pushed: {}", rpath.display());
      self.enqueue(rpath, rarevalue, category as u32, seed_id as u32);

      // move on to next
      seed_id = seed_id + 1;
    }
    return res;
  }


  pub fn get_next_input_rare(&self) -> Option<(Vec<u8>, PathBuf, u32, u32, u32)> {
    
    
    // pop the top one from queue
    let mut q = match self.input_queue.lock() {
      Ok(guard) => guard,
      Err(poisoned) => {
        warn!("Mutex for input queue posioned");
        poisoned.into_inner()
      },
    };    
    let qsize: usize = self.qlen();
    info!("qsize is: {:?}", qsize);
    
    while let Some(item) = q.pop_max() {
        let mut totalnum = self.num_inputs.load(Ordering::Relaxed);
        totalnum = totalnum - 1;
        self.num_inputs.store(totalnum, Ordering::Relaxed);
        let b = Path::new(&item.path).exists();
        // info!("new seed to run: {}", item.path.display);
        if b {            
          // info!("queueid: {}", item.queue_id);
            return Some((read_from_file(&item.path), item.path, item.queue_id, item.seed_id, (totalnum == 0) as u32))
        }
    }
    info!("queue empty now ");
    None
  }
}

pub struct Depot {
    pub input_queue: Mutex<PriorityQueue<SeedFilePath, PriorityValue>>,
    pub num_inputs: AtomicUsize,
    pub num_hangs: AtomicUsize,
    pub num_crashes: AtomicUsize,
    pub dirs: DepotDir,
}

impl Depot {
    pub fn new(in_dir: PathBuf, out_dir: &Path) -> Self {
        Self {
            input_queue: Mutex::new(PriorityQueue::new()),
            num_inputs: AtomicUsize::new(0),
            num_hangs: AtomicUsize::new(0),
            num_crashes: AtomicUsize::new(0),
            dirs: DepotDir::new(in_dir, out_dir),
        }
    }

    fn save_input(
        status: &StatusType,
        buf: &Vec<u8>,
        num: &AtomicUsize,
        dir: &Path,
    ) -> usize {
        let mut id = num.load(Ordering::Relaxed);
        trace!(
            "Find {} th new {:?} input",
            id,
            status,
        );
        let new_path = get_file_name(dir, id);
        let mut f = fs::File::create(new_path.as_path()).expect("Could not save new input file.");
        f.write_all(buf)
            .expect("Could not write seed buffer to file.");
        f.flush().expect("Could not flush file I/O.");
        id = id + 1;
        num.store(id, Ordering::Relaxed);
        id
    }

    fn save_input_queue(
        status: &StatusType,
        buf: &Vec<u8>,
        num: &AtomicUsize,
        dir: &Path,
        rare: &f32,
        input_q: &Mutex<PriorityQueue<SeedFilePath, PriorityValue>>,
        lvl: &u16,
    ) -> usize {
        let mut id = num.load(Ordering::Relaxed);
        trace!(
            "Find {} th new {:?} input",
            id,
            status,
        );
        //let new_path = get_file_name_rare(dir, id, rare);
        let new_path = get_file_name(dir, id);
        let mut q = match input_q.lock() {
            Ok(guard) => guard,
            Err(poisoned) => {
                warn!("Mutex poisoned! Results may be incorrect. Continuing...");
                poisoned.into_inner()
            },
        };

        let new_seed = SeedFilePath{file_id: id};
        // for rare rank
        let new_prio = PriorityValue{level: *lvl, rare_score: *rare};
        // for fifo rank
        // let a: u16 = id as u16;
        // let new_prio = PriorityValue{level: a, rare_score: 0.0};

        q.push(new_seed, new_prio);
        //println!("Insert new seed: {}, {}, {}", id, lvl, rare);

        let mut f = fs::File::create(new_path.as_path()).expect("Could not save new input file.");
        f.write_all(buf)
            .expect("Could not write seed buffer to file.");
        f.flush().expect("Could not flush file I/O.");
        id = id + 1;
        num.store(id, Ordering::Relaxed);
        id
    }

     pub fn save(&self, status: StatusType, buf: &Vec<u8>) -> usize {
         match status {
             StatusType::Normal => {
                 Self::save_input(&status, buf, &self.num_inputs, &self.dirs.inputs_dir)
             },
             StatusType::Timeout => {
                 Self::save_input(&status, buf, &self.num_hangs, &self.dirs.hangs_dir)
             },
             StatusType::Crash => Self::save_input(
                 &status,
                 buf,
                 &self.num_crashes,
                 &self.dirs.crashes_dir,
             ),
             _ => 0,
         }
     }

    pub fn empty(&self) -> bool {
        self.num_inputs.load(Ordering::Relaxed) == 0
        //let mut q = match self.input_queue.lock() {
        //    Ok(guard) => guard,
        //    Err(poisoned) => {
        //        warn!("Mutex poisoned! Results may be incorrect. Continuing...");
        //        poisoned.into_inner()
        //    },
        //};
        //q.is_empty()
    }

    pub fn next_random(&self) -> usize {
        rand::random::<usize>() % self.num_inputs.load(Ordering::Relaxed)
    }

    pub fn get_input_buf(&self, id: usize) -> Vec<u8> {
        let path = get_file_name(&self.dirs.inputs_dir, id);
        read_from_file(&path)
    }

    pub fn get_next_in_queue(&self) -> (Vec<u8>, usize) {
        let mut q = match self.input_queue.lock() {
            Ok(guard) => guard,
            Err(poisoned) => {
                warn!("Mutex poisoned! Results may be incorrect. Continuing...");
                poisoned.into_inner()
            },
        };
        let (x, y) = q.pop().unwrap();
        println!("[get_next_in_queue]: {:?}, {}, {}", x.file_id, y.level, y.rare_score);
        //let mut outlog = std::fs::OpenOptions::new().append(true).open("/home/jie/coco-loop/log.log").expect("cannot open file");
        //write!(outlog, "[new input] = {}, rare = {}\n", x.file_id, y.rare_score);
        let path = get_file_name(&self.dirs.inputs_dir, x.file_id);
        (read_from_file(&path), x.file_id)
    }

    pub fn get_input_path(&self, id: usize) -> PathBuf {
        get_file_name(&self.dirs.inputs_dir, id)
    }

    pub fn get_num_inputs(&self) -> usize {
        self.num_inputs.load(Ordering::Relaxed)
    }
}
