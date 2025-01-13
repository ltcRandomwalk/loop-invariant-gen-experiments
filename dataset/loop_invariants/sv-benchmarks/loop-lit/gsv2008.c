// Source: data/benchmarks/sv-benchmarks/loop-lit/gsv2008.c
#include <stdlib.h>
#define assume(e) if(!(e)) exit(-1);
#define LARGE_INT 1000000
extern int unknown_int(void);

int main() {
    int x,y;
    x = -50;
    y = unknown_int();
    if (!(-1000 < y && y < LARGE_INT)) return 0;
    /*@
  loop invariant -50 <= x < 0;
  loop invariant -1000 < y < LARGE_INT;
  loop invariant y >= -1000;
  loop variant -x;
*/
    while (x < 0) {
	x = x + y;
	y++;
    }
    {;
//@ assert(y > 0);
}

    return 0;
}