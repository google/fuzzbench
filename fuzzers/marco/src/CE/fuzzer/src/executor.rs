use crate::status_type::StatusType;
use super::{limit::SetLimit, *};

use crate::pipe_fd::PipeFd;
use crate::forksrv::Forksrv;

use crate::{
    branches, command,
    depot, 
};
use fastgen_common::{config, defs};

use std::{
    collections::HashMap,
    process::{Command, Stdio},
    sync::{
        atomic::{compiler_fence, Ordering},
        Arc,
    },
    time,
};
use wait_timeout::ChildExt;
use std::collections::HashSet;
//use std::io::Write;

pub struct ExecutorSync {
    pub cmd: command::CommandOpt,
    envs: HashMap<String, String>,
    depot: Arc<depot::DepotSync>,
    fd: PipeFd,
    tmout_cnt: usize,
    pub shmid: i32,
}

impl ExecutorSync {
  fn run_target(
        &self,
        target: &(String, Vec<String>),
        mem_limit: u64,
        time_limit: u64,
    ) -> StatusType {
        //info!("[new epi]: {}, {:?}, {:?}", &target.0, &target.1, &self.envs);
        let mut cmd = Command::new(&target.0);
        let mut child = cmd
            .args(&target.1)
          //  .stdin(Stdio::null())
            .env_clear()
            .envs(&self.envs)
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .mem_limit(mem_limit.clone())
            .setsid()
            .pipe_stdin(self.fd.as_raw_fd(), self.cmd.is_stdin)
            .spawn()
            .expect("Could not run target");


        let timeout = time::Duration::from_secs(time_limit);
        let ret = match child.wait_timeout(timeout).unwrap() {
            Some(status) => {
                if let Some(status_code) = status.code() {
                    if self.cmd.uses_asan && status_code == defs::MSAN_ERROR_CODE
                    {
                        StatusType::Crash
                    } else {
                        StatusType::Normal
                    }
                } else {
                    StatusType::Crash
                }
            }
            None => {
                // Timeout
                // child hasn't exited yet
                child.kill().expect("Could not send kill signal to child.");
                child.wait().expect("Error during waiting for child.");
                StatusType::Timeout
            }
        };
        ret
  }

  fn write_test(&mut self, buf: &Vec<u8>) {
        self.fd.write_buf(buf);
        if self.cmd.is_stdin {
            self.fd.rewind();
        }
  }

  pub fn new(
        cmd: command::CommandOpt,
        depot: Arc<depot::DepotSync>,
        shmid: i32,
    ) -> Self {
        // ** Envs **
        let mut envs = HashMap::new();
        envs.insert(
            defs::ASAN_OPTIONS_VAR.to_string(),
            defs::ASAN_OPTIONS_CONTENT.to_string(),
        );
        envs.insert(
            defs::MSAN_OPTIONS_VAR.to_string(),
            defs::MSAN_OPTIONS_CONTENT.to_string(),
        );
        envs.insert(
            defs::LD_LIBRARY_PATH_VAR.to_string(),
            cmd.ld_library.clone(),
        );

        let fd = pipe_fd::PipeFd::new(&cmd.out_file);
        
        Self {
            cmd,
            envs,
            depot,
            fd,
            tmout_cnt: 0,
            shmid,
        }
    }

    pub fn track(&mut self, id: usize, qid: usize, buf: &Vec<u8>) {
        //FIXME
        // let e = format!("taint_file=output/tmp/cur_input_2 solver_select=1 tid={}",id);
        let e = format!("taint_file={} tid={} shmid={} pipeid={} inputid={}", &self.cmd.out_file, &qid, &self.shmid, &self.cmd.id, &id);

        if self.cmd.is_stdin {
            let e = format!("taint_file=stdin tid={} shmid={} pipeid={} inputid={}", &qid, &self.shmid, &self.cmd.id, &id);
        } 
        info!("Track {}, e is {}", &id, e);

        // let mut outlog = std::fs::OpenOptions::new().append(true).open("/home/jie/coco-loop/log.log").expect("cannot open file");
        // write!(outlog, "[new input] = {}\n", id);
        self.envs.insert(
            defs::TAINT_OPTIONS.to_string(),
            e,
        );


        self.write_test(buf);

        compiler_fence(Ordering::SeqCst);
        let ret_status = self.run_target(
            &self.cmd.track,
            config::MEM_LIMIT_TRACK,
            //self.cmd.time_limit *
            config::TIME_LIMIT_TRACK,
        );
        compiler_fence(Ordering::SeqCst);

        if ret_status != StatusType::Normal {
            error!(
                "Crash or hang while tracking! -- {:?},  id: {}",
                ret_status, id
            );
            return;
        }
    }
}

