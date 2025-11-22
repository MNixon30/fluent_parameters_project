"""
Geometry Solver - Simplified workflow that skips geometry and parameter modifications.
This workflow only includes mesh script generation and case solving (batch/sequential).
No post-processing since there's no information on input variables.
"""

import os
from user_input_calc_functions import (
    user_input_project_folder,
    get_simulation_dimension,
    user_input_mesh_cores,
    user_input_solver_cores,
    find_fluent_exe,
    load_setup_from_file,
    save_setup_to_file,
    print_setup_status,
    validate_setup,
    choose_solver_type,
    cleanup_on_exit
)
import folder_management
import mesh_scripts
import batch_solver
import mesh_to_case_solver


def geom_solver_main_menu():
    """
    Main menu for the Geometry Solver workflow.
    Only includes Setup, Solution, and Exit (no Analysis).
    """
    print("\n" + "="*60)
    print("GEOMETRY SOLVER - MAIN MENU")
    print("="*60)
    print("Simplified workflow: Mesh Generation → Case Solving")
    print("(No geometry modifications or post-processing)")
    print("="*60)
    
    while True:
        print("\nChoose an option:")
        print("1. Setup - Configure simulation parameters")
        print("2. Solution - Generate mesh scripts and run solver")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1, 2, or 3): ").strip()
        
        if choice == "1":
            geom_solver_setup_menu()
        elif choice == "2":
            geom_solver_solution_menu()
        elif choice == "3":
            cleanup_on_exit()
            exit()
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")


def geom_solver_setup_menu():
    """
    Simplified setup menu for Geometry Solver workflow.
    Skips geometry and parametric configuration.
    Only includes: project folder, mesh/case journals, dimension, cores, program locations, solver type.
    """
    # Try to load existing setup first
    setup_params = load_setup_from_file() or {}
    
    while True:
        print("\n" + "="*60)
        print("GEOMETRY SOLVER - SETUP MENU")
        print("="*60)
        print("Current configuration status:")
        print_setup_status(setup_params)
        print("\nChoose a setup category:")
        print("1. Project folder")
        print("2. Mesh and case journal files (skip geometry)")
        print("3. Geometry files folder location")
        print("4. Dimension")
        print("5. CPU cores")
        print("6. Fluent executable location")
        print("7. Solver type (batch/sequential)")
        print("8. Save setup and return to main menu")
        print("9. View setup configurations")
        print("10. Cancel setup")
        print("11. Reset all settings")
        
        choice = input("\nEnter your choice (1-11): ").strip()
        
        if choice == "1":
            setup_params['project_folder'] = user_input_project_folder()
        elif choice == "2":
            setup_params['ref_files'] = geom_solver_user_input_files()
        elif choice == "3":
            setup_params['geometry_folder'] = geom_solver_user_input_geometry_folder(setup_params.get('project_folder'))
        elif choice == "4":
            setup_params['dimension'] = get_simulation_dimension()
        elif choice == "5":
            setup_params['meshing_cores'] = user_input_mesh_cores()
            setup_params['solver_cores'] = user_input_solver_cores()
        elif choice == "6":
            setup_params['fluent_path'] = find_fluent_exe()
        elif choice == "7":
            setup_params['solver_type'] = choose_solver_type()
        elif choice == "8":
            validation_result = validate_geom_solver_setup(setup_params)
            if validation_result:
                save_setup_to_file(setup_params)
                print("\n" + "="*60)
                print("SETUP COMPLETE!")
                print("="*60)
                print("All parameters have been configured and saved.")
                print("You can now run 'Solution' to start the simulation.")
                print("="*60)
                return
            else:
                # Show what's missing and ask if user wants to save partial setup
                print("\nSetup incomplete. Some required parameters are missing.")
                save_partial = input("Do you want to save your current progress anyway? (y/n): ").strip().lower()
                if save_partial in ['y', 'yes']:
                    save_setup_to_file(setup_params)
                    print("Partial setup saved. You can continue configuring later.")
                    return
                else:
                    print("Setup not saved. Please configure missing parameters.")
        elif choice == "9":
            print_setup_status(setup_params)
        elif choice == "10":
            print("Returning to main menu.")
            return
        elif choice == "11":
            if input("Are you sure you want to reset all settings? (y/n): ").strip().lower() == 'y':
                setup_params = {}
                print("All settings have been reset.")
        else:
            print("Invalid choice. Please enter 1-11.")


