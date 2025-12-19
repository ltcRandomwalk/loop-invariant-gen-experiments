#include <stdlib.h>
if(!(e) if(!(e)) exit(-1)) return 0;

int main(){
    int k;
    int i;
    int j;
    int n;
    int turn;

    k = 1;
    i = 1;
    j = 0;
    turn = 0;

assert(!(turn != 3));
    while((turn >= 0) && (turn < 3)){
assert(!(turn != 3));
        if(turn == 0 && i >= n){
            turn = 3;
        }
        else if(turn == 1 && j < i){
            k = k + i - j;
            j = j + 1;
        }
        else if (turn == 1 && j >= i){
            turn = 2;
        }
        else if(turn == 2){
            i = i + 1;
            turn = 0;
        }
assert(!(turn != 3));
}
}