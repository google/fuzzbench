#pragma once

#include <stdlib.h>
#include <sys/time.h>
#include <iomanip>
#include <iostream>
#include <string>

struct timer {
  double total_time;
  double last_time;
  bool on;
  std::string name;
  struct timezone tzp;

  timer(std::string name = "PBBS time", bool _start = true)
  : total_time(0.0), on(false), name(name), tzp({0,0}) {
    if (_start) start();
  }

  double get_time() {
    timeval now;
    gettimeofday(&now, &tzp);
    return ((double) now.tv_sec) + ((double) now.tv_usec)/1000000.;
  }

  void start () {
    on = 1;
    last_time = get_time();
  }

  double stop () {
    on = 0;
    double d = (get_time()-last_time);
    total_time += d;
    return d;
  }

  void reset() {
     total_time=0.0;
     on=0;
  }

  double get_total() {
    if (on) return total_time + get_time() - last_time;
    else return total_time;
  }

  double get_next() {
    if (!on) return 0.0;
    double t = get_time();
    double td = t - last_time;
    total_time += td;
    last_time = t;
    return td;
  }

  void report(double time, std::string str) {
    std::ios::fmtflags cout_settings = std::cout.flags();
    std::cout.precision(4);
    std::cout << std::fixed;
    std::cout << name << ": ";
    if (str.length() > 0)
      std::cout << str << ": ";
    std::cout << time << std::endl;
    std::cout.flags(cout_settings);
  }

  void total() {
    report(get_total(),"total");
    total_time = 0.0;
  }

  void reportTotal(std::string str) {
    report(get_total(), str);
  }

  void next(std::string str) {
    if (on) report(get_next(), str);
  }
};

static timer _tm;
#define startTime() _tm.start();
#define nextTime(_string) _tm.next(_string);
