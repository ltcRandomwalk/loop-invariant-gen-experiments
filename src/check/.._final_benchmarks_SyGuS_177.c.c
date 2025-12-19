#include <stdlib.h>
if(!(e) if(!(e)) exit(-1)) return 0;
extern int unknown(void);

int main(){
    int x;
    int y;
    int z;
    int c;
    int k;
    int turn;

    x = 0;
    y = 0;
    turn = 0;
if(!(z == k)) return 0;

assert(!(z == k));
    while(rand()%2==0){
assert(!(z == k));
        if(turn == 0){
            c = 0;
            if(rand()%2==0){
                turn = 1;
            }
            else{
                turn = 2;
            }
        }
        else if(turn == 1){
            if(z == (k + y - c)){
                y = y + 1;
                x = x + 1;
                c = c + 1;
                turn = 2;
            }
            else{
                y = y - 1;
                x = x + 1;
                c = c + 1;
                if(rand()%2==0){
                    turn = 2;
                }
            }
        }
        else if(turn == 2){
            x = x - 1;
            y = y - 1;
            if(rand()%2==0){
                turn = 3;
            }
        }
        else if(turn > 2 || turn < 0){
            z = x + y;
            turn = 0;
        }
assert(!(z == k));
}
}