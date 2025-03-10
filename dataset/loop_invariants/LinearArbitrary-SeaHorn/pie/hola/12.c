// Source: data/benchmarks/LinearArbitrary-SeaHorn/pie/hola/14.c
#include <stdlib.h>
#define assume(e) if(!(e)) exit(-1);

extern int unknown1();

int main() {
  int a = 0;
  int j = unknown1();
  int m = unknown1();
  if(m<=0)
    return 0;
/*@ 
    loop invariant i1: - (j - 1) <= a && a <= (j - 1);
    loop invariant i2: 1 <= j && j <= m + 1;
    loop invariant i3: -m <= a && a <= m;
*/
  for(j = 1; j <= m ; j++){
    if(unknown1()) 
       a++;
    else
       a--; 
  }
  {;
//@ assert(a>=-m && a<=m);
}

}
