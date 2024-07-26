//use protoc_rust::Customize;
fn main() {  
  println!(r"cargo:rustc-link-search=fuzzer/cpp_core/build");  
  println!(r"cargo:rustc-link-search=/usr/local/lib");
  println!(r"cargo:rustc-link-search=fuzzer/cpp_core/build/proto");
  println!(r"cargo:rustc-link-lib=proto");
  println!(r"cargo:rustc-link-search=/usr/lib/x86_64-linux-gnu/");  
  println!(r"cargo:rustc-link-lib=protobuf");
}
