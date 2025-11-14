import os
import subprocess
import re
import sys

def run_meshing_scripts(project_root, fluent_path, meshing_cores):
    """
    Runs all Fluent 2D/3D meshing journal scripts stored in <project_root>\test_files\scripts automatically.
    
    Parameters:
        project_root (str): Root folder of the project.
        fluent_path (str): Path to the Fluent executable.
        meshing_cores (int): Number of cores for meshing.
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
    all_mesh_files = [f for f in os.listdir(mesh_folder) if f.lower().endswith((".msh", ".msh.h5"))]
    
    if not all_mesh_files:
        raise FileNotFoundError(f"No mesh files found in {mesh_folder}")
    
    # Read the updated DesignPoints.csv to get only successful design points
    design_points_file = os.path.join(project_folder_path, "test_files", "dps", "DesignPoints.csv")
    successful_design_points = []
    
    if os.path.exists(design_points_file):
        try:
            import csv
            with open(design_points_file, 'r') as f:
                reader = csv.reader(f)
                header = next(reader)  # Skip header
                row_index = 0  # Design point index starts from 0
                for row in reader:
                    if row:  # Skip empty rows
                        successful_design_points.append(row_index)  # Use row index as design point index
                        row_index += 1
            print(f"📊 Found {len(successful_design_points)} successful design points: {successful_design_points}")
        except Exception as e:
            print(f"⚠️ Error reading DesignPoints.csv: {e}")
            # Fall back to processing all mesh files
            successful_design_points = None
    else:
        print("⚠️ DesignPoints.csv not found, will process all mesh files")
        successful_design_points = None
    
    # Filter mesh files to only include successful design points
    if successful_design_points is not None:
        mesh_files = []
        for dp_idx in successful_design_points:
            # Look for mesh file corresponding to this design point
            # Files are named like Geom_dp0.msh.h5, Geom_dp1.msh.h5, etc.
            expected_filename = f"Geom_dp{dp_idx}.msh.h5"
            if expected_filename in all_mesh_files:
                mesh_files.append(expected_filename)
            else:
                print(f"⚠️ Mesh file not found for design point {dp_idx}: {expected_filename}")
        print(f"📁 Processing {len(mesh_files)} mesh files for successful design points: {mesh_files}")
    else:
        # Fall back to processing all mesh files
        mesh_files = all_mesh_files
        print(f"📁 Processing all {len(mesh_files)} mesh files: {mesh_files}")
    
    if not mesh_files:
        raise FileNotFoundError(f"No mesh files found for successful design points in {mesh_folder}")

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
    # Also remove solver.exit() calls and print_all_to_console() calls since we handle those separately
    mesh_read_pattern = re.compile(r"solver\.settings\.file\.read_mesh\(file_name\s*=\s*r?['\"].*?['\"]\)")
    solver_exit_pattern = re.compile(r"solver\.exit\s*\(\s*\)")
    print_output_pattern = re.compile(r"solver\.settings\.parameters\.output_parameters\.print_all_to_console\s*\(\s*\)")
    processed_lines = []
    for line in remaining_lines:
        # Skip solver.exit() calls - we'll add one at the end after the loop
        if solver_exit_pattern.search(line):
            print(f"🗑️ Removing solver.exit() call from template: {line.strip()}")
            continue
        # Skip print_all_to_console() calls - we'll save to file instead
        if print_output_pattern.search(line):
            print(f"🗑️ Removing print_all_to_console() call from template (will save to file instead): {line.strip()}")
            continue
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

    # --- Handle saved design points ---
    if save_design_points is None:
        # Try to read from saved_design_points.csv file
        saved_dp_file = os.path.join(project_folder_path, "test_files", "dps", "saved_design_points.csv")
        if os.path.exists(saved_dp_file):
            try:
                import csv
                with open(saved_dp_file, 'r') as f:
                    reader = csv.reader(f)
                    header = next(reader)  # Skip header
                    save_design_points = []
                    for row in reader:
                        if row:  # Skip empty rows
                            save_design_points.append(int(row[0]))
                print(f"Loaded adjusted saved design points: {save_design_points}")
            except Exception as e:
                print(f"Error reading saved design points file: {e}")
                save_design_points = None
        else:
            save_design_points = None
    
    # --- Convert save_design_points to string for script ---
    save_points_str = str(save_design_points) if save_design_points else "None"
    
    # --- Build one unified script ---
    # Get path to IMPORTANT FILES FOR AUTOMATION directory (where snapshot_functions.py is located)
    # This assumes batch_solver.py is in the IMPORTANT FILES FOR AUTOMATION directory
    automation_folder = os.path.dirname(os.path.abspath(__file__))
    unified_script = f"""import os
