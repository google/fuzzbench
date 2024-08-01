// branch.rs
pub const MAP_SIZE_POW2: usize = 20;
pub const BRANCHES_SIZE: usize = 1 << MAP_SIZE_POW2;
pub const ENABLE_RANDOM_LEN: bool = false;
pub const ENABLE_MICRO_RANDOM_LEN: bool = true;
pub const TMOUT_SKIP: usize = 3;
pub const TIME_LIMIT: u64 = 1;
pub const MEM_LIMIT: u64 = 1024; // MB
pub const TIME_LIMIT_TRACK: u64 = 180; // 180
pub const MEM_LIMIT_TRACK: u64 = 0;

pub const MAX_INVARIABLE_NUM: usize = 16;
pub const MAX_INPUT_LEN: usize = 15000;
pub const SAVING_WHOLE: bool = true; // save all seeds for afl-grader-rare to filter. 
pub const USE_CODECACHE: bool = true;


//AFL
pub const MAX_SPLICE_TIMES: usize = 45;
pub const MAX_HAVOC_FLIP_TIMES: usize = 45;
pub const RANDOM_LEN_NUM: usize = 30;
