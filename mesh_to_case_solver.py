from user_input_calc_functions import *
import os
import subprocess
import sys
import re

def generate_individual_case_files(case_journal_template, project_folder, dimension, solver_cores, save_design_points=None):
    """
    Generate individual case files for each mesh journal file.
    Each case file will reference a different mesh file from the scripts folder.
    
    Parameters:
        case_journal_template (str): Path to the case journal template file
        project_folder (str): Root project folder path
        dimension (int): Simulation dimension (2 or 3)
        solver_cores (int): Number of cores for Fluent solver
        save_design_points (list, optional): List of design point indices (1-based) where case/data files should be saved
    
    Returns:
        list: List of generated case file paths
    """
    # Define paths
    scripts_folder = os.path.join(project_folder, "test_files", "scripts")
    case_files_folder = os.path.join(project_folder, "test_files", "cas_scripts")
    mesh_folder = os.path.join(project_folder, "test_files", "msh")
    output_folder = os.path.join(project_folder, "test_files", "out")
    cas_folder = os.path.join(project_folder, "test_files", "cas")
    
    # Ensure folders exist
    os.makedirs(case_files_folder, exist_ok=True)
    os.makedirs(output_folder, exist_ok=True)
    os.makedirs(cas_folder, exist_ok=True)
    
    # Read the updated DesignPoints.csv to get only successful design points
    design_points_file = os.path.join(project_folder, "test_files", "dps", "DesignPoints.csv")
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
    
    # Find mesh journal files, but only for successful design points
    all_mesh_journal_files = [f for f in os.listdir(scripts_folder) if f.endswith('.jou')]
    print(f"📁 Found {len(all_mesh_journal_files)} total mesh journal files: {all_mesh_journal_files}")
    
    if successful_design_points is not None:
        # Only process mesh files for successful design points
        mesh_journal_files = []
        for dp_idx in successful_design_points:
            # Look for mesh journal file corresponding to this design point
            # Files are named like Geom_dp0_mesh.jou, Geom_dp1_mesh.jou, etc.
            expected_filename = f"Geom_dp{dp_idx}_mesh.jou"
            if expected_filename in all_mesh_journal_files:
                mesh_journal_files.append(expected_filename)
            else:
                print(f"⚠️ Mesh journal file not found for design point {dp_idx}: {expected_filename}")
        
        # Sort the mesh journal files to ensure correct processing order
        mesh_journal_files.sort(key=lambda x: int(x.split('_dp')[1].split('_mesh')[0]))
    else:
        # Fall back to processing all mesh files
        mesh_journal_files = all_mesh_journal_files
        # Sort all files to ensure consistent order
        mesh_journal_files.sort()
    
    if not mesh_journal_files:
        print(f"❌ No mesh journal files found in {scripts_folder}")
        return []
    
    print(f"📁 Processing {len(mesh_journal_files)} mesh journal files: {mesh_journal_files}")
    
    # Read the case journal template
    try:
        with open(case_journal_template, 'r') as f:
            template_content = f.read()
    except Exception as e:
        print(f"❌ Error reading case journal template: {e}")
        return []
    
    # Find the FLUENT_PROD_DIR section in template (similar to generate_master_fluent_script)
    lines = template_content.split('\n')
    start_idx, end_idx = None, None
    
    for i, line in enumerate(lines):
        if "if not os.getenv('FLUENT_PROD_DIR')" in line:
            start_idx = i
        if start_idx is not None and line.strip() == "":
            end_idx = i
            break
    
    if start_idx is None or end_idx is None:
        print("❌ Could not find FLUENT_PROD_DIR block in template")
        return []
    
    # Keep all script lines after setup block
    remaining_lines = lines[end_idx+1:]
    
    # Check for and remove write_case calls, solver.exit(), and print_all_to_console() from template
    # to avoid conflicts with our automated save system
    template_write_calls = []
    template_exit_calls = []
    template_print_calls = []
    filtered_lines = []
    for line in remaining_lines:
        if "write_case" in line.lower() or "write_data" in line.lower():
            template_write_calls.append(line.strip())
            print(f"🗑️ Removing template write_case/write_data() call: {line.strip()}")
        elif "solver.exit" in line:
            template_exit_calls.append(line.strip())
            print(f"🗑️ Removing template solver.exit() call (will be in finally block): {line.strip()}")
        elif "print_all_to_console" in line:
            template_print_calls.append(line.strip())
            print(f"🗑️ Removing template print_all_to_console() call (will save to file instead): {line.strip()}")
        else:
            filtered_lines.append(line)
    
    if template_write_calls or template_exit_calls or template_print_calls:
        removed_count = len(template_write_calls) + len(template_exit_calls) + len(template_print_calls)
        print(f"✅ Removed {removed_count} template calls to prevent conflicts with automated save system.")
        remaining_lines = filtered_lines
    
    # Handle saved design points
    if save_design_points is None:
        # Try to read from saved_design_points.csv file
        saved_dp_file = os.path.join(project_folder, "test_files", "dps", "saved_design_points.csv")
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
    
    # Process each mesh journal file
    generated_case_files = []
    
    for idx, mesh_journal_file in enumerate(mesh_journal_files, 1):
        # Extract mesh file name from journal file name
        mesh_filename = mesh_journal_file.rsplit('_mesh.jou', 1)[0] + '.msh.h5'
        mesh_path = os.path.join(mesh_folder, mesh_filename)
        
        # Create case file name
        case_filename = mesh_journal_file.rsplit('_mesh.jou', 1)[0] + '_case.py'
        case_file_path = os.path.join(case_files_folder, case_filename)
        
        print(f"🔄 Generating case file {idx}/{len(mesh_journal_files)}: {case_filename}")
        
        # Convert save_design_points to string for script
        save_points_str = str(save_design_points) if save_design_points else "None"
        
        # Build the case script content
        # Get path to IMPORTANT FILES FOR AUTOMATION directory for snapshot_functions import
        automation_folder = os.path.dirname(os.path.abspath(__file__))
        case_script_content = f"""import os
import sys
import traceback

# Add IMPORTANT FILES FOR AUTOMATION to path for snapshot_functions import
automation_path = r"{automation_folder}"
if automation_path not in sys.path:
    sys.path.insert(0, automation_path)

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
os.environ.setdefault("MPLBACKEND", "Agg")

import ansys.fluent.core as pyfluent


def main():
    solver = None
    try:
        # Launch Fluent session
        solver = pyfluent.launch_fluent(
            ui_mode='no_gui',
            mode='solver',
            precision='single',
            processor_count={solver_cores},
            dimension={dimension})

        # Read mesh file
        mesh_path = r"{mesh_path}"
        print(f"Reading mesh: {{mesh_path}}")
        solver.settings.file.read_mesh(file_name=mesh_path)

        # Project folder for snapshot generation
        project_folder = r"{project_folder}"

        # Design points to save case/data files
        save_design_points = {save_points_str}

        # Case setup and solve (from template)
"""
        
        # Add the template content (not indented since it's not in a loop)
        # Replace any hardcoded mesh paths with the mesh_path variable
        for line in remaining_lines:
            # Replace hardcoded mesh file paths with mesh_path variable
            if "solver.settings.file.read_mesh" in line and "file_name =" in line:
                # Replace the entire line with a comment since we already read the mesh above
                case_script_content += f"        # Mesh already read above with: solver.settings.file.read_mesh(file_name=mesh_path)\n"
            else:
                case_script_content += "        " + line + "\n"
        
        # Add output saving section
        case_script_content += f"""
        # Save output parameters for this case
        output_folder = r"{output_folder}"
        os.makedirs(output_folder, exist_ok=True)
        output_file = os.path.join(output_folder, f"out_{idx-1}.txt")

        original_stdout = sys.stdout
        with open(output_file, "w", encoding="utf-8") as f:
            sys.stdout = f
            solver.settings.parameters.output_parameters.print_all_to_console()
            sys.stdout = original_stdout

        print(f"[DONE] Output saved to: {{output_file}}")

        # Save case and data files for specified design points
        if save_design_points is not None and {idx-1} in save_design_points:
            cas_folder = r"{cas_folder}"
            os.makedirs(cas_folder, exist_ok=True)
            
            # Generate case and data file names based on design point (0-based)
            case_filename = f"design_point_{idx-1}_case.cas"
            data_filename = f"design_point_{idx-1}_data.dat"
            
            case_path = os.path.join(cas_folder, case_filename)
            data_path = os.path.join(cas_folder, data_filename)
            
            print(f"Saving case file: {{case_filename}}")
            solver.settings.file.write_case(file_name=case_path)
            
            print(f"Saving data file: {{data_filename}}")
            solver.settings.file.write_data(file_name=data_path)
            
            print(f"Case and data files saved for design point {idx-1}")
        
        # Generate snapshots if configured (independent of case/data file saving)
        try:
            from pathlib import Path
            from snapshot_functions import load_snapshot_preferences, generate_snapshots_from_config
            
            project_folder_path = Path(r"{project_folder}")
            snapshot_config_path = project_folder_path / "test_files" / "plots" / "snapshot_config.json"
            
            if snapshot_config_path.exists():
                try:
                    preferences = load_snapshot_preferences(project_folder_path)
                    
                    # Check if this design point should have snapshots
                    if preferences.design_points is not None and {idx-1} in preferences.design_points:
                        print(f"[INFO] Generating snapshots for design point {idx-1}")
                        saved_images = generate_snapshots_from_config(
                            solver=solver,
                            preferences=preferences,
                            design_point_index={idx-1},
                            output_dir=None  # Uses default: project_folder/test_files/plots
                        )
                        if saved_images:
                            print(f"[SUCCESS] Generated {{len(saved_images)}} snapshot(s) for design point {idx-1}")
                        else:
                            print(f"[WARNING] No snapshots generated for design point {idx-1}")
                    else:
                        print(f"[INFO] Design point {idx-1} not in snapshot config design_points list, skipping snapshots")
                except Exception as snapshot_error:
                    print(f"[WARNING] Failed to generate snapshots for design point {idx-1}: {{snapshot_error}}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"[INFO] Snapshot config not found at {{snapshot_config_path}}, skipping snapshots")
        except ImportError as import_error:
            print(f"[WARNING] Could not import snapshot functions: {{import_error}}")
        except Exception as snapshot_error:
            print(f"[WARNING] Error checking snapshot config: {{snapshot_error}}")

        return 0
    except Exception as exc:
        print(f"[ERROR] Sequential case execution failed: {{exc}}")
        traceback.print_exc()
        return 1
    finally:
        if solver is not None:
            try:
                solver.exit()
            except Exception as exit_exc:
                print(f"[WARNING] Failed to close Fluent cleanly: {{exit_exc}}")


if __name__ == "__main__":
    sys.exit(main())
"""
        
        # Write the case file with UTF-8 encoding
        try:
            with open(case_file_path, 'w', encoding='utf-8') as f:
                f.write(case_script_content)
            generated_case_files.append(case_file_path)
            print(f"✅ Generated case file: {case_filename}")
        except Exception as e:
            print(f"❌ Error writing case file {case_filename}: {e}")
    
    print(f"🎯 Generated {len(generated_case_files)} individual case files")
    return generated_case_files



