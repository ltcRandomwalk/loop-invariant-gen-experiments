// Source: data/benchmarks/tpdb/C_Integer/Stroeder_15/svcomp_b.10.c
#include <stdlib.h>
#define assume(e) if(!(e)) exit(-1);
extern int unknown_int(void);

typedef enum {false, true} bool;

int main() {
    int c;
    int x, y;
    x = unknown_int();
    y = unknown_int();
    c = 0;
    while (x + y > 0) {
        if (x > 0) {
            x = x - 1;
        } else {
            if (y > 0) {
                y = y - 1;
            } else {
                
            }
        }
        c = c + 1;
    }
    return 0;
}