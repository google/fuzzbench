PPROF_PATH=/usr/local/bin/pprof HEAPCHECK=normal LD_PRELOAD="/usr/local/lib/libtcmalloc.so" cargo test test_scan -- --nocapture &>1 
