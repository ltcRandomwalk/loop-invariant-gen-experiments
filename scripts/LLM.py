from openai import OpenAI
import os
from typing import Dict, Tuple, List

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
            base_url='https://api.openai-proxy.org/v1',
            api_key=os.getenv("CLOSEAI_API_KEY"),
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

    def get_response_by_json(self, messages: List, input_token_list=[], output_token_list=[]) -> Tuple[str, List]:
        client = OpenAI(
            base_url='https://yunwu.ai/v1',
            api_key=os.getenv("YUNWU_API_KEY"),
        )

        chat_completion = client.chat.completions.create(
            messages=messages,
            model=self.model,
        )

        

        response = chat_completion.choices[0].message.content
        input_tokens = chat_completion.usage.prompt_tokens
        output_tokens = chat_completion.usage.completion_tokens

       

        input_token_list.append(input_tokens)
        output_token_list.append(output_tokens)
        #print(input_tokens, output_tokens, chat_completion.usage.total_tokens, chat_completion.usage.prompt_tokens_details)
        chat_history = messages + [ {"role": "assistant", "content": response}]
        #print(chat_completion)
        
        return response, chat_history
    
    def get_response_by_prompt(self, prompt, chat_history=[], input_token_list=[], output_token_list=[]) -> Tuple[str, List]:
        messages = chat_history + [ {"role": "user", "content": prompt} ]
        return self.get_response_by_json(messages, input_token_list, output_token_list)
    

