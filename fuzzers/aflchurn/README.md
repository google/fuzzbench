Workable benchmarks and their commits (2021-03-17):

- aspell_aspell_fuzzer (`b503ec3e3e134dbc28bf129c012e5d6245a39472`)
- file_magic_fuzzer (`8305d1cc5ec466b2d50d1b6000e7b3c8c4b08853`)
- grok_grk_decompress_fuzzer (`c007abeb226caef9c23bd786a36614b94703ff87`)
- harfbuzz_hb-shape-fuzzer (`818f109bdec9659c05f9fd9a1de1db85ece65cbe`)
- libxml2_libxml2_xml_reader_for_file_fuzzer (`99a864a1f7a9cb59865f803770d7d62fb47cad69`)
- libgit2_objects_fuzzer (`20cb30b6b8e269d2ce3474523562b2739a8efea2`)
- libhtp_fuzz_htp (`75cbbbd405695e97567931655fd5a441f86e5836`)
- neomutt_address-fuzz (`ebd3048fff6f1a60a1859fac2dedd0c962f6551b`)
- ndpi_fuzz_process_packet (`a845e997209b987ef85a2562697d4d0522cb0c66`)
- openvswitch_odp_target (`dfa2e3d04948ce6ff78057008314efe79eea4764`)
- openssl_x509 (`fb1ecf85c9f732e5827771ff243d7a70e06ce112`)
- picotls_fuzz-asn1 (`254a1801ede6ed8f4b0c86303c0a9cb8dab9b40f`)
- readstat_fuzz_format_spss_commands (`54874a7ac5bbf13fdabcd023ddabdabf5f8092f4`)
- systemd_fuzz-varlink (`cb367b17853d215ebcf2816118c1f53d003e5088`)
- unicorn_fuzz_emu_arm_armbe (`4ca2c7f0b09be190f95e0caa90371d3ed6362402`)
- usrsctp_fuzzer_connect (`e08eacffd438cb0760c926fbe60ccda011f6ce70`)
- unbound_fuzz_1_fuzzer (`1e0c957dcd7b0b1e03ff2d8bf58fdbb147ce4978`)
- yara_dotnet_fuzzer (`95ed87ce759481758d0ff2f09aab7c4f1d4f0fbc`)
- zstd_stream_decompress (`9ad7ea44ec9644c618c2e82be5960d868e48745d`)

Old commits of target programs may fail sometimes, but the newest commits should be workable.
When adding a new benchmark for AFLChurn, remove `--depth 1` to enable the analysis of commit history.