pub struct Executor {
    pub cmd: command::CommandOpt,
    pub branches: branches::Branches,
    envs: HashMap<String, String>,
    forksrv: Option<Forksrv>,
    depot: Arc<depot::Depot>,
    fd: PipeFd,
    tmout_cnt: usize,
    pub has_new_path: bool,
    pub unique_path_hash: HashSet<u64>,
    pub shmid: i32,
}

impl Executor {
    pub fn new(
        cmd: command::CommandOpt,
        global_branches: Arc<branches::GlobalBranches>,
        depot: Arc<depot::Depot>,
        shmid: i32,
    ) -> Self {
        // ** set for path hash 
        let mut unique_path_hash = HashSet::new();
        // ** Share Memory **
        let branches = branches::Branches::new(global_branches);
        // ** Envs **
        let mut envs = HashMap::new();
        envs.insert(
            defs::ASAN_OPTIONS_VAR.to_string(),
            defs::ASAN_OPTIONS_CONTENT.to_string(),
        );
        envs.insert(
            defs::MSAN_OPTIONS_VAR.to_string(),
            defs::MSAN_OPTIONS_CONTENT.to_string(),
        );
        envs.insert(
            defs::BRANCHES_SHM_ENV_VAR.to_string(),
            branches.get_id().to_string(),
        );
        envs.insert(
            defs::PATH_HASH_SHM_ENV_VAR.to_string(),
            branches.get_path_id().to_string(),
        );
        envs.insert(
            defs::LD_LIBRARY_PATH_VAR.to_string(),
            cmd.ld_library.clone(),
        );

        let fd = pipe_fd::PipeFd::new(&cmd.out_file);
        let forksrv = Some(forksrv::Forksrv::new(
            &cmd.forksrv_socket_path,
            &cmd.main,
            &envs,
            fd.as_raw_fd(),
            cmd.is_stdin,
            cmd.uses_asan,
            cmd.time_limit,
            cmd.mem_limit,
        ));

        Self {
            cmd,
            branches,
            envs,
            forksrv,
            depot,
            fd,
            tmout_cnt: 0,
            has_new_path: false,
            unique_path_hash,
            shmid,
        }
    }

    pub fn rebind_forksrv(&mut self) {
        {
            // delete the old forksrv
            self.forksrv = None;
        }
        let fs = forksrv::Forksrv::new(
            &self.cmd.forksrv_socket_path,
            &self.cmd.main,
            &self.envs,
            self.fd.as_raw_fd(),
            self.cmd.is_stdin,
            self.cmd.uses_asan,
            self.cmd.time_limit,
            self.cmd.mem_limit,
        );
        self.forksrv = Some(fs);
    }

    pub fn track(&mut self, id: usize, buf: &Vec<u8>) {
        //FIXME
        //let e = format!("taint_file=output/tmp/cur_input_2 solver_select=1 tid={}",id);
        let e = format!("taint_file={} tid={} shmid={} pipeid={} inputid={}", &self.cmd.out_file, &id, &self.shmid, &self.cmd.id, &id);
        info!("Track {}, e is {}", &id, e);

        // let mut outlog = std::fs::OpenOptions::new().append(true).open("/home/jie/coco-loop/log.log").expect("cannot open file");
        // write!(outlog, "[new input] = {}\n", id);
        self.envs.insert(
            defs::TAINT_OPTIONS.to_string(),
            e,
        );


        self.write_test(buf);

        compiler_fence(Ordering::SeqCst);
        let ret_status = self.run_target(
            &self.cmd.track,
            config::MEM_LIMIT_TRACK,
            //self.cmd.time_limit *
            config::TIME_LIMIT_TRACK,
        );
        compiler_fence(Ordering::SeqCst);

        if ret_status != StatusType::Normal {
            error!(
                "Crash or hang while tracking! -- {:?},  id: {}",
                ret_status, id
            );
            return;
        }
    }


