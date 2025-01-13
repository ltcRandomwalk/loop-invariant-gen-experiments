// Source: data/benchmarks/sv-benchmarks/recursive-simple/id_b2_o3.c
#include <stdlib.h>
#define assume(e) if(!(e)) exit(-1);
#define abort() exit(-2);
extern unsigned int unknown_uint(void);


/* Function_id */
unsigned int id(unsigned int x) {
  if (x==0) return 0;
  unsigned int ret = id(x-1) + 1;
  if (ret > 2) return 2;
  return ret;
}


/* Function_main */
int main(void) {
  unsigned int input = unknown_uint();
  unsigned int result = id(input);
  if (result == 3) {
    { ERROR: {; 
//@ assert(\false);
}
}
  }
}