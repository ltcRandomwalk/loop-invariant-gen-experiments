from openai import OpenAI
import os
from typing import Dict, Tuple, List
import random
import time

class LLM():
    def __init__(self):
        pass

    def get_response_by_json(self, messages):
        raise NotImplementedError
    
    def get_response_by_prompt(self, prompt):
        raise NotImplementedError
    
    def parse_session(self, chat_history):
        chatting = ""
        for history in chat_history:
            chatting += f"-----------Role: {history['role']}-----------\n"
            chatting += f"{history['content']}\n"
        return chatting

class CloseAILLM(LLM):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def get_response_by_json(self, messages: List) -> Tuple[str, List]:
        client = OpenAI(
            base_url='https://yunwu.ai/v1',
            api_key=os.getenv("YUNWU_API_KEY"),
        )

        chat_completion = client.chat.completions.create(
            messages=messages,
            model=self.model,
        )

        response = chat_completion.choices[0].message.content
        chat_history = messages + [ {"role": "assistant", "content": response}]
        
        return response, chat_history
    
    def get_response_by_prompt(self, prompt, chat_history=[]) -> Tuple[str, List]:
        messages = chat_history + [ {"role": "user", "content": prompt} ]
        return self.get_response_by_json(messages)
    

class XMCPLLM(LLM):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def parse_streaming_output(self, chat_completion):
        reasoning_content = ""
        content = ""
        input_tokens, output_tokens = 0, 0
        #print(chat_completion)
        for chunk in chat_completion:
            #print(chunk)
            if chunk.choices and hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content:
                reasoning_content += chunk.choices[0].delta.reasoning_content
            elif chunk.choices and hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                content += chunk.choices[0].delta.content
            elif hasattr(chunk, 'usage') and chunk.usage:
                input_tokens = chunk.usage.prompt_tokens
                output_tokens = chunk.usage.completion_tokens
        return reasoning_content, content, input_tokens, output_tokens


    def get_response_by_json(self, messages: List, input_token_list=[], output_token_list=[]) -> Tuple[str, List]:
        client = OpenAI(
            base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
            api_key=os.getenv("ALI_API_KEY"),
        )

        while True:
            try:
                chat_completion = client.chat.completions.create(
                    messages=messages,
                    model=self.model,
                    extra_body={"enable_reasoning": True},
                    stream=True,
                    stream_options={"include_usage": True}
                )
                break
            except Exception as e:
                print(repr(e))
                time.sleep(random.random() * 10)
                continue



        reasoning_content, response, input_tokens, output_tokens = self.parse_streaming_output(chat_completion)

        input_token_list.append(input_tokens)
        output_token_list.append(output_tokens)
        #print(input_tokens, output_tokens, chat_completion.usage.total_tokens, chat_completion.usage.prompt_tokens_details)
        chat_history = messages + [ {"role": "assistant", "content": response}]
        #print(reasoning_content)
        #print(response)
        #print(input_tokens, output_tokens)
        #print(chat_completion)

        
        return response, chat_history
    
    def get_response_by_prompt(self, prompt, chat_history=[], input_token_list=[], output_token_list=[]) -> Tuple[str, List]:
        messages = chat_history + [ {"role": "user", "content": prompt} ]
        return self.get_response_by_json(messages, input_token_list, output_token_list)
    

