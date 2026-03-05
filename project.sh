#!/usr/bin/env bash
clear
#source /home/tom/miniconda3/etc/profile.d/conda.sh
#conda activate base
# Use local editable install with fixes instead of PyPI version
#pip install -e /home/tom/github/wronai/code2llm --no-deps --quiet
#code2logic ./ -f toon --compact --no-repeat-module --function-logic --with-schema --name project -o ./
# Suppress Python syntax warnings from files with invalid syntax (e.g., markdown code blocks)
#python3 -W ignore -m code2llm ./ -f toon,evolution,code2logic -o ./project
pip install code2llm --upgrade
code2llm ./ -f toon,evolution,code2logic,project-yaml -o ./project --no-chunk
#code2llm ./ -f project-yaml -o ./project --no-chunk
#code2llm report --format html      # → dashboard.html
#code2llm ./ -f all -o ./project --no-chunk
code2llm report --format all -i ./project/project.yaml -o ./project       # → all views
rm -f project/analysis.json
rm -f project/analysis.yaml