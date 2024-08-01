#[link(name = "gd")]
#[link(name = "stdc++")]
#[link(name = "z3")]
extern {
  pub fn init_core(save_whole: bool, initial_count: u32);
  pub fn get_next_input(input: *mut u8, addr: *mut u64, ctx: *mut u64, order: *mut u32, fid: *mut u32) -> u32;
  pub fn run_solver(shmid: i32, pipeid: usize, brc_flip: u32, lastone: u32) -> u32;
  pub fn post_gra();
  pub fn post_fzr();
  pub fn wait_ce();
}