if __name__ == "__main__":
    llm = CloseAILLM("gpt-4o-2024-11-20")

    user1 = """
int main() {
    int a;
    int j;
    int m;

    //pre-condition
    a = 0;
    assume(m > 0);
    j = 1;

    //loop-body
    while (j <= m) {
        if (unknown())
            a++;
        else
            a--;
        j++;
    }

    //post-condition
    assert(a >= -m && a <= m);
}

Please analyze the above C code and verify the assertions in it.
In order to verify the assertions, you need to propose loop invariants for the loop in the program. A loop invariant is a property that satisfies the following conditions:
(1) Holds before the loop, regardless of the loop condition.
(2) Holds after each iteration of the loop, including the termination of the loop.

Besides, the loop invariant should be helpful to verify the assertions.

The loop invariant should strictly follow the grammar of C logical expressions. It can contain "&&", "||" and "!". Besides, the loop invariant should only contain variables that are declared in the program. It cannot contain any function or any other notations. Summarize the loop invariants in the following format in the end of your response:

```c 
/*@ 
    loop invariant i1: ...;
    loop invariant i2: ...;
    ...
*/

```

Don't explain.
    """

    assistant1 = """
/*@
    loop invariant i1: a >= -(j - 1) && a <= (j - 1);
    loop invariant i2: j >= 1;
    loop invariant i3: m > 0;
*/

    """

    user2prime = """
Your loop invarinats are not sufficient to prove the final assertion -m <= a <= m. Please fix your loop invariants.

The loop invariant should strictly follow the grammar of C logical expressions. It can contain "&&", "||" and "!". Besides, the loop invariant should only contain variables that are declared in the program. It cannot contain any function or any other notations. Summarize the fixed loop invariants in the following format in the end of your response:

```c 
/*@ 
    loop invariant i1: ...;
    loop invariant i2: ...;
    ...
*/

```

Don't explain.
    """

    user2 = """
Please prove the assertion a >= -m && a <= m using your proposed loop invariants step by step. 
Specifically, you should prove the following goal: {{I /\ not B}} ==> Q, where I is the loop invariants you proposed, B is the loop condition, and Q is the assertion.
You should prove the goal in the following steps: First, list the initial conditions. In this case, the initial conditions are conditions when the program executes to the assertion. This can be a loop invariant, or a branch condition, etc.. Then, prove the assertion a >= -m && a <= m step by step.
    """

    assistant2 = """
Here is the structured proof for the assertion `a >= -m && a <= m` using the proposed loop invariants.

---

### **[Initial]**
The conditions to prove `a >= -m && a <= m` once the program executes to the assertion are:

1. **Loop Invariants**:
   - **Invariant i1:** `a >= -(j - 1) && a <= (j - 1)`
   - **Invariant i2:** `j >= 1`
   - **Invariant i3:** `m > 0`

2. **Loop Exit Condition** (`not B`):
   - The loop condition is `B: j <= m`. The program exits the loop when `j > m`, so `not B` is `j > m`.

---

### **[Proof]**

We need to prove `{I /\ not B} ==> Q`, where:
- **I**: Loop invariants (`i1`, `i2`, `i3`)
- **not B**: Loop exit condition (`j > m`)
- **Q**: Final assertion (`a >= -m && a <= m`)

#### **[STEP 1: Derived Range of `a` from i1 When Loop Terminates]**
- From invariant **i1**: `a >= -(j - 1) && a <= (j - 1)`
  - At the end of the loop, `not B` implies `j > m`.
  - Substituting `j = m + 1`:
    - At termination, `a >= -(m + 1 - 1) && a <= (m + 1 - 1)`
    - Simplifies to: `a >= -m && a <= m`.

#### **[STEP 2: Validity of `m > 0` at Program Termination]**
- From invariant **i3**: `m > 0`
  - The value of `m` is never modified inside the loop.
  - Thus, `m > 0` is valid at and after the termination of the loop.
  - This ensures that the bounds `-m` and `m` are well-defined.

#### **[STEP 3: Combine Results to Prove the Assertion]**
- From **STEP 1**: At termination (`j = m + 1`), `a >= -m && a <= m` holds directly by substitution into **i1**.
- From **STEP 2**: Since `m > 0`, the bounds `-m` and `m` are correct and consistent.
- Therefore, the assertion `a >= -m && a <= m` holds.

---

### **[Conclusion]**

We have proven that `{I /\ not B} ==> Q`. Specifically:
- When the program exits the loop (`j > m`) and all loop invariants hold, the assertion `a >= -m && a <= m` is valid. Thus, the assertion is verified.
    """

    user3 = """
In your proof of STEP 1: Derived Range of `a` from i1 When Loop Terminates, "At loop termination, j is m + 1." is wrong. This is because the condition (j > m) cannot derive (j == m + 1).

This indicates that the loop invariants you proposed are all correct, but they are not sufficient to verify the assertion a >= -m && a <= m. 

Please fix your loop invariants in the following steps:
First, based on the error in your proof, analyze why the loop invariant are not sufficient to verify the assertion a >= -m && a <= m.
Then, from your analysis, carefully think about the verification problem again. Every time you propose a loop invariant, note that do not make the same mistake again.

The loop invariant should strictly follow the grammar of C logical expressions. It can contain "&&", "||" and "!". Besides, the loop invariant should only contain variables that are declared in the program. It cannot contain any function or any other notations. Summarize the fixed loop invariants in the following format in the end of your response:

```c 
/*@ 
    loop invariant i1: ...;
    loop invariant i2: ...;
    ...
*/
    """

    json_input = [
        {"role": "user", "content": user1},
        {"role": "assistant", "content": assistant1},
        {"role": "user", "content": user2},
        {"role": "assistant", "content": assistant2},
        {"role": "user", "content": user3},
      
    ]

    response, chat_history = llm.get_response_by_json(json_input)
    chatting = llm.parse_session(chat_history)
    print(chatting)


   

    
    