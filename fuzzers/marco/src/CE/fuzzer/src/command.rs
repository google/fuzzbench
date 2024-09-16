use crate::{check_dep, tmpfs};
use std::{
    path::{Path, PathBuf},
    process::Command,
};

static TMP_DIR: &str = "tmp";
static INPUT_FILE: &str = "cur_input";
static FORKSRV_SOCKET_FILE: &str = "forksrv_socket";
static TRACK_FILE: &str = "track";

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum InstrumentationMode {
    LLVM,
    Pin,
}

impl InstrumentationMode {
    pub fn from(mode: &str) -> Self {
        match mode {
            "llvm" => InstrumentationMode::LLVM,
            "pin" => InstrumentationMode::Pin,
            _ => unreachable!(),
        }
    }

    pub fn is_pin_mode(&self) -> bool {
        self == &InstrumentationMode::Pin
    }
}

#[derive(Debug, Clone)]
pub struct CommandOpt {
    pub id: usize,
    pub main: (String, Vec<String>),
    pub track: (String, Vec<String>),
    pub tmp_dir: PathBuf,
    pub out_file: String,
    pub forksrv_socket_path: String,
    pub track_path: String,
    pub is_stdin: bool,
    pub mem_limit: u64,
    pub time_limit: u64,
    pub is_raw: bool,
    pub uses_asan: bool,
    pub ld_library: String,
}

impl CommandOpt {
    pub fn new(
        track_target: &str,
        pargs: Vec<String>,
        out_dir: &Path,
        mut mem_limit: u64,
        time_limit: u64,
    ) -> Self {
        
        let tmp_dir = out_dir.join(TMP_DIR);
        tmpfs::create_tmpfs_dir(&tmp_dir);

        let out_file = tmp_dir.join(INPUT_FILE).to_str().unwrap().to_owned();
        let forksrv_socket_path = tmp_dir
            .join(FORKSRV_SOCKET_FILE)
            .to_str()
            .unwrap()
            .to_owned();

        let track_path = tmp_dir.join(TRACK_FILE).to_str().unwrap().to_owned();

        let has_input_arg = pargs.contains(&"@@".to_string());

        let clang_lib = Command::new("llvm-config")
            .arg("--libdir")
            .output()
            .expect("Can't find llvm-config")
            .stdout;
        let clang_lib = String::from_utf8(clang_lib).unwrap();
        // let ld_library = "$LD_LIBRARY_PATH:".to_string() + clang_lib.trim();
        let ld_library = "$LD_LIBRARY_PATH:/workdir/track3/include:/workdir/track3/include/tiny-AES128-C:/usr/local/lib:".to_string() + clang_lib.trim();

        assert_ne!(
            track_target, "-",
            "You should set track target with -t PROM in LLVM mode!"
        );

        let mut tmp_args = pargs.clone();
        let main_bin = tmp_args[0].clone();
        let main_args: Vec<String> = tmp_args.drain(1..).collect();
        let uses_asan = check_dep::check_asan(&main_bin);
        if uses_asan && mem_limit != 0 {
            warn!("The program compiled with ASAN, set MEM_LIMIT to 0 (unlimited)");
            mem_limit = 0;
        }

        let track_bin;
        track_bin = track_target.to_string();
        let track_args = main_args.clone();

        Self {
            id: 0,
            main: (main_bin, main_args),
            track: (track_bin, track_args),
            tmp_dir,
            out_file: out_file,
            forksrv_socket_path,
            track_path,
            is_stdin: !has_input_arg,
            mem_limit,
            time_limit,
            uses_asan,
            is_raw: true,
            ld_library,
        }
    }

    pub fn specify(&self, id: usize) -> Self {
        let mut cmd_opt = self.clone();
        let new_file = format!("{}_{}", &cmd_opt.out_file, id);
        let new_forksrv_socket_path = format!("{}_{}", &cmd_opt.forksrv_socket_path, id);
        let new_track_path = format!("{}_{}", &cmd_opt.track_path, id);
        if !self.is_stdin {
            for arg in &mut cmd_opt.main.1 {
                if arg == "@@" {
                    *arg = new_file.clone();
                }
            }
            for arg in &mut cmd_opt.track.1 {
                if arg == "@@" {
                    *arg = new_file.clone();
                }
            }
        }
        cmd_opt.id = id;
        cmd_opt.out_file = new_file.to_owned();
        cmd_opt.forksrv_socket_path = new_forksrv_socket_path.to_owned();
        cmd_opt.track_path = new_track_path.to_owned();
        cmd_opt.is_raw = false;
        cmd_opt
    }
}

impl Drop for CommandOpt {
    fn drop(&mut self) {
        if self.is_raw {
            tmpfs::clear_tmpfs_dir(&self.tmp_dir);
        }
    }
}
