frama-c -wp  -wp-verbose 100 -wp-debug 100 -wp-timeout 3  \
                -wp-prover=alt-ergo,z3,cvc4 $1  -wp-report-json $1__wp_report.json -kernel-warn-key annot-error=active -wp-print -wp-status-all -wp-log d:$1__debug_log.txt\
                -kernel-log a:$1__kernel_logs.txt -then -no-unicode -report -report-csv $1__output_dump.csv > $1_out.txt 2> $1_log.txt