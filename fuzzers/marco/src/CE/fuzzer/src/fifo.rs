use nix::unistd;
use nix::sys::stat;
//use std::io;
use std::io::prelude::*;
use std::io::BufReader;
use std::fs::File;
use std::collections::VecDeque;

pub fn make_pipe() {
  match unistd::mkfifo("/tmp/wp", stat::Mode::S_IRWXU) {
    Ok(_) => println!("created"),
    Err(err) => println!("Error creating fifo: {}", err),
  }
}

pub fn read_pipe(pipeid: usize) -> (Vec<(u32,u32,u64,u64,u64,u32,u32,u32)>, VecDeque<[u8;1024]>) {
  let f = match pipeid {
    2 => File::open("/tmp/wp2").expect("open pipe failed"),
    3 => File::open("/tmp/wp3").expect("open pipe failed"),
    _ => File::open("/tmp/wp2").expect("open pipe failed"),
  };
  let mut reader = BufReader::new(f);
  let mut ret = Vec::new();
  let mut retdata = VecDeque::new();
  loop {
    let mut buffer = String::new();
    let num_bytes = reader.read_line(&mut buffer).expect("read pipe failed");
    //if not EOF
    if num_bytes !=0  {
      let tokens: Vec<&str> = buffer.trim().split(',').collect();
      let tid = tokens[0].trim().parse::<u32>().expect("we expect u32 number in each line");
      let label = tokens[1].trim().parse::<u32>().expect("we expect u32 number in each line");
      let direction = tokens[2].trim().parse::<u64>().expect("we expect u32 number in each line");
      let addr = tokens[3].trim().parse::<u64>().expect("we expect u64 number in each line");
      let ctx = tokens[4].trim().parse::<u64>().expect("we expect u64 number in each line");
      let order = tokens[5].trim().parse::<u32>().expect("we expect u32 number in each line");
      let isgep = tokens[6].trim().parse::<u32>().expect("we expect u32 number in each line");
      let inputid = tokens[7].trim().parse::<u32>().expect("we expect u32 number in each line");
      ret.push((tid,label,direction,addr,ctx,order,isgep,inputid));
      if isgep == 2 {
        let mut buffer = String::new();
        let num_bytes = reader.read_line(&mut buffer).expect("read pipe failed");
        let size = label;
        let mut data = [0;1024];
        if num_bytes !=0 {
          let tokens: Vec<&str> = buffer.trim().split(',').collect();
          for i in 0..size as usize {
            data[i] = tokens[i].trim().parse::<u8>().expect("we expect u8");
          }
          retdata.push_back(data);
        } else {
          break;
        }
      }
    } else  {
      break;
    }
  }
  (ret,retdata)
}

#[cfg(test)]
mod tests {
  use super::*;
  
  #[test]
  fn test_make_pipe() {
    make_pipe()
  }

  #[test]
  fn test_read_pipe() {
    let v = read_pipe(2);
  }

}
