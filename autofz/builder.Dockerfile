ARG parent_image
ARG UID=2000
FROM $parent_image

# FROM fuyu0425/autofz:v1.0.1

RUN apt-get update && \
	apt-get install -y \
	vim \
	tmux \
	nano \
	htop \
	autoconf \
	automake \
	build-essential \
	libtool \
	cmake \
	git \
	sudo \
	software-properties-common \
	gperf \
	libselinux1-dev \
	bison \
	texinfo \
	flex \
	zlib1g-dev \
	libexpat1-dev \
	libmpg123-dev \
	wget \
	curl \
	python3-pip \
	python3-pip \
	unzip \
	pkg-config \
	clang \
	llvm-dev \
	apt-transport-https \
	ca-certificates \
	libc++1 \
	libc++-dev \
#	gcc-5-plugin-dev \
	zip \
	tree \
	re2c \
	bison \
	python \
	python3

