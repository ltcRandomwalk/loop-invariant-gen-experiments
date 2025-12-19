#include <stdlib.h>
if(!(e) if(!(e)) exit(-1)) return 0;
extern int unknown(void);

int main() {
    int x1;
    int x2;
    int x3;
    int x4;
    int x5;
    int x6;
    int x7;
    int p;
    int q;

    x1 = 0;
    x2 = 0;
    x3 = 0;
    x4 = 0;
    x5 = 0;
    x6 = p;
    x7 = q;
if(!(p >= 1)) return 0;
if(!(q >= 1)) return 0;

assert(x1 + x2 + x3 + x4 + x5 + x6 + x7 == p + q);
    while (rand()%2==0) {
assert(x1 + x2 + x3 + x4 + x5 + x6 + x7 == p + q);
        if (rand()%2==0) {
            if (x6 >= 1) {
                x1 = x1 + 1;
                x6 = x6 - 1;
            }
        } else {
            if (rand()%2==0) {
                if (x1 >= 1 && x7 >= 1) {
                    x1 = x1 - 1;
                    x2 = x2 + 1;
                    x7 = x7 - 1;
                }
            } else {
                if (rand()%2==0) {
                    if (x2 >= 1) {
                        x2 = x2 - 1;
                        x3 = x3 + 1;
                        x6 = x6 + 1;
                    }
                } else {
                    if (rand()%2==0) {
                        if (x3 >= 1 && x6 >= 1) {
                            x3 = x3 - 1;
                            x4 = x4 + 1;
                            x6 = x6 - 1;
                        }
                    } else {
                        if (rand()%2==0) {
                            if (x4 >= 1) {
                                x4 = x4 - 1;
                                x5 = x5 + 1;
                                x7 = x7 + 1;
                            }
                        } else {
                            if (x5 >= 1) {
                                x5 = x5 - 1;
                                x6 = x6 + 1;
                            }
                        }
                    }
                }
            }
        }
assert(x1 + x2 + x3 + x4 + x5 + x6 + x7 == p + q);
}
}