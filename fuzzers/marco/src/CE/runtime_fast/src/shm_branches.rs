// map branch counting shared memory.

use fastgen_common::config::BRANCHES_SIZE;
use fastgen_common::defs::BRANCHES_SHM_ENV_VAR;
use fastgen_common::defs::PATH_HASH_SHM_ENV_VAR;
use fastgen_common::shm;
use std::env;
use std::process;

#[no_mangle]
static mut __angora_cond_cmpid: u32 = 0;

pub type BranchBuf = [u8; BRANCHES_SIZE];
pub type PathHash = [u64; 1];
static mut __ANGORA_AREA_INITIAL: BranchBuf = [255; BRANCHES_SIZE]; // initialize to 1 for each bit
static mut __PATH_HASH_INITIAL: PathHash = [0; 1];    // J.H. 

#[no_mangle]
pub static mut __angora_area_ptr: *const u8 = unsafe{  &__ANGORA_AREA_INITIAL[0] as *const u8 };
#[no_mangle]
pub static mut __path_hash_ptr: *const u64 = unsafe{ &__PATH_HASH_INITIAL[0] as *const u64 };

pub fn map_branch_counting_shm() {
    let id_val = env::var(BRANCHES_SHM_ENV_VAR);
    match id_val {
        Ok(val) => {
            let shm_id = val.parse::<i32>().expect("Could not parse i32 value.");
            let mem = shm::SHM::<BranchBuf>::from_id(shm_id);
            if mem.is_fail() {
              eprintln!("fail to load shm");
              process::exit(1);
            }
            unsafe {
                __angora_area_ptr = mem.get_ptr() as *const u8;
            }
            return;
        }
        Err(_) => {}
    }

}

pub fn path_hash_shm() {
    let id_val = env::var(PATH_HASH_SHM_ENV_VAR);
    match id_val {
        Ok(val) => {
            let shm_id = val.parse::<i32>().expect("Could not parse i32 value.");
            let mem = shm::SHM::<PathHash>::from_id(shm_id);
            if mem.is_fail() {
              eprintln!("fail to load shm");
              process::exit(1);
            }
            unsafe {
                __path_hash_ptr = mem.get_ptr() as *const u64;
            }
            return;
        }
        Err(_) => {}
    }
}