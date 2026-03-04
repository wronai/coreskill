#!/usr/bin/env bash
source /home/tom/miniconda3/etc/profile.d/conda.sh
conda activate base
pip install code2llm --upgrade
#code2logic ./ -f toon --compact --no-repeat-module --function-logic --with-schema --name project -o ./
# Suppress Python syntax warnings from files with invalid syntax (e.g., markdown code blocks)
PYTHONWARNINGS="ignore::SyntaxWarning" code2llm ./ -f toon,evolution,code2logic -o ./project