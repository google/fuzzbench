#!/bin/bash -e
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


main() {
	local args=("$@")
	local argsWithoutSanitize=("${args[@]}")
	local fakePattern1="/out/fakeLibrary.a"
	local fakePattern2="-lFuzzingEngine"
	local fakePattern3="/usr/lib/libFuzzingEngine.a"
	declare -a dashLs=()
	for index in "${!argsWithoutSanitize[@]}"; do 
		if [[ ${argsWithoutSanitize[$index]} == *"-fsanitize"* ]] || 
		   [[ ${argsWithoutSanitize[$index]} == *"-Wl,-Bstatic"* ]] || 
		   [[ ${argsWithoutSanitize[$index]} == *"-Werror"* ]] || 
		   [[ ${argsWithoutSanitize[$index]} == *"-fvisibility=hidden"* ]]; then
		   unset -v 'argsWithoutSanitize[$index]'
		elif [[ ${argsWithoutSanitize[$index]} == *"/usr/lib/x86_64-linux-gnu/libsqlite3.a"* ]]; then
		   argsWithoutSanitize[$index]="/usr/lib/x86_64-linux-gnu/libsqlite3.so"
		elif [[ ${argsWithoutSanitize[$index]} == *"/usr/lib/x86_64-linux-gnu/libssl.a"* ]]; then
		   argsWithoutSanitize[$index]="/usr/lib/x86_64-linux-gnu/libssl.so"
		elif [[ ${argsWithoutSanitize[$index]} == *"/usr/lib/x86_64-linux-gnu/libcrypto.a"* ]]; then
		   argsWithoutSanitize[$index]="/usr/lib/x86_64-linux-gnu/libcrypto.so"
		elif [[ ${argsWithoutSanitize[$index]} == *"/usr/lib/x86_64-linux-gnu/hdf5/serial/libhdf5.a"* ]]; then
		   argsWithoutSanitize[$index]="/out/libhdf5.so"
		fi


		# memorize -L and -l options.
		if [[ ${argsWithoutSanitize[$index]} == "-l"* || ${argsWithoutSanitize[$index]} == "-L"* ]]; then
		   	dashLs=("${dashLs[@]}" "${argsWithoutSanitize[$index]}")
		fi
	done
	argsWithoutSanitize=("${argsWithoutSanitize[@]}")
	# if it has the fake library listed, and isn't complaining, detecting dependencies, preprocessing, 
	# creating assembly, or linking a shared library, then 
	# it must be linking a main executable, and we want to control the link
	# by building a shared library, and building a stand-along persistent mode driver
	# that invokes the library.
	if [[ ${args[@]} == *"$fakePattern1"* || ${args[@]} == *"$fakePattern2"* || ${args[@]} == *"$fakePattern3"* ]] &&
	   [[ ${args[@]} != *" -c "* ]] && 
	   [[ ${args[@]} != *" -M "* ]] && 
	   [[ ${args[@]} != *" -E "* ]] && 
	   [[ ${args[@]} != *" -S "* ]] &&
	   [[ ${args[@]} != *" -shared "* ]] ; then
		echo "in cxx.sh with args=${args[@]}"
		set -x
		local argsWithoutFakeLib=("${argsWithoutSanitize[@]}")
		# remove fakePatterns 
		for index in "${!argsWithoutFakeLib[@]}"; do 
			if [[ ${argsWithoutFakeLib[$index]} == *"$fakePattern1"* ||
			      ${argsWithoutFakeLib[$index]} == *"$fakePattern2"* ||
			      ${argsWithoutFakeLib[$index]} == *"$fakePattern3"* 
			   ]]; then
			   unset -v 'argsWithoutFakeLib[$index]'
			fi

		done
		argsWithoutFakeLib=("${argsWithoutFakeLib[@]}")

		local outfile=$(echo "bob ${args[@]}" | sed -e 's|.* -o *||' -e "s/ .*//" )
		local outfileBn=$(basename $outfile)
		local libname=/out/lib${outfileBn}.so
		local krb_str=""
		if [[ $BENCHMARK == *"wireshark"*  ]]; then
			krb_str="/usr/lib/x86_64-linux-gnu/libkrb5.so.3"
		fi
		clang++ -fPIC -shared "${argsWithoutFakeLib[@]}" -lcares $krb_str
		mv $outfile $libname
		AFL_LLVM_LTO_DONTWRITEID=1 AFL_MAP_SIZE=65536 AFL_LLVM_MAP_ADDR=0x1000000 /afl/afl-clang-fast -DFUZZER_LIB_NAME='"'"/out/lib${outfileBn}.so"'"' -I/src/aflplusplus/include -O3 -funroll-loops -fPIC  /tmp/aflpp_driver.c -c -o /tmp/aflpp_driver.o
		AFL_LLVM_LTO_DONTWRITEID=1 AFL_MAP_SIZE=65536 AFL_LLVM_MAP_ADDR=0x1000000 /afl/afl-clang-fast++ -I/src/aflplusplus/include -O3 -funroll-loops -fPIC  /tmp/aflpp_driver.o -o $outfile -lpthread -lm -lz -ldl

	else

		clang++ -fPIC "${argsWithoutSanitize[@]}"

	fi
}
main "$@" 