def geom_solver_user_input_files():
    """
    Simplified file input for Geometry Solver.
    Only requires mesh journal and case journal (no geometry file).
    """
    print("\n" + "="*60)
    print("FILE INPUT (Geometry Solver)")
    print("="*60)
    print("Note: Geometry modifications are skipped.")
    print("Only mesh and case journal files are required.")
    print("="*60)
    
    required_files = {
        "mesh_journal": {"prompt": "Enter the mesh journal file path (.jou):", "ext": [".jou", ""]},
        "case_journal": {"prompt": "Enter the case journal file path (.jou):", "ext": [".jou", ""]}
    }

    file_paths = {}
    
    for key, info in required_files.items():
        while True:
            path = input(info["prompt"] + " ").strip(' "\'')
            
            # Check existence
            if not os.path.isfile(path):
                print(f"File not found: {path}")
                continue
            
            # Check extension if specified
            ext = info["ext"]
            if ext:
                if isinstance(ext, list):
                    if not any(path.lower().endswith(e) for e in ext):
                        print(f"File must be one of: {', '.join(ext)}")
                        continue
                else:
                    if not path.lower().endswith(ext):
                        print(f"File must have extension: {ext}")
                        continue
            
            # Valid file
            file_paths[key] = os.path.abspath(path)
            break
    
    print("\nAll files successfully entered:")
    for key, path in file_paths.items():
        print(f"  {key}: {path}")
    
    return file_paths


def geom_solver_user_input_geometry_folder(project_folder=None):
    """
    Prompt user to enter the geometry files folder path.
    Returns the absolute path to the folder.
    """
    print("\n" + "="*60)
    print("GEOMETRY FILES FOLDER")
    print("="*60)
    print("Specify the folder containing your geometry files (.scdoc, .scdocx, .dsco)")
    
    if project_folder:
        default_folder = os.path.join(project_folder, "test_files", "geoms")
        print(f"Default location: {default_folder}")
    
    while True:
        folder = input("Enter the geometry folder path (or press Enter for default): ").strip(' "\'')
        
        # Use default if empty
        if not folder and project_folder:
            folder = default_folder
            print(f"Using default folder: {folder}")
        
        if not folder:
            print("Folder path cannot be empty.")
            continue
        
        if not os.path.isdir(folder):
            print(f"Folder not found: {folder}")
            create = input("Create this folder? (y/n): ").strip().lower()
            if create == 'y':
                try:
                    os.makedirs(folder, exist_ok=True)
                    print(f"Created folder: {folder}")
                except Exception as e:
                    print(f"Could not create folder: {e}")
                    continue
            else:
                continue
        
        # Check if folder contains geometry files
        geom_files = [f for f in os.listdir(folder) if f.lower().endswith(('.scdoc', '.scdocx', '.dsco'))]
        if geom_files:
            print(f"Found {len(geom_files)} geometry file(s) in folder:")
            for f in geom_files[:5]:  # Show first 5
                print(f"  - {f}")
            if len(geom_files) > 5:
                print(f"  ... and {len(geom_files) - 5} more")
        else:
            print("Warning: No geometry files found in this folder.")
            continue_anyway = input("Continue anyway? (y/n): ").strip().lower()
            if continue_anyway != 'y':
                continue
        
        folder = os.path.abspath(folder)
        print(f"Using geometry folder: {folder}")
        return folder


def validate_geom_solver_setup(setup_params):
    """
    Validate setup parameters for Geometry Solver workflow.
    Checks for required fields (without geometry file).
    """
    required_fields = [
        'project_folder',
        'ref_files',
        'geometry_folder',
        'dimension',
        'meshing_cores',
        'solver_cores',
        'fluent_path',
        'solver_type'
    ]
    
    missing_fields = []
    for field in required_fields:
        if field not in setup_params or setup_params[field] is None:
            missing_fields.append(field)
        elif field == 'ref_files':
            # Check that mesh_journal and case_journal are present
            if 'mesh_journal' not in setup_params['ref_files'] or 'case_journal' not in setup_params['ref_files']:
                missing_fields.append('ref_files (missing mesh_journal or case_journal)')
    
    if missing_fields:
        print("\nMissing required parameters:")
        for field in missing_fields:
            print(f"  - {field}")
        return False
    
    # Validate file paths
    ref_files = setup_params['ref_files']
    for file_type, file_path in ref_files.items():
        if not os.path.isfile(file_path):
            print(f"\nFile not found: {file_type} = {file_path}")
            return False
    
    # Validate folder exists
    if not os.path.isdir(setup_params['project_folder']):
        print(f"\nProject folder not found: {setup_params['project_folder']}")
        return False
    
    # Validate Fluent executable exists
    if not os.path.isfile(setup_params['fluent_path']):
        print(f"\nFluent executable not found: {setup_params['fluent_path']}")
        return False
    
    # Validate dimension
    if setup_params['dimension'] not in [2, 3]:
        print(f"\nInvalid dimension: {setup_params['dimension']} (must be 2 or 3)")
        return False
    
    # Validate solver type
    if setup_params['solver_type'] not in ['batch', 'sequential']:
        print(f"\nInvalid solver type: {setup_params['solver_type']} (must be 'batch' or 'sequential')")
        return False
    
    print("\nAll required parameters are valid!")
    return True


