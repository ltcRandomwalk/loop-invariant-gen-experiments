
from . import spilit
import subprocess
import psutil
from frama_c import FramaCBenchmark, FramaCChecker
from .Config import Config

class BMC():
    def __init__(self, cProgram, cAssertionList, benchmark_path):
        self.BMC_executable = "/home/tcli/LaM4Inv/release-ubuntu-latest/bin/esbmc"
        self.config = Config()
        self.cProgram = cProgram
        self.cAssertionList = cAssertionList
        self.resultpath = benchmark_path.replace('/', '_')
        self.benchmark = FramaCBenchmark(benchmark_path, self.config.benchmark_features, False)
        self.checker = FramaCChecker()

    def undefined_function(self, subassertion):
        cannot_exsit=['min', '?', 'max', 'unknown', 'factorial', 'pow', 'for', '=>', 'old', 'INT', '->>', '->']
        for cannot_exist_function in cannot_exsit:
            if str(cannot_exist_function) in subassertion:
                return False
        return True
    
    def run_command_with_timeout(self, command, timeout):
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = None, None
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            parent = psutil.Process(process.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
            stdout, stderr = process.communicate()
            return "Timeout"
        finally:
            process.stdout.close()
            process.stderr.close()

        output_str = f"{stdout}{stderr}"
        
        return output_str


    def run_bmc(self, AnsSet):
        for index in range(len(self.cAssertionList)):
            CAssertion=self.cAssertionList[index]
            CAssertionlist, outer_operator=spilit.c_assert_spilit(CAssertion)
            if outer_operator=='||':
                ifaddall=self.esbmc_and(self.cProgram,CAssertion[CAssertion.find("(")+1:CAssertion.rfind(")")])
                if ifaddall:
                    tempansset=[]
                    for subassertion in CAssertionlist:
                        if subassertion not in tempansset and self.undefined_function(subassertion):
                            ifAdd=self.esbmc_or(self.cProgram,subassertion)
                            if ifAdd:
                                tempansset.append(subassertion)
                    resans=""
                    for res in tempansset:
                        resans=resans+"("+res+")"+"||"
                    if resans[0:-2] not in AnsSet:
                        AnsSet.append(resans[0:-2])
            else:
                for subassertion in CAssertionlist:
                    if subassertion not in AnsSet and self.undefined_function(subassertion):
                        ifAdd=self.esbmc_and(self.cProgram,subassertion)
                        if ifAdd:
                            AnsSet.append(subassertion)
        return AnsSet

    
    def esbmc_and(self, cProgram,subassertion):
        establishment = self.checkInitialConditions([subassertion])
        if not establishment:
            return False
        # Remove all c
        assertion='assert('+subassertion+');'
        esbmcProgram=cProgram.replace('unknown()','rand()%2==0')
        file=open("./check/"+self.resultpath+".c","w")
        leftcount=0
        rightcount=0
        judge=True
        B=""
        for lines in esbmcProgram.splitlines():
            if "while" in lines:
                B=lines[lines.find("(")+1:lines.rfind(")")]
                lines=assertion+"\n"+lines+"\n"+assertion
            if "assume" in lines:
                condition=lines[lines.find("(")+1:lines.rfind(")")]
                lines="if(!("+condition+")) return 0;"
            if "{" in lines:
                leftcount+=1
            if "}" in lines:
                rightcount+=1
            if leftcount>1 and leftcount-1==rightcount and judge:
                file.write(assertion+"\n}\n}")
                judge=False
                break
            file.write(lines+"\n")
        file.close()
        tmp = str(subassertion).replace(' ','')
        tmp = tmp.replace('(','')
        tmp = tmp.replace(')','')
        B = B.replace(' ','')
        if tmp in B:
            return False
        
        command = [self.BMC_executable, "./check/"+self.resultpath+".c", "--floatbv", "--k-induction", "--max-k-step", str(10)]
            

        val = self.run_command_with_timeout(command, 600)

        if val != "subprocess.TimeoutExpired":
            if 'VERIFICATION FAILED' in str(val):
                return False
            else:
                return True
        else:
            return False

    def esbmc_or(self,cProgram,subassertion):
        establishment = self.checkInitialConditions([subassertion])
        if not establishment:
            return False
        
        assertion='assert(!('+subassertion+'));'
        esbmcProgram=cProgram.replace('unknown()','rand()%2==0')
        file=open("./check/"+self.resultpath+".c","w")
        leftcount=0
        rightcount=0
        judge=True
        for lines in esbmcProgram.splitlines():
            if "while" in lines:
                lines=assertion+"\n"+lines+"\n"+assertion
            if "assume" in lines:
                condition=lines[lines.find("(")+1:lines.rfind(")")]
                lines="if(!("+condition+")) return 0;"
            if "{" in lines:
                leftcount+=1
            if "}" in lines:
                rightcount+=1
            if leftcount>1 and leftcount-1==rightcount and judge:
                file.write(assertion+"\n}\n}")
                judge=False
                break
            file.write(lines+"\n")
        file.close()

        command = [self.BMC_executable, "./check/"+self.resultpath+".c", "--floatbv", "--k-induction", "--max-k-step", str(10)]


        val = self.run_command_with_timeout(command, 600)

        if val != "subprocess.TimeoutExpired":
            if 'VERIFICATION SUCCESSFUL' in str(val):
                return False
            else:
                return True
        else:
            return False
        
    def checkInitialConditions(self, initial_conditions):
        checker_input_with_initial_conditions = self.benchmark.combine_establishment_assertions(
            self.cProgram, initial_conditions, self.config.benchmark_features
        )

        __success, checker_message = self.checker.check(
            checker_input_with_initial_conditions,
            check_variant=False,
            check_contracts=False,
            timeout=1
        )

        return __success
        

if __name__ == "__main__":
    cProgram = """
    
int main()
{
    int x = 0;
    int size;
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
    cAssertionList = ["assert(x >= 0 && x <= size)"]
    benchmark = "../final_benchmark/code2inv/Linear/5.c"
    
    bmc = BMC(cProgram, cAssertionList, benchmark)
    AnsSet = bmc.run_bmc([])
    print(AnsSet)
    print("BMC completed.")