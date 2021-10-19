#!/bin/bash -ex
# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.



setup_zafl() {
	service postgresql start
	pushd /zipr
	source set_env_vars
	popd
	pushd /zafl
	source set_env_vars
	popd
	while ! pg_isready; do sleep 1; done
}

zafl_bins() {
	cd /out
	for i in *.so; do
		if [[ $i == "libzafl.so"                      ]] || 
		   [[ $i == "libhdf5.so"                      ]] || 
		   [[ $i == "libsz.so"                        ]] || 
		   [[ $i == "libaec.so"                       ]] || 
		   [[ $i == "libfuzzshark_ip_proto-ospf.so"   ]] || 
		   [[ $i == "libfuzzshark_ip_proto-udp.so"    ]] || 
		   [[ $i == "libfuzzshark_media_type-json.so" ]] || 
		   [[ $i == "libfuzzshark_tcp_port-bgp.so"    ]] || 
		   [[ $i == "libfuzzshark_udp_port-dhcp.so"   ]] || 
		   [[ $i == "libfuzzshark_udp_port-dns.so"    ]] || 
		   [[ $i == "libautozafl.so"                  ]] ; then
			continue
		fi
		local filesize=$(wc -c $i | cut -d' ' -f1 )
		mv $i $i.orig

		# wireshark exceeds memory with full analysis, so
		# skip full opts on programs that are too big, e.g. 10mb.
		if (( $filesize < 104857600 )) ; then 
			zafl.sh $i.orig $i -s -d -g -m 0x1000000 || true
		else
			zafl.sh $i.orig $i --no-stars -m 0x1000000 || true
		fi
		if [[ ! -x $i ]]; then
			echo "Unable to zafl $i"
			exit 1
		fi

		# rebuild the driver if it exists.
		local driverNameWithoutLib="${i#lib}"
		local driverName=$(basename ${driverNameWithoutLib} .so)
		if [[ -x $driverName ]]; then
			AFL_LLVM_LTO_DONTWRITEID=1 AFL_MAP_SIZE=65536 AFL_LLVM_MAP_ADDR=0x1000000 /afl/afl-clang-lto -DFUZZER_LIB_NAME='"'"/out/${i}"'"' -I/src/aflplusplus/include -O3 -funroll-loops -fPIC  /tmp/aflpp_driver.c -c -o /tmp/aflpp_driver.o
			AFL_LLVM_LTO_DONTWRITEID=1 AFL_MAP_SIZE=65536 AFL_LLVM_MAP_ADDR=0x1000000 /afl/afl-clang-lto++ -I/src/aflplusplus/include -O3 -funroll-loops -fPIC  /tmp/aflpp_driver.o -o $driverName -ldl
		fi

	done
}

main() {
	setup_zafl
	zafl_bins
	exit 0
}

main "$@"