    fn do_if_has_new(&mut self, buf: &Vec<u8>, status: StatusType) -> (bool, usize) {
        // new edge: one byte in bitmap
        let has_new_path = self.branches.has_new(status);
        let mut new_id = 0;
       // let (has_new_path, rareness) = self.branches.has_new_unique_path(status, &mut self.unique_path_hash);
        
        //if has_new_path > 0 { // fix naming! 
        if has_new_path { // fix naming! 
            //println!("{} queue, rareness: {}", has_new_path, rareness);
            self.has_new_path = true;
        //    new_id = self.depot.save(status, &buf, rareness, has_new_path);
            new_id = self.depot.save(status, &buf);
        }
        (has_new_path, new_id)
       // else {
        //    (false, new_id)
       // }
    }

    pub fn run(&mut self, buf: &Vec<u8>) -> StatusType {
        self.run_init();
        let status = self.run_inner(buf);
        self.do_if_has_new(buf, status);
        self.check_timeout(status)
    }

    pub fn run_sync(&mut self, buf: &Vec<u8>) -> (bool, usize)  {
        self.run_init();
        let status = self.run_inner(buf);
        let ret = self.do_if_has_new(buf, status); // generate?
	    self.check_timeout(status);
	    ret
    }

    pub fn run_norun(&mut self, buf: &Vec<u8>)  {
        let status = StatusType::Normal;
        //self.depot.save(status, &buf, std::f32::MAX, 2);
        self.depot.save(status, &buf);
    }

    
    fn run_init(&mut self) {
        self.has_new_path = false;
    }

    fn check_timeout(&mut self, status: StatusType) -> StatusType {
        let mut ret_status = status;
        if ret_status == StatusType::Error {
            self.rebind_forksrv();
            ret_status = StatusType::Timeout;
        }

        if ret_status == StatusType::Timeout {
            self.tmout_cnt = self.tmout_cnt + 1;
            if self.tmout_cnt >= config::TMOUT_SKIP {
                ret_status = StatusType::Skip;
                self.tmout_cnt = 0;
            }
        } else {
            self.tmout_cnt = 0;
        };

        ret_status
    }

    fn run_inner(&mut self, buf: &Vec<u8>) -> StatusType {
        self.write_test(buf);

        self.branches.clear_trace();

        compiler_fence(Ordering::SeqCst);
        let ret_status = if let Some(ref mut fs) = self.forksrv {
            fs.run()
        } else {
            warn!("run does not go through forksrv");
            self.run_target(&self.cmd.main, self.cmd.mem_limit, self.cmd.time_limit)
        };
        compiler_fence(Ordering::SeqCst);

        ret_status
    }

    
    pub fn random_input_buf(&self) -> Vec<u8> {
        let id = self.depot.next_random();
        self.depot.get_input_buf(id)
    }

    fn write_test(&mut self, buf: &Vec<u8>) {
        self.fd.write_buf(buf);
        if self.cmd.is_stdin {
            self.fd.rewind();
        }
    }

    fn run_target(
        &self,
        target: &(String, Vec<String>),
        mem_limit: u64,
        time_limit: u64,
    ) -> StatusType {
        info!("[new epi]: {}, {:?}, {:?}", &target.0, &target.1, &self.envs);
        let mut cmd = Command::new(&target.0);
        let mut child = cmd
            .args(&target.1)
          //  .stdin(Stdio::null())
            .env_clear()
            .envs(&self.envs)
            // .stdout(Stdio::null())
            // .stderr(Stdio::null())
          //  .mem_limit(mem_limit.clone())
            .setsid()
            .pipe_stdin(self.fd.as_raw_fd(), self.cmd.is_stdin)
            .spawn()
            .expect("Could not run target");


        let timeout = time::Duration::from_secs(time_limit);
        let ret = match child.wait_timeout(timeout).unwrap() {
            Some(status) => {
                if let Some(status_code) = status.code() {
                    if self.cmd.uses_asan && status_code == defs::MSAN_ERROR_CODE
                    {
                        StatusType::Crash
                    } else {
                        StatusType::Normal
                    }
                } else {
                    StatusType::Crash
                }
            }
            None => {
                // Timeout
                // child hasn't exited yet
                child.kill().expect("Could not send kill signal to child.");
                child.wait().expect("Error during waiting for child.");
                StatusType::Timeout
            }
        };
        ret
    }

}
