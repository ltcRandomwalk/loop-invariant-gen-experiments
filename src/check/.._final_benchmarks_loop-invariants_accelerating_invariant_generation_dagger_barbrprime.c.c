#include <stdlib.h>
if(!(e) if(!(e)) exit(-1)) return 0;
extern int unknown(void);

int main() {
    int barber;
    int chair;
    int open;
    int p1;
    int p2;
    int p3;
    int p4;
    int p5;

    barber = 0;
    chair = 0;
    open = 0;
    p1 = 0;
    p2 = 0;
    p3 = 0;
    p4 = 0;
    p5 = 0;

assert(p5 >= open);
    while (rand()%2==0) {
assert(p5 >= open);
        if (rand()%2==0) {
            if(p1 == 0 && barber >= 1) {
            barber = barber - 1;
            chair = chair + 1;
            p1 = 1;
            }
        }
        else {
            if (rand()%2==0) {
                if(p2 == 0 && barber >= 1) {
                barber = barber - 1;
                chair = chair + 1;
                p2 = 1;
                }
            }
            else {
                if (rand()%2==0) {
                    if(p2 == 1 && open >= 1) {
                    open = open - 1;
                    p2 = 0;
                    }
                }
                else {
                    if (rand()%2==0) {
                        if(p3 == 0 && barber >= 1) {
                        barber = barber - 1;
                        chair = chair + 1;
                        p3 = 1;
                        }
                    }
                    else {
                        if (rand()%2==0) {
                            if(p3 == 1 && open >= 1) {
                            open = open - 1;
                            p3 = 0;
                            }
                        }
                        else {
                            if (rand()%2==0) {
                                if(p4 == 0 && barber >= 1) {
                                barber = barber - 1;
                                chair = chair + 1;
                                p4 = p4 + 1;
                                }
                            }
                            else {
                                if (rand()%2==0) {
                                    if(p4 == 1 && open >= 1) {
                                    open = open - 1;
                                    p4 = p4 - 1;
                                    }
                                }
                                else {
                                    if (rand()%2==0) {
                                        if(p5 == 0) {
                                        barber = barber + 1;
                                        p5 = 1;
                                        }
                                    }
                                    else {
                                        if (rand()%2==0) {
                                            if(p5 == 1 && chair >= 1) {
                                            chair = chair - 1;
                                            p5 = 2;
                                            }
                                        }
                                        else {
                                            if (rand()%2==0) {
                                                if(p5 == 2) {
                                                open = open + 1;
                                                p5 = 3;
                                                }
                                            }
                                            else {
                                                if (rand()%2==0) {
                                                    if(p5 == 3 && open == 0)
                                                    p5 = 0;
                                                }
                                                else {
                                                    if(p1 == 1 && open >= 1) {
                                                    open = open - 1;
                                                    p1 = 0;
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
assert(p5 >= open);
}
}