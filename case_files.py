#CASE FILE STUFF

import os
import re
import csv

def generate_master_fluent_script(input_file_path: str, project_folder_path: str, dimension: int):
    """
    Generates a single Fluent Python script that loops over all mesh files in
    <project_folder_path>/test_files/msh, runs a case for each, and records all
    output parameters into separate numbered files.

    Replaces any hardcoded mesh path in the template with the loop variable.
    """

    # --- Locate all mesh files ---
    mesh_folder = os.path.join(project_folder_path, "test_files", "msh")
    mesh_files = [f for f in os.listdir(mesh_folder) if f.lower().endswith((".msh", ".msh.h5"))]
    
    if not mesh_files:
        raise FileNotFoundError(f"No mesh files found in {mesh_folder}")

    # --- Read template script ---
    with open(input_file_path, "r") as f:
        lines = f.readlines()

    # --- Find FLUENT_PROD_DIR section ---
    start_idx, end_idx = None, None
    for i, line in enumerate(lines):
        if "if not os.getenv('FLUENT_PROD_DIR')" in line:
            start_idx = i
        if start_idx is not None and line.strip() == "":
            end_idx = i
            break
    if start_idx is None or end_idx is None:
        raise ValueError("Could not find the FLUENT_PROD_DIR block in the input file.")

    # --- Keep all script lines after setup block ---
    remaining_lines = lines[end_idx+1:]

    # --- Replace any hardcoded mesh read path in the template ---
    mesh_read_pattern = re.compile(r"solver\.settings\.file\.read_mesh\(file_name\s*=\s*r?['\"].*?['\"]\)")
    processed_lines = []
    for line in remaining_lines:
        if mesh_read_pattern.search(line):
            # Keep this line without extra indentation
            processed_lines.append("    solver.settings.file.read_mesh(file_name=mesh_path)\n")
        else:
            # Indent all other lines inside the loop
            processed_lines.append("    " + line if line.strip() else line)

    # --- Prepare output folder ---
    output_folder = os.path.join(project_folder_path, "test_files", "cas_scripts")
    os.makedirs(output_folder, exist_ok=True)

    # --- Build one unified script ---
    unified_script = f"""import ansys.fluent.core as pyfluent
import os, sys

# Launch Fluent session
solver = pyfluent.launch_fluent(
    ui_mode='no_gui',
    mode='solver',
    precision='single',
    processor_count=2,
    dimension={dimension})

# --- Mesh files to loop over ---
mesh_folder = r"{mesh_folder}"
mesh_files = [f for f in os.listdir(mesh_folder) if f.lower().endswith(('.msh', '.msh.h5'))]

# --- Loop through all meshes ---
for idx, mesh_name in enumerate(mesh_files, start=1):
    mesh_path = os.path.join(mesh_folder, mesh_name)
    print(f"\\n=== Running case {{idx}} / {{len(mesh_files)}}: {{mesh_name}} ===")

"""

    # Add processed lines (mesh read not double-indented)
    unified_script += "".join(processed_lines)

    # Add the block that saves output parameters
    unified_script += f"""
    # --- Save output parameters for this case ---
    output_folder = os.path.join(r"{project_folder_path}", "test_files", "out")
    os.makedirs(output_folder, exist_ok=True)
    output_file = os.path.join(output_folder, f"out_{{idx-1}}.txt")

    original_stdout = sys.stdout
    with open(output_file, "w", encoding="utf-8") as f:
        sys.stdout = f
        solver.settings.parameters.output_parameters.print_all_to_console()
        sys.stdout = original_stdout

    print(f"✔ Output saved to: {{output_file}}")
"""

    # --- Save final unified Python file ---
    output_script_path = os.path.join(output_folder, "run_all_cases.py")
    with open(output_script_path, "w", encoding="utf-8") as f:
        f.write(unified_script)

    print(f"\n✅ Single unified Fluent script created at:\n{output_script_path}")






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


summarize_fluent_results(r"C:\Users\mitch\Ravens_Racing_CFD\z_Project_Test")

