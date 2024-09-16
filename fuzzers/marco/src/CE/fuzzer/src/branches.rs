use crate::status_type::StatusType;
use fastgen_common::{config::BRANCHES_SIZE, shm::SHM};
use std::{
    self,
    sync::{
        atomic::{AtomicUsize, Ordering},
        Arc, RwLock,
    },
};
#[cfg(feature = "unstable")]
use std::intrinsics::unlikely;
use std::collections::HashSet;

pub type BranchBuf = [u8; BRANCHES_SIZE];
pub type PathHash = [u64; 1];
#[cfg(target_pointer_width = "32")]
type BranchEntry = u32;
#[cfg(target_pointer_width = "64")]
type BranchEntry = u64;
#[cfg(target_pointer_width = "32")]
const ENTRY_SIZE: usize = 4;
#[cfg(target_pointer_width = "64")]
const ENTRY_SIZE: usize = 8;
type BranchBufPlus = [BranchEntry; BRANCHES_SIZE / ENTRY_SIZE];

// Map of bit bucket
// [1], [2], [3], [4, 7], [8, 15], [16, 31], [32, 127], [128, infinity]
static COUNT_LOOKUP: [u8; 256] = [
    0, 1, 2, 4, 8, 8, 8, 8, 16, 16, 16, 16, 16, 16, 16, 16, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32,
    32, 32, 32, 32, 32, 32, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128,
    128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128,
    128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128,
    128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128,
    128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128,
    128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128,
    128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128,
];

macro_rules! cast {
    ($ptr:expr) => {{
        unsafe { std::mem::transmute($ptr) }
    }};
}

pub struct GlobalBranches {
    virgin_branches: RwLock<Box<BranchBuf>>,
    tmouts_branches: RwLock<Box<BranchBuf>>,
    crashes_branches: RwLock<Box<BranchBuf>>,
    total_hit: RwLock<Box<BranchBuf>>,  
    density: AtomicUsize,
}

impl GlobalBranches {
    pub fn new() -> Self {
        Self {
            virgin_branches: RwLock::new(Box::new([255u8; BRANCHES_SIZE])),
            tmouts_branches: RwLock::new(Box::new([255u8; BRANCHES_SIZE])),
            crashes_branches: RwLock::new(Box::new([255u8; BRANCHES_SIZE])),
            total_hit: RwLock::new(Box::new([255u8; BRANCHES_SIZE])),
            density: AtomicUsize::new(0),
        }
    }

    pub fn get_density(&self) -> f32 {
        let d = self.density.load(Ordering::Relaxed);
        (d * 10000 / BRANCHES_SIZE) as f32 / 100.0
    }
}

pub struct Branches {
    global: Arc<GlobalBranches>,
    trace: SHM<BranchBuf>,
    path_hash: SHM<PathHash>,
}

impl Branches {
    pub fn new(global: Arc<GlobalBranches>) -> Self {
        let trace = SHM::<BranchBuf>::new();
        let path_hash = SHM::<PathHash>::new();
        Self { global, trace, path_hash }
    }

    pub fn clear_trace(&mut self) {
        self.trace.clear();
        self.path_hash[0] = 0;
    }

    pub fn get_id(&self) -> i32 {
        self.trace.get_id()
    }
    pub fn get_path_id(&self) -> i32 {
        self.path_hash.get_id()
    }

    fn get_path(&self, total_buf: &RwLock<Box<BranchBuf>>) -> (Vec<(usize, u8)>, f32) {
        let mut rareness :f32 = 0.0;
        let mut path = Vec::<(usize, u8)>::new();
        let buf_plus: &BranchBufPlus = cast!(&*self.trace); 
        let buf: &BranchBuf = &*self.trace;
        
        // load current hit count
        let mut to_write = vec![];
        {
            let total_buf_read = total_buf.read().unwrap();
            //let total_buf: &BranchBuf = &mut *self.total_hit;
            for (i, &v) in buf_plus.iter().enumerate() {
                macro_rules! run_loop { () => {{
                    let base = i * ENTRY_SIZE;
                    for j in 0..ENTRY_SIZE {
                        let idx = base + j;
                        let new_val = buf[idx]; // 0 ~ 2^20-1
                        let mut old_hit = total_buf_read[idx];
                        if new_val > 0 { // new_val => hit count of one branch. 
                            path.push((idx, COUNT_LOOKUP[new_val as usize]));              
                            //println!("Before: {}, after: {}", old_hit, new_val);     
                            old_hit += new_val;
                            let flt = new_val as f32;
                            let flt_total = old_hit as f32;
                            rareness += (flt / flt_total);      
                            to_write.push((idx, old_hit));
                        }
                    }
                }}}
                #[cfg(feature = "unstable")]
                {
                    if unsafe { unlikely(v > 0) } {
                        run_loop!()
                    }
                }
                #[cfg(not(feature = "unstable"))]
                {
                    if v > 0 {
                        run_loop!()
                    }
                }
            }
        }
        // store new hitcount back
        {
            let mut total_buf_write = total_buf.write().unwrap();
            for &br in &to_write {
                total_buf_write[br.0] = br.1;
            }
        }

        // debug!("count branch table: {}", path.len());
        (path, rareness)
    }

