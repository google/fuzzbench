use std::{
    fs::{File, OpenOptions},
    io::{prelude::*, SeekFrom},
    os::unix::io::{AsRawFd, RawFd},
};

pub struct PipeFd {
    file: File,
}

impl PipeFd {
    pub fn new(file_name: &str) -> Self {
        let f = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .open(file_name)
            .expect("Fail to open default input file!");

        Self { file: f }
    }

    pub fn as_raw_fd(&self) -> RawFd {
        self.file.as_raw_fd()
    }

    pub fn write_buf(&mut self, buf: &Vec<u8>) {
        self.file.seek(SeekFrom::Start(0)).unwrap();
        self.file.write(buf).unwrap();
        self.file.set_len(buf.len() as u64).unwrap();
        self.file.flush().unwrap();
        // f.sync_all().unwrap();
    }

    pub fn rewind(&mut self) {
        self.file.seek(SeekFrom::Start(0)).unwrap();
    }
}
