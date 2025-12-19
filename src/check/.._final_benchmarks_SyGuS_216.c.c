#include <stdlib.h>
if(!(e) if(!(e)) exit(-1)) return 0;
extern int unknown(void);

int main() {
    int invalid;
    int unowned;
    int nonexclusive;
    int exclusive;
    int RETURN;

    unowned = 0;
    nonexclusive = 0;
    exclusive = 0;
if(!(invalid >= 1)) return 0;

assert(exclusive >= 0);
    while(!((nonexclusive + unowned) >= 1 && invalid >= 1)) {
assert(exclusive >= 0);
        if(invalid >= 1){
            if(rand()%2==0){
                nonexclusive = nonexclusive + exclusive;
                exclusive = 0;
                invalid = invalid - 1;
                unowned = unowned + 1;
            }
            else{
                exclusive = 1;
                unowned = 0;
                nonexclusive = 0;
            }
        }
        else if((nonexclusive + unowned) >= 1){
            invalid = invalid + unowned + nonexclusive - 1;
            nonexclusive = 0;
            exclusive = exclusive + 1;
            unowned = 0;
        }
assert(exclusive >= 0);
}
}