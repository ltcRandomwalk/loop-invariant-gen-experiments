import argparse
import sys
import os
import json
from datetime import datetime
import multiprocessing
from functools import partial
from StepProofVerifier.StepProofVerifier import StepProofVerifier
import time
import traceback

def process_benchmark(benchmark, repeat_time, log_dir, no_preprocess):
    try:
        # 创建安全的目录名称
        safe_name = benchmark.replace("../", "").replace("/", "__").replace(".c", "")
        bench_log_dir = os.path.join(log_dir, safe_name)
        os.makedirs(bench_log_dir, exist_ok=True)

        success_count = 0
        once_success_count = 0
        total_success_iters = 0

        data = []

        for i in range(repeat_time):
            run_log_path = os.path.join(bench_log_dir, f"run_{i}.txt")
            
            # 运行验证器
            verifier = StepProofVerifier(benchmark)

            start_time = time.time()
            success, invariant_block, iters, input_token, output_token, success_by_bmc = verifier.runWithShortenTokens(log_path=run_log_path, no_preprocess=no_preprocess)
            end_time = time.time()

            

            data.append({
                "isSuccess": success,
                "invariant_block": invariant_block,
                "iters": iters,
                "time": end_time - start_time,
                "input_token": input_token,
                "output_token": output_token,
                "success_by_bmc": success_by_bmc
            })

            # 写入运行结果到独立日志文件
            with open(run_log_path, 'a') as f:
                f.write(f"\nResult:\nSuccess: {success}\nInvariant Block: {invariant_block}\nIterations: {iters}\n")

            if success:
                success_count += 1
                total_success_iters += iters
                if iters == 0:
                    once_success_count += 1

        # 计算统计指标
        avg_iters = total_success_iters / success_count if success_count else 0
        valid_runs = success_count - once_success_count
        avg_without_once = total_success_iters / valid_runs if valid_runs > 0 else 0

        results =  {
            "benchmark": benchmark,
            "valid": True,
            "success_rate": f"{success_count}/{repeat_time}",
            "once_success_count": once_success_count,
            "average_success_iters": avg_iters,
            "average_success_iters_without_once": avg_without_once,
            "detailed_data": data
        }
    except Exception as e:
        results =  {
            "benchmark": benchmark,
            "valid": False,
            "exception": repr(e),
            "traceback": traceback.format_exc()
        }
    
    with open(os.path.join(bench_log_dir, "results.json"), 'w') as f:
        json.dump(results, f, indent=2)
    
    return results

def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench-file", required=True, help="File containing benchmark paths")
    parser.add_argument("--repeat-time", type=int, default=5, help="Number of repetitions per benchmark")
    parser.add_argument("--no-preprocess", help="Do not preprocess the benchmarks", action="store_true")
    return parser.parse_args(args)

if __name__ == "__main__":
    args = parse_args(sys.argv[1:])

    # 创建日志目录
    timestamp = datetime.now().strftime("%m_%d_%H_%M_%S")
    log_dir = f"logs/parallel_logs_{timestamp}"
    os.makedirs(log_dir, exist_ok=True)

    # 读取benchmark列表
    with open(args.bench_file) as f:
        benchmarks = [line.strip() for line in f.readlines()]

    benchmarks = [ f"../final_benchmarks/{benchmark}" for benchmark in benchmarks ]

    print(f"Loaded {len(benchmarks)} benchmarks, starting parallel processing...")

    # 创建进程池并行处理
    with multiprocessing.Pool(processes=32) as pool:
        worker = partial(process_benchmark, repeat_time=args.repeat_time, log_dir=log_dir, no_preprocess=args.no_preprocess)
        results = pool.map(worker, benchmarks)

    # 保存最终结果
    result_path = os.path.join(log_dir, "aggregated_results.json")
    with open(result_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Processing completed. Results saved to {result_path}")
    print(f"Individual benchmark logs available in: {log_dir}")