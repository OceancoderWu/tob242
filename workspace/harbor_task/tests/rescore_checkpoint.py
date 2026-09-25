"""Independently reload a measured checkpoint under the frozen protocol."""
import argparse
import subprocess
import sys
from pathlib import Path

TESTS=Path(__file__).resolve().parent
TASK=Path('/workspace') if Path('/workspace/environment/public_assets').is_dir() else TESTS.parent

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--method',type=Path,required=True)
    parser.add_argument('--checkpoint',type=Path,required=True)
    parser.add_argument('--seed',type=int,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--data',type=Path,default=TASK/'environment/public_assets/data')
    parser.add_argument('--test-data',type=Path,default=TESTS/'benchmark_data')
    args=parser.parse_args()
    subprocess.run([sys.executable,str(TESTS/'train_eval.py'),'--method',str(args.method.resolve()),
                    '--reload',str(args.checkpoint.resolve()),'--seed',str(args.seed),
                    '--output',str(args.output.resolve()),'--data',str(args.data.resolve()),'--test-data',str(args.test_data.resolve())],check=True)
if __name__=='__main__':main()
