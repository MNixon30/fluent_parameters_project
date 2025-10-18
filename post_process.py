import os
import csv
import re


def summarize_fluent_results(project_root: str, output_filename="summary2.csv"):
    """
    Summarizes all numeric results from Fluent output files in
    <project_root>/test_files/out and writes a combined CSV file
    in <project_root>/test_files/out_final.

    Args:
        project_root (str): Root folder of the project.
        output_filename (str): Name of the output summary file.
    """
    input_folder = os.path.join(project_root, "test_files", "out")
    output_folder = os.path.join(project_root, "test_files", "out_final")
    os.makedirs(output_folder, exist_ok=True)

    output_files = [f for f in os.listdir(input_folder) if f.lower().endswith(".txt")]
    if not output_files:
        print(f"No output files found in {input_folder}")
        return

    all_results = {}
    parameters_order = []

    # Correct regex to capture full scientific notation numbers
    pattern = re.compile(r"(\S+)\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)")

    # Read each output file
    for file_name in sorted(output_files):
        file_path = os.path.join(input_folder, file_name)
        results = {}
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                match = pattern.search(line)
                if match:
                    param, value = match.groups()
                    results[param] = float(value)
                    if param not in parameters_order:
                        parameters_order.append(param)
        all_results[file_name] = results

    # Save summary CSV
    summary_path = os.path.join(output_folder, output_filename)
    with open(summary_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        # Header row
        writer.writerow(["Output Parameter"] + list(sorted(all_results.keys())))
        # For each parameter, write its value from each file
        for param in parameters_order:
            row = [param]
            for file_name in sorted(all_results.keys()):
                row.append(all_results[file_name].get(param, ""))
            writer.writerow(row)

    print(f"\n✅ Summary of all results saved to: {summary_path}")