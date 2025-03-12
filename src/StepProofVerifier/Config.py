from pathlib import Path
import os

class Config():
    benchmark_features = "one_loop_one_method"
    prompt_dir = os.path.join(str(Path(__file__).resolve().parent), "prompts")
    get_init_invariants_template = os.path.join(prompt_dir, "get_init_invariants.txt")
    establishment_proof_template = os.path.join(prompt_dir, "establishment_proof.txt")
    preservation_proof_template = os.path.join(prompt_dir, "preservation_proof.txt")
    assertion_proof_template = os.path.join(prompt_dir, "assertion_proof.txt")
    natural_proof_rules = os.path.join(prompt_dir, "natural_proof_rules.txt")
    formalize_step_template = os.path.join(prompt_dir, "formalize_step.txt")
    feedback_proof_template = os.path.join(prompt_dir, "feedback_proof.txt")
    feedback_establishment_template = os.path.join(prompt_dir, "feedback_establishment.txt")
    feedback_preservation_template = os.path.join(prompt_dir, "feedback_preservation.txt")
    feedback_assertion_template = os.path.join(prompt_dir, "feedback_assertion.txt")