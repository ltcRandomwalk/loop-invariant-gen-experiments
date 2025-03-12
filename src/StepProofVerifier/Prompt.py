from .Config import Config
from typing import Dict, List


class Prompt():
    @staticmethod
    def get_init_invariants_prompt(code):
        with open(Config.get_init_invariants_template, 'r') as f:
            template = f.read()
        return template.format(code=code)
    
    @staticmethod
    def prove_establishment_prompt(invariant):
        with open(Config.establishment_proof_template, 'r') as f:
            template = f.read()
        with open(Config.natural_proof_rules, 'r') as f:
            template += f.read()
        return template.format(loop_invariant=invariant)
    
    @staticmethod
    def prove_preservation_prompt(invariant):
        with open(Config.preservation_proof_template, 'r') as f:
            template = f.read()
        with open(Config.natural_proof_rules, 'r') as f:
            template += f.read()
        return template.format(loop_invariant=invariant)
    
    @staticmethod
    def prove_assertion_prompt(assertion):
        with open(Config.assertion_proof_template, 'r') as f:
            template = f.read()
        with open(Config.natural_proof_rules, 'r') as f:
            template += f.read()
        return template.format(assertion=assertion)
    
    @staticmethod
    def formalize_step_prompt(code, invariant_block, natural_proof, step):
        with open(Config.formalize_step_template, 'r') as f:
            template = f.read()
        return template.format(code=code, invariant_block=invariant_block, natural_proof=natural_proof, step=step)
    
    @staticmethod
    def feedback_prompt(step: str, implications: List[Dict], invariant: str, type: str):
        
        prompt = ""
        for implication in implications:
            condition, conclusion, comment = implication["condition"], implication["conclusion"], implication["comment"]
            with open(Config.feedback_proof_template, 'r') as f:
                prompt += f.read().format(step=step, condition=condition, conclusion=conclusion, comment=comment)
            
        if type == "establishment":
            with open(Config.feedback_establishment_template, 'r') as f:
                prompt += f.read().format(invariant=invariant)
        elif type == "preservation":
            with open(Config.feedback_preservation_template, 'r') as f:
                prompt += f.read().format(invariant=invariant)
        elif type == "assertion":
            with open(Config.feedback_assertion_template, 'r') as f:
                prompt += f.read().format(assertion=invariant)
        else:
            assert(False)
        
        return prompt