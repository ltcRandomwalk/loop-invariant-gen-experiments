import os
import sys
import json

loris_result_file = ""
lam4inv_result_file = ""
original_benchmark_file = "/home/tcli/loop-invariant-gen-experiments/experiments/finalbenchmark.txt"




original_benchmarks = []
with open(original_benchmark_file, 'r') as f:
    for line in f.readlines():
        original_benchmarks.append("../final_benchmarks/"+line.strip())


exist_benchmarks = set()

f = open(loris_result_file, 'r')
results = json.loads(f.read().strip().strip(','))

benchmark_count = len(results)

valid_benchmark_count = 0

success_count = 0
can_once_success_count = 0
can_repair_count = 0

average_success_rate = 0
average_success_rate_without_once = 0
average_success_iters = 0
average_success_iters_without_once = 0

success_iters_list = []
success_iters_without_once_list = []

all_repair_count = 0

total_success_by_our_method = 0
total_once_success = 0
total_success_try = 0

total_success_time = 0.0

loris_solved_benchmarks = set()
lam4inv_solved_benchmarks = set()

input_token_list = []
output_token_list = []

detail_success_list = []

for result in results:
    exist_benchmarks.add(result["benchmark"])
    if result["benchmark"] not in original_benchmarks:
        continue
    if not result["valid"]:
        continue
    valid_benchmark_count += 1
    
    success_try, total_try = [ int(_) for _ in result['success_rate'].split('/') ]
    total_success_try += success_try

    detail_success = []
    for data in result["detailed_data"]:
        if data["isSuccess"]:
            detail_success.append(1)
            total_success_time += data["time"]
            iters = data["iters"]
            input_token_list.append(data["input_token"])
            output_token_list.append(data["output_token"])
            success_iters_list.append(iters)
            if iters > 0:
                success_iters_without_once_list.append(iters)
        else:
            detail_success.append(0)
    detail_success_list.append(detail_success)

    __success = False
    if success_try > 0:
        success_count += 1
        __success = True
        loris_solved_benchmarks.add(result["benchmark"])
    once_success = result['once_success_count']
    if success_try > once_success:
        can_repair_count += 1

    total_success_by_our_method += success_try - once_success
    total_once_success += once_success
    
    if success_try != 0 and once_success == 0:
        all_repair_count += 1

    if once_success > 0:
        can_once_success_count += 1

    if __success:
        average_success_iters += result['average_success_iters']
    
    if result['average_success_iters_without_once'] > 0:
        average_success_iters_without_once += result['average_success_iters_without_once']


success_number_list = []
for i in range(5):
    success_number_list.append(sum([detail_success[i] for detail_success in detail_success_list]))

messages = f"""
Total benchmark: {len(original_benchmarks)}
Valid benchmark: {valid_benchmark_count}
# Success benchmarks: {success_count}
# Benchmarks all success in one iter: {success_count - can_repair_count}
# Benchmarks can success by feedback: {can_repair_count}
# Benchmarks all success by feedback: {all_repair_count}

Average success rate: {(total_success_by_our_method + total_once_success) / (len(original_benchmarks)*5)}
Average success iters: { sum(success_iters_list) / len(success_iters_list) }
Average success iters without once success: { sum(success_iters_without_once_list) / len(success_iters_without_once_list) }
Average success time cost: {total_success_time / total_success_try}

Total success by our method : {total_success_by_our_method}
Total once success: {total_once_success}

# Average Input token: {sum(input_token_list) / len(input_token_list)}
# Average Output token: {sum(output_token_list) / len(output_token_list)}

# Average success number: {sum(success_number_list) / len(success_number_list)}
"""

missing_benchmarks = open("/home/tcli/loop-invariant-gen-experiments/experiments/missingbenchmark.txt", 'w')
for benchmark in original_benchmarks:
    if benchmark not in exist_benchmarks:
        messages += f"Missing benchmark: {benchmark}\n"
        missing_benchmarks.write(benchmark.replace("../final_benchmarks/", "") + "\n")


missing_benchmarks.close()
print(messages)
