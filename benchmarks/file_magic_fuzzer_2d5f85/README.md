# file v5.35

Modified the source `magic_fuzzer.cc` to exercise the functionality that exposes
these four CVEs (use `magic_file` versus `magic_buffer`).  These bugs are related, 
but not easily found within 24hr fuzzing. 

- bug benchmark
- 4 known bugs with POCs

## CVE-2019-8904
- [bug report](https://bugs.astron.com/view.php?id=62)
- [POC input](https://bugs.astron.com/file_download.php?file_id=40&type=bug)
- [patch](https://github.com/file/file/commit/94b7501f48e134e77716e7ebefc73d6bbe72ba55)
  Avoid non-nul-terminated string read.

## CVE-2019-8905
- [bug report](https://bugs.astron.com/view.php?id=63)
- [POC input](https://bugs.astron.com/file_download.php?file_id=41&type=bug)
- [patch](https://github.com/file/file/commit/d65781527c8134a1202b2649695d48d5701ac60b)
  limit size of file_printable.

## CVE-2019-8906
- [bug report](https://bugs.astron.com/view.php?id=64)
- [POC input](https://bugs.astron.com/file_download.php?file_id=42&type=bug)

## CVE-2019-8907
- [bug report](https://bugs.astron.com/view.php?id=65)
- [POC input](https://bugs.astron.com/file_download.php?file_id=43&type=bug)