def geom_solver_solution_menu():
    """
    Simplified solution menu for Geometry Solver workflow.
    Only includes mesh script generation and case solving.
    No design points, parameter modifications, or post-processing.
    """
    print("\n" + "="*60)
    print("GEOMETRY SOLVER - SOLUTION MENU")
    print("="*60)
    
    # Try to load existing setup
    setup_params = load_setup_from_file()
    
    if setup_params is None:
        print("No setup found! Please run 'Setup' first.")
        print("="*60)
        return
    
    # Validate setup
    if not validate_geom_solver_setup(setup_params):
        print("Setup is incomplete. Please complete the setup first.")
        return
    
    print("Loaded existing setup configuration.")
    print("="*60)
    
    while True:
        print("\n" + "="*60)
        print("SOLUTION WORKFLOW")
        print("="*60)
        print("\nChoose a solution step:")
        print("1. Create folders and prepare files")
        print("2. Generate mesh scripts")
        print("3. Run meshing (generate mesh files)")
        print("4. Generate case scripts")
        print("5. Run case solving (batch or sequential)")
        print("6. Return to main menu")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == "1":
            # Create folders and move files
            print("\nSTEP 1: PREPARE FILES AND FOLDERS")
            print("="*40)
            
            project_folder = setup_params['project_folder']
            ref_files = setup_params['ref_files']
            
            # Create folders
            folder_management.create_folders(project_root=project_folder)
            
            # Move journal files to project folder
            updated_ref_paths = {}
            journal_folder = os.path.join(project_folder, "test_files", "jou")
            os.makedirs(journal_folder, exist_ok=True)
            
            import shutil
            for file_type, file_path in ref_files.items():
                if file_type in ['mesh_journal', 'case_journal']:
                    dest_path = os.path.join(journal_folder, os.path.basename(file_path))
                    shutil.copy2(file_path, dest_path)
                    updated_ref_paths[file_type] = dest_path
                    print(f"Copied {file_type}: {os.path.basename(file_path)}")
            
            # Update setup params with updated paths
            setup_params['ref_files'] = updated_ref_paths
            save_setup_to_file(setup_params)
            
            print("\nFiles prepared successfully!")
            
        elif choice == "2":
            # Generate mesh scripts
            print("\nSTEP 2: GENERATE MESH SCRIPTS")
            print("="*40)
            
            project_folder = setup_params['project_folder']
            mesh_journal = setup_params['ref_files'].get('mesh_journal')
            
            if not mesh_journal or not os.path.exists(mesh_journal):
                print("Mesh journal file not found. Please complete step 1 first.")
                continue
            
            # Get geometry folder from setup (or use default)
            geom_folder = setup_params.get('geometry_folder')
            if not geom_folder:
                # Fall back to default location
                geom_folder = os.path.join(project_folder, "test_files", "geoms")
                print(f"Warning: Geometry folder not specified in setup. Using default: {geom_folder}")
            
            if not os.path.exists(geom_folder):
                print(f"Error: Geometry folder not found: {geom_folder}")
                print("Please configure the geometry folder in Setup menu (option 3).")
                continue
            
            # Check if geometry files exist
            geom_files = [f for f in os.listdir(geom_folder) if f.lower().endswith(('.scdoc', '.scdocx', '.dsco'))]
            if not geom_files:
                print(f"Error: No geometry files found in: {geom_folder}")
                print("Please ensure geometry files (.scdoc, .scdocx, .dsco) are in the geometry folder.")
                continue
            
            print(f"Found {len(geom_files)} geometry file(s) in folder")
            
            # Clean journal
            mesh_scripts.clean_journal(mesh_journal)
            
            # Calculate relative path from project root for mesh_scripts function
            # mesh_scripts joins the path with project_root using os.path.join
            # If the path is absolute, os.path.join ignores project_root, so we need relative path
            try:
                # Try to get relative path if geom_folder is within project_folder
                common_path = os.path.commonpath([project_folder, geom_folder])
                if common_path == project_folder or common_path == geom_folder:
                    # geom_folder is within project_folder or they're the same
                    geom_folder_rel = os.path.relpath(geom_folder, project_folder)
                    # Convert Windows path separators to forward slashes for consistency
                    geom_folder_rel = geom_folder_rel.replace('\\', '/')
                else:
                    print(f"Warning: Geometry folder is outside project folder.")
                    print(f"Project folder: {project_folder}")
                    print(f"Geometry folder: {geom_folder}")
                    print(f"Common path: {common_path}")
                    print("The geometry folder should ideally be within the project folder.")
                    continue
            except ValueError:
                # If paths are on different drives (Windows), os.path.commonpath raises ValueError
                print(f"Error: Geometry folder is on a different drive than project folder.")
                print(f"Project folder: {project_folder}")
                print(f"Geometry folder: {geom_folder}")
                print("Please ensure geometry folder is within or on the same drive as project folder.")
                continue
            
            # Generate mesh scripts
            try:
                mesh_scripts.generate_meshing_scripts_auto(
                    project_root=project_folder,
                    journal_template=mesh_journal,
                    geom_folder=geom_folder_rel
                )
                print("\nMesh scripts generated successfully!")
            except Exception as e:
                print(f"Error generating mesh scripts: {e}")
                import traceback
                traceback.print_exc()
            
        elif choice == "3":
            # Run meshing
            print("\nSTEP 3: RUN MESHING")
            print("="*40)
            
            project_folder = setup_params['project_folder']
            fluent_path = setup_params.get('fluent_path')
            meshing_cores = setup_params.get('meshing_cores')
            
            if not fluent_path:
                print("Fluent path not configured. Please complete setup first.")
                continue
            
            script_folder = os.path.join(project_folder, "test_files", "scripts")
            if not os.path.exists(script_folder):
                print(f"Mesh scripts folder not found: {script_folder}")
                print("Please generate mesh scripts first (step 2).")
                continue
            
            # Check if scripts exist
            mesh_scripts_list = [f for f in os.listdir(script_folder) if f.endswith('.jou')]
            if not mesh_scripts_list:
                print(f"No mesh journal scripts found in {script_folder}")
                print("Please generate mesh scripts first (step 2).")
                continue
            
            print(f"Found {len(mesh_scripts_list)} mesh journal scripts")
            confirm = input("\nProceed with meshing? (y/n): ").strip().lower()
            
            if confirm == 'y':
                try:
                    batch_solver.run_meshing_scripts(
                        project_root=project_folder,
                        fluent_path=fluent_path,
                        meshing_cores=meshing_cores
                    )
                    print("\nMeshing completed!")
                except Exception as e:
                    print(f"Error during meshing: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("Meshing cancelled.")
            
        elif choice == "4":
            # Generate case scripts
            print("\nSTEP 4: GENERATE CASE SCRIPTS")
            print("="*40)
            
            project_folder = setup_params['project_folder']
            case_journal = setup_params['ref_files'].get('case_journal')
            dimension = setup_params.get('dimension')
            solver_cores = setup_params.get('solver_cores')
            
            if not case_journal or not os.path.exists(case_journal):
                print("Case journal file not found. Please complete step 1 first.")
                continue
            
            # Check if mesh files exist
            mesh_folder = os.path.join(project_folder, "test_files", "msh")
            if not os.path.exists(mesh_folder):
                print(f"Mesh folder not found: {mesh_folder}")
                print("Please run meshing first (step 3).")
                continue
            
            mesh_files = [f for f in os.listdir(mesh_folder) if f.lower().endswith(('.msh', '.msh.h5'))]
            if not mesh_files:
                print(f"No mesh files found in {mesh_folder}")
                print("Please run meshing first (step 3).")
                continue
            
            print(f"Found {len(mesh_files)} mesh files")
            
            # Ask if user wants to save case/data files for any design points
            save_design_points = None
            save_choice = input("\nSave case/data files for specific design points? (y/n): ").strip().lower()
            if save_choice == 'y':
                try:
                    points_input = input("Enter design point indices (comma-separated, e.g., 1,5,10) or press Enter for none: ").strip()
                    if points_input:
                        save_design_points = [int(x.strip()) for x in points_input.split(',')]
                        print(f"Will save case/data files for design points: {save_design_points}")
                except ValueError:
                    print("Invalid input. Proceeding without saving case/data files.")
            
            try:
                solver_type = setup_params.get('solver_type', 'batch')
                
                if solver_type == 'batch':
                    # Generate batch solver script
                    batch_solver.generate_master_fluent_script(
                        case_journal_template=case_journal,
                        project_folder=project_folder,
                        dimension=dimension,
                        solver_cores=solver_cores,
                        save_design_points=save_design_points
                    )
                    print("\nBatch solver script generated successfully!")
                else:
                    # Generate individual case files for sequential solving
                    mesh_to_case_solver.generate_individual_case_files(
                        case_journal_template=case_journal,
                        project_folder=project_folder,
                        dimension=dimension,
                        solver_cores=solver_cores,
                        save_design_points=save_design_points
                    )
                    print("\nIndividual case scripts generated successfully!")
                    
            except Exception as e:
                print(f"Error generating case scripts: {e}")
                import traceback
                traceback.print_exc()
            
        elif choice == "5":
            # Run case solving
            print("\nSTEP 5: RUN CASE SOLVING")
            print("="*40)
            
            project_folder = setup_params['project_folder']
            solver_type = setup_params.get('solver_type', 'batch')
            
            if solver_type == 'batch':
                # Run batch solver
                cas_scripts_folder = os.path.join(project_folder, "test_files", "cas_scripts")
                batch_script = os.path.join(cas_scripts_folder, "run_all_cases.py")
                
                if not os.path.exists(batch_script):
                    print(f"Batch solver script not found: {batch_script}")
                    print("Please generate case scripts first (step 4).")
                    continue
                
                print(f"Found batch solver script: {os.path.basename(batch_script)}")
                confirm = input("\nProceed with batch solving? (y/n): ").strip().lower()
                
                if confirm == 'y':
                    try:
                        batch_solver.run_generated_fluent_script(project_root=project_folder)
                        print("\nBatch solving completed!")
                    except Exception as e:
                        print(f"Error during batch solving: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print("Batch solving cancelled.")
                    
            else:
                # Run sequential solver
                cas_scripts_folder = os.path.join(project_folder, "test_files", "cas_scripts")
                
                if not os.path.exists(cas_scripts_folder):
                    print(f"Case scripts folder not found: {cas_scripts_folder}")
                    print("Please generate case scripts first (step 4).")
                    continue
                
                case_scripts = [f for f in os.listdir(cas_scripts_folder) if f.endswith('.py')]
                if not case_scripts:
                    print(f"No case scripts found in {cas_scripts_folder}")
                    print("Please generate case scripts first (step 4).")
                    continue
                
                print(f"Found {len(case_scripts)} case scripts")
                confirm = input("\nProceed with sequential solving? (y/n): ").strip().lower()
                
                if confirm == 'y':
                    try:
                        # Run case Python files sequentially
                        import subprocess
                        import re
                        
                        # Sort case scripts by design point index
                        def extract_dp_index(script_name):
                            dp_match = re.search(r'_dp(\d+)_', script_name)
                            return int(dp_match.group(1)) if dp_match else 999999
                        
                        case_scripts.sort(key=extract_dp_index)
                        
                        successful = 0
                        failed = 0
                        
                        for idx, case_script in enumerate(case_scripts, 1):
                            script_path = os.path.join(cas_scripts_folder, case_script)
                            print(f"\nRunning {idx}/{len(case_scripts)}: {case_script}")
                            
                            try:
                                result = subprocess.run(
                                    ["python", script_path],
                                    cwd=project_folder,
                                    check=False
                                )
                                
                                if result.returncode == 0:
                                    successful += 1
                                    print(f"Completed: {case_script}")
                                else:
                                    failed += 1
                                    print(f"Failed: {case_script} (exit code: {result.returncode})")
                            except Exception as e:
                                failed += 1
                                print(f"Error running {case_script}: {e}")
                        
                        print(f"\nSequential solving completed!")
                        print(f"   Successful: {successful}/{len(case_scripts)}")
                        if failed > 0:
                            print(f"   Failed: {failed}/{len(case_scripts)}")
                    except Exception as e:
                        print(f"Error during sequential solving: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print("Sequential solving cancelled.")
            
        elif choice == "6":
            print("Returning to main menu.")
            return
        else:
            print("Invalid choice. Please enter 1-6.")


# Main entry point
if __name__ == "__main__":
    geom_solver_main_menu()

