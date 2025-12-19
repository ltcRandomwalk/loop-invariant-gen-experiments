import argparse
import sys
from StepProofVerifier.StepProofVerifier import StepProofVerifier
from loopy import Loopy
from datetime import datetime
import os
import json


def parse_args(args):
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--bench-file",
        help="Specify all the benchmarks in this file.",
        default="",
        type=str
    )

    parser.add_argument(
        "--repeat-time",
        help="The repeat time for each benchmark.",
        default=5,
        type=int
    )


    return parser.parse_args(args)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])

    if not args.bench_file:
        print("No benchmark files!")
        exit(0)

    nowtime = datetime.now().strftime(f"%m_%d_%H_%M_%S")

    log_dir = f"logs/StepProof_{nowtime}"
    os.mkdir(log_dir)

    log_file_path = os.path.join(log_dir, "log.txt")
    log_file = open(log_file_path, 'w')
    json_log_file_path = os.path.join(log_dir, "result.json")
    json_log_file = open(json_log_file_path, 'w')

    with open(args.bench_file, 'r') as f:
        benchmark_files = [ benchmark.strip() for benchmark in f.readlines() ]
    
    benchmark_num = len(benchmark_files)
    log_file.write(f"Found {benchmark_num} benchmarks!\n")
    
    for benchmark in benchmark_files:
        try: 
            benchmark = benchmark.replace("../", "")
            success_count = 0
            total_success_iters = 0
            once_success_count = 0
            

            for i in range(args.repeat_time):
                log_file.write(f"Running benchmark {benchmark} for time {i+1}...\n\n")
                verifier = StepProofVerifier(benchmark)
                __success, invariant_block, iters = verifier.run(log_path=f'{os.path.join(log_dir, benchmark.replace("../", "").replace("/", "__").replace(".c", ".txt"))}_{i}')
                if __success:
                    success_count += 1
                    total_success_iters += iters
                    if iters == 0:
                        once_success_count += 1
                log_file.write(f"Result:\n{__success}\n{invariant_block}\niters:{iters}\n\n")
                log_file.flush()
            
            json_logs = {
                "benchmark": benchmark,
                "valid": True,
                "success_rate": f"{success_count}/{args.repeat_time}",
                "once_success_count": once_success_count,
                "average_success_iters": 0 if success_count == 0 else total_success_iters / success_count,
                "average_success_iters_without_once": 0 if total_success_iters == 0 else total_success_iters / (success_count - once_success_count)
            }

            
        except Exception as e:
            json_logs = {
                "benchmark": benchmark,
                "valid": False,
                "exception": repr(e)
            }

        json_log_file.write(json.dumps(json_logs, indent=4, ensure_ascii=False))
        json_log_file.write(", \n")
        json_log_file.flush()


    

   

