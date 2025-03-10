from urllib import response
from frama_c import FramaCBenchmark, FramaCChecker
from .Config import Config
from datetime import datetime
import logging
from .Prompt import Prompt
from .LLM import CloseAILLM
import re

class StepProofVerifier():
    def __init__(self, benchmark_path):
        self.config = Config()
        self.checker = FramaCChecker()
        self.benchmark_path = benchmark_path
        self.benchmark = FramaCBenchmark(benchmark_path, self.config.benchmark_features, False)
        
        self.model = "gpt-4o-2024-11-20"
        self.llm = CloseAILLM(self.model)
        self.chat_session = []
        self.max_iter = 5
        self.benchmark_features = self.config.benchmark_features
        

    def getInitInvariants(self):
        ### Return invariant block
        code = self.benchmark.get_code(self.benchmark_path)
        prompt = Prompt.get_init_invariants_prompt(code)
        response, chat_history = self.llm.get_response_by_prompt(prompt)
        self.chat_session += chat_history
        # Parsing invariants
        invariant_block = re.findall(r'(?<=```c\s).*?(?=```)', response, re.DOTALL)[-1]
        return invariant_block
    
    def checkInvariants(self, invariant_block):
        checker_input_with_annotations = self.benchmark.combine_llm_outputs(
            self.benchmark.get_code(self.benchmark_path),
            [invariant_block],
            self.benchmark_features,
        )

        __success, checker_message = self.checker.check(
            checker_input_with_annotations,
            check_variant=False,
            check_contracts=False,
        )

        return __success, checker_message
    

    def getNaturalProof(self, loop_invariant: str, type: str):
        if type == "establishment":
            prompt = Prompt.prove_establishment_prompt(loop_invariant)
        elif type == "preservation":
            prompt = Prompt.prove_preservation_prompt(loop_invariant)
        elif type == "assertion":
            prompt = Prompt.prove_assertion_prompt(loop_invariant)
        else:
            logging.ERROR(f"Invalid type while getting natural proof: {type}")
            assert(False)
        
        response, chat_history = self.llm.get_response_by_prompt(prompt, chat_history=self.chat_session)
        self.chat_session = chat_history
        return response

    def run(self):
        self.log_path = datetime.now().strftime(f"logs/StepProof_%m_%d_%H_%M_%S")
        logging.basicConfig(filename=self.log_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.info(f"Running benchmark {self.benchmark_path}...\n")

        ### 1. Get Initial Invariants
        invariant_block = self.getInitInvariants()
        logging.info(f"Initial invariant block: \n {invariant_block}\n")
        #logging.info(self.llm.parse_session(self.chat_session))

        iters = 0
        logging.info(f"Begin iteration...\n")
        while iters < self.max_iter:
            ### 2. Check Invariants
            
            success, checker_message = self.checkInvariants(invariant_block)
            if success:
                logging.info(f"Succeed in {iters} iterations!\n")
                logging.info(f"Resulted invariants: {invariant_block}\n")
                return
            
            iters += 1

            logging.info(f"===================Iteration: {iters}===================")
            not_established_invariants, not_preserved_invariants, not_valid_assertions = self.parse_framac_output(checker_message)
            
            logging.info(f"Not established: {not_established_invariants}")
            logging.info(f"Not preserved: {not_preserved_invariants}")
            logging.info(f"Not valid assertions: {not_valid_assertions}")

            ### 3. Natural Language Proof

            if not_established_invariants:
                invariant, type = not_established_invariants[0], "establishment"
            elif not_preserved_invariants:
                invariant, type = not_preserved_invariants[0], "preservation"
            elif not_valid_assertions:
                invariant, type = not_valid_assertions[0], "assertion"
            else:
                assert(False)
            logging.info(f"Get natural proof for the {type} of {invariant}")
            natural_proof = self.getNaturalProof(invariant, type)
            # logging.info(self.llm.parse_session(self.chat_session))


            ### 4. Formalize and check each step of the proof


            ### 5. Feedback and get fixed loop invariants






            


    def parse_framac_output(self, checker_message):
        not_established_invariants = []
        not_preserved_invariants = []
        not_valid_assertion = []
        for line in checker_message.split('\n'):
            pattern = r'loop invariant (.*?) is preserved but not established\.'
            matches = re.findall(pattern, line)
            if len(matches) == 1:
                not_established_invariants += matches 
            
            pattern = r'loop invariant (.*?) is established but not preserved\.'
            matches = re.findall(pattern, line)
            if len(matches) == 1:
                not_preserved_invariants += matches 
            
            pattern = r'loop invariant (.*?) is neither established nor preserved\.'
            matches = re.findall(pattern, line)
            if len(matches) == 1:
                not_preserved_invariants += matches 
                not_established_invariants += matches
            
            pattern = r'Assertion (.*?): Unproven'
            matches = re.findall(pattern, line)
            if len(matches) == 1:
                not_valid_assertion += matches 
        
        return not_established_invariants, not_preserved_invariants, not_valid_assertion
            

