#include <stdlib.h>
if(!(e) if(!(e)) exit(-1)) return 0;
extern int unknown(void);

int main() {
    int invalid;
    int unowned;
    int nonexclusive;
    int exclusive;

    exclusive = 0;
    nonexclusive = 0;
    unowned = 0;
if(!(invalid >= 1)) return 0;

assert(invalid + unowned + exclusive + nonexclusive >= 1);
    while (rand()%2==0) {
assert(invalid + unowned + exclusive + nonexclusive >= 1);
        if (rand()%2==0) {
            if(invalid >= 1){
            nonexclusive = nonexclusive + exclusive;
            exclusive = 0;
            invalid = invalid - 1;
            unowned = unowned + 1;
            }
        } else {
            if (rand()%2==0) {
                if(nonexclusive + unowned >= 1){
                invalid = invalid + unowned + nonexclusive - 1;
                exclusive = exclusive + 1;
                unowned = 0;
                nonexclusive = 0;
                }
            } else {
                if(invalid >= 1){
                unowned = 0;
                nonexclusive = 0;
                exclusive = 1;
                invalid = invalid + unowned + exclusive + nonexclusive - 1;
                }
            }
        }
assert(invalid + unowned + exclusive + nonexclusive >= 1);
}
}