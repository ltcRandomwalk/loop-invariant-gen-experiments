from LLM import XMCPLLM
from pathlib import Path


with open('/home/tcli/loop-invariant-gen-experiments/experiments/transformrest.txt', 'r') as f:
    benchmarks = f.read().strip().split('\n')

for benchmark in benchmarks:
    with open(benchmark, 'r') as f:
        code = f.read()
    
    llm = XMCPLLM("yunwu/gpt-4.1-2025-04-14")

    with open("transform.txt", 'r') as f:
        prompt = f.read()

    prompt += f"""
    The original program is:

{code}

Please transform the format of the program into the one I want. Output just the result program, do not explain. Do not output ```c and ``` as well.
    """
    
    response, _ = llm.get_response_by_prompt(prompt)
    
    new_benchmark = benchmark.replace("dataset", "new_benchmark")

    file_path = Path(new_benchmark)

    # 创建父目录（如果不存在）
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # 创建并写入文件
    file_path.write_text(response)

    print(f"Finish processing {new_benchmark}")