rm -rf fuzzer/output
RUST_MIN_STACK=8388608 RUST_LOG=info cargo test --release test_grading -- --nocapture
