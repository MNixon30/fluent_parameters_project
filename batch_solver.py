import os
import subprocess
import re
import sys

def run_meshing_scripts(project_root, fluent_path, meshing_cores):
    """
    Runs all Fluent 2D meshing journal scripts stored in <project_root>\test_files\scripts automatically.
    
    Parameters:
        project_root (str): Root folder of the project.
    """
    script_folder = os.path.join(project_root, "test_files", "scripts")

    if not os.path.exists(script_folder):
        print(f"⚠️ Folder not found: {script_folder}")
        return

    # Find all .jou files in the folder
    script_paths = [os.path.join(script_folder, f)
                    for f in os.listdir(script_folder)
                    if f.endswith(".jou")]

    if not script_paths:
        print(f"⚠️ No .jou scripts found in {script_folder}")
        return

    fluent_exe = fluent_path

    # Define the geoms folder for cleanup
    geoms_folder = os.path.join(project_root, "test_files", "geoms")

    for script in script_paths:
        print(f"🌀 Running meshing script: {os.path.basename(script)}")
        subprocess.run([fluent_exe,
                        "3d",
                        "-meshing",    # Explicit meshing mode
                        "-hidden",
                        "-g",     
                        f"-t{meshing_cores}",         # Number of threads
                        "-i", script]) # Input journal
        print(f"✅ Finished: {os.path.basename(script)}")
        
        # Clean up .fmd files created by Fluent to save space
        if os.path.exists(geoms_folder):
            fmd_files = [f for f in os.listdir(geoms_folder) if f.lower().endswith('.fmd')]
            for fmd_file in fmd_files:
                fmd_path = os.path.join(geoms_folder, fmd_file)
                try:
                    os.remove(fmd_path)
                    print(f"🗑️ Deleted .fmd file: {fmd_file}")
                except Exception as e:
                    print(f"⚠️ Could not delete {fmd_file}: {e}")




def generate_master_fluent_script(input_file_path: str, project_folder_path: str, dimension: int, solver_cores, save_design_points=None):
    """
    Generates a single Fluent Python script that loops over all mesh files in
    <project_folder_path>/test_files/msh, runs a case for each, and records all
    output parameters into separate numbered files.

    Replaces any hardcoded mesh path in the template with the loop variable.
    
    Args:
        input_file_path (str): Path to the case journal template
        project_folder_path (str): Root folder of the project
        dimension (int): Simulation dimension (2 or 3)
        solver_cores (int): Number of cores for solver
        save_design_points (list, optional): List of design point indices (1-based) where case/data files should be saved
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

    # --- Prepare output folders ---
    output_folder = os.path.join(project_folder_path, "test_files", "cas_scripts")
    os.makedirs(output_folder, exist_ok=True)
    
    # --- Prepare cas folder for case/data files ---
    cas_folder = os.path.join(project_folder_path, "test_files", "cas")
    os.makedirs(cas_folder, exist_ok=True)

    # --- Convert save_design_points to string for script ---
    save_points_str = str(save_design_points) if save_design_points else "None"
    
    # --- Build one unified script ---
    unified_script = f"""import ansys.fluent.core as pyfluent
import os, sys

# Launch Fluent session
solver = pyfluent.launch_fluent(
    ui_mode='no_gui',
    mode='solver',
    precision='single',
    processor_count={solver_cores},
    dimension={dimension})

# --- Mesh files to loop over ---
mesh_folder = r"{mesh_folder}"
mesh_files = [f for f in os.listdir(mesh_folder) if f.lower().endswith(('.msh', '.msh.h5'))]

# --- Design points to save case/data files ---
save_design_points = {save_points_str}

# --- Loop through all meshes ---
for idx, mesh_name in enumerate(mesh_files, start=1):
    mesh_path = os.path.join(mesh_folder, mesh_name)
    print(f"\\n=== Running case {{idx}} / {{len(mesh_files)}}: {{mesh_name}} ===")

"""

    # Add processed lines (mesh read not double-indented)
    unified_script += "".join(processed_lines)

    # Add the block that saves output parameters and case/data files
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

    print(f"[DONE] Output saved to: {{output_file}}")
    
    # --- Save case and data files for specified design points ---
    if save_design_points is not None and idx in save_design_points:
        cas_folder = os.path.join(r"{project_folder_path}", "test_files", "cas")
        os.makedirs(cas_folder, exist_ok=True)
        
        # Generate case and data file names based on design point
        case_filename = f"design_point_{{idx}}_case.cas"
        data_filename = f"design_point_{{idx}}_data.dat"
        
        case_path = os.path.join(cas_folder, case_filename)
        data_path = os.path.join(cas_folder, data_filename)
        
        print(f"Saving case file: {{case_filename}}")
        solver.settings.file.write_case(file_name=case_path)
        
        print(f"Saving data file: {{data_filename}}")
        solver.settings.file.write_data(file_name=data_path)
        
        print(f"Case and data files saved for design point {{idx}}")
"""

    # --- Save final unified Python file ---
    output_script_path = os.path.join(output_folder, "run_all_cases.py")
    with open(output_script_path, "w", encoding="utf-8") as f:
        f.write(unified_script)

    print(f"\n✅ Single unified Fluent script created at:\n{output_script_path}")





def run_generated_fluent_script(project_root: str):
    """
    Runs the generated Fluent Python script located at:
    <project_root>/test_files/cas_scripts/run_all_cases.py

    Args:
        project_root (str): Root folder of the project.
    """
    script_path = os.path.join(project_root, "test_files", "cas_scripts", "run_all_cases.py")

    if not os.path.isfile(script_path):
        raise FileNotFoundError(f"Generated script not found: {script_path}")

    print(f"▶ Running generated Fluent script: {script_path}\n")

    # Use subprocess to run the Python script
    result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)

    # Print the output of the script
    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)

    if result.returncode == 0:
        print("\n✅ Script ran successfully!")
    else:
        print(f"\n❌ Script exited with code {result.returncode}")