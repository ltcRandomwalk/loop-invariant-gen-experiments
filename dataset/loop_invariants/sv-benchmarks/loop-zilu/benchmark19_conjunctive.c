// Source: data/benchmarks/sv-benchmarks/loop-zilu/benchmark19_conjunctive.c
#include <stdlib.h>
#define assume(e) if(!(e)) exit(-1);
extern int unknown_int(void);

#include <assert.h>

int main() {
  int j = unknown_int();
  int k = unknown_int();
  int n = unknown_int();
  if (!((j==n) && (k==n) && (n>0))) return 0;
  while (j>0 && n>0) {
    j--;k--;
  }
  {;
//@ assert((k == 0));
}

  return 0;
}