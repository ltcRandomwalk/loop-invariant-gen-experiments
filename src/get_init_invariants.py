from loopy_llm import LLM, Prompt
from frama_c import FramaCBenchmark, FramaCChecker
from openai import OpenAI
import os

import re
from smt_solver import verify_implication
import json
import sys

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
        model="chatgpt-4o-latest",
    )
    
    return chat_completion.choices[0].message.content
    

def check_loop_invariants(benchmark_file, invariant_answer):
    benchmark = FramaCBenchmark(benchmark_file, benchmark_features, False)
    
    codeblock_filter = lambda x: checker.has_invariant(x) or (
        checker.has_function_contract(x)
        if "multiple_methods" in benchmark_features
        else False
    )
    
    code = benchmark.get_code(benchmark_file)
    
    annotation_blocks = extract_custom_strings(invariant_answer)[0]
    
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
    Please print the loop invariants as C logical expressions. You can use "&&" or "||" to represent conjunction or disjunction. If a variable is not initialized, it can be any legal value. Do not use variables or functions that are not defined in the program. Do not change the original program and assertion. 
    Print the loop invariants in the following format:

    /*@
        loop invariant i1: ...;
        loop invariant i2: ...;
        ...
    */
    """
    
    initial_invariant = get_closeai_answer([{"role": "user", "content": prompt}])
    
    return check_loop_invariants(benchmark_file, initial_invariant)

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
        
        pattern = r'Assertion (.*?): Unproven'
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
    
    In particular, you should prove that the loop invariant holds before the loop. You should first list the known conditions, and from the conditions, prove that the loop invariant holds before the loop step by step.
    The conditions in this case are the program states before the loop. Note that, if a variable is not initialized, you should not make any assumption on it.
    
    You should first prove the goal in natural language, and then formalize the key steps of your proof with a json file. The format of the json file is as follow:
    ```json
    {{
        "Step 1: <Proof Goal>": ["<Condition> ==> <Conclusion>", "<Condition> ==> <Conclusion>", ...]
        "Step 2: <Proof Goal>": ["<Condition> ==> <Conclusion>", "<Condition> ==> <Conclusion>", ...]
        ...
    }}
    ```
    For the blank <Proof Goal>, briefly summary the proof goal in natural language. The condition and conclusion should be **pure C logical expression**, which strictly follows the grammar of C logical expression. The condition should be sufficient to derive the conclusion. Do not add comments in the json file.
    
    
    
    
    """
    
    response = get_closeai_answer([{"role": "user", "content": prompt}])
    return prompt, response

def preservation_feedback(code, annotation_block, loop_invariant):
    prompt = f"""
    {code}
    
    Please analyze the above C code and verify the assertions in it. 
    In order to verify the assertion, you need to propose loop invariants for the loop in the program. A loop invariant is a property that holds **before the loop**, and **after each iteration of the loop**. Besides, the loop invariants should be helpful to verify the assertion.
    
    In your previous answer, the loop invariants you proposed are:
    {annotation_block}
    
    The preservation of the loop invariant {loop_invariant} cannot be verified. In order to help you correct the mistake, I will ask you to give a proof of the preservation of this loop invariant {loop_invariant}.
    
    In particular, you should prove that if all the loop invariants hold before a loop, then after a loop, the loop invariant {loop_invariant} still holds. 
    You should first list the known conditions. The known conditions are all the loop invariants you proposed, and the condition that enters the loop.
    From the conditions, you prove the loop invariant {loop_invariant} still holds after the loop. 
    
    You should first prove the goal in natural language, and then formalize the key steps of your proof with a json file. The format of the json file is as follow:
    ```json
    {{
        "Step 1: <Proof Goal>": ["<Condition> ==> <Conclusion>", "<Condition> ==> <Conclusion>", ...]
        "Step 2: <Proof Goal>": ["<Condition> ==> <Conclusion>", "<Condition> ==> <Conclusion>", ...]
        ...
    }}
    ```
    For the blank <Proof Goal>, briefly summary the proof goal in natural language. The condition and conclusion should be **pure C logical expression**, which strictly follows the grammar of C logical expression. The condition should be sufficient to derive the conclusion. Do not add comments in the json file.
    
    
    """
    
    response = get_closeai_answer([{"role": "user", "content": prompt}])
    return prompt, response


def assertion_feedback(code, annotation_block, assertion):
    prompt = f"""
    {code}
    
    Please analyze the above C code and verify the assertions in it. 
    In order to verify the assertion, you need to propose loop invariants for the loop in the program. A loop invariant is a property that holds **before the loop**, and **after each iteration of the loop**. Besides, the loop invariants should be helpful to verify the assertion.
    
    In your previous answer, the loop invariants you proposed are:
    {annotation_block}
    
    The loop invariants are all correct, but they are not sufficient to prove the assertion. In order to help you correct the mistake, I will ask you to give a proof of the assertion using the loop invariants.
    
    In particular, you should prove that if all the loop invariants hold after the exit of the loop, then the assertion {assertion} holds.
    You should first list the known conditions. The known conditions are all the loop invariants you proposed, and the condition that exits the loop.
    From the conditions, you prove the assertion {assertion} holds.
    
    You should first prove the goal in natural language, and then formalize the key steps of your proof with a json file. The format of the json file is as follow:
    ```json
    {{
        "Step 1: <Proof Goal>": ["<Condition> ==> <Conclusion>", "<Condition> ==> <Conclusion>", ...]
        "Step 2: <Proof Goal>": ["<Condition> ==> <Conclusion>", "<Condition> ==> <Conclusion>", ...]
        ...
    }}
    ```
    For the blank <Proof Goal>, briefly summary the proof goal in natural language. The condition and conclusion should be **pure C logical expression**, which strictly follows the grammar of C logical expression. The condition should be sufficient to derive the conclusion. Do not add comments in the json file.
    
    
    """
    
    response = get_closeai_answer([{"role": "user", "content": prompt}])
    return prompt, response


