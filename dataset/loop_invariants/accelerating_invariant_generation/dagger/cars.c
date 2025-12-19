int main() {
    int x1;
    int v1;
    int x2;
    int v2;
    int x3;
    int v3;
    int t;

    // pre-condition
    x1 = 100;
    x2 = 75;
    x3 = -50;
    assume(v3 >= 0);
    assume(v1 <= 5);
    assume(v1 - v3 >= 0);
    assume(2 * v2 - v1 - v3 == 0);
    t = 0;
    assume(v2 + 5 >= 0);
    assume(v2 <= 5);

    // loop-body
    while (v2 + 5 >= 0 && v2 <= 5) {
        if (unknown()) {
            if(2 * x2 - x1 - x3 >= 0){
            x1 = x1 + v1;
            x3 = x3 + v3;
            x2 = x2 + v2;
            v2 = v2 - 1;
            t = t + 1;
            }
        } else {
            if(2 * x2 - x1 - x3 <= 0){
            x1 = x1 + v1;
            x3 = x3 + v3;
            x2 = x2 + v2;
            v2 = v2 + 1;
            t = t + 1;
            }
        }
    }

    // post-conditions
    assert(v1 <= 5 && 2 * v2 + 2 * t >= v1 + v3 && 5 * t + 75 >= x2 && v2 <= 6 && v3 >= 0 && v2 + 6 >= 0 && x2 + 5 * t >= 75 && v1 - 2 * v2 + v3 + 2 * t >= 0 && v1 - v3 >= 0);
    
}