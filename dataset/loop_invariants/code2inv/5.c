// Source: data/benchmarks/code2inv/5.c
#include <stdlib.h>
#define assume(e) if(!(e)) exit(-1);

int main()
{
    int x = 0;
    int size;
    int y, z;
   /*@
  loop invariant i1: x >= 0;
  loop invariant i2: (x > 0) ==> (y <= z);
  loop invariant i3: (x > 0) ==> (z <= y ==> (y == z));
*/
    while(x < size) {
       x += 1;
       if( z <= y) {
          y = z;
       }
    }

    if(size > 0) {
       {;
//@ assert(z >= y);
}

    }
}