#include<stdlib.h>
#define assume(e) if(!(e)) exit(-1);
int main() { 
    int x, y;

    assume(x == 0); 
    /*@
        loop invariant (x >= 0 && x <= 99);
        loop invariant (x % 2) == (y % 2);
        loop invariant (x == 0 || x > 0);
    */
    while(x<99) {
        if (y % 2 == 0) 
        { 
            x = x + 2;
        } 
        else 
        {
            x = x + 1;
        }

    }

        {;
        //@ assert((x % 2) == (y % 2));
        }
    
    return 0;
}