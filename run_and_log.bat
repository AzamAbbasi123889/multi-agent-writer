@echo off
cd /d "c:\Users\HP\multi agent writer"
python run_test.py > pipeline_output.txt 2>&1
echo DONE >> pipeline_output.txt
