use fastgen_common::{config, defs};
use std::env;

use byteorder::{LittleEndian, WriteBytesExt};
use libc;
use std::{io::prelude::*, os::unix::net::UnixStream, process, time::Duration};

pub fn start_forkcli() {
    match env::var(defs::FORKSRV_SOCKET_PATH_VAR) {
        Ok(socket_path) => {
            let mut socket = match UnixStream::connect(socket_path) {
                Ok(sock) => sock,
                Err(e) => {
                    eprintln!("Couldn't connect: {:?}", e);
                    return;
                },
            };

            socket
                .set_read_timeout(Some(Duration::from_secs(config::TIME_LIMIT_TRACK * 2)))
                .expect("Couldn't set read timeout");
            socket
                .set_write_timeout(Some(Duration::from_secs(config::TIME_LIMIT_TRACK * 2)))
                .expect("Couldn't set write timeout");

            let mut sig_buf = [0; 4];
            unsafe { super::context::reset_context(); }
            loop {
                if socket.read(&mut sig_buf).is_err() {
                    process::exit(0);
                }

                let child_pid = unsafe { libc::fork() };

                if child_pid == 0 {
                    unsafe { super::context::reset_context(); }
                    return;
                }

                let mut pid_buf = vec![];
                pid_buf
                    .write_i32::<LittleEndian>(child_pid)
                    .expect("Could not write to child.");
                if socket.write(&pid_buf).is_err() {
                    process::exit(1);
                }

                let mut status: libc::c_int = 0;
                if unsafe { libc::waitpid(child_pid, &mut status as *mut libc::c_int, 0) } < 0 {
                    process::exit(1);
                }

                let mut status_buf = vec![];
                status_buf
                    .write_i32::<LittleEndian>(status)
                    .expect("Could not write to child.");
                if socket.write(&status_buf).is_err() {
                    process::exit(1);
                }
            }
        },
        Err(_) => {
             //eprintln!("Could not find socket path");
        },
    }
}

