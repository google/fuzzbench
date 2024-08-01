#!/bin/bash
CPU_COUNT=${2}
PROGSET=${3}

start=0
end=10

# real-world set
if [ "$PROGSET" == "0" ]; then
    OROOT="/hyper/jie/icse_cov/outroot${1}"
    TOUT="24h"
    RUNSCRIPT="run_icse.sh"
    declare -a TARG=(
        "size" \
        "nm-new" \
        "readelf"  \
        "objdump" \
        "xml" \
        "cms_transform_fuzzer" \
        "magic_fuzzer" \
        "decode_fuzzer" \
        "curl_fuzzer_http" \
        "convert_woff2ttf_fuzzer" \
        "libjpeg_turbo_fuzzer" \
        "ossfuzz" \
        "tcpdump" \
        "ftfuzzer" \
        "tiff_read_rgba_fuzzer" \
        "libpng_read_fuzzer" \
    )

# unibench set
elif [ "$PROGSET" == "1" ]; then
    OROOT="/hyper/jie/icse_bug/outroot${1}"
    TOUT="24h"
    RUNSCRIPT="run_icse_bug.sh"                        # TODO:
    declare -a TARG=(
        "cflow" \
        "tiffsplit" \
        "flvmeta" \
        "mujs" \
        "wav2swf" \
        "jhead" \
        "lame" \
        "tcpdump" \
        "infotocap" \
        "mp42aac" \
        "imginfo" \
        "jq" \
        "mp3gain" \
        "sqlite3" \
    )
else
    OROOT="/hyper/jie/icse_cgc/outroot${1}"
    TOUT="1h"
    RUNSCRIPT="run_icse_cgc.sh"
    declare -a TARG=(    # the cgc binaries
        # "Accel" \
        # "Barcoder" \
        # "basic_emulator"\
        # "BitBlaster"\
        # "Bloomy_Sunday"\
        # "Board_Game"\
        # "BudgIT"\
        # "CableGrind"\
        # "CableGrindLlama"\
        # "Casino_Games"\
        # "CGC_Symbol_Viewer_CSV"\
        # "Checkmate"\
        # "chess_mimic"\
        # "CNMP"\
        # "COLLIDEOSCOPE"\
        # "cotton_swab_arithmetic"\
        # "CTTP"\
        # "cyber_blogger"\
        # "Differ"\
        # "Dive_Logger"\
        # "Divelogger2"\
        # "Dungeon_Master"\
        # "ECM_TCM_Simulator"\
        # "Eddy"\
        # "Email_System_2"\
        # "Enslavednode_chat"\
        # "expression_database"\
        # "Flash_File_System"\

        # "Flight_Routes"\
        # "FSK_BBS"\
        # "Game_Night"\
        # "Glue"\
        # "GreatView"\

        # "GREYMATTER"\
        # "Griswold"\
        # "HackMan"\
        # "Headscratch"\
        # "HIGHCOO"\

        # "Hug_Game"\
        # "KKVS"\
        # "LMS"\
        # "Loud_Square_Instant_Messaging_Protocol_LSIMP"\
        # "Matchmaker"\

        # "Mathematical_Solver"\
        # "Movie_Rental_Service_Redux"\
        # "Multi_Arena_Pursuit_Simulator"\
        # "Multicast_Chat_Server"\
        # "Multipass"\

        # "Music_Store_Client"\
        # "No_Paper._Not_Ever._NOPE"\
        # "On_Sale"\
        # "One_Vote"\
        # "online_job_application"\

        # "online_job_application2"\
        # "OTPSim"\
        # "Overflow_Parking"\
        # "Pac_for_Edges"\
        # "Packet_Analyzer"\

        # "Packet_Receiver"\
        # "Palindrome2"\
        # "Pattern_Finder"\
        # "PCM_Message_decoder"\
        # "Personal_Fitness_Manager"\

        # "PKK_Steganography"\
        # "Printer"\
        # "PRU"\
        # "QuadtreeConways"\
        # "RAM_based_filesystem"\

        # "Recipe_Database"\
        # "Rejistar"\
        # "Resort_Modeller"\
        # "root64_and_parcour"\
        # "router_simulator"\

        # "Sad_Face_Template_Engine_SFTE"\
        # "Sample_Shipgame"\
        # "SAuth"\
        # "Scrum_Database"\
        # "SCUBA_Dive_Logging"\

        # "Secure_Compression"\
        # "SFTSCBSISS"\
        # "Shortest_Path_Tree_Calculator"\
        # "ShoutCTF"\
        # "SIGSEGV"\

        # "Simple_Stack_Machine"\
        # "simplenote"\
        # "simpleOCR"\
        # "SLUR_reference_implementation"\
        # "Snail_Mail"\

        # "SOLFEDGE"\
        # "Space_Attackers"\
        # "Square_Rabbit"\
        # "stack_vm"\
        # "Stock_Exchange_Simulator"\

        # "stream_vm"\
        # "stream_vm2"\
        # "Street_map_service"\
        # "String_Info_Calculator"\
        # "TAINTEDLOVE"\

        # "Tennis_Ball_Motion_Calculator" \
        # "TFTTP"\
        # "The_Longest_Road"\
        # "Thermal_Controller_v3"\
        # "Tick-A-Tack"\

        # "User_Manager"\
        # "vFilter"\
        # "Virtual_Machine"\
        # "virtual_pet"\
        # "WhackJack"\

        # "WordCompletion"\
        # "XStore"\
        # "yolodex"\
    )

