// create a tmpfs to make our fuzzing faster
// only for :
// inputs directory and .cur_input, .socket file

use libc;
use std::{fs, os::unix::fs::symlink, path::Path, env};
use fastgen_common::defs;

static LINUX_TMPFS_DIR: &str = "/dev/shm";

pub fn create_tmpfs_dir(target: &Path) {
    if env::var(defs::PERSIST_TRACK_FILES).is_ok() {
        fs::create_dir(&target).unwrap();
        return;
    }
    let shm_dir = Path::new(LINUX_TMPFS_DIR);
    if shm_dir.is_dir() {
        // support tmpfs
        // create a dir in /dev/shm, then symlink it to target
        let pid = unsafe { libc::getpid() as usize };
        let dir_name = format!("angora_tmp_{}", pid);
        let tmp_dir = shm_dir.join(dir_name);
        fs::create_dir(&tmp_dir).unwrap();
        if target.exists() {
            fs::remove_file(target).unwrap();
        }
        symlink(&tmp_dir, target).unwrap();
    } else {
        // not support
        warn!(
            "System does not have {} directory! Can't use tmpfs.",
            LINUX_TMPFS_DIR
        );
        fs::create_dir(&target).unwrap();
    }
}

pub fn clear_tmpfs_dir(target: &Path) {
    if env::var(defs::PERSIST_TRACK_FILES).is_ok() {
        return;
    }
    if target.exists() {
        fs::remove_file(target).unwrap();
    }
    let shm_dir = Path::new(LINUX_TMPFS_DIR);
    if shm_dir.is_dir() {
        // support tmpfs
        let pid = unsafe { libc::getpid() as usize };
        let dir_name = format!("angora_tmp_{}", pid);
        let tmp_dir = shm_dir.join(dir_name);
        fs::remove_dir_all(&tmp_dir).unwrap();
    }
}
