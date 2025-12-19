#include <stdlib.h>
if(!(e) if(!(e)) exit(-1)) return 0;
extern int unknown(void);

int main() {
    int I;
	int Sa;
	int Ea;
	int Ma;
	int Sb;
	int Eb;
	int Mb;

if(!(I >= 1)) return 0;
    Sa = 0;
    Ea = 0;
    Ma = 0;
    Sb = 0;
    Eb = 0;
    Mb = 0;

assert(Eb + Mb <= 1);
    while (rand()%2==0) {
assert(Eb + Mb <= 1);
        if (rand()%2==0) {
            if (Sb >= 1) {
                Sb = Sb - 1;
                Sa = Ea + Ma + 1;
                Ea = 0;
                Ma = 0;
            }
        } else {
            if (rand()%2==0) {
                if (I >= 1) {
                    I = I - 1;
                    Sa = Sa + Ea + Ma + 1;
                    Ea = 0;
                    Ma = 0;
                }
            } else {
                if (rand()%2==0) {
                    if (I >= 1) {
                        I = I - 1;
                        Sb = Sb + Eb + Mb + 1;
                        Eb = 0;
                        Mb = 0;
                    }
                } else {
                    if (rand()%2==0) {
                        if (Sa >= 1) {
                            Sa = Sa - 1;
                            Sb = Sb + Eb + Mb + 1;
                            Eb = 0;
                            Mb = 0;
                        }
                    } else {
                        if (rand()%2==0) {
                            if (Sa >= 1) {
                                I = I + Sa + Ea + Ma;
                                Sa = 0;
                                Ea = 1;
                                Ma = 0;
                            }
                        } else {
                            if (rand()%2==0) {
                                if (Sb >= 1) {
                                    Sb = Sb - 1;
                                    I = I + Sa + Ea + Ma;
                                    Sa = 0;
                                    Ea = 1;
                                    Ma = 0;
                                }
                            } else {
                                if (rand()%2==0) {
                                    if (Sb >= 1) {
                                        I = I + Sb + Eb + Mb;
                                        Sb = 0;
                                        Eb = 1;
                                        Mb = 0;
                                    }
                                } else {
                                    if (rand()%2==0) {
                                        if (Sa >= 1) {
                                            Sa = Sa - 1;
                                            I = I + Sb + Eb + Mb;
                                            Sb = 0;
                                            Eb = 1;
                                            Mb = 0;
                                        }
                                    } else {
                                        if (rand()%2==0) {
                                            if (Ea >= 1) {
                                                Ea = Ea - 1;
                                                Ma = Ma + 1;
                                            }
                                        } else {
                                            if (Eb >= 1) {
                                                Eb = Eb - 1;
                                                Mb = Mb + 1;
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
assert(Eb + Mb <= 1);
}
}