fi

mkdir -p "$OROOT"
DKIMG="coco_design2"

# Declare the associative array
declare -A CONF

# Initialize the associative array
CONF=(
    ["0"]="symsan"
    ["5"]="marco"
    ["1"]="symsan-pp"
    ["2"]="symsan-unvisited"
    ["3"]="marco-unvisited"
    ["4"]="marco-mc"
    ["20"]="marco-rdm"
    ["21"]="marco-cfg"
)


CONFN="5"
for PROGRAM in "${TARG[@]}"; do
    CONFIG="${CONF[${CONFN}]}"
    TRIAL=$start
    while [ $TRIAL -ne $end ]; do
        DOCKERNAME="${DKIMG}_${PROGRAM}_conf${CONFN}_${TRIAL}_${1}"
        DATADIR="$OROOT/conf${CONFN}_${PROGRAM}_${TRIAL}"

        echo ${CPU_COUNT} $TOUT $CONFIG $TRIAL $PROGRAM $DOCKERNAME $DATADIR
        docker stop $DOCKERNAME
        docker rm $DOCKERNAME

        sudo rm -rf $DATADIR
        mkdir -p $DATADIR

        if [ "$CONFN" == "0" ]; then
            MPDIR=`pwd`/src/benchmarks/cgc-bin/cb-multios-ori/build
        else
            MPDIR=`pwd`/src/benchmarks/cgc-bin/cb-multios-reach/build
        fi

        docker run --ulimit core=0 -d --name $DOCKERNAME \
                --cpuset-cpus "${CPU_COUNT}" \
                -v $DATADIR:/outroot \
                -v $MPDIR:/workdir/track3 \
                -v `pwd`/src/benchmarks/cgc-bin:/workdir/cgc-dir \
                -v `pwd`/src/benchmarks/targets:/workdir/targets \
                -v `pwd`/src/CE:/data/src/CE \
                -v `pwd`/src/CE_ori:/data/src/CE_ori \
                -v `pwd`/src/CE_new:/data/src/CE_new \
                -v `pwd`/src/AFLplusplus:/data/src/AFLplusplus \
                -v `pwd`/src/scheduler/main.py:/data/src/scheduler/main.py \
                -v `pwd`/small_exec.elf:/workdir/small_exec.elf \
                -v /home/jie/unifuzz/unibench_targets/ce_targets_ori:/workdir/unibench_targets/ce_targets_ori \
                -v /home/jie/unifuzz/unibench_targets/ce_targets_reach:/workdir/unibench_targets/ce_targets_reach \
                -v /home/jie/unifuzz/seeds/general_evaluation:/data/src/seeds/general_evaluation \
                -v `pwd`/run_icse_bug.sh:/workdir/run_icse_bug.sh \
                -v `pwd`/run_icse.sh:/workdir/run_icse.sh \
                -v `pwd`/run_icse_cgc.sh:/workdir/run_icse_cgc.sh \
                $DKIMG timeout $TOUT /bin/bash $RUNSCRIPT $CONFN $TRIAL $PROGRAM

        TRIAL=$(($TRIAL+1))
        CPU_COUNT=$((CPU_COUNT+1))
    done
    echo ""
done
