import datetime
import json
import multiprocessing
import os
import random
import re
import traceback
import warnings
from copy import deepcopy

import yaml

from llm_utils import Logger
from loopy_factory import LoopyFactory
from loopy_llm import LLM, Prompt


class Loopy:
    def __init__(
        self,
        model: str = "gpt-4",
        debug: bool = False,
        log_path: str = "",
        arg_params: dict = {},
    ):
        self.model = model
        self.debug = debug
        self.log_path = log_path
        self.benchmark_features = ""
        self.arg_params = arg_params
        self.benchmark = None
        self.checker = None

    def set_config(self, config_file, no_preprocess=False):
        config = yaml.load(open(config_file, "r"), Loader=yaml.FullLoader)

        self.arg_params = {"cli_args": self.arg_params, "config_file_args": config}

        if not "benchmarks" in config:
            raise Exception("No benchmarks file specified in config file")
        Logger.log_info(f"Using input file: {config['benchmarks']}")
        benchmarks = config["benchmarks"]

        if "benchmark_features" in config:
            self.benchmark_features = config["benchmark_features"]
        else:
            Logger.log_info(
                "Setting benchmark features to default: one_loop one_method"
            )
            self.benchmark_features = "one_loop one_method"

        if not "model" in config:
            raise Exception("No model specified config file")
        Logger.log_info(f"Using model: {config['model']}")
        self.model = config["model"]

        if "checker" not in config:
            raise Exception("No checker specified in config file")

        if config["checker"] == "boogie":
            warnings.warn(
                "Boogie checker integration is experimental, use Frama-C instead",
                UserWarning,
            )
        loopyfact = LoopyFactory(config["checker"])
        self.benchmark = loopyfact.get_benchmark(benchmarks, self.benchmark_features, no_preprocess)
        self.checker = loopyfact.get_checker()

        if "checker_timeout" in config:
            self.checker.timeout = config["checker_timeout"]
        else:
            self.checker.timeout = 3

        Logger.log_info(
            f"Using checker: {config['checker']}, with timeout: {self.checker.timeout}"
        )

        if "debug" in config:
            self.debug = config["debug"]

        self.llm = LLM(
            self.model,
            self.debug,
        )

        Logger.log_info("Validating input files")
        self.benchmark.validate_inputs(no_preprocess)
        Logger.log_info(f"Found {len(self.benchmark.input_file_paths)} valid benchmarks")

        return self

    @staticmethod
    def write_benchmark_log(log_folder, benchmark_filename, json_log):
        Logger.log_info(f"Writing log for {benchmark_filename}")
        with open(
            os.path.join(
                log_folder,
                benchmark_filename.replace(".c", ".json")
                .replace("../", "")
                .replace("/", "__"),
            ),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(json.dumps(json_log, indent=4, ensure_ascii=False))

    @staticmethod
    def shuffle(input_list):
        temp = deepcopy(input_list)
        random.shuffle(temp)
        return temp

    @staticmethod
    def run_parallel(inputs, func):
        assert len(inputs) <= 32

        pool = multiprocessing.Pool(processes=len(inputs))
        results = pool.map(func, inputs)
        pool.close()
        pool.join()
        return results

    @staticmethod
    def prune_wrapper(checker_input):
        checker = LoopyFactory("frama-c").get_checker()
        try:
            success, pruned_code, num_frama_c_calls = checker.houdini(
                checker_input,
                features="one_loop_one_method",
                use_json_dump_for_invariants=True,
            )
        except Exception as e:
            print(e)
            traceback.print_exc()
        return success

    @staticmethod
    def combine_and_prune_with_k(
        benchmark,
        n,
        k,
        shuffle_times=10,
        max_cores=16,
        combine_llm_output_lambda=None,
        features="one_loop_one_method",
    ):
        invariants_from_completions = [
            b["annotations"] for b in benchmark["completions"]
        ]

        if len(invariants_from_completions) < n:
            invariants_from_completions = invariants_from_completions + [
                "\nloop invariant \\false;\n"
                for _ in range(n - len(invariants_from_completions))
            ]

        random_permutations = [
            Loopy.shuffle(invariants_from_completions) for _ in range(shuffle_times)
        ]
        candidates = [rp[:k] for rp in random_permutations]
        candidate_inputs = [
            combine_llm_output_lambda(benchmark["benchmark_code"], candidate, features)
            for candidate in candidates
        ]

        max_m = (len(candidates) // max_cores) + 1
        pass_k_prune = 0.0
        for m in range(0, max_m):
            checker_inputs = candidate_inputs[m * max_cores : (m + 1) * max_cores]
            Logger.log_action(
                "Combine and Pruning",
                f"[Batch {m+1}/{max_m}]: {len(checker_inputs)} candidates in parallel, k={k}, File: {benchmark['file']}",
            )
            try:
                results = Loopy.run_parallel(checker_inputs, Loopy.prune_wrapper)
                pass_k_prune += sum(results)
                Logger.log_info(
                    f"[Batch {m+1}/{max_m}]: Combine and Prune with k = {pass_k_prune / len(results)} for k={k}, {len(checker_inputs)} parallel benchmarks, File: {benchmark['file']}"
                )
            except Exception as e:
                Logger.log_error(str(e))

        pass_k_prune = pass_k_prune / len(candidates)
        if pass_k_prune > 0.0:
            Logger.log_success(
                f"Combine and Prune with k = {pass_k_prune} for k={k}, {len(candidates)} benchmarks, File: {benchmark['file']}"
            )
        else:
            Logger.log_error(
                f"Combine and Prune with k = {pass_k_prune} for k={k}, {len(candidates)} benchmarks, File: {benchmark['file']}"
            )
        return pass_k_prune, checker_inputs

    def find_loop_invariants(
        self, max_benchmarks=1, start_index=0, prompt="with_nudges"
    ):
        if self.llm is None or self.benchmark is None or self.checker is None:
            raise Exception("Pipeline not initialized. Call load_config first.")

        log_json = []
        stats = {"success": [], "failure": [], "skipped": [], "total": 0}

        # create logs dir
        self.log_path = datetime.datetime.now().strftime(
            f"../logs/loopy_%Y_%m_%d_%H_%M_%S/"
        )
        if not os.path.exists(os.path.dirname(self.log_path)):
            os.makedirs(os.path.dirname(self.log_path))

        log_file = open(self.log_path + "final.json", "w", encoding="utf-8")

        sliced_benchmarks = self.benchmark.input_file_paths[
            start_index : start_index + max_benchmarks
        ]

        loopy_prompt = None
        if prompt == "with_nudges":
            loopy_prompt = Prompt(
                system_text_file="templates/simplified_system_message.txt",
                prompt_text_file="templates/simplified_prompt_with_nudges.txt",
                num_completions=5,
            )
        elif prompt == "without_nudges":
            loopy_prompt = Prompt(
                system_text_file="templates/simplified_system_message.txt",
                prompt_text_file="templates/simplified_prompt.txt",
                num_completions=5,
            )
        elif prompt == "arrays_simplified":
            loopy_prompt = Prompt(
                prompt_text_file="templates/simplified_prompt_arrays.txt",
                num_completions=5,
            )
        elif prompt == "arrays_without_nudges":
            loopy_prompt = Prompt(
                system_text_file="templates/array_system_message.txt",
                prompt_text_file="templates/simplified_prompt_with_nudges.txt",
                num_completions=8,
            )
        elif prompt == "arrays_with_nudges":
            loopy_prompt = Prompt(
                system_text_file="templates/array_system_message.txt",
                prompt_text_file="templates/array_prompt_with_nudges.txt",
                num_completions=8,
            )
        else:
            loopy_prompt = Prompt(
                system_text_file=None,
                prompt_text_file="templates/plain.txt",
                num_completions=5,
            )

        for benchmark_index, benchmark_file in enumerate(sliced_benchmarks):
            Logger.log_info(
                f"Running benchmark: {start_index + benchmark_index + 1}/{len(sliced_benchmarks)}"
            )

            instance_log_json = {
                "file": benchmark_file,
                "benchmark_code": self.benchmark.get_code(benchmark_file),
                "success": False,
            }
            success = False

            try:
                codeblock_filter = lambda x: self.checker.has_invariant(x) or (
                    self.checker.has_function_contract(x)
                    if "multiple_methods" in self.benchmark_features
                    else False
                )
                annotation_blocks, llm_outputs = self.llm.generate_annotation(
                    input={"code": self.benchmark.get_code(benchmark_file)},
                    prompt=loopy_prompt,
                    extraction_filter=codeblock_filter,
                )
                
                #print(annotation_blocks, llm_outputs)

                instance_log_json["llm_conversation"] = llm_outputs
                instance_log_json["annotation_blocks"] = annotation_blocks

                completions = []
                for block in annotation_blocks:
                    completion_json = {
                        "num_solver_calls": 0,
                    }
                    if len(block) == 2 and block[0] == (
                        "ERROR: Output does not contain at least 1 complete code block"
                    ):
                        completion_json["success"] = False
                        completion_json["num_solver_calls"] = 0
                        completion_json["llm_output"] = block[1]
                        completion_json["error"] = (
                            "Output does not contain at least 1 code block"
                        )
                        completions.append(completion_json)
                        continue

                    Logger.log_info(f"Checking completion {len(completions) + 1}")

                    checker_input_with_annotations = self.benchmark.combine_llm_outputs(
                        self.benchmark.get_code(benchmark_file),
                        [block],
                        self.benchmark_features,
                    )
                    completion_json["annotations"] = block
                    __success, checker_message = self.checker.check(
                        checker_input_with_annotations,
                        check_variant=False,
                        check_contracts=False,
                    )

                    completion_json["num_solver_calls"] += 1
                    completion_json["checker_output_for_annotations"] = __success
                    completion_json["checker_message_for_annotations"] = checker_message

                    if not __success:
                        try:
                            (
                                __success,
                                pruned_code,
                                num_frama_c_calls,
                            ) = self.checker.houdini(
                                checker_input_with_annotations,
                                check_variant=False,
                                check_contracts=False,
                            )

                            completion_json["num_solver_calls"] += num_frama_c_calls
                            completion_json["code_after_prune"] = pruned_code
                            completion_json["checker_output_after_prune"] = __success
                        except Exception as e:
                            completion_json["houdini_error"] = str(e)

                    success = __success or success

                    if __success:
                        Logger.log_success(
                            f"Completion {len(completions) + 1} is correct"
                        )
                    else:
                        Logger.log_error(
                            f"Completion {len(completions) + 1} is incorrect"
                        )

                    completions.append(completion_json)

                instance_log_json["completions"] = completions

                checker_input_with_combined_annotations = self.benchmark.combine_llm_outputs(
                    self.benchmark.get_code(benchmark_file),
                    [
                        block
                        for block in annotation_blocks
                        if not (
                            len(block) == 2
                            and block[0]
                            == (
                                "ERROR: Output does not contain at least 1 complete code block"
                            )
                        )
                    ],
                    self.benchmark_features,
                )

                Logger.log_info(
                    f"Checking combined annotations for benchmark: {start_index + benchmark_index + 1}/{len(sliced_benchmarks)}"
                )

                __success, checker_message = self.checker.check(
                    checker_input_with_combined_annotations,
                    check_variant=False,
                    check_contracts=False,
                )

                if __success:
                    Logger.log_success(
                        f"Combined annotations are correct for benchmark: {start_index + benchmark_index + 1}/{len(sliced_benchmarks)}"
                    )
                else:
                    Logger.log_error(
                        f"Combined annotations are incorrect for benchmark: {start_index + benchmark_index + 1}/{len(sliced_benchmarks)}"
                    )

                instance_log_json["checker_output_for_combined_annotations"] = __success
                instance_log_json["checker_message_for_combined_annotations"] = (
                    checker_message
                )
                instance_log_json["code_with_combined_annotations"] = (
                    checker_input_with_combined_annotations
                )

                success = __success or success

                if not __success:
                    Logger.log_info(
                        f"Houdini for combined annotations for benchmark: {start_index + benchmark_index + 1}/{len(sliced_benchmarks)}"
                    )

                    try:
                        (
                            __success,
                            pruned_code,
                            num_frama_c_calls,
                        ) = self.checker.houdini(
                            checker_input_with_combined_annotations,
                            check_variant=False,
                            check_contracts=False,
                        )

                        if __success:
                            Logger.log_success(
                                f"Houdini for combined annotations successful for benchmark: {start_index + benchmark_index + 1}/{len(sliced_benchmarks)}"
                            )
                        else:
                            Logger.log_error(
                                f"Houdini for combined annotations unsuccessful for benchmark: {start_index + benchmark_index + 1}/{len(sliced_benchmarks)}"
                            )

                        instance_log_json["combined_annotation_num_solver_calls"] = (
                            num_frama_c_calls + 1
                        )
                        instance_log_json["code_after_prune"] = pruned_code
                        instance_log_json["checker_output_after_prune"] = __success
                    except Exception as e:
                        instance_log_json["houdini_error"] = str(e)

                success = __success or success

                instance_log_json["success"] = success

            except Exception as e:
                Logger.log_error(traceback.format_exc())
                if isinstance(e, KeyboardInterrupt):
                    instance_log_json["success"] = False
                    stats["skipped"].append(benchmark_file)
                    break
                else:
                    instance_log_json["error"] = str(e)
                    instance_log_json["success"] = False
                    stats["skipped"].append(benchmark_file)
                    log_json.append(instance_log_json)
                    Loopy.write_benchmark_log(
                        self.log_path,
                        benchmark_file,
                        {"log": instance_log_json, "stats": stats},
                    )
                    continue

            if instance_log_json["success"]:
                Logger.log_success(
                    f"Benchmark {start_index + benchmark_index + 1}/{len(sliced_benchmarks)} succeeded"
                )
                stats["success"].append(benchmark_file)

            else:
                Logger.log_error(
                    f"Benchmark {start_index + benchmark_index + 1}/{len(sliced_benchmarks)} failed"
                )
                stats["failure"].append(benchmark_file)

            stats["total"] += 1
            stats["success_count"] = len(stats["success"])
            stats["failure_count"] = len(stats["failure"])
            stats["success_rate"] = (
                stats["success_count"] / stats["total"] if stats["total"] != 0 else 0
            )

            log_json.append(instance_log_json)

            Loopy.write_benchmark_log(
                self.log_path,
                benchmark_file,
                {"logs": instance_log_json, "stats": stats},
            )
        log_file.write(
            json.dumps(
                {"params": self.arg_params, "logs": log_json, "stats": stats},
                indent=4,
                ensure_ascii=False,
            )
        )
        log_file.close()

        return

    def repair_loop_invariants(
        self,
        max_benchmarks=1,
        start_index=0,
        input_log="",
        k=8,
        num_repairs=7,
    ):
        generation_log = json.load(open(input_log, "r", encoding="utf-8"))

        generation_log = generation_log["logs"][
            start_index : start_index + max_benchmarks
        ]

        if self.llm is None or self.benchmark is None or self.checker is None:
            raise Exception("Pipeline not initialized. Call load_config first.")

        log_json = []
        stats = {
            "gen_success": [],
            "repair_success": [],
            "repair_failure": [],
            "gen_skipped": [],
            "repair_skipped": [],
            "total": 0,
        }

        self.log_path = datetime.datetime.now().strftime(
            f"../logs/repair_loopy_%Y_%m_%d_%H_%M_%S/"
        )
        if not os.path.exists(os.path.dirname(self.log_path)):
            os.makedirs(os.path.dirname(self.log_path))

        log_file = open(self.log_path + "final.json", "w", encoding="utf-8")

        repair_prompt = Prompt(
            system_text_file="templates/healing_system_message.txt",
            prompt_text_file="templates/healing_prompt.txt",
            num_completions=1,
        )

        for benchmark_index, gen_benchmark_log in enumerate(generation_log):
            Logger.log_info(
                f"Running benchmark: {start_index + benchmark_index + 1}/{len(generation_log)}"
            )

            benchmark_code = gen_benchmark_log["benchmark_code"]
            instance_log_json = {
                "file": gen_benchmark_log["file"],
                "benchmark_code": benchmark_code,
                "success": False,
                "repair_tries": [],
            }
            success = False

            if "completions" not in gen_benchmark_log:
                Logger.log_info(
                    f"Skipping benchmark without completions: {start_index + benchmark_index + 1}/{len(generation_log)}"
                )
                instance_log_json["success"] = False
                stats["gen_skipped"].append(gen_benchmark_log["file"])
                log_json.append(instance_log_json)
                Loopy.write_benchmark_log(
                    self.log_path,
                    gen_benchmark_log["file"],
                    {"logs": instance_log_json, "stats": stats},
                )
                continue

            try:
                pass_8_success, candidates = Loopy.combine_and_prune_with_k(
                    gen_benchmark_log,
                    15,
                    k,
                    combine_llm_output_lambda=self.benchmark.combine_llm_outputs,
                )
                if pass_8_success:
                    Logger.log_success(
                        f"Skipping successful benchmark: {start_index + benchmark_index + 1}/{len(generation_log)}"
                    )
                    instance_log_json["success"] = True
                    instance_log_json["candidates"] = candidates
                    stats["gen_success"].append(gen_benchmark_log["file"])

                    log_json.append(instance_log_json)
                    Loopy.write_benchmark_log(
                        self.log_path,
                        gen_benchmark_log["file"],
                        {"logs": instance_log_json, "stats": stats},
                    )
                    continue

                failing_candidate = random.choice(candidates)

                Logger.log_info(
                    f"Starting repair for benchmark: {start_index + benchmark_index + 1}/{len(generation_log)}"
                )

                num_repair_calls = 0
                repair_tries = []
                success = False
                houdini_success = False
                while num_repair_calls < num_repairs:
                    success, checker_message = self.checker.check(
                        failing_candidate,
                        check_variant=False,
                        check_contracts=False,
                    )

                    if success:
                        Logger.log_success(
                            f"Repair successful for benchmark: {start_index + benchmark_index + 1}/{len(generation_log)} with {num_repair_calls} repair calls"
                        )
                        instance_log_json["success"] = True
                        repair_tries.append(
                            {
                                "repair_candidate": failing_candidate,
                                "llm_conversation": [],
                                "success": True,
                                "checker_message": checker_message,
                            }
                        )
                        stats["repair_success"].append(gen_benchmark_log["file"])
                        break

                    repair_try_json = {
                        "repair_candidate": failing_candidate,
                        "repair_error_message": checker_message,
                    }

                    if "Annotation error on line" in checker_message:
                        matches = re.findall(
                            r"Annotation error on line (\d+): ", checker_message
                        )
                        line_num = int(matches[0]) - 1
                        checker_message = checker_message.replace(
                            f"Annotation error on line {line_num + 1}: ",
                            f"Syntax error on line '{failing_candidate.splitlines()[line_num]}': ",
                        )

                    (
                        repair_annotation_blocks,
                        repair_llm_outputs,
                    ) = self.llm.generate_annotation(
                        input={"code": failing_candidate, "error": checker_message},
                        prompt=repair_prompt,
                        extraction_filter=lambda x: self.checker.has_invariant(x),
                    )

                    assert len(repair_annotation_blocks) == 1, "Invalid repair"

                    if len(
                        repair_annotation_blocks[0]
                    ) == 2 and repair_annotation_blocks[0] == (
                        "ERROR: Output does not contain at least 1 complete code block"
                    ):
                        Logger.log_error(
                            f"LLM query failed for benchmark: {start_index + benchmark_index + 1}/{len(generation_log)}"
                        )
                        continue

                    num_repair_calls += 1

                    repair_try_json["llm_conversation"] = repair_llm_outputs
                    repair_try_json["annotation_blocks"] = repair_annotation_blocks

                    new_checker_input = self.benchmark.combine_llm_outputs(
                        benchmark_code,
                        repair_annotation_blocks,
                        "one_loop_one_method",
                    )
                    repair_try_json["repaired_checker_input"] = new_checker_input

                    success, checker_message = self.checker.check(
                        new_checker_input,
                        check_variant=False,
                        check_contracts=False,
                    )

                    houdini_success, pruned_code, _ = self.checker.houdini(
                        new_checker_input,
                        check_variant=False,
                        check_contracts=False,
                    )

                    if success or houdini_success:
                        Logger.log_success(
                            f"Repair successful for benchmark: {start_index + benchmark_index + 1}/{len(generation_log)} with {num_repair_calls} repair calls"
                        )
                        repair_try_json["success"] = True
                        repair_try_json["checker_message"] = checker_message
                        repair_try_json["success_after_prune"] = houdini_success
                        repair_try_json["code_after_prune"] = pruned_code

                        instance_log_json["success"] = True
                        repair_tries.append(repair_try_json)
                        break

                    else:
                        Logger.log_error(
                            f"Repair unsuccessful for benchmark: {start_index + benchmark_index + 1}/{len(generation_log)} with {num_repair_calls} repair calls"
                        )
                        failing_candidate = new_checker_input
                        repair_try_json["success"] = False
                        repair_try_json["checker_message"] = checker_message
                        repair_try_json["success_after_prune"] = houdini_success
                        repair_try_json["code_after_prune"] = pruned_code
                        repair_tries.append(repair_try_json)
                        continue

                instance_log_json["repair_tries"] = repair_tries
                instance_log_json["success"] = success or houdini_success

                if instance_log_json["success"]:
                    Logger.log_success(
                        f"Benchmark {start_index + benchmark_index + 1}/{len(generation_log)} succeeded"
                    )
                    stats["repair_success"].append(gen_benchmark_log["file"])
                else:
                    Logger.log_error(
                        f"Benchmark {start_index + benchmark_index + 1}/{len(generation_log)} failed"
                    )
                    stats["repair_failure"].append(gen_benchmark_log["file"])

                Loopy.write_benchmark_log(
                    self.log_path,
                    gen_benchmark_log["file"],
                    {"logs": instance_log_json, "stats": stats},
                )

            except Exception as e:
                Logger.log_error(traceback.format_exc())
                if isinstance(e, KeyboardInterrupt):
                    instance_log_json["success"] = False
                    stats["repair_skipped"].append(gen_benchmark_log["file"])
                    break
                else:
                    instance_log_json["error"] = str(e)
                    instance_log_json["success"] = False
                    stats["repair_skipped"].append(gen_benchmark_log["file"])
                    log_json.append(instance_log_json)
                    Loopy.write_benchmark_log(
                        self.log_path,
                        gen_benchmark_log["file"],
                        {"logs": instance_log_json, "stats": stats},
                    )
                    continue

            stats["total"] += 1
            stats["gen_success_count"] = len(stats["gen_success"])
            stats["repair_success_count"] = len(stats["repair_success"])
            stats["repair_failure_count"] = len(stats["repair_failure"])
            stats["gen_skipped_count"] = len(stats["gen_skipped"])
            stats["repair_skipped_count"] = len(stats["repair_skipped"])

        log_file.write(
            json.dumps(
                {"params": self.arg_params, "logs": log_json, "stats": stats},
                indent=4,
                ensure_ascii=False,
            )
        )
        log_file.close()

        return

    def interprocedural_loop_invariant_analysis(self, max_benchmarks=1, start_index=0):
        if self.llm is None or self.benchmark is None or self.checker is None:
            raise Exception("Pipeline not initialized. Call load_config first.")

        log_json = []
        stats = {"success": [], "failure": [], "skipped": [], "total": 0}

        # create logs dir
        self.log_path = datetime.datetime.now().strftime(
            f"../logs/loopy_%Y_%m_%d_%H_%M_%S/"
        )
        if not os.path.exists(os.path.dirname(self.log_path)):
            os.makedirs(os.path.dirname(self.log_path))

        log_file = open(self.log_path + "final.json", "w", encoding="utf-8")

        sliced_benchmarks = self.benchmark.input_file_paths[
            start_index : start_index + max_benchmarks
        ]

        pre_post_prompt = Prompt(
            system_text_file="templates/m1_prepost_system.txt",
            prompt_text_file="templates/m1_prepost_prompt.txt",
            num_completions=8,
        )

        for benchmark_index, benchmark_file in enumerate(sliced_benchmarks):
            Logger.log_info(
                f"Running benchmark: {start_index + benchmark_index + 1}/{len(sliced_benchmarks)}"
            )

            instance_log_json = {
                "file": benchmark_file,
                "benchmark_code": self.benchmark.get_code(benchmark_file),
                "success": False,
            }
            success = False

            try:
                annotation_blocks, llm_outputs = self.llm.generate_annotation(
                    input={"code": self.benchmark.get_code(benchmark_file)},
                    prompt=pre_post_prompt,
                    extraction_filter=lambda x: self.checker.has_invariant(x)
                    or self.checker.has_function_contract(x),
                )

                instance_log_json["llm_conversation"] = llm_outputs
                instance_log_json["annotation_blocks"] = annotation_blocks

                completions = []
                for block in annotation_blocks:
                    completion_json = {
                        "num_solver_calls": 0,
                    }
                    if len(block) == 2 and block[0] == (
                        "ERROR: Output does not contain at least 1 complete code block"
                    ):
                        completion_json["success"] = False
                        completion_json["num_solver_calls"] = 0
                        completion_json["llm_output"] = block[1]
                        completion_json["error"] = (
                            "Output does not contain at least 1 code block"
                        )
                        completions.append(completion_json)
                        continue

                    Logger.log_info(f"Checking completion {len(completions) + 1}")

                    checker_input_with_annotations = self.benchmark.combine_llm_outputs(
                        self.benchmark.get_code(benchmark_file),
                        [block],
                        "multiple_loops_multiple_methods",
                    )
                    completion_json["annotations"] = block
                    __success, checker_message = self.checker.check(
                        checker_input_with_annotations,
                        check_variant=False,
                        check_contracts=True,
                    )

                    completion_json["num_solver_calls"] += 1
                    completion_json["checker_output_for_annotations"] = __success
                    completion_json["checker_message_for_annotations"] = checker_message

                    if not __success:
                        try:
                            (
                                __success,
                                pruned_code,
                                num_frama_c_calls,
                            ) = self.checker.houdini(
                                checker_input_with_annotations,
                                check_variant=False,
                                check_contracts=True,
                            )

                            completion_json["num_solver_calls"] += num_frama_c_calls
                            completion_json["code_after_prune"] = pruned_code
                            completion_json["checker_output_after_prune"] = __success
                        except Exception as e:
                            completion_json["code_after_prune"] = (
                                checker_input_with_annotations
                            )
                            completion_json["checker_output_after_prune"] = False
                            completion_json["checker_message_after_prune"] = str(e)
                            __success = False

                    success = __success or success

                    if __success:
                        Logger.log_success(
                            f"Completion {len(completions) + 1} is correct"
                        )
                    else:
                        Logger.log_error(
                            f"Completion {len(completions) + 1} is incorrect"
                        )

                    completions.append(completion_json)

                instance_log_json["completions"] = completions

                checker_input_with_combined_annotations = self.benchmark.combine_llm_outputs(
                    self.benchmark.get_code(benchmark_file),
                    [
                        block
                        for block in annotation_blocks
                        if not (
                            len(block) == 2
                            and block[0]
                            == (
                                "ERROR: Output does not contain at least 1 complete code block"
                            )
                        )
                    ],
                    "multiple_loops_multiple_methods",
                )

                Logger.log_info(
                    f"Checking combined annotations for benchmark: {start_index + benchmark_index + 1}/{len(sliced_benchmarks)}"
                )

                __success, checker_message = self.checker.check(
                    checker_input_with_combined_annotations,
                    check_variant=False,
                    check_contracts=True,
                )

                if __success:
                    Logger.log_success(
                        f"Combined annotations are correct for benchmark: {start_index + benchmark_index + 1}/{len(sliced_benchmarks)}"
                    )
                else:
                    Logger.log_error(
                        f"Combined annotations are incorrect for benchmark: {start_index + benchmark_index + 1}/{len(sliced_benchmarks)}"
                    )

                instance_log_json["checker_output_for_combined_annotations"] = __success
                instance_log_json["checker_message_for_combined_annotations"] = (
                    checker_message
                )
                instance_log_json["code_with_combined_annotations"] = (
                    checker_input_with_combined_annotations
                )

                success = __success or success

                if not __success:
                    Logger.log_info(
                        f"Houdini for combined annotations for benchmark: {start_index + benchmark_index + 1}/{len(sliced_benchmarks)}"
                    )

                    try:
                        (
                            __success,
                            pruned_code,
                            num_frama_c_calls,
                        ) = self.checker.houdini(
                            checker_input_with_combined_annotations,
                            check_variant=False,
                            check_contracts=True,
                        )
                    except Exception as e:
                        Logger.log_error(traceback.format_exc())
                        Logger.log_error(str(e))
                        __success = False
                        pruned_code = checker_input_with_combined_annotations
                        num_frama_c_calls = 0

                    if __success:
                        Logger.log_success(
                            f"Houdini for combined annotations successful for benchmark: {start_index + benchmark_index + 1}/{len(sliced_benchmarks)}"
                        )
                    else:
                        Logger.log_error(
                            f"Houdini for combined annotations unsuccessful for benchmark: {start_index + benchmark_index + 1}/{len(sliced_benchmarks)}"
                        )

                    instance_log_json["combined_annotation_num_solver_calls"] = (
                        num_frama_c_calls + 1
                    )
                    instance_log_json["code_after_prune"] = pruned_code
                    instance_log_json["checker_output_after_prune"] = __success

                success = __success or success

                instance_log_json["success"] = success

            except Exception as e:
                Logger.log_error(traceback.format_exc())
                if isinstance(e, KeyboardInterrupt):
                    instance_log_json["success"] = False
                    stats["skipped"].append(benchmark_file)
                    break
                else:
                    instance_log_json["error"] = str(e)
                    instance_log_json["success"] = False
                    stats["skipped"].append(benchmark_file)
                    log_json.append(instance_log_json)
                    Loopy.write_benchmark_log(
                        self.log_path,
                        benchmark_file,
                        {"log": instance_log_json, "stats": stats},
                    )
                    continue

            if instance_log_json["success"]:
                Logger.log_success(
                    f"Benchmark {start_index + benchmark_index + 1}/{len(sliced_benchmarks)} succeeded"
                )
                stats["success"].append(benchmark_file)

            else:
                Logger.log_error(
                    f"Benchmark {start_index + benchmark_index + 1}/{len(sliced_benchmarks)} failed"
                )
                stats["failure"].append(benchmark_file)

            stats["total"] += 1
            stats["success_count"] = len(stats["success"])
            stats["failure_count"] = len(stats["failure"])
            stats["success_rate"] = (
                stats["success_count"] / stats["total"] if stats["total"] != 0 else 0
            )

            log_json.append(instance_log_json)

            Loopy.write_benchmark_log(
                self.log_path,
                benchmark_file,
                {"log": instance_log_json, "stats": stats},
            )

        log_file.write(
            json.dumps(
                {"params": self.arg_params, "logs": log_json, "stats": stats},
                indent=4,
                ensure_ascii=False,
            )
        )
        log_file.close()

        return

    def termination_analysis(self, max_benchmarks=1, start_index=0):
        if self.llm is None or self.benchmark is None or self.checker is None:
            raise Exception("Pipeline not initialized. Call load_config first.")

        log_json = []
        stats = {"success": [], "failure": [], "skipped": [], "total": 0}

        # create logs dir
        self.log_path = datetime.datetime.now().strftime(
            f"../logs/loopy_%Y_%m_%d_%H_%M_%S/"
        )
        if not os.path.exists(os.path.dirname(self.log_path)):
            os.makedirs(os.path.dirname(self.log_path))

        log_file = open(self.log_path + "final.json", "w", encoding="utf-8")

        sliced_benchmarks = self.benchmark.input_file_paths[
            start_index : start_index + max_benchmarks
        ]

        alg_variant_prompt = Prompt(
            system_text_file="templates/termination_variants_system.txt",
            prompt_text_file="templates/termination_variants_prompt.txt",
            num_completions=5,
        )
        lexico_variant_prompt = Prompt(
            system_text_file="templates/termination_lexico_system.txt",
            prompt_text_file="templates/termination_lexico_prompt.txt",
            num_completions=5,
        )
        multi_phase_variant_prompt = Prompt(
            system_text_file="templates/termination_mphase_system.txt",
            prompt_text_file="templates/termination_mphase_prompt.txt",
            num_completions=5,
        )

        invariants_prompt = Prompt(
            system_text_file="templates/termination_invariants_system.txt",
            prompt_text_file="templates/termination_invariants_prompt.txt",
            num_completions=5,
        )

        for benchmark_index, benchmark_file in enumerate(sliced_benchmarks):
            Logger.log_info(
                f"Running benchmark: {start_index + benchmark_index + 1}/{len(sliced_benchmarks)}"
            )
            benchmark_success = False

            instance_log_json = {
                "file": benchmark_file,
                "benchmark_code": self.benchmark.get_code(benchmark_file),
                "success": False,
            }

            try:
                # Try the basic prompt first
                Logger.log_info(
                    f"Using basic prompt for benchmark: {start_index + benchmark_index + 1}/{len(sliced_benchmarks)}"
                )
                (
                    alg_variant_code_blocks,
                    alg_variant_llm_output,
                ) = self.llm.generate_annotation(
                    input={"code": self.benchmark.get_code(benchmark_file)},
                    prompt=alg_variant_prompt,
                    extraction_filter=self.checker.has_variant,
                )

                alg_variants = self.benchmark.get_variant_expressions(
                    [
                        code_block
                        for code_block in alg_variant_code_blocks
                        if not (
                            len(code_block) == 2
                            and code_block[0]
                            == "ERROR: Output does not contain at least 1 complete code block"
                        )
                    ]
                )

                instance_log_json["simple_variants"] = alg_variants
                instance_log_json["simple_variant_llm_output"] = alg_variant_llm_output
                instance_log_json["simple_variant_log"] = {}

                invariants_log = self.generate_invariants_for_variant(
                    invariants_prompt,
                    alg_variants,
                    self.benchmark.get_code(benchmark_file),
                )

                instance_log_json["simple_variant_log"] = invariants_log
                instance_log_json["simple_variant_success"] = invariants_log["success"]

                # If the basic prompt works, we are done
                if invariants_log["success"]:
                    benchmark_success = True
                    Logger.log_success(
                        f"Benchmark {start_index + benchmark_index + 1}/{len(sliced_benchmarks)} succeeded with a basic prompt"
                    )
                    instance_log_json["success"] = True
                    log_json.append(instance_log_json)
                    stats["success"].append(benchmark_file)
                    Loopy.write_benchmark_log(
                        self.log_path,
                        benchmark_file,
                        {"log": instance_log_json, "stats": stats},
                    )
                    continue

                # If the basic prompt does not work, try the lexicographic prompt next
                Logger.log_info(
                    f"Using lexicographic prompt for benchmark: {start_index + benchmark_index + 1}/{len(sliced_benchmarks)}"
                )
                (
                    lexico_variant_code_blocks,
                    lexico_variant_llm_output,
                ) = self.llm.generate_annotation(
                    input={"code": self.benchmark.get_code(benchmark_file)},
                    prompt=lexico_variant_prompt,
                    extraction_filter=self.checker.has_variant,
                )

                lexico_variants = self.benchmark.get_variant_expressions(
                    [
                        code_block
                        for code_block in lexico_variant_code_blocks
                        if not (
                            len(code_block) == 2
                            and code_block[0]
                            == "ERROR: Output does not contain at least 1 complete code block"
                        )
                    ]
                )

                instance_log_json["lexicographic_variants"] = lexico_variants
                instance_log_json["lexicographic_variant_llm_output"] = (
                    lexico_variant_llm_output
                )
                instance_log_json["lexicographic_variant_log"] = {}

                invariants_log = self.generate_invariants_for_variant(
                    invariants_prompt,
                    lexico_variants,
                    self.benchmark.get_code(benchmark_file),
                )

                instance_log_json["lexicographic_variant_log"] = invariants_log
                instance_log_json["lexicographic_variant_success"] = invariants_log[
                    "success"
                ]

                # If the lexicographic prompt works, we can move on
                if invariants_log["success"]:
                    benchmark_success = True
                    Logger.log_success(
                        f"Benchmark {start_index + benchmark_index + 1}/{len(sliced_benchmarks)} succeeded with a lexicographic prompt"
                    )
                    instance_log_json["success"] = True
                    log_json.append(instance_log_json)
                    stats["success"].append(benchmark_file)
                    Loopy.write_benchmark_log(
                        self.log_path,
                        benchmark_file,
                        {"log": instance_log_json, "stats": stats},
                    )
                    continue

                # If the lexicographic prompt does not work, we try the multi-phase prompt
                Logger.log_info(
                    f"Using multi-phase prompt for benchmark: {start_index + benchmark_index + 1}/{len(sliced_benchmarks)}"
                )
                (
                    multi_phase_variant_code_blocks,
                    multi_phase_variant_llm_output,
                ) = self.llm.generate_annotation(
                    input={"code": self.benchmark.get_code(benchmark_file)},
                    prompt=multi_phase_variant_prompt,
                    extraction_filter=self.checker.has_variant,
                )

                multi_phase_variants = self.benchmark.get_variant_expressions(
                    [
                        code_block
                        for code_block in multi_phase_variant_code_blocks
                        if not (
                            len(code_block) == 2
                            and code_block[0]
                            == "ERROR: Output does not contain at least 1 complete code block"
                        )
                    ]
                )

                instance_log_json["multi_phase_variants"] = multi_phase_variants
                instance_log_json["multi_phase_variant_llm_output"] = (
                    multi_phase_variant_llm_output
                )
                instance_log_json["multi_phase_variant_log"] = {}

                invariants_log = self.generate_invariants_for_variant(
                    invariants_prompt,
                    multi_phase_variants,
                    self.benchmark.get_code(benchmark_file),
                )

                instance_log_json["multi_phase_variant_log"] = invariants_log
                instance_log_json["multi_phase_variant_success"] = invariants_log[
                    "success"
                ]

                # If the multi-phase prompt works, we can move on
                if invariants_log["success"]:
                    benchmark_success = True
                    Logger.log_success(
                        f"Benchmark {start_index + benchmark_index + 1}/{len(sliced_benchmarks)} succeeded with a multi-phase prompt"
                    )
                    instance_log_json["success"] = True
                    log_json.append(instance_log_json)
                    stats["success"].append(benchmark_file)
                    Loopy.write_benchmark_log(
                        self.log_path,
                        benchmark_file,
                        {"log": instance_log_json, "stats": stats},
                    )
                    continue

                # If no prompt works, we fail and move on
                Logger.log_error(
                    f"Benchmark {start_index + benchmark_index + 1}/{len(sliced_benchmarks)} failed"
                )
                log_json.append(instance_log_json)
                stats["failure"].append(benchmark_file)
                instance_log_json["success"] = False
                Loopy.write_benchmark_log(
                    self.log_path,
                    benchmark_file,
                    {"log": instance_log_json, "stats": stats},
                )

            except Exception as e:
                Logger.log_error(traceback.format_exc())
                if isinstance(e, KeyboardInterrupt):
                    instance_log_json["success"] = False
                    stats["skipped"].append(benchmark_file)
                    break
                else:
                    instance_log_json["error"] = str(e)
                    instance_log_json["success"] = False
                    stats["skipped"].append(benchmark_file)
                    log_json.append(instance_log_json)
                    Loopy.write_benchmark_log(
                        self.log_path,
                        benchmark_file,
                        {"log": instance_log_json, "stats": stats},
                    )
                    continue

            stats["total"] += 1
            stats["success_count"] = len(stats["success"])
            stats["failure_count"] = len(stats["failure"])
            stats["success_rate"] = (
                stats["success_count"] / stats["total"] if stats["total"] != 0 else 0
            )

            log_json.append(instance_log_json)

        log_file.write(
            json.dumps(
                {"params": self.arg_params, "logs": log_json, "stats": stats},
                indent=4,
                ensure_ascii=False,
            )
        )
        log_file.close()

        return

    def generate_invariants_for_variant(self, prompt, variants, checker_input):
        # one set of variants
        invariants_log = {"success": False}

        for var_index, variant in enumerate(variants):
            Logger.log_info(
                f"Checking variant [{var_index + 1}]/[{len(variants)}]: {variant}"
            )
            variant_log = {"variant": variant}
            try:
                # syntax error check
                checker_inputs_with_variants = self.benchmark.combine_llm_outputs(
                    checker_input,
                    (
                        "",
                        ["\n".join(["loop variant " + x + ";" for x in variant])],
                    ),
                    "termination_one_loop_one_method",
                )

                error_free_variants = []

                for checker_input_with_variant in checker_inputs_with_variants:
                    success, checker_message = self.checker.check(
                        checker_input_with_variant,
                        check_variant=True,
                        check_contracts=False,
                    )

                    if "Annotation error on line " in checker_message:
                        Logger.log_error(f"Annotation error in variant: {variant}")
                        continue
                    else:
                        error_free_variants.append(checker_input_with_variant)

                if len(error_free_variants) == 0:
                    variant_log["error"] = (
                        "All variant candidates have annotation errors"
                    )
                    variant_log["success"] = False
                    invariants_log[str(variant)] = variant_log
                    Logger.log_error(f"Annotation errors in variant: {variant}")
                    continue

                Logger.log_info(f"Generating invariants for variant: {variant}")

                # Generate invariants for this variant
                (
                    invariant_code_blocks,
                    invariant_llm_output,
                ) = self.llm.generate_annotation(
                    input={
                        "code": checker_input,
                        "loop_variant": "(" + ", ".join(variant) + ")",
                    },
                    prompt=prompt,
                    extraction_filter=self.checker.has_invariant,
                )

                variant_log["invariant_code_blocks"] = invariant_code_blocks
                variant_log["invariant_llm_output"] = invariant_llm_output

                checker_input_with_invariants = self.benchmark.combine_llm_outputs(
                    checker_input,
                    list(
                        filter(
                            lambda x: not (
                                len(x) == 2
                                and x[0]
                                == "ERROR: Output does not contain at least 1 complete code block"
                            ),
                            invariant_code_blocks,
                        )
                    ),
                    "one_loop_one_method",
                )

                # Houdini for the invariant set
                success, pruned_code, num_frama_c_calls = self.checker.houdini(
                    checker_input_with_invariants,
                    check_variant=False,
                    check_contracts=False,
                )

                inductive_invariants = self.benchmark.extract_loop_invariants(
                    pruned_code
                )

                if len(inductive_invariants) == 0:
                    Logger.log_error(
                        f"No inductive invariants found for variant: {variant}"
                    )
                else:
                    Logger.log_success(
                        f"Inductive invariants found for variant: {variant}"
                    )

                variant_log["inductive_invariants"] = inductive_invariants
                # candidates with variants and invariants
                checker_full_inputs = self.benchmark.combine_llm_outputs(
                    checker_input,
                    (
                        inductive_invariants,
                        ["\n".join(["loop variant " + x + ";" for x in variant])],
                    ),
                    "termination_one_loop_one_method",
                )

                variant_candidates = []
                for checker_inp in checker_full_inputs:
                    Logger.log_info(
                        f"Checking variant candidate for variant: {variant}"
                    )
                    success, checker_message = self.checker.check(
                        checker_inp,
                        check_variant=True,
                        check_contracts=False,
                    )
                    variant_candidates.append(
                        {
                            "candidate_with_combined_invariants_and_variant": checker_inp,
                            "checker_output": success,
                            "checker_message": checker_message,
                        }
                    )
                    if success:
                        Logger.log_success(
                            f"Variant candidate is correct for variant: {variant}"
                        )
                    else:
                        Logger.log_error(
                            f"Variant candidate is incorrect for variant: {variant}"
                        )

                variant_log["final_variant_candidates"] = variant_candidates
                variant_log["success"] = any(
                    [x["checker_output"] for x in variant_candidates]
                )

                invariants_log[str(variant)] = variant_log
                invariants_log["success"] = (
                    invariants_log["success"] or variant_log["success"]
                )

                if variant_log["success"]:
                    Logger.log_success(f"Variant {variant} is correct for benchmark")
                    break
                else:
                    Logger.log_error(f"Variant {variant} is incorrect for benchmark")

            except Exception as e:
                Logger.log_error(traceback.format_exc())
                variant_log["error"] = str(e)
                variant_log["success"] = False
                invariants_log[str(variant)] = variant_log
                invariants_log["success"] = False

        return invariants_log