import sys

# Add IMPORTANT FILES FOR AUTOMATION to path for snapshot_functions import
# This allows the generated script to import snapshot_functions module
automation_path = r"{automation_folder}"
if automation_path not in sys.path:
    sys.path.insert(0, automation_path)

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
os.environ.setdefault("MPLBACKEND", "Agg")

import ansys.fluent.core as pyfluent

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
    if save_design_points is not None and (idx-1) in save_design_points:
        cas_folder = os.path.join(r"{project_folder_path}", "test_files", "cas")
        os.makedirs(cas_folder, exist_ok=True)
        
        # Generate case and data file names based on design point (0-based)
        case_filename = f"design_point_{{idx-1}}_case.cas"
        data_filename = f"design_point_{{idx-1}}_data.dat"
        
        case_path = os.path.join(cas_folder, case_filename)
        data_path = os.path.join(cas_folder, data_filename)
        
        print(f"Saving case file: {{case_filename}}")
        solver.settings.file.write_case(file_name=case_path)
        
        print(f"Saving data file: {{data_filename}}")
        solver.settings.file.write_data(file_name=data_path)
        
        print(f"Case and data files saved for design point {{idx-1}}")
    
    # --- Generate snapshots if configured (independent of case/data file saving) ---
    try:
        from pathlib import Path
        from snapshot_functions import load_snapshot_preferences, generate_snapshots_from_config
        
        project_folder = Path(r"{project_folder_path}")
        snapshot_config_path = project_folder / "test_files" / "plots" / "snapshot_config.json"
        
        if snapshot_config_path.exists():
            try:
                preferences = load_snapshot_preferences(project_folder)
                
                # Check if this design point should have snapshots
                if preferences.design_points is not None and (idx-1) in preferences.design_points:
                    print(f"[INFO] Generating snapshots for design point {{idx-1}}")
                    saved_images = generate_snapshots_from_config(
                        solver=solver,
                        preferences=preferences,
                        design_point_index=(idx-1),
                        output_dir=None  # Uses default: project_folder/test_files/plots
                    )
                    if saved_images:
                        print(f"[SUCCESS] Generated {{len(saved_images)}} snapshot(s) for design point {{idx-1}}")
                    else:
                        print(f"[WARNING] No snapshots generated for design point {{idx-1}}")
                else:
                    print(f"[INFO] Design point {{idx-1}} not in snapshot config design_points list, skipping snapshots")
            except Exception as snapshot_error:
                print(f"[WARNING] Failed to generate snapshots for design point {{idx-1}}: {{snapshot_error}}")
                import traceback
                traceback.print_exc()
        else:
            print(f"[INFO] Snapshot config not found at {{snapshot_config_path}}, skipping snapshots")
    except ImportError as import_error:
        print(f"[WARNING] Could not import snapshot functions: {{import_error}}")
    except Exception as snapshot_error:
        print(f"[WARNING] Error checking snapshot config: {{snapshot_error}}")

# --- Close Fluent session after all cases are processed ---
solver.exit()
print("\\n[INFO] All cases processed. Fluent session closed.")
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