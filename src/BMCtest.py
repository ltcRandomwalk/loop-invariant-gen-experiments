from StepProofVerifier.BMC import BMC
import os
import sys

if __name__ == "__main__":
    cProgram = """
    
int main()
{
    int x = 0;
    int size = 5;
    int y, z;

    while(x < size) {
       x += 1;
       if( z <= y) {
          y = z;
       }
    }

    //post-condition
    if(size > 0) {
       assert (z >= y);
    }
}

    """
    cAssertionList = ["assert(x >= 0 && x < size)", "assert(y > z)", "assert(z >= y)", "assert(x == 0 )"]
    benchmark = "../final_benchmark/code2inv/Linear/5.c"
    
    bmc = BMC(cProgram, cAssertionList, benchmark)
    AnsSet = bmc.run_bmc([])
    print(AnsSet)
    print("BMC completed.")