#[inline(always)]
pub fn xxhash(h1: u32, h2: u32, h3: u32) -> u32 {
  //const PRIME32_1: u32 = 2654435761;
  const PRIME32_2: u32 = 2246822519u32;
  const PRIME32_3: u32 = 3266489917u32;
  const PRIME32_4: u32 =  668265263u32;
  const PRIME32_5: u32 =  374761393u32;

  let mut h32: u32 = PRIME32_5;
  h32 = h32.overflowing_add(h1.overflowing_mul(PRIME32_3).0).0;
  h32 = (h32 << 17 | h32 >> 15).overflowing_mul(PRIME32_4).0;
  h32 = h32.overflowing_add(h2.overflowing_mul(PRIME32_3).0).0;
  h32  = (h32 << 17 | h32 >> 15).overflowing_mul(PRIME32_4).0;
  h32 = h32.overflowing_add(h3.overflowing_mul(PRIME32_3).0).0;
  h32  = (h32 << 17 | h32 >> 15).overflowing_mul(PRIME32_4).0;

  h32 ^= h32 >> 15;
  h32 = h32.overflowing_mul(PRIME32_2).0;
  h32 ^= h32 >> 13;
  h32 = h32.overflowing_mul(PRIME32_3).0;
  h32 ^= h32 >> 16;

  h32
}