def get_formalized_proof(previous_conversation):
    prompt = f"""
    Now, please formalize each step of your proof. In particular, for each step, you should represent your proof in a list of implications.
    Answer the question in the the following json format. For the blank <Proof Goal>, briefly summary the proof goal in natural language. 
    For each implication, represent it in the format "c1 ==> c2". c1 and c2 should be **pure C logical expressions**, without any natural languange in it. c1 can derive c2 without any other conditions.
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
    
    return prompt, get_closeai_answer(msgs)

def check_proof(proof_response):
    try:
        json_proof = re.findall(r'(?<=```json\s).*?(?=```)', proof_response, re.DOTALL)[0]
        json_proof = json.loads(json_proof)
    except Exception as e:
        return []
    
    wrong_implications = []
    for step, implications in json_proof.items():
        for implication in implications:
            #P_c, Q_c = implication["Condition"], implication["Conclusion"]
            try:
                if "==>" not in implication:
                    continue 
                P_c, Q_c = implication.split("==>")
                is_valid, model = verify_implication(P_c, Q_c)
                if not is_valid:
                    wrong_implications.append((step, implication))
            except Exception as e:
                print(implication, repr(e))
    return wrong_implications

def get_repaired_invariants(previous_conversation, wrong_implications, loop_invariant, fail_reason):
    prompt = "In your proof, there are the following errors:\n"
    
    errors = ""
    for step, implication in wrong_implications:
        #P_c, Q_c = implication["Condition"], implication["Conclusion"]
        assert( "==>" in implication )
        P_c, Q_c = implication.split("==>")
        errors += f"In {step}, {P_c} cannot derive {Q_c}.\n"
    prompt += errors 
    
    if fail_reason == "establishment":
        prompt += f"Based on the error, please carefully think about your thinking process of proposing the loop invariant and analyze why your previous loop invariant {loop_invariant} is not established (hold before the loop). Then, verify the program assertion again."
    elif fail_reason == "preservation":
        prompt += f"Based on the error, please carefully think about your thinking process of proposing the loop invariant and analyze why your previous loop invariant {loop_invariant} is not preserved. Then, verify the program assertion again."
    else:
        prompt += f"Based on the error, please carefully think about your thinking process of proposing the loop invariant and analyze why the loop invariants are not sufficient to prove the assertion. Then, verify the program assertion again."
    
    prompt += """
     That is, you should first propose loop invariants, and verify the final assertion based on them.  Do not make any change on the original program and assertion. 
In the end, print the fixed loop invariants in the following format, where each loop invariant should be a C logical expression.
    /*@
        loop invariant i1: ...;
        loop invariant i2: ...;
        ...
    */
    """
    
    msgs = previous_conversation + [
        {"role": "user", "content": prompt}
    ]
    
    return prompt, get_closeai_answer(msgs)
    


if __name__ == "__main__":
    benchmark_file = sys.argv[1]
    outputFileName = "_".join(benchmark_file.split("/")[3:])
    outputFile = open(os.path.join("/home/tcli/loop-invariant-gen-experiments/logs", outputFileName + '.txt'), 'w')
    sys.stdout = outputFile
    __success, annotation_blocks, checker_message = get_init_invariants(benchmark_file)
    benchmark = FramaCBenchmark(benchmark_file, benchmark_features, False)
    code = benchmark.get_code(benchmark_file)
    print(__success)
    print(checker_message)
    if  __success:
        exit(0)
        
        
    iters = 0
    while iters < 10:
        iters += 1
        print(f"================================Iteration: {iters}================================")
        not_established_invariants, not_preserved_invariants, not_valid_assertion = parse_framac_output(checker_message)
        print(not_established_invariants, not_preserved_invariants, not_valid_assertion)
        
        if not_established_invariants:
            proof_prompt, proof_response = establishment_feedback(code, annotation_blocks, not_established_invariants[0])
            prepared_invariant = not_established_invariants[0]
            reason = "establishment"
        elif not_preserved_invariants:
            proof_prompt, proof_response = preservation_feedback(code, annotation_blocks, not_preserved_invariants[0])
            prepared_invariant = not_preserved_invariants[0]
            reason = "preservation"
        elif not_valid_assertion:
            proof_prompt, proof_response = assertion_feedback(code, annotation_blocks, not_valid_assertion[0])
            prepared_invariant = not_valid_assertion[0]
            reason = "assertion"
        else:
            print("Success!")
            exit(0)
        
        
        print(f"================================Iteration: {iters} - Proof ================================")
        print(f"{proof_prompt}\n\n{proof_response}")
        
        wrong_implications = check_proof(proof_response)
        print(wrong_implications)
        if not wrong_implications:
            continue
        
        repaired_prompt, repaired_response = get_repaired_invariants([
            {"role": "user", "content": proof_prompt},
            {"role": "assistant", "content": proof_response}
        ], wrong_implications, prepared_invariant, reason)
        
        print(f"================================Iteration: {iters} - Repair ================================")
        
        print(f"{repaired_prompt}\n\n{repaired_response}")
        
        __success, annotation_blocks, checker_message = check_loop_invariants(benchmark_file, repaired_response)
        print(__success)
        print(checker_message)
    outputFile.close()
    
        
    
        
    
        
    
    
    