#!/usr/bin/env python3
"""Run the ECAE experiment. Execute from project root."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    from experiments import run
    run.main()