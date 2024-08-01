extern "C" {
    #[cfg(not(any(feature = "unstable", test)))]
    #[link(name = "context", kind = "static")]
    pub fn __angora_reset_context();
}

#[cfg(feature = "unstable")]
#[thread_local]
#[no_mangle]
static mut __angora_prev_loc: u32 = 0;
#[cfg(feature = "unstable")]
#[thread_local]
#[no_mangle]
static mut __angora_context: u32 = 0;

#[inline(always)]
pub unsafe fn reset_context() {
    #[cfg(not(any(feature = "unstable", test)))]
    {
        __angora_reset_context();
    }
    #[cfg(feature = "unstable")]
    {
        unsafe {
            __angora_prev_loc = 0;
            __angora_context = 0;
        }
    }
}
