use libc;
use std::{
    os::unix::{io::RawFd, process::CommandExt},
    process::Command,
};

pub trait SetLimit {
    fn mem_limit(&mut self, size: u64) -> &mut Self;
    fn setsid(&mut self) -> &mut Self;
    fn pipe_stdin(&mut self, fd: RawFd, is_stdin: bool) -> &mut Self;
    //fn dup2(&mut self, src: libc::c_int, dst: libc::c_int) -> &mut Self;
    //fn close_fd(&mut self, fd: libc::c_int) -> &mut Self;
}

impl SetLimit for Command {
    fn mem_limit(&mut self, size: u64) -> &mut Self {
        if size == 0 {
            return self;
        }

        let func = move || {
            let size = size << 20;
            let mem_limit: libc::rlim_t = size;
            let r = libc::rlimit {
                rlim_cur: mem_limit,
                rlim_max: mem_limit,
            };

            let r0 = libc::rlimit {
                rlim_cur: 0,
                rlim_max: 0,
            };

            unsafe {
                libc::setrlimit(libc::RLIMIT_AS, &r);
                // libc::setrlimit(libc::RLIMIT_DATA, &r);
                libc::setrlimit(libc::RLIMIT_CORE, &r0);
            };

            Ok(())
        };

        unsafe { self.pre_exec(func) }
    }

    fn setsid(&mut self) -> &mut Self {
        let func = move || {
            unsafe {
                libc::setsid();
            };
            Ok(())
        };
        unsafe { self.pre_exec(func) }
    }

    fn pipe_stdin(&mut self, fd: RawFd, is_stdin: bool) -> &mut Self {
        if is_stdin {
            let func = move || {
                let ret = unsafe { libc::dup2(fd, libc::STDIN_FILENO) };
                if ret < 0 {
                    panic!("dup2() failded");
                }
                unsafe {
                    libc::close(fd);
                }
                Ok(())
            };
            unsafe { self.pre_exec(func) }
        } else {
            self
        }
    }
}