    pub fn has_new(&mut self, status: StatusType) -> bool {
        let gb_map = match status {
            StatusType::Normal => &self.global.virgin_branches,
            StatusType::Timeout => &self.global.tmouts_branches,
            StatusType::Crash => &self.global.crashes_branches,
            _ => {
                return false;
            },
        };
        // let (path, rareness) = self.get_path();
        let all_hit = &self.global.total_hit;
        let (path, rareness) = self.get_path(all_hit);
/*
        let path_hash: &PathHash = &*self.path_hash;
        println!("path_hash: {}", path_hash[0]);
        //let edge_num = path.len();
        println!("Before new path hash insertion, we have {} unique paths", UNIQ_PATH_SET.len());
        if UNIQ_PATH_SET.insert(path_hash[0]) {
            println!("Hit new! set size shall increase by 1: {}", UNIQ_PATH_SET.len());
        }
        else {
            println!("Nothing new! set size remains the same: {}", UNIQ_PATH_SET.len());
        }
        // rare score => priority sum(1/hitcount)
        // path hash => save, hash(current edge adress, hash), xor()

        // set store hash and decide if should generate. 
*/        

        let mut to_write = vec![];
        let mut num_new_edge = 0;
        {
            // read only
            let gb_map_read = gb_map.read().unwrap();
            for &br in &path {
                let gb_v = gb_map_read[br.0];

                if gb_v == 255u8 {
                    num_new_edge += 1;
                }

                if (br.1 & gb_v) > 0 {
                    to_write.push((br.0, gb_v & (!br.1)));
                }
            }
        }

        if num_new_edge > 0 {
            if status == StatusType::Normal {
                // only count virgin branches
                self.global
                    .density
                    .fetch_add(num_new_edge, Ordering::Relaxed);
            }
        }

        if to_write.is_empty() {
            return false;
        }

        {
            // write
            let mut gb_map_write = gb_map.write().unwrap();
            for &br in &to_write {
                gb_map_write[br.0] = br.1;
            }
        }

        true
    }

    pub fn has_new_unique_path(&mut self, status: StatusType, unique_path_set: &mut HashSet<u64>) -> (u16, f32) { // return level and rareness score. 
        let mut path_unique: bool = false; 
        let gb_map = match status {
            StatusType::Normal => &self.global.virgin_branches,
            StatusType::Timeout => &self.global.tmouts_branches,
            StatusType::Crash => &self.global.crashes_branches,
            _ => {
                //return false;
                return (0, 0.0);
            },
        };
        let all_hit = &self.global.total_hit;
        let (path, rareness) = self.get_path(all_hit);
        let path_hash: &PathHash = &*self.path_hash;
        //println!("path_hash: {}", path_hash[0]);
        //let edge_num = path.len();
        //println!("Before new path hash insertion, we have {} unique paths", unique_path_set.len());
        path_unique = unique_path_set.insert(path_hash[0]); // true means made insertion, new path! 
        
        let mut to_write = vec![];
        let mut num_new_edge = 0;
        {
            // read only
            let gb_map_read = gb_map.read().unwrap();
            for &br in &path {
                let gb_v = gb_map_read[br.0];

                if gb_v == 255u8 {
                    num_new_edge += 1;
                }

                if (br.1 & gb_v) > 0 {
                    to_write.push((br.0, gb_v & (!br.1)));
                }
            }
        }

        if num_new_edge > 0 {
            if status == StatusType::Normal {
                // only count virgin branches
                self.global
                    .density
                    .fetch_add(num_new_edge, Ordering::Relaxed);
            }
            assert!(path_unique, "new edge but not path unique???");
        }

        if to_write.is_empty() { // no need to update map 
            if path_unique{
                return (1, rareness);
            }
            else {
                return (0, rareness);
            }
        }

        {
            // write
            let mut gb_map_write = gb_map.write().unwrap();
            for &br in &to_write {
                gb_map_write[br.0] = br.1;
            }
        }
        

        if num_new_edge > 0 {
            return (2, rareness);
        }
        else if path_unique {
            return (1, rareness);
        }
        return (0, rareness);
        
    }
}

impl std::fmt::Debug for Branches {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(f, "")
    }
}

/*
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    #[ignore]
    fn branch_empty() {
        let global_branches = Arc::new(GlobalBranches::new());
        let mut br = Branches::new(global_branches);
        assert_eq!(br.has_new(StatusType::Normal), (false, false, 0));
        assert_eq!(br.has_new(StatusType::Timeout), (false, false, 0));
        assert_eq!(br.has_new(StatusType::Crash), (false, false, 0));
    }

    #[test]
    #[ignore]
    fn branch_find_new() {
        let global_branches = Arc::new(GlobalBranches::new());
        let mut br = Branches::new(global_branches);
        assert_eq!(br.has_new(StatusType::Normal), (false, false, 0));
        {
            let trace = &mut br.trace;
            trace[4] = 1;
            trace[5] = 1;
            trace[8] = 3;
        }
        let path = br.get_path();
        assert_eq!(path.len(), 3);
        assert_eq!(path[2].1, COUNT_LOOKUP[3]);
        assert_eq!(br.has_new(StatusType::Normal), (true, true, 3));
    }
}
*/

