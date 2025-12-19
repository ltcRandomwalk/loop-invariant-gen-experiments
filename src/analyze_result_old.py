import json
import os
import sys

if __name__ == "__main__":
    result_file = sys.argv[1]

    f = open(result_file, 'r')
    results = json.loads('['+f.read().strip().strip(',')+']')

    benchmark_count = len(results)

    success_count = 0
    can_once_success_count = 0
    can_repair_count = 0

    average_success_rate = 0
    average_success_rate_without_once = 0
    average_success_iters = 0
    average_success_iters_without_once = 0

    all_repair_count = 0

    total_success_by_our_method = 0
    total_once_success = 0

    valid_benchmark_count = 0
    
    for result in results:
        if not result["valid"]:
            continue
        valid_benchmark_count += 1
        success_try, total_try = [ int(_) for _ in result['success_rate'].split('/') ]
        __success = False
        if success_try > 0:
            success_count += 1
            __success = True
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

    messages = f"""
Total benchmark: {benchmark_count}
Valid benchmark: {valid_benchmark_count}
# Success benchmarks: {success_count}
# Benchmarks all success in one iter: {success_count - can_repair_count}
# Benchmarks can success by feedback: {can_repair_count}
# Benchmarks all success by feedback: {all_repair_count}

Average success rate: {success_count / valid_benchmark_count}
Average success iters: {average_success_iters / success_count}
Average success iters without once success: {average_success_iters_without_once / success_count}

Total success by our method : {total_success_by_our_method}
Total once success: {total_once_success}
    """

    print(messages)
