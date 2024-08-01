### Fastgen

Build

```
./build/build.sh
```


### Dependencies

* Have to point /usr/include/llvm to llvm-6.0
* Have to point /usr/include/llvm-c to llvm-6.0


### Tests result 

(cocofuzz - full negation)

```
switch2: yes
switch: yes
gep: TODO  
gep2: TODO
alloca: no constraints
bitflip: yes
asan: no constraints
bool: not solvable
call_fn: yes
call_fn2:  yes
call_fn3:  yes
cf1:  yes
cf2:  yes
cf3:  yes
context: yes
recursion: no 
pointer: yes
sign: yes
mini: yes
mini2: yes
shift_and: yes
fstream:  yes
cpp_string: yes
strcmp: yes
strcmp2: yes
memcmp: yes
loop: yes
infer_type: yes
if_eq: yes
stat: stat call not supported
stdin: getchar not supported
```

### TODOs

* add AstNode caching
* Test search from current input
* Options switch between continuous/non-continuous solving
