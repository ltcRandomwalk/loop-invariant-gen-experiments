from enum import verify
from urllib import response
from frama_c import FramaCBenchmark, FramaCChecker
from .Config import Config
from datetime import datetime
import logging
from .Prompt import Prompt
from .LLM import CloseAILLM
import re
from .SMTSolver import verify_implication, is_valid_c_expression

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
        pattern = r'/\*@.*?\*/'
        invariant_block = re.findall(pattern, response, re.DOTALL)[-1]
        return invariant_block
        #invariant_block = re.findall(r'(?<=```c\s).*?(?=```)', response, re.DOTALL)[-1]
        #return invariant_block
    
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

    
    def getProofSteps(self, natrual_proof: str):
        pattern = r'\[STEP \d+: .*?\]'

        groups = re.findall(pattern, natrual_proof)
        return groups
    
    

    def checkNaturalProof(self, invariant_block, natural_proof, proof_steps):
        code = self.benchmark.get_code(self.benchmark_path)
        for step in proof_steps:
            logging.info(f"Formalizing step {step}....")
            formalization_prompt = Prompt.formalize_step_prompt(code, invariant_block, natural_proof, step)
            formalized_proof, formalize_session = self.llm.get_response_by_prompt(formalization_prompt)
            logging.info(formalized_proof)

            wrong_implications = self.checkFormalizedProof(formalized_proof)
            if wrong_implications:
                return step, wrong_implications
        return None, None


    def checkFormalizedProof(self, formalized_proof: str):
        wrong_implications = []
        known_conditions = []

        extract_initial_conditions = False
        check_implication = False
        for line in formalized_proof.split('\n'):
            if "[Initial]" in line:   # Parse initial conditions
                extract_initial_conditions = True
            elif "[Proof]" in line:   # Begin checking implications
                check_implication = True
                extract_initial_conditions = False

            if extract_initial_conditions:
                line = line.strip()
                if "//" in line:
                    line = line.split("//")[0]
                if is_valid_c_expression(line):
                    known_conditions.append(line)
                continue

            if check_implication:
                line = line.strip()

                logging.info(f"Checking line {line}...")
                try:
                    if "==>" not in line:
                        continue
                    if "//" in line:
                        implication, comment = line.split("//")
                    else:
                        implication, comment = line, ""
                    
                    P_c, Q_c = implication.split("==>")
                    if "true" in P_c:
                        known_conditions.append(Q_c)
                        continue
                    P_c_list = known_conditions + [ P_c ]
                    known_conditions.append(Q_c)
                    is_valid, model = verify_implication(P_c_list, Q_c)
                    if not is_valid:
                        wrong_implications.append({"condition": P_c, "conclusion": Q_c, "comment": comment})
                    
                except Exception as e:
                    
                    logging.warning(repr(e))
                    continue
        return wrong_implications
    
    def getFeedbackInvariants(self, invariant, type, step, wrong_implications):
        prompt = Prompt.feedback_prompt(step, wrong_implications, invariant, type)
        response, chat_history = self.llm.get_response_by_prompt(prompt, chat_history=self.chat_session)
        self.chat_session = chat_history
        invariant_block = re.findall(r'(?<=```c\s).*?(?=```)', response, re.DOTALL)[-1]
        return invariant_block




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
            logging.info(f"Natural Proof: {natural_proof}")

            ### 4. Formalize and check each step of the proof
            proof_steps = self.getProofSteps(natural_proof)
            logging.info(f"Found proof steps in natural language proof: {proof_steps}")

            step, wrong_implications = self.checkNaturalProof(invariant_block, natural_proof, proof_steps)
            logging.info(f"Wrong proof in step {step}: {wrong_implications}")
            if not step:   # TODO: No error found in the proof.
                continue

            



            ### 5. Feedback and get fixed loop invariants
            invariant_block = self.getFeedbackInvariants(invariant, type, step, wrong_implications)
            logging.info(f"Fixed invariant block: {invariant_block}")







            


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
            

