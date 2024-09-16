extern crate cc;

fn main() {
cc::Build::new()
        .file("src/context.c")
        .compile("libcontext.a");
}
