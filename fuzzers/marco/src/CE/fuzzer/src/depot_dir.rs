use fastgen_common::defs;
use std::{
    fs,
    path::{Path, PathBuf},
};

#[derive(Debug)]
pub struct DepotDir {
    pub inputs_dir: PathBuf,
    pub hangs_dir: PathBuf,
    pub crashes_dir: PathBuf,
    pub seeds_dir: PathBuf,
}

impl DepotDir {
    pub fn new(seeds_dir: PathBuf, out_dir: &Path) -> Self {

        let inputs_dir = out_dir.join(defs::INPUTS_DIR);
        let hangs_dir = out_dir.join(defs::HANGS_DIR);
        let crashes_dir = out_dir.join(defs::CRASHES_DIR);

        fs::create_dir(&crashes_dir).unwrap();
        fs::create_dir(&hangs_dir).unwrap();
        fs::create_dir(&inputs_dir).unwrap();

        Self {
            inputs_dir,
            hangs_dir,
            crashes_dir,
            seeds_dir,
        }
    }
}

#[derive(Debug)]
pub struct DepotSyncDir {
    pub grader_queue_dir: PathBuf,
    pub grader_path_dir: PathBuf,
    pub afl_queue_dir: PathBuf,
    pub ce_queue_dir: PathBuf,
    pub greenlight: PathBuf,
}

impl DepotSyncDir {
    pub fn new(out_dir: &Path) -> Self {
        let grader_queue_dir = out_dir.join("grader").join("queue");
        let grader_path_dir = out_dir.join("grader-path").join("queue");
        let afl_queue_dir = out_dir.join("afl-slave").join("queue");
        // let ce_queue_dir = out_dir.join("ce_output0").join("queue");
        let ce_queue_dir = out_dir.join("fifo").join("queue");
        let greenlight = out_dir.join("greenlight");

        Self {
            grader_queue_dir,
            grader_path_dir,
            afl_queue_dir,
            ce_queue_dir,
            greenlight,
        }
    }
}
