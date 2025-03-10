from .Config import Config

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