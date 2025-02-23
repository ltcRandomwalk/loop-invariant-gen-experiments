// Source: data/benchmarks/LinearArbitrary-SeaHorn/loops/loops/sum01_true-unreach-call_true-termination.i.annot.c
#include <stdlib.h>
#define assume(e) if(!(e)) exit(-1);
extern int unknown_int(void);

int main(){
  int i, n=unknown_int(), sn=0;
assume(n < 1000 && n >= -1000);
/*@
  loop invariant i1: i == 1 || (i > 1 && i <= n + 1);
  loop invariant i2: sn == 2 * (i - 1);
*/
  for(i=1; i<=n; i++){
    sn = sn +(2);
  }
  {;
//@ assert(sn==n*(2)|| sn == 0);
}

} 