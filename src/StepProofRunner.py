from StepProofVerifier.StepProofVerifier import StepProofVerifier
import os
import sys

if __name__ == "__main__":
    benchmark_path = sys.argv[1]
    verifier = StepProofVerifier(benchmark_path)
    verifier.run()