def run_fluent_mesh_case(project_root, fluent_path, meshing_cores):
    """
    Runs mesh to case conversion sequentially using existing generated case files.
    For each mesh: runs mesh journal -> runs case file -> deletes mesh file -> moves to next.
    
    Parameters:
        project_root (str): Root folder of the project
        fluent_path (str): Path to Fluent executable
        solver_cores (int): Number of cores for Fluent solver
        dimension (int): Simulation dimension (2 or 3)
        case_journal_template (str): Path to the case journal template file
    
    Returns:
        list: List of successfully processed case file paths
    """
    
   
    # Define paths
    mesh_journal_folder = os.path.join(project_root, "test_files", "scripts")
    mesh_folder = os.path.join(project_root, "test_files", "msh")
    case_files_folder = os.path.join(project_root, "test_files", "cas_scripts")
    
    # Read the updated DesignPoints.csv to get only successful design points
    design_points_file = os.path.join(project_root, "test_files", "dps", "DesignPoints.csv")
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
    
    # Find mesh journal files, but only for successful design points
    all_mesh_journal_files = [f for f in os.listdir(mesh_journal_folder) if f.endswith('.jou')]
    print(f"📁 Found {len(all_mesh_journal_files)} total mesh journal files: {all_mesh_journal_files}")
    
    if successful_design_points is not None:
        # Only process mesh files for successful design points
        mesh_journal_files = []
        for dp_idx in successful_design_points:
            # Look for mesh journal file corresponding to this design point
            # Files are named like Geom_dp0_mesh.jou, Geom_dp1_mesh.jou, etc.
            expected_filename = f"Geom_dp{dp_idx}_mesh.jou"
            if expected_filename in all_mesh_journal_files:
                mesh_journal_files.append(expected_filename)
            else:
                print(f"⚠️ Mesh journal file not found for design point {dp_idx}: {expected_filename}")
        
        # Sort the mesh journal files to ensure correct processing order
        mesh_journal_files.sort(key=lambda x: int(x.split('_dp')[1].split('_mesh')[0]))
    else:
        # Fall back to processing all mesh files
        mesh_journal_files = all_mesh_journal_files
        # Sort all files to ensure consistent order
        mesh_journal_files.sort()
    
    if not mesh_journal_files:
        print(f"❌ No mesh journal files found in {mesh_journal_folder}")
        return []
    
    print(f"📁 Processing {len(mesh_journal_files)} mesh journal files: {mesh_journal_files}")
    
    processed_files = []
    
    # Process each mesh journal and its corresponding case file
    for idx, mesh_journal_file in enumerate(mesh_journal_files, 1):
        mesh_journal_path = os.path.join(mesh_journal_folder, mesh_journal_file)
        
        # Extract mesh file name from journal file name
        mesh_filename = mesh_journal_file.rsplit('_mesh.jou', 1)[0] + '.msh.h5'
        mesh_path = os.path.join(mesh_folder, mesh_filename)
        
        # Find corresponding case file
        case_filename = mesh_journal_file.rsplit('_mesh.jou', 1)[0] + '_case.py'
        case_file_path = os.path.join(case_files_folder, case_filename)
        
        print(f"\n🔄 Processing {idx}/{len(mesh_journal_files)}: {mesh_filename}")
        
        # Step 1: Run mesh journal
        print(f"🌀 Running mesh journal: {mesh_journal_file}")
        try:
            subprocess.run([fluent_path,
                          "3d",
                          "-meshing",
                          "-hidden",
                          "-g",
                          f"-t{meshing_cores}",
                          "-i", mesh_journal_path])
            print(f"✅ Mesh journal completed: {mesh_journal_file}")
            
            # Clean up .fmd files created by Fluent to save space
            geoms_folder = os.path.join(project_root, "test_files", "geoms")
            if os.path.exists(geoms_folder):
                fmd_files = [f for f in os.listdir(geoms_folder) if f.lower().endswith('.fmd')]
                for fmd_file in fmd_files:
                    fmd_path = os.path.join(geoms_folder, fmd_file)
                    try:
                        os.remove(fmd_path)
                        print(f"🗑️ Deleted .fmd file: {fmd_file}")
                    except Exception as e:
                        print(f"⚠️ Could not delete {fmd_file}: {e}")
                        
        except Exception as e:
            print(f"❌ Error running mesh journal {mesh_journal_file}: {e}")
            continue
        
        # Step 2: Run case file (similar to run_generated_fluent_script)
        print(f"▶ Running case file: {case_filename}")
        try:
            result = subprocess.run([sys.executable, case_file_path], capture_output=True, text=True)
            
            # Print the output of the script (like run_generated_fluent_script)
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print("Errors:", result.stderr)
            
            if result.returncode == 0:
                print(f"✅ Case file completed successfully: {case_filename}")
                processed_files.append(case_file_path)
            else:
                print(f"❌ Case file failed with exit code {result.returncode}: {case_filename}")
                continue
                
        except Exception as e:
            print(f"❌ Error running case file {case_filename}: {e}")
            continue
        
        # Step 3: Delete mesh file to save space
        if os.path.exists(mesh_path):
            try:
                os.remove(mesh_path)
                print(f"🗑️ Deleted mesh file: {mesh_filename}")
            except Exception as e:
                print(f"⚠️ Could not delete mesh file {mesh_filename}: {e}")
        else:
            print(f"⚠️ Mesh file not found: {mesh_filename}")
    
    print(f"\n🎯 Successfully processed {len(processed_files)} out of {len(mesh_journal_files)} files")
    return processed_files





