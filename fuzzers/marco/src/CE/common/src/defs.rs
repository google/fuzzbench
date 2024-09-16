use std;
// -- envs
pub static DISABLE_CPU_BINDING_VAR: &str = "ANGORA_DISABLE_CPU_BINDING";
pub static ANGORA_BIN_DIR: &str = "ANGORA_BIN_DIR";

// executor.rs
pub static TRACK_OUTPUT_VAR: &str = "ANGORA_TRACK_OUTPUT";
pub static COND_STMT_ENV_VAR: &str = "ANGORA_COND_STMT_SHM_ID";
pub static BRANCHES_SHM_ENV_VAR: &str = "ANGORA_BRANCHES_SHM_ID";
pub static PATH_HASH_SHM_ENV_VAR: &str = "PATH_HASH_SHM_ID";
pub static LD_LIBRARY_PATH_VAR: &str = "LD_LIBRARY_PATH";
pub static ASAN_OPTIONS_VAR: &str = "ASAN_OPTIONS";
pub static MSAN_OPTIONS_VAR: &str = "MSAN_OPTIONS";
pub static ASAN_OPTIONS_CONTENT: &str =
    "abort_on_error=1:detect_leaks=0:symbolize=0:allocator_may_return_null=1";
pub const MSAN_ERROR_CODE: i32 = 86;
pub static MSAN_OPTIONS_CONTENT: &str =
    "exit_code=86:symbolize=0:abort_on_error=1:allocator_may_return_null=1:msan_track_origins=0";

// depot.rs
pub static CRASHES_DIR: &str = "crashes";
pub static HANGS_DIR: &str = "hangs";
pub static INPUTS_DIR: &str = "queue";

pub static GRADER_DIR: &str = "grader";
pub static GRADER_Q_DIR: &str = "queue";
pub static GRADER_CTL_DIR: &str = "../grader-ctrl/queue";
pub static GRADER_P_DIR: &str = "../grader-path/queue";

// forksrv.rs
pub static ENABLE_FORKSRV: &str = "ANGORA_ENABLE_FORKSRV";
pub static FORKSRV_SOCKET_PATH_VAR: &str = "ANGORA_FORKSRV_SOCKET_PATH";

// command.rs
pub static ANGORA_DIR_NAME: &str = "angora";
pub static ANGORA_LOG_FILE: &str = "angora.log";
pub static COND_QUEUE_FILE: &str = "cond_queue.csv";
pub static CHART_STAT_FILE: &str = "chart_stat.json";

// tmpfs.rs
pub static PERSIST_TRACK_FILES: &str = "ANGORA_DISABLE_TMPFS";

pub const UNREACHABLE: u64 = std::u64::MAX;

pub const SLOW_SPEED: u32 = 888888;

pub static TAINT_OPTIONS: &str = "TAINT_OPTIONS";
