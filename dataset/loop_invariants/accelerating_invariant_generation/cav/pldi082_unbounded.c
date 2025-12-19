// Source: data/benchmarks/accelerating_invariant_generation/cav/pldi082_unbounded.c
#include <stdlib.h>
#define assume(e) if(!(e)) exit(-1);

int main(){

  int x = 0;
  int y = 0;
  int N;

  if(N < 0)
    return 1;

    /*@ 
      loop invariant 0 <= x;
      loop invariant -1 <= y;
      loop invariant x <= N+1 ==> y == x;
      loop invariant x > N+1 ==> y == 2*(N+1) - x;
    */

  while (y>=0){
     if (x <= N)
        y++;
     else if(x >= N+1)
       y--;

     x++;
  }

  //@ assert(!(N >= 0 && y < -1 && x >= 2 * N + 4));

  if(N >= 0)
    if(y < -1)
      if (x >= 2 * N + 4)
        goto ERROR;

  return 1;
{ ERROR: {; 
//@ assert(\false);
}
}
}
