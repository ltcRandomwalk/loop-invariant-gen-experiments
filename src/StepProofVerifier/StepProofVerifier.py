from typing import List
from frama_c import FramaCBenchmark, FramaCChecker
from .Config import Config
from datetime import datetime
import logging
from .Prompt import Prompt
from .LLM import CloseAILLM, XMCPLLM
import re
from .SMTSolver import verify_implication, is_valid_c_expression

class StepProofVerifier():
    def __init__(self, benchmark_path):
        self.config = Config()
        self.checker = FramaCChecker()
        self.benchmark_path = benchmark_path
        self.benchmark = FramaCBenchmark(benchmark_path, self.config.benchmark_features, False)
        
        self.model = "volc/deepseek-v3-250324"
        self.llm = XMCPLLM(self.model)
        self.chat_session = []
        self.max_iter = 10
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
    
    

    def checkNaturalProof(self, invariant_block, natural_proof, proof_steps, type, loop_invariant):
        code = self.benchmark.get_code(self.benchmark_path)
        for step in proof_steps:
            logging.info(f"Formalizing step {step}....")
            formalization_prompt = Prompt.formalize_step_prompt(code, invariant_block, natural_proof, step)
            formalized_proof, formalize_session = self.llm.get_response_by_prompt(formalization_prompt)
            logging.info(formalized_proof)

            errors_in_proof = self.checkFormalizedProof(formalized_proof, type, loop_invariant)
            if errors_in_proof:
                return step, errors_in_proof
        return None, None
    

    def checkInitialConditions(self, initial_conditions, type) -> List[str]:
        """
        Return initial conditions that are not valid.
        """
        if type != "establishment":
            raise Exception("Check initial conditions for cases that are not establishment.")
        
        code = self.benchmark.get_code(self.benchmark_path)
        checker_input_with_initial_conditions = self.benchmark.combine_establishment_assertions(
            code, initial_conditions, self.benchmark_features
        )

        logging.info(f"Checker input with initial conditions: {checker_input_with_initial_conditions}")

        __success, checker_message = self.checker.check(
            checker_input_with_initial_conditions,
            check_variant=False,
            check_contracts=False,
        )

        _, _, not_valid_assertions = self.parse_framac_output(checker_message)

        return not_valid_assertions




    def checkFormalizedProof(self, formalized_proof: str, type: str, loop_invariant: str):
        wrong_implications = []
        known_conditions = []
        errors_in_proof = []
        initial_conditions = []   # Just used to check whether the initial conditions are correct.
        wrong_conditions = []

        extract_initial_conditions = False
        check_implication = False
        check_conclusion = False
        for line in formalized_proof.split('\n'):
            if "[Initial]" in line:   # Being parsing initial conditions
                extract_initial_conditions = True
                continue
            elif "[Proof]" in line:   # Begin checking implications
                if type == "establishment":    # TODO: For other types of proof goal, how to check initial conditions?
                    incorrect_initials = self.checkInitialConditions(initial_conditions, type)
                    logging.info(f"Incorrect initial conditions: {incorrect_initials}")
                    for initial in incorrect_initials:
                        errors_in_proof.append({"type": "initial", "condition": initial})


                check_implication = True
                extract_initial_conditions = False
                logging.info(f"Extracted initial conditions: {known_conditions}")
                continue
            elif "[Conclusion]" in line: # Begin checking conclusion
                check_conclusion = True
                check_implication = False
                continue


            if extract_initial_conditions:
                line = line.strip()
                condition = ""
                if "//" in line:
                    condition = line.split("//")[0].strip()
                    comment = line.split("//")[-1].strip()
                if is_valid_c_expression(condition):       # TODO: A legal initial condition should not contain "true", and should not be a single value.
                    known_conditions.append(condition)
                    if comment.lower() == "initial":
                        initial_conditions.append(condition)
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

                    is_valid, model = verify_implication(known_conditions, P_c)   # Check whether the conditions are used correctly.
                    if not is_valid:
                        wrong_conditions.append({"condition": P_c, "conclusion": Q_c, "comment": comment})

                    P_c_list = known_conditions + [ P_c ]
                    known_conditions.append(Q_c)
                    is_valid, model = verify_implication(P_c_list, Q_c)     # Check whether the implication is correct.
                    if not is_valid:
                        wrong_implications.append({"condition": P_c, "conclusion": Q_c, "comment": comment})
                    
                except Exception as e:
                    
                    logging.warning(repr(e))
                    continue

            if check_conclusion:
                line = line.strip()
                logging.info(f"Checking conclusion {line}...")  # TODO: how to check the conclusion


        for implication in wrong_conditions:
            errors_in_proof.append({"type": "implication:condition", "content": implication})
        for implication in wrong_implications:
            errors_in_proof.append({"type": "implication:conclusion", "content": implication})
        return errors_in_proof
    
    def getFeedbackInvariants(self, invariant, type, step, errors_in_proof):
        prompt = Prompt.feedback_prompt(step, errors_in_proof, invariant, type)
        response, chat_history = self.llm.get_response_by_prompt(prompt, chat_history=self.chat_session)
        self.chat_session = chat_history
        invariant_blocks = re.findall(r'(?<=```c\s).*?(?=```)', response, re.DOTALL)
        if not invariant_blocks:
            return ""
        return invariant_blocks[-1]
    
    def getSyntaxErrorInvariants(self):
        prompt = Prompt.syntax_feedback_prompt()
        response, chat_history = self.llm.get_response_by_prompt(prompt, chat_history=self.chat_session)
        self.chat_session = chat_history
        invariant_blocks = re.findall(r'(?<=```c\s).*?(?=```)', response, re.DOTALL)
        if not invariant_blocks:
            return ""
        return invariant_blocks[-1]




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
            else:      # Syntax Error
                # assert(False)
                invariant_block = self.getSyntaxErrorInvariants()
                logging.info(f"Syntax Error. Fixed invariant block: {invariant_block}")
                continue
            logging.info(f"Get natural proof for the {type} of {invariant}")
            natural_proof = self.getNaturalProof(invariant, type)
            logging.info(f"Natural Proof: {natural_proof}")

            ### 4. Formalize and check each step of the proof
            proof_steps = self.getProofSteps(natural_proof)
            logging.info(f"Found proof steps in natural language proof: {proof_steps}")

            step, errors_in_proof = self.checkNaturalProof(invariant_block, natural_proof, proof_steps, type, invariant)
            logging.info(f"Wrong proof in step {step}: {errors_in_proof}")
            #if not step:   # TODO: No error found in the proof.
                #continue

            



            ### 5. Feedback and get fixed loop invariants
            invariant_block = self.getFeedbackInvariants(invariant, type, step, errors_in_proof)
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
            

