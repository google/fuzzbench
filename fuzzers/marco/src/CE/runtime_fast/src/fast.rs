use super::{forkcli, shm_branches};

use std::sync::Once;

static START: Once = Once::new();

#[ctor]
fn fast_init() {
    START.call_once(|| {
        shm_branches::map_branch_counting_shm();
        shm_branches::path_hash_shm();
        forkcli::start_forkcli();
    });
}

#[no_mangle]
pub extern "C" fn __angora_trace_cmp(
) -> u32 {
  0
}

#[no_mangle]
pub extern "C" fn __angora_trace_switch(
) -> u32 {
  0
}
