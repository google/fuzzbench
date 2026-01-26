#!/bin/bash

echo "start"

while [[ $# -gt 0 ]]; do
    case "$1" in
        -i)
            input="$2"
            shift 2
            ;;
        -o)
            output="$2"
            shift 2
            ;;
        *)
            remaining_command+=("$1")
            shift
            ;;
    esac
done

# Remaining arguments are the program to run and its options
# program_to_run="$1"
# shift
# program_args="$@"

# Run the command
# echo "./afl-fuzz -c $cmp_program -m $memory_limit -- $program_to_run $program_args"
# $cmp_program -m $memory_limit -- $program_to_run $program_args
# echo ./afl-fuzz -i $input -o $output ${remaining_command[*]}


# separate the initial seeds into multiple independent seed sets
# Check if the provided path is a valid directory
if [ ! -d "$input" ]; then
  echo "Error: $input is not a valid directory."
  exit 1
fi

# Create individual folders for each seed file
counter=1
for seed_file in "$input"/*; do
  # Check if it's a file
  if [ -f "$seed_file" ]; then
    # Create a new directory named by the counter
    new_dir="$input/$counter"
    mkdir -p "$new_dir"

    # Move the seed file into the newly created directory
    mv "$seed_file" "$new_dir"

    # Increment the counter
    ((counter++))
  fi
done

# run the sub-fuzzing for a target time limit
# -V to control the fuzzing time (second)
dir_count=$(find "$input" -mindepth 1 -maxdepth 1 -type d | wc -l)
echo $dir_count
if [ "$dir_count" -lt 1 ]; then
  dir_count=1
fi

totalTime=79200
# fuzz_time=60

if [ "$fuzz_time" -lt 60 ]; then
  fuzz_time=60
fi

echo $fuzz_time

find "$input" -mindepth 1 -maxdepth 1 -type d | while read -r subdir; do

  # run the sub-fuzzing
  # echo ./afl-fuzz -i $subdir -o tmp -V $fuzz_time -c $cmp_program -m $memory_limit -- $program_to_run $program_args
  # ./afl-fuzz -i $subdir -o tmp -V $fuzz_time -c $cmp_program -m $memory_limit -- $program_to_run $program_args

  start=$(date +%s)
  fuzz_time=$(($totalTime / $dir_count))
  echo ./afl-fuzz -i $subdir -o tmp -V $fuzz_time ${remaining_command[*]}
  ./afl-fuzz -i $subdir -o tmp -V $fuzz_time ${remaining_command[*]}
  end=$(date +%s)
  runtime=$((end - start))

  echo "runtime:" $runtime

  totalTime=$((totalTime - runtime))
  dir_count=$((dir_count - 1))

  echo "updated totalTime:" $totalTime
  echo "updated dir_count:" $dir_count

  # merge the current outputs into the global output
  if [ -d "$output/default" ]; then
    
    # Iterate over each file in the source directory
    for file in tmp/default/queue/*; do
      # Get the base name of the file (without path)
      file_name=$(basename "$file")

      target_dir=$output/default/queue

      # If a file with the same name exists in the target directory
      if [ -e "$target_dir/$file_name" ]; then
        # Append a timestamp or incrementing number to avoid name clash
        timestamp=$(date +%s)
        new_file_name="${file_name%.*}_$timestamp.${file_name##*.}"

        echo "Name clash: Renaming '$file_name' to '$new_file_name'"
        cp "$file" "$target_dir/$new_file_name"
      else
        # No name clash, simply copy the file
        cp "$file" "$target_dir/$file_name"
      fi
    done

  else
    if [ ! -d "$output" ]; then
      mkdir $output
    fi
    cp -r tmp/default $output
  fi

  rm -r -f tmp

done

sleep 86400

# collect the finial results periodically