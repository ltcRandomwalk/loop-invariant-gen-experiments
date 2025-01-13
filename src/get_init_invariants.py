from loopy_llm import LLM, Prompt
from frama_c import FramaCBenchmark, FramaCChecker
from openai import OpenAI
import os

import re

def extract_custom_strings(input_string):
    pattern = r'/\*@.*?\*/'
    matches = re.findall(pattern, input_string, re.DOTALL)
    return matches

checker = FramaCChecker()
benchmark_features = "one_loop_one_method"


def get_closeai_answer(messages):
    from openai import OpenAI

    client = OpenAI(
        base_url='https://api.openai-proxy.org/v1',
        api_key=os.getenv("CLOSEAI_API_KEY"),
    )

    chat_completion = client.chat.completions.create(
        messages=messages,
        model="gpt-4o-2024-11-20",
    )
    
    return chat_completion.choices[0].message.content
    
    

def get_init_invariants(benchmark_file):
    benchmark = FramaCBenchmark(benchmark_file, benchmark_features, False)
    
    codeblock_filter = lambda x: checker.has_invariant(x) or (
        checker.has_function_contract(x)
        if "multiple_methods" in benchmark_features
        else False
    )
    
    code = benchmark.get_code(benchmark_file)
    
    prompt = f"""
    {code}
    Please analyze the above C code and verify the assertions in it. 
    In order to verify the assertion, you need to propose loop invariants for the loop in the program. A loop invariant is a property that holds **before the loop**, and **after each iteration of the loop**. Besides, the loop invariants should be helpful to verify the assertion.
    Please print the loop invariants as C logical expressions. You can use "&&" or "||" to represent conjunction or disjunction. If a variable is not initialized, it can be any legal value. Do not use variables or functions that are not defined in the program. Do not change the original program and assertion. Do not explain.
    Print the loop invaraints in the following format:

    /*@
        loop invariant i1: ...;
        loop invariant i2: ...;
        ...
    */
    """
    
    annotation_blocks = extract_custom_strings(get_closeai_answer([{"role": "user", "content": prompt}]))[0]
    
    print(annotation_blocks)
    
    checker_input_with_annotations = benchmark.combine_llm_outputs(
        benchmark.get_code(benchmark_file),
        [annotation_blocks],
        benchmark_features,
    )
    
    __success, checker_message = checker.check(
        checker_input_with_annotations,
        check_variant=False,
        check_contracts=False,
    )
    
    return __success, annotation_blocks, checker_message

def parse_framac_output(checker_message):
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
        
        pattern = r'Assertion (.*?): Unknown'
        matches = re.findall(pattern, line)
        if len(matches) == 1:
            not_valid_assertion += matches 
    
    return not_established_invariants, not_preserved_invariants, not_valid_assertion

def establishment_feedback(code, annotation_block, loop_invariant):
    prompt = f"""
    {code}
    
    Please analyze the above C code and verify the assertions in it. 
    In order to verify the assertion, you need to propose loop invariants for the loop in the program. A loop invariant is a property that holds **before the loop**, and **after each iteration of the loop**. Besides, the loop invariants should be helpful to verify the assertion.
    
    In your previous answer, the loop invariants you proposed are:
    {annotation_block}
    
    The establishment of the loop invariant {loop_invariant} cannot be verified. In order to help you correct the mistake, I will ask you to give a proof of the establishment of this loop invariant {loop_invariant}.
    In particular, you should prove that the loop invariant holds before the loop. You should fisrt list the known conditions, and from the conditions, prove the loop invariant step by step.
    The conditions in this case are the program states before the loop. Note that, if a variable is not initialized, you should not make any assumption on it.
    
    Answer the question in the following format:
    ```
    Known Conditions:
    <>
    
    Step 1: <Proof Goal>
    <Proof>
    
    Step 2: <Proof Goal>
    <Proof>
    
    ...
    
    """
    
    response = get_closeai_answer([{"role": "user", "content": prompt}])
    return prompt, response


def get_formalized_proof(previous_conversation):
    prompt = f"""
    Now, please formalize each step of your proof. In particular, for each step, you should represent your proof in a list of implications.
    Answer the question in the the following json format. For the blank <Proof Goal>, briefly summary the proof goal in natural language. 
    For each implication, represent it in the format "c1 ==> c2", where c1 and c2 are two **pure C logical expressions**, and c1 can derive c2. Do not use any natural language in the implication. The implication should be able to be checked without other conditions.
    {{
        "Step 1: <Proof Goal>": ["<Implication 1>", "<Implication 2>", ...]
        "Step 2: <Proof Goal>": ["<Implication 1>", "<Implication 2>", ...]
        ...
    }}
    
    Do not explain.
    """
    
    msgs = previous_conversation + [
        {"role": "user", "content": prompt}
    ]
    
    return get_closeai_answer(msgs)


if __name__ == "__main__":
    benchmark_file = "/home/tcli/loop-invariant-gen-experiments/test.c"
    __success, annotation_blocks, checker_message = get_init_invariants(benchmark_file)
    benchmark = FramaCBenchmark(benchmark_file, benchmark_features, False)
    code = benchmark.get_code(benchmark_file)
    print(__success)
    print(checker_message)
    if  __success:
        exit(0)
    not_established_invariants, not_preserved_invariants, not_valid_assertion = parse_framac_output(checker_message)
    print(not_established_invariants, not_preserved_invariants, not_valid_assertion)
    
    if not not_established_invariants:
        exit(0)
    
    repair_prompt, natural_proof = establishment_feedback(code, annotation_blocks, not_established_invariants[0])
    
    formalized_proof = get_formalized_proof(
        [
            {"role": "user", "content": repair_prompt},
            {"role": "assistant", "content": natural_proof}
        ]
    )
    
    print(f"{repair_prompt}\n{natural_proof}\n{formalized_proof}")