use libc;

pub struct SHM<T: Sized> {
  id: i32,
  size: usize,
  ptr: *mut T,
}


impl<T> SHM<T> {
  pub fn new() -> Self {
    let size = std::
  }
}
