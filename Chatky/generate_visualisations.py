"""
Generate a visualisation PDF for every solution in solutions/
and write them to visualisations/.
"""

import os
import glob
import subprocess
import sys

python = sys.executable
os.makedirs("visualisations", exist_ok=True)

solution_files = sorted(glob.glob("solutions/solution_*.json"))
if not solution_files:
    print("No solution files found in solutions/")
    sys.exit(1)

for sol_path in solution_files:
    name     = os.path.basename(sol_path).replace(".json", "")   # solution_0
    pdf_path = f"visualisations/{name}.pdf"
    print(f"  {sol_path} → {pdf_path} ...", end=" ", flush=True)
    result = subprocess.run(
        [python, "visualize.py", sol_path, pdf_path],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("OK")
    else:
        print("FAILED")
        print(result.stderr[-400:])

print(f"\nDone. {len(solution_files)} PDFs written to visualisations/")
