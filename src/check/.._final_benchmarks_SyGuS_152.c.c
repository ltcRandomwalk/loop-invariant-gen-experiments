#include <stdlib.h>
if(!(e) if(!(e)) exit(-1)) return 0;
extern int unknown(void);

int main(){
    int i;
    int pvlen;
    int t;
    int k;
    int n;
    int j;
    int turn;

    k = 0;
    i = 0;
    turn = 0;

assert(!(turn != 2));
    while(turn < 5){
assert(!(turn != 2));
        if(turn == 0){
            i = i + 1;
            if(rand()%2==0){
                turn = 1;
            }
        }
        else if(turn == 1){
            if(i > pvlen){
                pvlen = i;
            }
            i = 0;
            turn = 2;
        }
        else if(turn == 2){
            t = i;
            i = i + 1;
            k = k + 1;
            if(rand()%2==0){
                turn = 3;
            }
        }
        else if(turn == 3){
            if(rand()%2==0){
                turn = 4;
            }
        }
        else if(turn == 4){
            n = i;
            j = 0;
            turn = 5;
        }
assert(!(turn != 2));
}
}