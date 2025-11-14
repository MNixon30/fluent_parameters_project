import os
import csv
from datetime import datetime

from graph_functions_user_input import run_graph_menu

try:
    from snapshot_user_inputs import main as run_snapshot_user_inputs
    SNAPSHOT_AVAILABLE = True
except ImportError:
    SNAPSHOT_AVAILABLE = False
    print("Warning: Snapshot user input module not available. Snapshot configuration will be disabled.")

try:
    from skopt.sampler import Lhs
    from skopt.space import Space
    from ansys.fluent.core.filereader.case_file import CaseFile
    SKOPT_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Required modules not available: {e}")
    print("Some features may be limited. Please install required packages.")
    SKOPT_AVAILABLE = False












def user_input_project_folder():
    """
    Prompt the user to enter a project folder path.
    Returns the absolute path to the folder.
    """
    while True:
        folder = input("Enter the project folder path: ").strip()
        if not os.path.isdir(folder):
            print(f"❌ Folder not found: {folder}")
        else:
            folder = os.path.abspath(folder)
            print(f"📂 Using project folder: {folder}")
            return folder




def user_input_files():
    """
    Prompt the user to input 5 required files:
    - Geometry file
    - Mesh file (.msh)
    - Case file (.cas or .cas.h5)
    - Mesh journal file (.jou)
    - Case journal file (.jou)
    
    Returns:
        dict: Keys are descriptive names, values are full file paths.
    """
    
    required_files = {
        "geometry_file": {"prompt": "Enter the geometry file path (must be spaceclaim file):", "ext": None},
        "mesh_file": {"prompt": "Enter the mesh file path (.msh):", "ext": [".msh", ".msh.h5"]},
        "case_file": {"prompt": "Enter the case file path (.cas or .cas.h5):", "ext": [".cas", ".cas.h5"]},
        "mesh_journal": {"prompt": "Enter the mesh journal file path:", "ext": [".jou", ""]},
        "case_journal": {"prompt": "Enter the case journal file path:", "ext": [".jou", ""]}
    }

    file_paths = {}
    
    for key, info in required_files.items():
        while True:
            path = input(info["prompt"] + " ").strip(' "\'')
            
            # Check existence
            if not os.path.isfile(path):
                print(f"❌ File not found: {path}")
                continue
            
            # Check extension if specified
            ext = info["ext"]
            if ext:
                if isinstance(ext, list):
                    if not any(path.lower().endswith(e) for e in ext):
                        print(f"❌ File must be one of: {', '.join(ext)}")
                        continue
                else:
                    if not path.lower().endswith(ext):
                        print(f"❌ File must have extension: {ext}")
                        continue
            
            # Valid file
            file_paths[key] = os.path.abspath(path)
            break
    
    print("\n✅ All files successfully entered:")
    for k, v in file_paths.items():
        print(f"  {k}: {v}")
    
    return file_paths



def get_simulation_dimension():
    """
    Prompt the user to enter the simulation dimension (2 or 3) and return it as an integer.
    
    Returns:
        int: 2 or 3, representing the simulation dimension.
    """
    dimension = None
    while dimension not in [2, 3]:
        try:
            user_input = input("What dimension is this simulation? Enter 2 or 3: ")
            dimension = int(user_input)
            if dimension not in [2, 3]:
                print("Invalid input. Please enter 2 or 3.")
        except ValueError:
            print("Invalid input. Please enter a number (2 or 3).")
    return dimension



def user_input_mesh_cores():
    """
    Prompt the user to enter the number of processor cores for meshing execution.
    Provides recommendations based on available cores.
    
    Returns:
        int: Number of cores for meshing.
    """
    import os
    max_cores = os.cpu_count()  # Get system's maximum core count
    
    # Calculate recommended meshing cores
    if max_cores <= 4:
        recommended_meshing = max(1, max_cores - 1)
    elif max_cores <= 8:
        recommended_meshing = max_cores // 2
    else:
        recommended_meshing = max_cores // 2
    
    print(f"\n💻 Available cores: {max_cores}")
    print(f"📋 Recommended meshing cores: {recommended_meshing}")
    
    # Get meshing cores
    while True:
        try:
            meshing_input = input(f"Enter number of cores for meshing (1-{max_cores}, recommended: {recommended_meshing}): ")
            if meshing_input.strip() == "":
                meshing_cores = recommended_meshing
                print(f"✅ Using recommended meshing cores: {meshing_cores}")
                break
            meshing_cores = int(meshing_input)
            if 1 <= meshing_cores <= max_cores:
                print(f"✅ Using {meshing_cores} cores for meshing")
                break
            else:
                print(f"❌ Invalid input. Please enter a number between 1 and {max_cores}.")
        except ValueError:
            print("❌ Invalid input. Please enter a valid number.")
    
    return meshing_cores


def user_input_solver_cores():
    """
    Prompt the user to enter the number of processor cores for solver execution.
    Provides recommendations based on available cores.
    
    Returns:
        int: Number of cores for solver.
    """
    import os
    max_cores = os.cpu_count()  # Get system's maximum core count
    
    # Calculate recommended solver cores
    if max_cores <= 4:
        recommended_solver = max(1, max_cores - 1)
    elif max_cores <= 8:
        recommended_solver = max_cores - 2
    else:
        recommended_solver = max_cores - 2
    
    print(f"\n💻 Available cores: {max_cores}")
    print(f"📋 Recommended solver cores: {recommended_solver}")
    
    # Get solver cores
    while True:
        try:
            solver_input = input(f"Enter number of cores for solver (1-{max_cores}, recommended: {recommended_solver}): ")
            if solver_input.strip() == "":
                solver_cores = recommended_solver
                print(f"✅ Using recommended solver cores: {solver_cores}")
                break
            solver_cores = int(solver_input)
            if 1 <= solver_cores <= max_cores:
                print(f"✅ Using {solver_cores} cores for solver")
                break
            else:
                print(f"❌ Invalid input. Please enter a number between 1 and {max_cores}.")
        except ValueError:
            print("❌ Invalid input. Please enter a valid number.")
    
    return solver_cores



def find_spaceclaim_exe():
    """
    Locate the SpaceClaim executable on a Windows PC.
    Provides option to specify path manually or use auto-detection.

    Returns:
        str: Full path to SpaceClaim.exe if found, else None.
    """
    print("\n🔍 SpaceClaim Executable Location:")
    print("1. Auto-detect SpaceClaim.exe")
    print("2. Specify path manually")
    
    while True:
        choice = input("Choose option (1 or 2): ").strip()
        if choice == "1":
            # Auto-detect logic
            exe_name = "SpaceClaim.exe"
            likely_dirs = [
                r"C:\Program Files\ANSYS Inc",
                r"C:\Program Files (x86)\ANSYS Inc",
                r"C:\Program Files",
                r"C:\Program Files (x86)"
            ]

            print("🔍 Auto-detecting SpaceClaim.exe...")

            # Search likely directories first
            for base_dir in likely_dirs:
                for root, dirs, files in os.walk(base_dir):
                    if exe_name in files:
                        found_path = os.path.join(root, exe_name)
                        print(f"✅ SpaceClaim found: {found_path}")
                        return found_path

            # Optional: fallback to full C: drive (slower)
            print("⚠️ Not found in common directories, searching entire C: drive...")
            for root, dirs, files in os.walk(r"C:\\"):
                if exe_name in files:
                    found_path = os.path.join(root, exe_name)
                    print(f"✅ SpaceClaim found: {found_path}")
                    return found_path

            print("❌ SpaceClaim.exe not found automatically.")
            return None
            
        elif choice == "2":
            # Manual path logic
            while True:
                path = input("Enter the full path to SpaceClaim.exe: ").strip(' "\'')
                
                if not path:
                    print("❌ Path cannot be empty.")
                    continue
                    
                # Check if file exists
                if not os.path.isfile(path):
                    print(f"❌ File not found: {path}")
                    continue
                    
                # Check if it's actually SpaceClaim.exe
                if not path.lower().endswith("spaceclaim.exe"):
                    print("❌ File must be SpaceClaim.exe")
                    continue
                    
                print(f"✅ SpaceClaim path confirmed: {path}")
                return os.path.abspath(path)
        else:
            print("❌ Invalid choice. Please enter 1 or 2.")



def find_fluent_exe():
    """
    Locate the Fluent executable on a Windows PC.
    Provides option to specify path manually or use auto-detection.

    Returns:
        str: Full path to fluent.exe if found, else None.
    """
    print("\n🔍 Fluent Executable Location:")
    print("1. Auto-detect fluent.exe")
    print("2. Specify path manually")
    
    while True:
        choice = input("Choose option (1 or 2): ").strip()
        if choice == "1":
            # Auto-detect logic
            exe_name = "fluent.exe"
            likely_dirs = [
                r"C:\Program Files\ANSYS Inc",
                r"C:\Program Files (x86)\ANSYS Inc",
                r"C:\Program Files",
                r"C:\Program Files (x86)"
            ]

            print("🔍 Auto-detecting fluent.exe...")

            # Search likely directories first
            for base_dir in likely_dirs:
                for root, dirs, files in os.walk(base_dir):
                    if exe_name in files:
                        found_path = os.path.join(root, exe_name)
                        print(f"✅ Fluent found: {found_path}")
                        return found_path

            # Optional: fallback to full C: drive (slower)
            print("⚠️ Not found in common directories, searching entire C: drive...")
            for root, dirs, files in os.walk(r"C:\\"):
                if exe_name in files:
                    found_path = os.path.join(root, exe_name)
                    print(f"✅ Fluent found: {found_path}")
                    return found_path

            print("❌ fluent.exe not found automatically.")
            return None
            
        elif choice == "2":
            # Manual path logic
            while True:
                path = input("Enter the full path to fluent.exe: ").strip(' "\'')
                
                if not path:
                    print("❌ Path cannot be empty.")
                    continue
                    
                # Check if file exists
                if not os.path.isfile(path):
                    print(f"❌ File not found: {path}")
                    continue
                    
                # Check if it's actually fluent.exe
                if not path.lower().endswith("fluent.exe"):
                    print("❌ File must be fluent.exe")
                    continue
                    
                print(f"✅ Fluent path confirmed: {path}")
                return os.path.abspath(path)
        else:
            print("❌ Invalid choice. Please enter 1 or 2.")



def choose_solver_type():
    """
    Prompt the user to choose between batch mesh processing or sequential mesh-case processing.
    
    Returns:
        str: 'batch' for batch processing or 'sequential' for mesh-case processing
    """
    print("\n" + "="*60)
    print("🔧 SOLVER TYPE SELECTION")
    print("="*60)
    print("Choose your processing method:")
    print("1. Batch Processing - Generate all meshes, then solve all cases together")
    print("   • Faster for large datasets")
    print("   • Uses more disk space (keeps all mesh files)")
    print("   • Traditional approach")
    print()
    print("2. Sequential Processing - Mesh one case, solve it, delete mesh, repeat")
    print("   • Uses less disk space (deletes mesh files after processing)")
    print("   • More memory efficient")
    print("   • Recommended for limited storage")
    print("="*60)
    
    while True:
        choice = input("Enter your choice (1 or 2): ").strip()
        
        if choice == "1":
            print("✅ Selected: Batch Processing")
            return "batch"
        elif choice == "2":
            print("✅ Selected: Sequential Processing")
            return "sequential"
        else:
            print("❌ Invalid choice. Please enter 1 or 2.")


def start_calculation():
    """
    Asks the user if they want to begin the calculation process.
    Provides a final confirmation before starting the computationally intensive operations.
    
    Returns:
        bool: True if user wants to proceed, False if they want to cancel.
    """
    print("\n" + "="*60)
    print("🚀 READY TO START CALCULATION")
    print("="*60)
    print("All setup is complete. The following operations will now begin:")
    print("• SpaceClaim geometry generation")
    print("• Fluent meshing")
    print("• CFD solving")
    print("• Post-processing")
    print("\n⚠️  This process may take several hours depending on your setup.")
    print("="*60)
    
    while True:
        choice = input("\nDo you want to begin calculation? (y/n): ").strip().lower()
        
        if choice in ['y', 'yes']:
            print("\n✅ Starting calculation process...")
            return True
        elif choice in ['n', 'no']:
            print("\n❌ Calculation cancelled by user.")
            return False
        else:
            print("❌ Please enter 'y' for yes or 'n' for no.")


def get_design_points_to_save(num_design_points, project_folder):
    """
    Asks the user which design points should have case and data files saved.
    Creates a CSV file to track which design points should be saved.
    
    Args:
        num_design_points (int): Total number of design points that will be generated
        project_folder (str): Project folder path where CSV will be saved
    
    Returns:
        list: List of design point indices (0-based) to save, or None if none selected.
    """
    print("\n" + "="*60)
    print("💾 CASE/DATA FILE SAVING")
    print("="*60)
    print(f"You have {num_design_points} design points that will be generated.")
    print("You can save case (.cas) and data (.dat) files for specific design points.")
    print("These files contain the complete Fluent solution and can be used to:")
    print("• Restart simulations")
    print("• Post-process specific cases")
    print("• Share results with others")
    print("="*60)
    
    while True:
        choice = input("\nDo you want to save case/data files for any design points? (y/n): ").strip().lower()
        
        if choice in ['n', 'no']:
            print("✅ No case/data files will be saved.")
            
            # Delete the saved design points CSV file since no files will be saved
            delete_saved_design_points_csv(project_folder)
            
            return None
        elif choice in ['y', 'yes']:
            break
        else:
            print("❌ Please enter 'y' for yes or 'n' for no.")
    
    print(f"\nEnter the design point numbers you want to save (0-based indexing, 0-{num_design_points-1}).")
    print("Examples:")
    print("• Single point: 0")
    print("• Multiple points: 0,2,4")
    print("• Range: 0-4")
    print("• Mixed: 0,2-4,7")
    
    while True:
        input_str = input("\nEnter design points to save: ").strip()
        
        if not input_str:
            print("❌ Please enter at least one design point number.")
            continue
            
        try:
            design_points = parse_design_points_input(input_str, num_design_points)
            if design_points:
                print(f"✅ Will save case/data files for design points: {design_points}")
                
                # Create CSV file to track saved design points
                create_saved_design_points_csv(design_points, project_folder)
                
                return design_points
            else:
                print("❌ No valid design points found. Please try again.")
        except ValueError as e:
            print(f"❌ Invalid input: {e}")
            print("Please use format like: 0,2,4 or 0-4 or 0,2-4,7")


def parse_design_points_input(input_str, max_design_points):
    """
    Parse user input for design points to save.
    Supports formats like: 0,2,4 or 0-4 or 0,2-4,7
    
    Args:
        input_str (str): User input string
        max_design_points (int): Maximum number of design points available
        
    Returns:
        list: Sorted list of unique design point indices (0-based)
    """
    design_points = set()
    
    # Split by comma and process each part
    parts = input_str.split(',')
    
    for part in parts:
        part = part.strip()
        
        if '-' in part:
            # Handle range (e.g., "0-4")
            try:
                start, end = map(int, part.split('-'))
                if start <= end:
                    if start < 0 or end >= max_design_points:
                        raise ValueError(f"Range {part} exceeds valid range (0-{max_design_points-1})")
                    design_points.update(range(start, end + 1))
                else:
                    raise ValueError(f"Invalid range: {part}")
            except ValueError:
                raise ValueError(f"Invalid range format: {part}")
        else:
            # Handle single number
            try:
                num = int(part)
                if num >= 0 and num < max_design_points:
                    design_points.add(num)
                elif num < 0:
                    raise ValueError(f"Design point must be non-negative: {num}")
                else:
                    raise ValueError(f"Design point {num} exceeds maximum ({max_design_points-1})")
            except ValueError:
                raise ValueError(f"Invalid number: {part}")
    
    # Final validation
    if design_points:
        invalid_points = [p for p in design_points if p >= max_design_points]
        if invalid_points:
            raise ValueError(f"Design points {invalid_points} exceed maximum ({max_design_points-1})")
    
    return sorted(list(design_points)) if design_points else None


def create_saved_design_points_csv(design_points, project_folder):
    """
    Create a CSV file to track which design points should be saved.
    
    Args:
        design_points (list): List of design point indices to save
        project_folder (str): Project folder path
    """
    import csv
    import os
    
    # Create the dps folder if it doesn't exist
    dps_folder = os.path.join(project_folder, "test_files", "dps")
    os.makedirs(dps_folder, exist_ok=True)
    
    # Create the saved_design_points.csv file
    saved_dp_file = os.path.join(dps_folder, "saved_design_points.csv")
    
    with open(saved_dp_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['design_point_index'])  # Header
        for dp in design_points:
            writer.writerow([dp])
    
    print(f"✅ Saved design points configuration saved to: {saved_dp_file}")


def delete_saved_design_points_csv(project_folder):
    """
    Delete the saved design points CSV file.
    
    Args:
        project_folder (str): Project folder path
    """
    import os
    
    # Path to the saved design points CSV file
    dps_folder = os.path.join(project_folder, "test_files", "dps")
    saved_dp_file = os.path.join(dps_folder, "saved_design_points.csv")
    
    if os.path.exists(saved_dp_file):
        try:
            os.remove(saved_dp_file)
            print(f"✅ Deleted saved design points configuration file: {saved_dp_file}")
        except Exception as e:
            print(f"⚠️ Could not delete saved design points file: {e}")
    else:
        print("ℹ️ No saved design points file found to delete.")


def main_menu():
    """
    Main menu system for the CFD automation program.
    """
    print("\n" + "="*60)
    print("CFD AUTOMATION PROGRAM")
    print("="*60)
    print("Welcome to the CFD automation system!")
    print("This program will help you automate your CFD workflow.")
    print("="*60)
    
    while True:
        print("\nChoose an option:")
        print("1. Setup - Configure simulation parameters")
        print("2. Solution - Run simulation workflow")
        print("3. Analysis - View simulation results")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1, 2, 3, or 4): ").strip()
        
        if choice == "1":
            setup_menu()
        elif choice == "2":
            solution_menu()
        elif choice == "3":
            analysis_menu()
        elif choice == "4":
            cleanup_on_exit()
            exit()
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")


def cleanup_on_exit():
    """
    Ask user if they want to keep configuration files when exiting.
    """
    print("\n" + "="*60)
    print("EXIT PROGRAM")
    print("="*60)
    print("Do you want to keep your configuration files for next time?")
    print("- Yes: Keep setup_config.json and solution_config.json")
    print("- No: Delete all configuration files and start fresh next time")
    print("="*60)
    
    while True:
        choice = input("\nKeep configuration files? (y/n): ").strip().lower()
        
        if choice in ['y', 'yes']:
            print("\nConfiguration files will be kept for next time.")
            print("Goodbye!")
            break
        elif choice in ['n', 'no']:
            delete_config_files()
            print("\nConfiguration files deleted. Starting fresh next time.")
            print("Goodbye!")
            break
        else:
            print("Please enter 'y' for yes or 'n' for no.")


def delete_config_files():
    """
    Delete the configuration JSON files.
    """
    import os
    
    config_files = [
        "setup_config.json",
        "solution_config.json"
    ]
    
    deleted_files = []
    for file in config_files:
        if os.path.exists(file):
            try:
                os.remove(file)
                deleted_files.append(file)
            except Exception as e:
                print(f"Could not delete {file}: {e}")
    
    if deleted_files:
        print(f"Deleted files: {', '.join(deleted_files)}")
    else:
        print("No configuration files found to delete.")


def setup_menu():
    """
    Setup sub-menu with categorized options.
    """
    # Try to load existing setup first
    setup_params = load_setup_from_file() or {}
    
    while True:
        print("\n" + "="*60)
        print("SETUP MENU")
        print("="*60)
        print("Current configuration status:")
        print_setup_status(setup_params)
        print("\nChoose a setup category:")
        print("1. Project folder")
        print("2. Case, mesh, geom and journal files")
        print("3. Dimension")
        print("4. CPU cores")
        print("5. Program locations")
        print("6. Solver type")
        print("7. Save setup and return to main menu")
        print("8. View setup configurations")
        print("9. Cancel setup")
        print("10. Reset all settings")
        print("11. Clean up configuration files")
        
        choice = input("\nEnter your choice (1-11): ").strip()
        
        if choice == "1":
            setup_params['project_folder'] = user_input_project_folder()
        elif choice == "2":
            setup_params['ref_files'] = user_input_files()
        elif choice == "3":
            setup_params['dimension'] = get_simulation_dimension()
        elif choice == "4":
            setup_params['meshing_cores'] = user_input_mesh_cores()
            setup_params['solver_cores'] = user_input_solver_cores()
        elif choice == "5":
            setup_params['spaceclaim_path'] = find_spaceclaim_exe()
            setup_params['fluent_path'] = find_fluent_exe()
        elif choice == "6":
            setup_params['solver_type'] = choose_solver_type()
        elif choice == "7":
            validation_result = validate_setup(setup_params)
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
        elif choice == "8":
            # View setup configurations
            view_setup_configurations_menu(setup_params)
        elif choice == "9":
            print("Setup cancelled.")
            return
        elif choice == "10":
            if input("Are you sure you want to reset all settings? (y/n): ").strip().lower() == 'y':
                setup_params = {}
                print("All settings have been reset.")
        elif choice == "11":
            if input("Are you sure you want to delete all configuration files? (y/n): ").strip().lower() == 'y':
                delete_config_files()
                setup_params = {}
                print("Configuration files deleted and settings reset.")
        else:
            print("Invalid choice. Please enter 1-11.")


def view_setup_configurations_menu(setup_params):
    """
    View and modify setup configurations menu.
    
    Args:
        setup_params (dict): Current setup parameters
    """
    # Try to load solution config to show complete picture
    solution_params = load_solution_from_file() or {}
    
    while True:
        print("\n" + "="*60)
        print("VIEW SETUP CONFIGURATIONS")
        print("="*60)
        print("Choose what to view:")
        print("1. View basic setup configuration")
        print("2. View solution progress (if available)")
        print("3. Return to setup menu")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            view_setup_summary(setup_params)
        elif choice == "2":
            if solution_params:
                view_solution_progress_menu(solution_params)
            else:
                print("No solution progress found. Complete solution steps first.")
        elif choice == "3":
            print("Returning to setup menu.")
            return
        else:
            print("Invalid choice. Please enter 1-3.")


def view_solution_progress_menu(solution_params):
    """
    View solution progress in a simplified menu.
    
    Args:
        solution_params (dict): Solution parameters
    """
    while True:
        print("\n" + "="*50)
        print("SOLUTION PROGRESS")
        print("="*50)
        print("Choose what to view:")
        print("1. Named selections")
        print("2. Parameter movements")
        print("3. Design points")
        print("4. Save configuration")
        print("5. Return to previous menu")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            view_named_selections(solution_params)
        elif choice == "2":
            view_parameter_selections(solution_params)
        elif choice == "3":
            view_design_points(solution_params, {})
        elif choice == "4":
            view_save_configuration(solution_params)
        elif choice == "5":
            return
        else:
            print("Invalid choice. Please enter 1-5.")


def modify_design_points_menu(setup_params, solution_params):
    """
    Menu to modify design points configuration.
    
    Args:
        setup_params (dict): Setup parameters
        solution_params (dict): Solution parameters
    """
    if 'design_points_path' not in solution_params:
        print("\nNo design points found. Please complete solution step 3 first.")
        return
    
    print("\n" + "="*50)
    print("MODIFY DESIGN POINTS")
    print("="*50)
    print(f"Current design points: {solution_params.get('num_design_points', 0)}")
    
    while True:
        print("\nChoose an action:")
        print("1. Regenerate design points")
        print("2. View current design points")
        print("3. Add design point")
        print("4. Delete design point")
        print("5. Return to previous menu")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            # Regenerate design points
            if 'geom_parameters' not in solution_params:
                print("No parameter movements defined. Please complete solution step 2 first.")
                continue
                
            import solver_setup
            design_points_path, num_design_points = solver_setup.get_sample_points_from_ranges(
                solution_params['geom_parameters'], setup_params['project_folder'])
            
            solution_params['design_points_path'] = design_points_path
            solution_params['num_design_points'] = num_design_points
            
            save_solution_to_file(solution_params)
            print(f"Design points regenerated: {num_design_points} points")
            
        elif choice == "2":
            # View current design points
            view_design_points(solution_params, setup_params)
            
        elif choice == "3":
            # Add design point
            add_individual_design_point(solution_params, setup_params)
            
        elif choice == "4":
            # Delete design point
            delete_individual_design_point(solution_params, setup_params)
            
        elif choice == "5":
            return
        else:
            print("Invalid choice. Please enter 1-5.")


def add_individual_design_point(solution_params, setup_params):
    """
    Add a single design point to the existing design points file.
    
    Args:
        solution_params (dict): Solution parameters
        setup_params (dict): Setup parameters
    """
    import pandas as pd
    import numpy as np
    
    design_points_path = solution_params['design_points_path']
    
    try:
        # Read existing design points
        df = pd.read_csv(design_points_path)
        headers = df.columns.tolist()
        num_params = len(headers)
        
        print(f"\nAdding new design point with {num_params} parameters:")
        print(f"Parameters: {', '.join(headers)}")
        
        # Get parameter ranges for validation
        import solver_setup
        lower_bounds, upper_bounds = get_parameter_bounds(solution_params['geom_parameters'])
        
        # Get user input for new design point
        while True:
            try:
                values_input = input(f"Enter values for new design point (space-separated): ").strip()
                if not values_input:
                    print("❌ No values entered. Cancelling.")
                    return
                
                values = [float(x.strip()) for x in values_input.split()]
                if len(values) != num_params:
                    print(f"❌ Need exactly {num_params} values. Got {len(values)}.")
                    continue
                
                # Check bounds and warn if outside, but accept anyway
                warnings = []
                for i, (val, low, high, header) in enumerate(zip(values, lower_bounds, upper_bounds, headers)):
                    if not (low <= val <= high):
                        warnings.append(f"{header} value {val} is outside bounds [{low}, {high}]")
                
                # Accept the point regardless of bounds
                if warnings:
                    print(f"⚠️ Design point with warnings:")
                    for warning in warnings:
                        print(f"   {warning}")
                    confirm = input("Add this design point anyway? (y/n): ").strip().lower()
                    if confirm not in ['y', 'yes']:
                        continue
                
                # Add the new row
                new_row = pd.DataFrame([values], columns=headers)
                df = pd.concat([df, new_row], ignore_index=True)
                
                # Save updated CSV
                df.to_csv(design_points_path, index=False)
                
                # Update solution parameters
                solution_params['num_design_points'] = len(df)
                save_solution_to_file(solution_params)
                
                print(f"✅ Design point added successfully!")
                print(f"New total: {len(df)} design points")
                break
                
            except ValueError:
                print("❌ Invalid input. Enter space-separated numbers.")
            except Exception as e:
                print(f"❌ Error adding design point: {e}")
                break
                
    except Exception as e:
        print(f"❌ Error reading design points file: {e}")


def delete_individual_design_point(solution_params, setup_params):
    """
    Delete a single design point from the existing design points file.
    
    Args:
        solution_params (dict): Solution parameters
        setup_params (dict): Setup parameters
    """
    import pandas as pd
    
    design_points_path = solution_params['design_points_path']
    
    try:
        # Read existing design points
        df = pd.read_csv(design_points_path)
        
        if len(df) == 0:
            print("❌ No design points to delete.")
            return
        
        print(f"\nCurrent design points ({len(df)} total):")
        print("-" * 50)
        
        # Display design points with indices
        for i, row in df.iterrows():
            values_str = ", ".join([f"{val:.3f}" for val in row.values])
            print(f"{i}: [{values_str}]")
        
        print("-" * 50)
        
        # Get user input for which point to delete
        while True:
            try:
                delete_input = input(f"Enter design point index to delete (0-{len(df)-1}): ").strip()
                if not delete_input:
                    print("❌ No index entered. Cancelling.")
                    return
                
                delete_idx = int(delete_input)
                if delete_idx < 0 or delete_idx >= len(df):
                    print(f"❌ Invalid index. Enter a number between 0 and {len(df)-1}.")
                    continue
                
                # Confirm deletion
                deleted_row = df.iloc[delete_idx]
                values_str = ", ".join([f"{val:.3f}" for val in deleted_row.values])
                print(f"\nYou are about to delete design point {delete_idx}: [{values_str}]")
                confirm = input("Are you sure? (y/n): ").strip().lower()
                
                if confirm in ['y', 'yes']:
                    # Delete the row
                    df = df.drop(delete_idx).reset_index(drop=True)
                    
                    # Save updated CSV
                    df.to_csv(design_points_path, index=False)
                    
                    # Update solution parameters
                    solution_params['num_design_points'] = len(df)
                    
                    # Update save configuration if needed
                    if 'save_design_points' in solution_params and solution_params['save_design_points']:
                        # Remove deleted index from save list and adjust other indices
                        save_points = solution_params['save_design_points']
                        updated_save_points = []
                        for point_idx in save_points:
                            if point_idx < delete_idx:
                                # Keep unchanged
                                updated_save_points.append(point_idx)
                            elif point_idx > delete_idx:
                                # Shift down by 1
                                updated_save_points.append(point_idx - 1)
                            # point_idx == delete_idx is removed (not added to updated list)
                        
                        solution_params['save_design_points'] = updated_save_points
                        
                        # Update the CSV file with the new save configuration
                        if updated_save_points:
                            create_saved_design_points_csv(updated_save_points, setup_params['project_folder'])
                        else:
                            delete_saved_design_points_csv(setup_params['project_folder'])
                    
                    save_solution_to_file(solution_params)
                    
                    print(f"✅ Design point {delete_idx} deleted successfully!")
                    print(f"Remaining: {len(df)} design points")
                    break
                else:
                    print("Deletion cancelled.")
                    break
                    
            except ValueError:
                print("❌ Invalid input. Enter a number.")
            except Exception as e:
                print(f"❌ Error deleting design point: {e}")
                break
                
    except Exception as e:
        print(f"❌ Error reading design points file: {e}")


def get_parameter_bounds(geom_parameters):
    """
    Extract lower and upper bounds from geometry parameters for validation.
    
    Args:
        geom_parameters (dict): Geometry parameters with movement ranges
    
    Returns:
        tuple: (lower_bounds, upper_bounds) lists
    """
    lower_bounds = []
    upper_bounds = []
    
    for param_name, moves in geom_parameters.items():
        # Translations
        for t_move in moves.get("translate", []):
            if t_move.get("enabled", False):
                lower_bounds.append(t_move.get("min", 0.0))
                upper_bounds.append(t_move.get("max", 0.0))
        
        # Rotations
        for r_move in moves.get("rotate", []):
            if r_move.get("enabled", False):
                lower_bounds.append(r_move.get("min", 0.0))
                upper_bounds.append(r_move.get("max", 0.0))
    
    return lower_bounds, upper_bounds


def modify_parameter_movements_menu(setup_params, solution_params):
    """
    Menu to modify parameter movements.
    
    Args:
        setup_params (dict): Setup parameters
        solution_params (dict): Solution parameters
    """
    # Import solver_setup at the top of the function
    import solver_setup
    
    if 'geom_parameters' not in solution_params:
        print("\nNo parameter movements found. Please complete solution step 2 first.")
        return
    
    print("\n" + "="*50)
    print("MODIFY PARAMETER MOVEMENTS")
    print("="*50)
    
    while True:
        print("\nChoose an action:")
        print("1. View current parameter movements")
        print("2. Modify parameter movements (add/remove translations/rotations)")
        print("3. Add new parameter")
        print("4. Remove parameter")
        print("5. Return to previous menu")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            view_parameter_selections(solution_params)
            
        elif choice == "2":
            # Modify parameter movements (add/remove translations/rotations)
            if 'geom_parameters_list' not in solution_params:
                print("No parameters selected.")
                continue
                
            # Store original state to detect if any changes were made
            import copy
            original_geom_parameters = copy.deepcopy(solution_params.get('geom_parameters', {}))
            
            modify_parameter_movements_detailed(solution_params, setup_params)
            
            # Check if any changes were made and regenerate design points if needed
            current_geom_parameters = solution_params.get('geom_parameters', {})
            if current_geom_parameters != original_geom_parameters and 'design_points_path' in solution_params:
                print("\nAuto-regenerating design points due to parameter changes...")
                import solver_setup
                design_points_path, num_design_points = solver_setup.get_sample_points_from_ranges(
                    solution_params['geom_parameters'], setup_params['project_folder'])
                
                # Keep the same save configuration
                save_design_points = solution_params.get('save_design_points', None)
                
                solution_params['design_points_path'] = design_points_path
                solution_params['num_design_points'] = num_design_points
                solution_params['save_design_points'] = save_design_points
                
                save_solution_to_file(solution_params)
                print(f"Design points regenerated: {num_design_points} points")
                
        elif choice == "3":
            # Add new parameter
            if 'named_selections' not in solution_params:
                print("No named selections available. Please complete solution step 1 first.")
                continue
                
            print("\nAvailable named selections:")
            for i, selection in enumerate(solution_params['named_selections'], 1):
                if selection not in solution_params['geom_parameters_list']:
                    print(f"{i}. {selection}")
            
            try:
                selection_choice = input("\nEnter selection number to add: ").strip()
                selection_idx = int(selection_choice) - 1
                
                if 0 <= selection_idx < len(solution_params['named_selections']):
                    new_param = solution_params['named_selections'][selection_idx]
                    if new_param not in solution_params['geom_parameters_list']:
                        solution_params['geom_parameters_list'].append(new_param)
                        
                        # Define movements for new parameter
                        new_movements = solver_setup.define_movement_ranges_with_directions([new_param])
                        solution_params['geom_parameters'].update(new_movements)
                        
                        save_solution_to_file(solution_params)
                        print(f"Parameter {new_param} added successfully.")
                        
                        # Auto-regenerate design points if they exist
                        if 'design_points_path' in solution_params:
                            print("\nAuto-regenerating design points due to new parameter...")
                            design_points_path, num_design_points = solver_setup.get_sample_points_from_ranges(
                                solution_params['geom_parameters'], setup_params['project_folder'])
                            
                            # Keep the same save configuration
                            save_design_points = solution_params.get('save_design_points', None)
                            
                            solution_params['design_points_path'] = design_points_path
                            solution_params['num_design_points'] = num_design_points
                            solution_params['save_design_points'] = save_design_points
                            
                            save_solution_to_file(solution_params)
                            print(f"Design points regenerated: {num_design_points} points")
                    else:
                        print("Parameter already exists.")
                else:
                    print("Invalid selection number.")
            except (ValueError, IndexError):
                print("Invalid input.")
                
        elif choice == "4":
            # Remove parameter
            if not solution_params['geom_parameters_list']:
                print("No parameters to remove.")
                continue
                
            print("\nCurrent parameters:")
            for i, param in enumerate(solution_params['geom_parameters_list'], 1):
                print(f"{i}. {param}")
            
            try:
                param_choice = input("\nEnter parameter number to remove: ").strip()
                param_idx = int(param_choice) - 1
                
                if 0 <= param_idx < len(solution_params['geom_parameters_list']):
                    removed_param = solution_params['geom_parameters_list'].pop(param_idx)
                    if removed_param in solution_params['geom_parameters']:
                        del solution_params['geom_parameters'][removed_param]
                    
                    save_solution_to_file(solution_params)
                    print(f"Parameter {removed_param} removed successfully.")
                    
                    # Auto-regenerate design points if they exist
                    if 'design_points_path' in solution_params:
                        print("\nAuto-regenerating design points due to parameter removal...")
                        design_points_path, num_design_points = solver_setup.get_sample_points_from_ranges(
                            solution_params['geom_parameters'], setup_params['project_folder'])
                        
                        # Keep the same save configuration
                        save_design_points = solution_params.get('save_design_points', None)
                        
                        solution_params['design_points_path'] = design_points_path
                        solution_params['num_design_points'] = num_design_points
                        solution_params['save_design_points'] = save_design_points
                        
                        save_solution_to_file(solution_params)
                        print(f"Design points regenerated: {num_design_points} points")
                else:
                    print("Invalid parameter number.")
            except (ValueError, IndexError):
                print("Invalid input.")
                
        elif choice == "5":
            return
        else:
            print("Invalid choice. Please enter 1-5.")


def check_if_regeneration_needed(change_type):
    """
    Check if design points need to be regenerated based on the type of changes made.
    Regenerate for all changes including ranges, toggles, axis directions, and translate directions.
    
    Args:
        change_type (str): Type of change made ('range', 'direction', 'axis', 'toggle')
    
    Returns:
        bool: True if regeneration is needed, False otherwise
    """
    # Regenerate for all types of changes
    return True


def modify_single_parameter(param_name, solution_params):
    """
    Modify a single parameter's movement ranges.
    
    Args:
        param_name (str): Name of the parameter to modify
        solution_params (dict): Solution parameters
    
    Returns:
        tuple: (changes_made: bool, change_type: str) where change_type is 'range', 'direction', 'axis', 'toggle', or None
    """
    if param_name not in solution_params['geom_parameters']:
        print(f"Parameter {param_name} not found in movements.")
        return False, None
    
    param_data = solution_params['geom_parameters'][param_name]
    
    # Store original state to detect changes
    original_param_data = {}
    if 'translate' in param_data:
        original_param_data['translate'] = [translate_info.copy() for translate_info in param_data['translate']]
    if 'rotate' in param_data:
        original_param_data['rotate'] = [rotate_info.copy() for rotate_info in param_data['rotate']]
    
    print(f"\nModifying parameter: {param_name}")
    print("Current configuration:")
    
    if 'translate' in param_data:
        translate_info = param_data['translate'][0]
        print(f"  Translate: {'Enabled' if translate_info.get('enabled') else 'Disabled'}")
        if translate_info.get('enabled'):
            print(f"    Range: {translate_info.get('min')} to {translate_info.get('max')}")
            print(f"    Direction: {translate_info.get('direction')}")
    
    if 'rotate' in param_data:
        rotate_info = param_data['rotate'][0]
        print(f"  Rotate: {'Enabled' if rotate_info.get('enabled') else 'Disabled'}")
        if rotate_info.get('enabled'):
            print(f"    Range: {rotate_info.get('min')} to {rotate_info.get('max')}")
            print(f"    Axis: {rotate_info.get('axis')}")
    
    # Simple modification interface
    print("\nChoose what to modify:")
    print("1. Toggle translate")
    print("2. Toggle rotate")
    print("3. Modify translate range")
    print("4. Modify rotate range")
    print("5. Modify translate direction")
    print("6. Modify rotate axis")
    print("7. Cancel")
    
    choice = input("\nEnter your choice (1-7): ").strip()
    
    changes_made = False
    change_type = None
    
    if choice == "1":
        # Toggle translate
        translate_info = param_data['translate'][0]
        translate_info['enabled'] = not translate_info.get('enabled', False)
        print(f"Translate {'enabled' if translate_info['enabled'] else 'disabled'}.")
        
        # If enabling, ask for range and direction
        if translate_info['enabled']:
            try:
                min_val = float(input(f"Enter minimum translate value (current: {translate_info.get('min', 0)}): ") or translate_info.get('min', 0))
                max_val = float(input(f"Enter maximum translate value (current: {translate_info.get('max', 0)}): ") or translate_info.get('max', 0))
                
                # Ask for direction vector
                print("Enter translation direction vector (x, y, z components):")
                print("Examples: [1,0,0] for X-axis, [0,1,0] for Y-axis, [0,0,1] for Z-axis")
                direction_input = input(f"Direction vector (current: {translate_info.get('direction', [0,0,0])}): ").strip()
                
                if direction_input:
                    try:
                        # Parse direction vector (expecting format like "1,0,0" or "[1,0,0]")
                        direction_input = direction_input.strip('[]()')
                        direction_components = [float(x.strip()) for x in direction_input.split(',')]
                        if len(direction_components) == 3:
                            translate_info['direction'] = direction_components
                        else:
                            print("Invalid direction vector. Must have 3 components. Using default [1,0,0]")
                            translate_info['direction'] = [1, 0, 0]
                    except ValueError:
                        print("Invalid direction vector format. Using default [1,0,0]")
                        translate_info['direction'] = [1, 0, 0]
                else:
                    # Keep current direction or use default
                    translate_info['direction'] = translate_info.get('direction', [1, 0, 0])
                
                translate_info['min'] = min_val
                translate_info['max'] = max_val
                print(f"Translate range set: {min_val} to {max_val}")
                print(f"Translate direction set: {translate_info['direction']}")
            except ValueError:
                print("Invalid input. Values must be numbers.")
                translate_info['enabled'] = False
        changes_made = True
        change_type = 'toggle'
        
    elif choice == "2":
        # Toggle rotate
        rotate_info = param_data['rotate'][0]
        rotate_info['enabled'] = not rotate_info.get('enabled', False)
        print(f"Rotate {'enabled' if rotate_info['enabled'] else 'disabled'}.")
        
        # If enabling, ask for range and axis
        if rotate_info['enabled']:
            try:
                min_val = float(input(f"Enter minimum rotate value (current: {rotate_info.get('min', 0)}): ") or rotate_info.get('min', 0))
                max_val = float(input(f"Enter maximum rotate value (current: {rotate_info.get('max', 0)}): ") or rotate_info.get('max', 0))
                
                # Ask for rotation axis vector
                print("Enter rotation axis vector (x, y, z components):")
                print("Examples: [1,0,0] for X-axis, [0,1,0] for Y-axis, [0,0,1] for Z-axis")
                axis_input = input(f"Axis vector (current: {rotate_info.get('axis', [0,0,1])}): ").strip()
                
                if axis_input:
                    try:
                        # Parse axis vector (expecting format like "0,0,1" or "[0,0,1]")
                        axis_input = axis_input.strip('[]()')
                        axis_components = [float(x.strip()) for x in axis_input.split(',')]
                        if len(axis_components) == 3:
                            rotate_info['axis'] = axis_components
                        else:
                            print("Invalid axis vector. Must have 3 components. Using default [0,0,1]")
                            rotate_info['axis'] = [0, 0, 1]
                    except ValueError:
                        print("Invalid axis vector format. Using default [0,0,1]")
                        rotate_info['axis'] = [0, 0, 1]
                else:
                    # Keep current axis or use default
                    rotate_info['axis'] = rotate_info.get('axis', [0, 0, 1])
                
                rotate_info['min'] = min_val
                rotate_info['max'] = max_val
                print(f"Rotate range set: {min_val} to {max_val}")
                print(f"Rotate axis set: {rotate_info['axis']}")
            except ValueError:
                print("Invalid input. Values must be numbers.")
                rotate_info['enabled'] = False
        changes_made = True
        change_type = 'toggle'
        
    elif choice == "3":
        # Modify translate range
        translate_info = param_data['translate'][0]
        try:
            min_val = float(input(f"Enter minimum translate value (current: {translate_info.get('min', 0)}): ") or translate_info.get('min', 0))
            max_val = float(input(f"Enter maximum translate value (current: {translate_info.get('max', 0)}): ") or translate_info.get('max', 0))
            
            # Ask for direction vector if not already set
            if not translate_info.get('direction'):
                print("Enter translation direction vector (x, y, z components):")
                print("Examples: [1,0,0] for X-axis, [0,1,0] for Y-axis, [0,0,1] for Z-axis")
                direction_input = input(f"Direction vector (current: {translate_info.get('direction', [0,0,0])}): ").strip()
                
                if direction_input:
                    try:
                        direction_input = direction_input.strip('[]()')
                        direction_components = [float(x.strip()) for x in direction_input.split(',')]
                        if len(direction_components) == 3:
                            translate_info['direction'] = direction_components
                        else:
                            print("Invalid direction vector. Must have 3 components. Using default [1,0,0]")
                            translate_info['direction'] = [1, 0, 0]
                    except ValueError:
                        print("Invalid direction vector format. Using default [1,0,0]")
                        translate_info['direction'] = [1, 0, 0]
                else:
                    translate_info['direction'] = translate_info.get('direction', [1, 0, 0])
            
            translate_info['min'] = min_val
            translate_info['max'] = max_val
            translate_info['enabled'] = True
            print(f"Translate range updated: {min_val} to {max_val}")
            print(f"Translate direction: {translate_info['direction']}")
            changes_made = True
            change_type = 'range'
        except ValueError:
            print("Invalid input. Values must be numbers.")
            
    elif choice == "4":
        # Modify rotate range
        rotate_info = param_data['rotate'][0]
        try:
            min_val = float(input(f"Enter minimum rotate value (current: {rotate_info.get('min', 0)}): ") or rotate_info.get('min', 0))
            max_val = float(input(f"Enter maximum rotate value (current: {rotate_info.get('max', 0)}): ") or rotate_info.get('max', 0))
            
            # Ask for rotation axis vector if not already set
            if not rotate_info.get('axis'):
                print("Enter rotation axis vector (x, y, z components):")
                print("Examples: [1,0,0] for X-axis, [0,1,0] for Y-axis, [0,0,1] for Z-axis")
                axis_input = input(f"Axis vector (current: {rotate_info.get('axis', [0,0,1])}): ").strip()
                
                if axis_input:
                    try:
                        axis_input = axis_input.strip('[]()')
                        axis_components = [float(x.strip()) for x in axis_input.split(',')]
                        if len(axis_components) == 3:
                            rotate_info['axis'] = axis_components
                        else:
                            print("Invalid axis vector. Must have 3 components. Using default [0,0,1]")
                            rotate_info['axis'] = [0, 0, 1]
                    except ValueError:
                        print("Invalid axis vector format. Using default [0,0,1]")
                        rotate_info['axis'] = [0, 0, 1]
                else:
                    rotate_info['axis'] = rotate_info.get('axis', [0, 0, 1])
            
            rotate_info['min'] = min_val
            rotate_info['max'] = max_val
            rotate_info['enabled'] = True
            print(f"Rotate range updated: {min_val} to {max_val}")
            print(f"Rotate axis: {rotate_info['axis']}")
            changes_made = True
            change_type = 'range'
        except ValueError:
            print("Invalid input. Values must be numbers.")
            
    elif choice == "5":
         # Modify translate direction only
         translate_info = param_data['translate'][0]
         if not translate_info.get('enabled', False):
             print("Translate is currently disabled.")
             enable_choice = input("Do you want to enable translate and set direction? (y/n): ").strip().lower()
             if enable_choice not in ['y', 'yes']:
                 print("Translate direction modification cancelled.")
                 return False, None
             translate_info['enabled'] = True
             print("Translate has been enabled.")
             
         print("Enter translation direction vector (x, y, z components):")
         print("Examples: [1,0,0] for X-axis, [0,1,0] for Y-axis, [0,0,1] for Z-axis")
         direction_input = input(f"Direction vector (current: {translate_info.get('direction', [0,0,0])}): ").strip()
         
         if direction_input:
             try:
                 direction_input = direction_input.strip('[]()')
                 direction_components = [float(x.strip()) for x in direction_input.split(',')]
                 if len(direction_components) == 3:
                     translate_info['direction'] = direction_components
                     print(f"Translate direction updated: {direction_components}")
                     changes_made = True
                     change_type = 'direction'
                 else:
                     print("Invalid direction vector. Must have 3 components.")
                     return False, None
             except ValueError:
                 print("Invalid direction vector format.")
                 return False, None
         else:
             print("No changes made.")
             return False, None
             
    elif choice == "6":
         # Modify rotate axis only
         rotate_info = param_data['rotate'][0]
         if not rotate_info.get('enabled', False):
             print("Rotate is not enabled. Please enable rotate first.")
             return False, None
             
         print("Enter rotation axis vector (x, y, z components):")
         print("Examples: [1,0,0] for X-axis, [0,1,0] for Y-axis, [0,0,1] for Z-axis")
         axis_input = input(f"Axis vector (current: {rotate_info.get('axis', [0,0,1])}): ").strip()
         
         if axis_input:
             try:
                 axis_input = axis_input.strip('[]()')
                 axis_components = [float(x.strip()) for x in axis_input.split(',')]
                 if len(axis_components) == 3:
                     rotate_info['axis'] = axis_components
                     print(f"Rotate axis updated: {axis_components}")
                     changes_made = True
                     change_type = 'axis'
                 else:
                     print("Invalid axis vector. Must have 3 components.")
                     return False, None
             except ValueError:
                 print("Invalid axis vector format.")
                 return False, None
         else:
             print("No changes made.")
             return False, None
             
    elif choice == "7":
        return False, None
    else:
        print("Invalid choice.")
        return False, None
    
    # Check if actual changes were made by comparing with original
    if changes_made:
        current_param_data = {}
        if 'translate' in param_data:
            current_param_data['translate'] = [translate_info.copy() for translate_info in param_data['translate']]
        if 'rotate' in param_data:
            current_param_data['rotate'] = [rotate_info.copy() for rotate_info in param_data['rotate']]
        
        if original_param_data != current_param_data:
            return True, change_type
        else:
            print("No actual changes were made.")
            return False, None
    
    return False, None


def modify_save_configuration_menu(setup_params, solution_params):
    """
    Menu to modify save configuration.
    
    Args:
        setup_params (dict): Setup parameters
        solution_params (dict): Solution parameters
    """
    if 'save_design_points' not in solution_params:
        print("\nNo save configuration found. Please complete solution step 3 first.")
        return
    
    print("\n" + "="*50)
    print("MODIFY SAVE CONFIGURATION")
    print("="*50)
    
    current_save = solution_params['save_design_points']
    num_points = solution_params.get('num_design_points', 0)
    
    if current_save is None:
        print("Current configuration: No files will be saved")
    else:
        print(f"Current configuration: Save files for {len(current_save)} design points")
        print(f"Design points to save: {current_save}")
    
    print(f"Total design points available: {num_points}")
    
    while True:
        print("\nChoose an action:")
        print("1. View current save configuration")
        print("2. Modify save configuration")
        print("3. Clear save configuration (save no files)")
        print("4. Return to previous menu")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            view_save_configuration(solution_params)
            
        elif choice == "2":
            save_design_points = get_design_points_to_save(num_points, setup_params['project_folder'])
            solution_params['save_design_points'] = save_design_points
            save_solution_to_file(solution_params)
            print("Save configuration updated.")
            
        elif choice == "3":
            solution_params['save_design_points'] = None
            save_solution_to_file(solution_params)
            
            # Delete the saved design points CSV file since no files will be saved
            delete_saved_design_points_csv(setup_params['project_folder'])
            
            print("Save configuration cleared. No files will be saved.")
            
        elif choice == "4":
            return
        else:
            print("Invalid choice. Please enter 1-4.")


def print_setup_status(setup_params):
    """
    Print the current status of setup parameters.
    
    Args:
        setup_params (dict): Setup parameters to check
    """
    status_map = {
        'project_folder': 'Project folder',
        'ref_files': 'Reference files',
        'dimension': 'Dimension',
        'meshing_cores': 'Meshing cores',
        'solver_cores': 'Solver cores',
        'spaceclaim_path': 'SpaceClaim path',
        'fluent_path': 'Fluent path',
        'solver_type': 'Solver type'
    }
    
    for param, display_name in status_map.items():
        if param in setup_params:
            print(f"✓ {display_name}: Configured")
        else:
            print(f"✗ {display_name}: Not set")


def solution_menu():
    """
    Solution sub-menu with workflow options.
    """
    print("\n" + "="*60)
    print("SOLUTION MENU")
    print("="*60)
    
    # Try to load existing setup
    setup_params = load_setup_from_file()
    
    if setup_params is None:
        print("No setup found! Please run 'Setup' first.")
        print("="*60)
        return
    
    print("Loaded existing setup configuration.")
    print("="*60)
    
    # Import required modules at the top
    import folder_management
    import solver_setup
    
    # Try to load existing solution params
    solution_params = load_solution_from_file() or {}

    # Ensure design points path aligns with the current project folder
    design_points_default = os.path.join(
        setup_params['project_folder'],
        "test_files",
        "dps",
        "DesignPoints.csv",
    )
    stored_path = solution_params.get('design_points_path')
    if not stored_path:
        solution_params['design_points_path'] = design_points_default
    else:
        normalized_stored = os.path.normcase(os.path.abspath(stored_path))
        normalized_default = os.path.normcase(os.path.abspath(design_points_default))
        if normalized_stored != normalized_default:
            if not os.path.exists(stored_path):
                print(f"[INFO] Resetting design points path to project default: {design_points_default}")
                solution_params['design_points_path'] = design_points_default
    
    while True:
        print("\n" + "="*60)
        print("SOLUTION WORKFLOW")
        print("="*60)
        print("Current progress:")
        print_solution_status(solution_params)
        print("\nChoose a solution step:")
        print("1. Load named selections")
        print("2. Define named movements")
        print("3. Design points (method and number of points selection)")
        print("4. Save case/data files for certain design points")
        print("5. Setup Contours and Plots")
        print("6. Automatic DP refinement")
        print("7. Run simulation")
        print("8. View data")
        print("9. Modify configurations")
        print("10. Save current progress")
        print("11. Return to main menu")
        print("12. Reset solution progress")
        
        choice = input("\nEnter your choice (1-12): ").strip()
        
        if choice == "1":
            # Step 1: Get named selections from case file
            print("\nSTEP 1: LOAD NAMED SELECTIONS")
            print("="*40)
            
            # Create folders and move files first
            folder_management.create_folders(project_root=setup_params['project_folder'])
            updated_ref_paths = folder_management.move_all_ref_files(setup_params['ref_files'], setup_params['project_folder'])
            
            # Get named selections
            named_selections = solver_setup.get_names_from_casefile(casefile_path=updated_ref_paths["case_file"])
            solution_params['named_selections'] = named_selections
            solution_params['updated_ref_paths'] = updated_ref_paths
            
            print("Named selections loaded successfully.")
            save_solution_to_file(solution_params)
            
        elif choice == "2":
            # Step 2: Choose named parameters and define movements
            print("\nSTEP 2: DEFINE NAMED MOVEMENTS")
            print("="*40)
            
            if 'named_selections' not in solution_params:
                print("Please complete step 1 first (Named Parameters).")
                continue
                
            # Ask if user wants to modify existing parameters
            if 'geom_parameters_list' in solution_params:
                print("You have existing named parameter selections.")
                modify = input("Do you want to modify them? (y/n): ").strip().lower()
                if modify != 'y':
                    print("Using existing parameter selections.")
                else:
                    geom_parameters_list = solver_setup.choose_named_parameters(named_selections=solution_params['named_selections'])
                    solution_params['geom_parameters_list'] = geom_parameters_list
            else:
                geom_parameters_list = solver_setup.choose_named_parameters(named_selections=solution_params['named_selections'])
                solution_params['geom_parameters_list'] = geom_parameters_list
            
            # Ask if user wants to modify movement ranges
            if 'geom_parameters' in solution_params:
                print("You have existing movement ranges.")
                modify = input("Do you want to modify them? (y/n): ").strip().lower()
                if modify != 'y':
                    print("Using existing movement ranges.")
                else:
                    geom_parameters = solver_setup.define_movement_ranges_with_directions(solution_params['geom_parameters_list'])
                    solution_params['geom_parameters'] = geom_parameters
            else:
                geom_parameters = solver_setup.define_movement_ranges_with_directions(solution_params['geom_parameters_list'])
                solution_params['geom_parameters'] = geom_parameters
            
            print("Named movements defined successfully.")
            save_solution_to_file(solution_params)
            
        elif choice == "3":
            # Step 3: Design points generation
            print("\nSTEP 3: DESIGN POINTS")
            print("="*40)
            
            if 'geom_parameters' not in solution_params:
                print("Please complete step 2 first (Define named movements).")
                continue
                
            # Ask if user wants to regenerate design points
            if 'design_points_path' in solution_params:
                num_points = solution_params.get('num_design_points')
                if num_points is not None:
                    print(f"You have existing design points: {num_points} points")
                else:
                    print("A design points file is recorded, but the point count is unknown.")
                regenerate = input("Do you want to regenerate design points? (y/n): ").strip().lower()
                if regenerate != 'y':
                    print("Using existing design points.")
                else:
                    design_points_path, num_design_points = solver_setup.get_sample_points_from_ranges(
                        solution_params['geom_parameters'], setup_params['project_folder'])
                    
                    solution_params['design_points_path'] = design_points_path
                    solution_params['num_design_points'] = num_design_points
            else:
                design_points_path, num_design_points = solver_setup.get_sample_points_from_ranges(
                    solution_params['geom_parameters'], setup_params['project_folder'])
                
                solution_params['design_points_path'] = design_points_path
                solution_params['num_design_points'] = num_design_points
            
            print("Design points configuration completed successfully.")
            save_solution_to_file(solution_params)
            
        elif choice == "4":
            # Step 4: Save case/data files for certain design points
            print("\nSTEP 4: SAVE CASE/DATA FILES")
            print("="*40)
            
            if 'design_points_path' not in solution_params:
                print("No design points found. Please complete step 3 first.")
                continue
                
            # Call the save case/data files menu
            save_case_data_files_menu(solution_params, setup_params)
            
        elif choice == "5":
            # Step 5: Setup Contours and Plots
            print("\nSTEP 5: SETUP CONTOURS AND PLOTS")
            print("="*40)
            
            if not SNAPSHOT_AVAILABLE:
                print("Snapshot configuration module is not available.")
                print("Please ensure snapshot_user_inputs.py is in the same directory.")
                continue
            
            if 'design_points_path' not in solution_params:
                print("No design points found. Please complete step 3 first.")
                continue
            
            # Get project folder from setup params
            project_folder = setup_params.get('project_folder')
            if not project_folder:
                print("Project folder not found in setup configuration.")
                continue
            
            print(f"Opening snapshot configuration menu for project: {project_folder}")
            print("This will allow you to configure surfaces, plots, and design points for snapshot generation.")
            
            # Call the snapshot user input menu
            try:
                # Temporarily change to the project folder directory for relative path resolution
                import sys
                from pathlib import Path
                original_cwd = Path.cwd()
                project_path = Path(project_folder)
                
                # Change to project folder so snapshot_user_inputs can find setup_config.json
                if project_path.exists():
                    os.chdir(project_path)
                
                # Import and run the snapshot user input menu
                from snapshot_user_inputs import main as run_snapshot_user_inputs
                run_snapshot_user_inputs()
                
                # Restore original directory
                os.chdir(original_cwd)
                
                print("\n[INFO] Returning to solution menu.")
                
            except Exception as e:
                # Restore original directory in case of error
                try:
                    os.chdir(original_cwd)
                except:
                    pass
                print(f"[ERROR] Failed to run snapshot configuration: {e}")
                import traceback
                traceback.print_exc()
            
        elif choice == "6":
            # Step 6: Automatic DP refinement
            print("\nSTEP 6: AUTOMATIC DP REFINEMENT")
            print("="*40)
            try:
                from model_refinment_inputs import refinment_inputs
            except ImportError as exc:
                print(f"Unable to load refinement inputs module: {exc}")
                continue
            
            project_folder = setup_params['project_folder']
            refinment_inputs(project_folder)
            
        elif choice == "7":
            # Step 7: Run simulation
            print("\nSTEP 7: RUN SIMULATION")
            print("="*40)
            
            if not validate_solution_params(solution_params):
                print("Please complete all previous steps first.")
                continue
                
            # Show summary before running
            print_simulation_summary(setup_params, solution_params)
            
            # Ask for final confirmation
            if not start_calculation():
                print("Simulation cancelled by user.")
                continue
                
            # Run the simulation
            execute_simulation_from_params(setup_params, solution_params)
            return
            
        elif choice == "8":
            # View data submenu
            view_data_menu(solution_params, setup_params)
            
        elif choice == "9":
            # Modify configurations submenu
            modify_configurations_menu(setup_params, solution_params)
            
        elif choice == "10":
            save_solution_to_file(solution_params)
            print("Solution progress saved.")
            
        elif choice == "11":
            print("Returning to main menu.")
            return
            
        elif choice == "12":
            if input("Are you sure you want to reset solution progress? (y/n): ").strip().lower() == 'y':
                solution_params = {}
                save_solution_to_file(solution_params)
                print("Solution progress has been reset.")
        else:
            print("Invalid choice. Please enter 1-12.")


def save_case_data_files_menu(solution_params, setup_params):
    """
    Menu for configuring which design points to save case/data files for.
    
    Args:
        solution_params (dict): Solution parameters
        setup_params (dict): Setup parameters
    """
    print("\n" + "="*60)
    print("SAVE CASE/DATA FILES CONFIGURATION")
    print("="*60)
    
    while True:
        print("\nChoose an action:")
        print("1. View current design points")
        print("2. Configure which design points to save")
        print("3. View current save configuration")
        print("4. Clear save configuration")
        print("5. Return to solution menu")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            # View current design points
            view_design_points(solution_params, setup_params)
            
        elif choice == "2":
            # Configure which design points to save
            num_design_points = solution_params.get('num_design_points', 0)
            save_design_points = get_design_points_to_save(num_design_points, setup_params['project_folder'])
            solution_params['save_design_points'] = save_design_points
            save_solution_to_file(solution_params)
            print("Save configuration updated.")
            
        elif choice == "3":
            # View current save configuration
            view_save_configuration(solution_params)
            
        elif choice == "4":
            # Clear save configuration
            solution_params['save_design_points'] = None
            save_solution_to_file(solution_params)
            
            # Delete the saved design points CSV file since no files will be saved
            delete_saved_design_points_csv(setup_params['project_folder'])
            
            print("Save configuration cleared. No files will be saved.")
            
        elif choice == "5":
            return
            
        else:
            print("Invalid choice. Please enter 1-5.")


def modify_configurations_menu(setup_params, solution_params):
    """
    Menu to modify solution configurations.
    
    Args:
        setup_params (dict): Setup parameters
        solution_params (dict): Solution parameters
    """
    while True:
        print("\n" + "="*60)
        print("MODIFY CONFIGURATIONS")
        print("="*60)
        print("Choose what to modify:")
        print("1. Modify design points")
        print("2. Modify parameter movements")
        print("3. Modify save configuration")
        print("4. Return to solution menu")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            modify_design_points_menu(setup_params, solution_params)
        elif choice == "2":
            modify_parameter_movements_menu(setup_params, solution_params)
        elif choice == "3":
            save_case_data_files_menu(solution_params, setup_params)
        elif choice == "4":
            print("Returning to solution menu.")
            return
        else:
            print("Invalid choice. Please enter 1-4.")


def view_data_menu(solution_params, setup_params):
    """
    View data submenu to display named selections, design points, and parametric options.
    
    Args:
        solution_params (dict): Solution parameters
        setup_params (dict): Setup parameters
    """
    while True:
        print("\n" + "="*60)
        print("VIEW DATA")
        print("="*60)
        print("Choose what to view:")
        print("1. Named selections (from case file)")
        print("2. Selected parameters and movement ranges")
        print("3. Design points")
        print("4. Files to save configuration")
        print("5. Setup configuration summary")
        print("6. Return to solution menu")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == "1":
            view_named_selections(solution_params)
        elif choice == "2":
            view_parameter_selections(solution_params)
        elif choice == "3":
            view_design_points(solution_params, setup_params)
        elif choice == "4":
            view_save_configuration(solution_params)
        elif choice == "5":
            view_setup_summary(setup_params)
        elif choice == "6":
            print("Returning to solution menu.")
            return
        else:
            print("Invalid choice. Please enter 1-6.")


def view_named_selections(solution_params):
    """
    Display the named selections loaded from the case file.
    """
    print("\n" + "="*50)
    print("NAMED SELECTIONS")
    print("="*50)
    
    if 'named_selections' not in solution_params:
        print("No named selections loaded yet.")
        print("Please complete 'Load named selections' first.")
        return
    
    named_selections = solution_params['named_selections']
    
    if not named_selections:
        print("No named selections found in the case file.")
    else:
        print(f"Found {len(named_selections)} named selections:")
        for i, selection in enumerate(named_selections, 1):
            print(f"{i}. {selection}")
    
    print("="*50)


def view_parameter_selections(solution_params):
    """
    Display the selected parameters and their movement ranges.
    """
    print("\n" + "="*50)
    print("PARAMETER SELECTIONS & MOVEMENT RANGES")
    print("="*50)
    
    if 'geom_parameters_list' not in solution_params:
        print("No parameter selections made yet.")
        print("Please complete 'Define named movements' first.")
        return
    
    geom_parameters_list = solution_params['geom_parameters_list']
    geom_parameters = solution_params.get('geom_parameters', {})
    
    print(f"Selected {len(geom_parameters_list)} parameters:")
    print()
    
    for i, param_info in enumerate(geom_parameters_list, 1):
        # Handle different data structures
        if isinstance(param_info, dict):
            # If it's a dictionary, extract name and direction
            param_name = param_info.get('name', 'Unknown')
            direction = param_info.get('direction', 'Unknown')
        elif isinstance(param_info, str):
            # If it's a string, use it as the parameter name
            param_name = param_info
            direction = 'Unknown'
        else:
            # Handle other cases
            param_name = str(param_info)
            direction = 'Unknown'
        
        print(f"{i}. Parameter: {param_name}")
        
        # Show movement range if available
        if param_name in geom_parameters:
            param_data = geom_parameters[param_name]
            if isinstance(param_data, dict):
                # Handle complex nested structure with translate/rotate
                if 'translate' in param_data:
                    translate_data = param_data['translate']
                    if isinstance(translate_data, list) and len(translate_data) > 0:
                        enabled_translations = [t for t in translate_data if t.get('enabled', False)]
                        if enabled_translations:
                            print(f"   - Translations ({len(enabled_translations)}):")
                            for j, translate_info in enumerate(enabled_translations, 1):
                                min_val = translate_info.get('min', 'Not set')
                                max_val = translate_info.get('max', 'Not set')
                                direction_vec = translate_info.get('direction', [])
                                print(f"     {j}. Range: {min_val} to {max_val}, Direction: {direction_vec}")
                        else:
                            print("   - Translations: All disabled")
                    else:
                        print("   - Translations: Not configured")
                
                if 'rotate' in param_data:
                    rotate_data = param_data['rotate']
                    if isinstance(rotate_data, list) and len(rotate_data) > 0:
                        enabled_rotations = [r for r in rotate_data if r.get('enabled', False)]
                        if enabled_rotations:
                            print(f"   - Rotations ({len(enabled_rotations)}):")
                            for j, rotate_info in enumerate(enabled_rotations, 1):
                                min_val = rotate_info.get('min', 'Not set')
                                max_val = rotate_info.get('max', 'Not set')
                                axis_vec = rotate_info.get('axis', [])
                                print(f"     {j}. Range: {min_val} to {max_val} deg, Axis: {axis_vec}")
                        else:
                            print("   - Rotations: All disabled")
                    else:
                        print("   - Rotations: Not configured")
                
                # Fallback for simple structure
                if 'lower' in param_data and 'upper' in param_data:
                    lower = param_data.get('lower', 'Not set')
                    upper = param_data.get('upper', 'Not set')
                    print(f"   Range: {lower} to {upper}")
            else:
                print(f"   Range data: {param_data}")
        else:
            print("   Range: Not defined")
        print()
    
    print("="*50)


def view_design_points(solution_params, setup_params):
    """
    Display information about the generated design points.
    """
    print("\n" + "="*50)
    print("DESIGN POINTS")
    print("="*50)
    
    if 'design_points_path' not in solution_params:
        print("No design points generated yet.")
        print("Please complete 'Design points' configuration first.")
        return
    
    design_points_path = solution_params['design_points_path']
    num_design_points = solution_params.get('num_design_points', 0)
    
    print(f"Number of design points: {num_design_points}")
    print(f"Design points file: {design_points_path}")
    
    # Try to read and display a sample of the design points
    try:
        import pandas as pd
        df = pd.read_csv(design_points_path)
        
        print(f"\nDesign points preview (first 5 rows):")
        print("-" * 50)
        print(df.head().to_string(index=True))
        
        if len(df) > 5:
            print(f"\n... and {len(df) - 5} more rows")
            
    except ImportError:
        print("\nNote: Install pandas to view design points preview")
    except Exception as e:
        print(f"\nCould not read design points file: {e}")
    
    print("="*50)


def view_save_configuration(solution_params):
    """
    Display which design points will have case/data files saved.
    """
    print("\n" + "="*50)
    print("SAVE CONFIGURATION")
    print("="*50)
    
    if 'save_design_points' not in solution_params:
        print("No save configuration set yet.")
        print("Please complete 'Design points' configuration first.")
        return
    
    save_design_points = solution_params['save_design_points']
    
    if save_design_points is None:
        print("No case/data files will be saved.")
    else:
        print(f"Case/data files will be saved for {len(save_design_points)} design points:")
        print("Design points to save:", save_design_points)
        
        # Show which files will be created
        print("\nFiles that will be created:")
        for dp in save_design_points:
            print(f"- design_point_{dp}_case.cas")  # Display as 0-based to match user input
            print(f"- design_point_{dp}_data.dat")  # Display as 0-based to match user input
    
    print("="*50)


def view_setup_summary(setup_params):
    """
    Display a summary of the setup configuration.
    """
    print("\n" + "="*50)
    print("SETUP CONFIGURATION SUMMARY")
    print("="*50)
    
    print(f"Project folder: {setup_params.get('project_folder', 'Not set')}")
    print(f"Dimension: {setup_params.get('dimension', 'Not set')}D")
    print(f"Meshing cores: {setup_params.get('meshing_cores', 'Not set')}")
    print(f"Solver cores: {setup_params.get('solver_cores', 'Not set')}")
    print(f"Solver type: {setup_params.get('solver_type', 'Not set')}")
    print(f"SpaceClaim path: {setup_params.get('spaceclaim_path', 'Not set')}")
    print(f"Fluent path: {setup_params.get('fluent_path', 'Not set')}")
    
    # Show reference files
    ref_files = setup_params.get('ref_files', {})
    if ref_files:
        print("\nReference files:")
        for key, path in ref_files.items():
            print(f"- {key}: {path}")
    
    print("="*50)


def validate_setup(setup_params):
    """
    Validate that all required setup parameters are present.
    
    Args:
        setup_params (dict): Setup parameters to validate
    
    Returns:
        bool: True if setup is complete, False otherwise
    """
    required_params = ['project_folder', 'ref_files', 'dimension', 'meshing_cores', 
                      'solver_cores', 'spaceclaim_path', 'fluent_path', 'solver_type']
    
    missing_params = [param for param in required_params if param not in setup_params]
    
    if missing_params:
        print(f"Missing required parameters: {', '.join(missing_params)}")
        return False
    
    return True


def validate_solution_params(solution_params):
    """
    Validate that all required solution parameters are present.
    
    Args:
        solution_params (dict): Solution parameters to validate
    
    Returns:
        bool: True if solution params are complete, False otherwise
    """
    required_params = ['named_selections', 'updated_ref_paths', 'geom_parameters_list', 
                      'geom_parameters', 'design_points_path', 'num_design_points', 'save_design_points']
    
    missing_params = [param for param in required_params if param not in solution_params]
    
    if missing_params:
        print(f"Missing required solution parameters: {', '.join(missing_params)}")
        return False
    
    return True


def execute_simulation_from_params(setup_params, solution_params):
    """
    Execute the simulation with the given setup and solution parameters.
    
    Args:
        setup_params (dict): Setup parameters
        solution_params (dict): Solution parameters
    """
    import os
    
    # Import required modules
    import mesh_to_case_solver
    import folder_management
    import solver_setup
    import sc_files
    import mesh_scripts
    import batch_solver
    import post_process
    
    # Extract parameters
    project_folder = setup_params['project_folder']
    dim = setup_params['dimension']
    meshing_cores = setup_params['meshing_cores']
    solver_cores = setup_params['solver_cores']
    spaceclaim_path = setup_params['spaceclaim_path']
    fluent_path = setup_params['fluent_path']
    solver_type = setup_params['solver_type']
    
    # Use pre-computed solution parameters
    updated_ref_paths = solution_params['updated_ref_paths']
    geom_parameters_list = solution_params['geom_parameters_list']
    geom_parameters = solution_params['geom_parameters']
    save_design_points = solution_params['save_design_points']
    
    def run_single_simulation(run_label):
        """
        Execute a single simulation pass using the current design points.
        """
        print(f"\nStarting {run_label} simulation execution...")
        
        # Generate SpaceClaim script and run it
        script_path = sc_files.generate_spaceclaim_script(
            project_folder,
            geom_parameters,
            updated_ref_paths["geometry_file"],
            geom_parameters_list,
            None,
            save_design_points,
        )
        
        sc_files.run_spaceclaim_script_headless(script_path, spaceclaim_path)
        
        mesh_scripts.clean_journal(updated_ref_paths["mesh_journal"])
        mesh_scripts.generate_meshing_scripts_auto(project_folder, updated_ref_paths["mesh_journal"])
        
        if solver_type == "batch":
            # Traditional batch processing
            print("\nStarting Batch Processing...")
            batch_solver.run_meshing_scripts(project_folder, fluent_path, meshing_cores)
            
            batch_solver.generate_master_fluent_script(
                updated_ref_paths["case_journal"],
                project_folder,
                dim,
                solver_cores,
                None,
            )
            batch_solver.run_generated_fluent_script(project_folder)
            
        elif solver_type == "sequential":
            # Sequential mesh-case processing
            print("\nStarting Sequential Processing...")
            mesh_to_case_solver.generate_individual_case_files(
                updated_ref_paths["case_journal"],
                project_folder,
                dim,
                solver_cores,
                None,
            )
            mesh_to_case_solver.run_fluent_mesh_case(project_folder, fluent_path, meshing_cores)
        
        post_process.summarize_fluent_results(project_folder)
        
        print(f"\n{run_label.capitalize()} simulation completed successfully!")
    
    # Primary simulation pass
    run_single_simulation("primary")
    
    # Check if refinement inputs exist for an additional pass
    refinement_config_path = os.path.join(project_folder, "refinement_config.json")
    if not os.path.exists(refinement_config_path):
        return
    
    print("\n[INFO] Refinement configuration detected. Initializing refinement workflow...")
    try:
        from model_refinment import (
            create_model_refinment,
            move_ref_files,
            create_refinment_dps,
            final_file_move,
            summerize_refinment_results,
        )
    except ImportError as exc:
        print(f"[WARNING] Unable to import refinement modules ({exc}). Skipping refinement pass.")
        return
    
    try:
        create_model_refinment(project_folder)
    except Exception as exc:
        print(f"[WARNING] Failed to create refinement model: {exc}. Skipping refinement pass.")
        return
    
    rif_folder = move_ref_files(project_folder)
    if not rif_folder:
        print("[WARNING] Unable to archive base simulation results. Skipping refinement pass.")
        return
    
    try:
        refined_design_points_path = create_refinment_dps(project_folder, rif_folder)
    except Exception as exc:
        print(f"[WARNING] Refinement design point generation failed: {exc}. Skipping refinement pass.")
        return
    
    if not refined_design_points_path or not os.path.exists(refined_design_points_path):
        print("[WARNING] Refinement design points were not created. Skipping refinement pass.")
        return
    
    solution_params['design_points_path'] = refined_design_points_path
    
    # Update the number of design points if possible
    num_points = None
    try:
        import pandas as pd  # type: ignore
        df = pd.read_csv(refined_design_points_path)
        num_points = len(df.index)
    except Exception:
        try:
            with open(refined_design_points_path, 'r') as f:
                num_points = sum(1 for _ in f) - 1  # subtract header
        except Exception:
            num_points = None
    
    if num_points is not None and num_points >= 0:
        solution_params['num_design_points'] = num_points
    
    # Persist the updated solution configuration
    save_solution_to_file(solution_params)
    
    print("\n[INFO] Re-running simulation with refinement design points...")
    run_single_simulation("refinement")

    # Archive the refined results and summarize across all refinement runs
    try:
        new_rif_folder = final_file_move(project_folder)
        if new_rif_folder:
            print(f"[INFO] Final refinement files archived to: {new_rif_folder}")
        else:
            print("[WARNING] Could not archive refinement files into a rif folder.")
    except Exception as exc:
        print(f"[WARNING] Failed during final refinement file move: {exc}")
        new_rif_folder = False

    try:
        summary_paths = summerize_refinment_results(project_folder)
        if summary_paths:
            print("[INFO] Consolidated refinement results generated:")
            for key, path in summary_paths.items():
                print(f"  {key}: {path}")
        else:
            print("[WARNING] No refinement results were consolidated.")
    except Exception as exc:
        print(f"[WARNING] Failed to summarize refinement results: {exc}")


def save_setup_to_file(setup_params):
    """
    Save setup parameters to a file for later use.
    
    Args:
        setup_params (dict): Dictionary containing all setup parameters
    """
    import json
    import os
    
    setup_file = os.path.join(os.getcwd(), "setup_config.json")
    
    try:
        with open(setup_file, 'w') as f:
            json.dump(setup_params, f, indent=2)
        print(f"Setup saved to: {setup_file}")
    except Exception as e:
        print(f"Could not save setup: {e}")


def load_setup_from_file():
    """
    Load setup parameters from file.
    
    Returns:
        dict: Setup parameters or None if file not found
    """
    import json
    import os
    
    setup_file = os.path.join(os.getcwd(), "setup_config.json")
    
    if not os.path.exists(setup_file):
        return None
    
    try:
        with open(setup_file, 'r') as f:
            setup_params = json.load(f)
        return setup_params
    except Exception as e:
        print(f"Could not load setup: {e}")
        return None


def save_solution_to_file(solution_params):
    """
    Save solution parameters to a file for later use.
    
    Args:
        solution_params (dict): Dictionary containing solution parameters
    """
    import json
    import os
    
    solution_file = os.path.join(os.getcwd(), "solution_config.json")
    
    try:
        with open(solution_file, 'w') as f:
            json.dump(solution_params, f, indent=2)
    except Exception as e:
        print(f"Could not save solution progress: {e}")


def load_solution_from_file():
    """
    Load solution parameters from file.
    
    Returns:
        dict: Solution parameters or None if file not found
    """
    import json
    import os
    
    solution_file = os.path.join(os.getcwd(), "solution_config.json")
    
    if not os.path.exists(solution_file):
        return None
    
    try:
        with open(solution_file, 'r') as f:
            solution_params = json.load(f)
        return solution_params
    except Exception as e:
        print(f"Could not load solution progress: {e}")
        return None


def print_solution_status(solution_params):
    """
    Print the current status of solution parameters.
    
    Args:
        solution_params (dict): Solution parameters to check
    """
    status_map = {
        'named_selections': 'Named parameters extracted',
        'updated_ref_paths': 'Reference files processed',
        'geom_parameters_list': 'Parameter selections made',
        'geom_parameters': 'Movement ranges defined',
        'design_points_path': 'Design points generated',
        'num_design_points': 'Number of design points',
        'save_design_points': 'Save files selection'
    }
    
    for param, display_name in status_map.items():
        if param in solution_params:
            if param == 'num_design_points':
                print(f"✓ {display_name}: {solution_params[param]}")
            elif param == 'save_design_points' and solution_params[param] is not None:
                print(f"✓ {display_name}: {len(solution_params[param])} points selected")
            elif param == 'save_design_points' and solution_params[param] is None:
                print(f"✓ {display_name}: No files to save")
            else:
                print(f"✓ {display_name}: Complete")
        else:
            print(f"✗ {display_name}: Not completed")


def print_simulation_summary(setup_params, solution_params):
    """
    Print a summary of the simulation configuration before running.
    
    Args:
        setup_params (dict): Setup parameters
        solution_params (dict): Solution parameters
    """
    print("\n" + "="*60)
    print("SIMULATION SUMMARY")
    print("="*60)
    print(f"Project folder: {setup_params['project_folder']}")
    print(f"Dimension: {setup_params['dimension']}D")
    print(f"Meshing cores: {setup_params['meshing_cores']}")
    print(f"Solver cores: {setup_params['solver_cores']}")
    print(f"Solver type: {setup_params['solver_type']}")
    print(f"SpaceClaim path: {setup_params['spaceclaim_path']}")
    print(f"Fluent path: {setup_params['fluent_path']}")
    print(f"Design points: {solution_params['num_design_points']}")
    if solution_params['save_design_points'] is not None:
        print(f"Files to save: {len(solution_params['save_design_points'])} design points")
    else:
        print("Files to save: None")
    print("="*60)


def modify_parameter_movements_detailed(solution_params, setup_params):
    """
    Detailed menu for modifying parameter movements with add/remove options.
    
    Args:
        solution_params (dict): Solution parameters
        setup_params (dict): Setup parameters
    """
    print("\n" + "="*60)
    print("MODIFY PARAMETER MOVEMENTS - DETAILED")
    print("="*60)
    
    while True:
        print("\nCurrent parameters:")
        for i, param in enumerate(solution_params['geom_parameters_list'], 1):
            print(f"{i}. {param}")
        
        try:
            param_choice = input("\nEnter parameter number to modify (or 'back' to return): ").strip()
            
            if param_choice.lower() == 'back':
                return
            else:
                param_idx = int(param_choice) - 1
                if 0 <= param_idx < len(solution_params['geom_parameters_list']):
                    param_name = solution_params['geom_parameters_list'][param_idx]
                    modify_single_parameter_detailed(param_name, solution_params, setup_params)
                else:
                    print("Invalid parameter number.")
                    
        except ValueError:
            print("Invalid input. Please enter a number or 'back'.")


def modify_single_parameter_detailed(param_name, solution_params, setup_params):
    """
    Detailed modification of a single parameter's movements.
    
    Args:
        param_name (str): Name of the parameter to modify
        solution_params (dict): Solution parameters
        setup_params (dict): Setup parameters
    """
    print(f"\n" + "="*50)
    print(f"MODIFYING PARAMETER: {param_name}")
    print("="*50)
    
    # Get current parameter data
    geom_parameters = solution_params.get('geom_parameters', {})
    if param_name not in geom_parameters:
        geom_parameters[param_name] = {
            'translate': [{'enabled': False, 'min': 0.0, 'max': 0.0, 'direction': [0,0,0]}],
            'rotate': [{'enabled': False, 'min': 0.0, 'max': 0.0, 'axis': [0,0,1]}]
        }
    
    param_data = geom_parameters[param_name]
    
    # Store original state to detect changes
    import copy
    original_param_data = copy.deepcopy(param_data)
    
    while True:
        print(f"\nCurrent movements for {param_name}:")
        
        # Display current translations
        if 'translate' in param_data and param_data['translate']:
            enabled_translations = [t for t in param_data['translate'] if t.get('enabled', False)]
            if enabled_translations:
                print(f"  Translations ({len(enabled_translations)}):")
                for i, t in enumerate(enabled_translations, 1):
                    print(f"    {i}. Range: {t.get('min', 0)} to {t.get('max', 0)}, Direction: {t.get('direction', [0,0,0])}")
            else:
                print("  Translations: None enabled")
        
        # Display current rotations
        if 'rotate' in param_data and param_data['rotate']:
            enabled_rotations = [r for r in param_data['rotate'] if r.get('enabled', False)]
            if enabled_rotations:
                print(f"  Rotations ({len(enabled_rotations)}):")
                for i, r in enumerate(enabled_rotations, 1):
                    print(f"    {i}. Range: {r.get('min', 0)} to {r.get('max', 0)} deg, Axis: {r.get('axis', [0,0,1])}")
            else:
                print("  Rotations: None enabled")
        
        print("\nChoose an action:")
        print("1. Add translation")
        print("2. Add rotation")
        print("3. Modify existing translation")
        print("4. Modify existing rotation")
        print("5. Remove translation")
        print("6. Remove rotation")
        print("7. Return to parameter selection")
        
        choice = input("\nEnter your choice (1-7): ").strip()
        
        if choice == "1":
            add_translation(param_name, param_data)
        elif choice == "2":
            add_rotation(param_name, param_data)
        elif choice == "3":
            modify_existing_translation(param_name, param_data)
        elif choice == "4":
            modify_existing_rotation(param_name, param_data)
        elif choice == "5":
            remove_translation(param_name, param_data)
        elif choice == "6":
            remove_rotation(param_name, param_data)
        elif choice == "7":
            # Check if any changes were made
            if param_data != original_param_data:
                # Save changes (design points will be regenerated at menu level)
                solution_params['geom_parameters'] = geom_parameters
                save_solution_to_file(solution_params)
                print("✅ Parameter changes saved.")
            else:
                print("No changes made to parameter.")
            return
        else:
            print("Invalid choice. Please enter 1-7.")


def add_translation(param_name, param_data):
    """Add a new translation to a parameter."""
    print(f"\nAdding new translation for {param_name}")
    
    # Get min/max values
    while True:
        try:
            min_val = float(input("  Translation min value: ").strip())
            max_val = float(input("  Translation max value: ").strip())
            if max_val < min_val:
                print("❌ Invalid range. Ensure max >= min.")
                continue
            break
        except ValueError:
            print("❌ Enter numeric values only.")
    
    # Get direction
    allowed_vectors = [[1,0,0], [0,1,0], [0,0,1]]
    while True:
        try:
            dir_input = input("  Translation direction vector (x,y,z, allowed: 1,0,0 or 0,1,0 or 0,0,1): ").strip()
            direction = [int(x) for x in dir_input.split(",")]
            if direction not in allowed_vectors:
                print("❌ Invalid direction. Must be one of: [1,0,0], [0,1,0], [0,0,1]")
                continue
            
            # Check if direction already exists
            existing_directions = [t.get('direction', []) for t in param_data.get('translate', []) if t.get('enabled', False)]
            if direction in existing_directions:
                print("❌ This direction already exists for this parameter.")
                continue
            
            break
        except ValueError:
            print("❌ Invalid input. Enter integers separated by commas.")
    
    # Add the translation
    if 'translate' not in param_data:
        param_data['translate'] = []
    
    param_data['translate'].append({
        'enabled': True,
        'min': min_val,
        'max': max_val,
        'direction': direction
    })
    
    print(f"✅ Translation added: {min_val} to {max_val}, Direction: {direction}")


def add_rotation(param_name, param_data):
    """Add a new rotation to a parameter."""
    print(f"\nAdding new rotation for {param_name}")
    
    # Get min/max values
    while True:
        try:
            min_val = float(input("  Rotation min value (deg): ").strip())
            max_val = float(input("  Rotation max value (deg): ").strip())
            if max_val < min_val:
                print("❌ Invalid range. Ensure max >= min.")
                continue
            break
        except ValueError:
            print("❌ Enter numeric values only.")
    
    # Get axis
    allowed_vectors = [[1,0,0], [0,1,0], [0,0,1]]
    while True:
        try:
            axis_input = input("  Rotation axis vector (x,y,z, allowed: 1,0,0 or 0,1,0 or 0,0,1): ").strip()
            axis = [int(x) for x in axis_input.split(",")]
            if axis not in allowed_vectors:
                print("❌ Invalid axis. Must be one of: [1,0,0], [0,1,0], [0,0,1]")
                continue
            
            # Check if axis already exists
            existing_axes = [r.get('axis', []) for r in param_data.get('rotate', []) if r.get('enabled', False)]
            if axis in existing_axes:
                print("❌ This axis already exists for this parameter.")
                continue
            
            break
        except ValueError:
            print("❌ Invalid input. Enter integers separated by commas.")
    
    # Add the rotation
    if 'rotate' not in param_data:
        param_data['rotate'] = []
    
    param_data['rotate'].append({
        'enabled': True,
        'min': min_val,
        'max': max_val,
        'axis': axis
    })
    
    print(f"✅ Rotation added: {min_val} to {max_val} deg, Axis: {axis}")


def modify_existing_translation(param_name, param_data):
    """Modify an existing translation."""
    if 'translate' not in param_data or not param_data['translate']:
        print("No translations to modify.")
        return
    
    enabled_translations = [t for t in param_data['translate'] if t.get('enabled', False)]
    if not enabled_translations:
        print("No enabled translations to modify.")
        return
    
    print("\nSelect translation to modify:")
    for i, t in enumerate(enabled_translations, 1):
        print(f"  {i}. Range: {t.get('min', 0)} to {t.get('max', 0)}, Direction: {t.get('direction', [0,0,0])}")
    
    while True:
        try:
            choice = int(input("Enter translation number to modify: ").strip())
            if 1 <= choice <= len(enabled_translations):
                # Find the actual index in the full list
                actual_idx = param_data['translate'].index(enabled_translations[choice-1])
                
                # Get new values
                print("Enter new values (press Enter to keep current value):")
                
                # Min value
                current_min = enabled_translations[choice-1].get('min', 0)
                new_min_input = input(f"  New min value (current: {current_min}): ").strip()
                new_min = float(new_min_input) if new_min_input else current_min
                
                # Max value
                current_max = enabled_translations[choice-1].get('max', 0)
                new_max_input = input(f"  New max value (current: {current_max}): ").strip()
                new_max = float(new_max_input) if new_max_input else current_max
                
                if new_max < new_min:
                    print("❌ Invalid range. Ensure max >= min.")
                    continue
                
                # Direction
                current_direction = enabled_translations[choice-1].get('direction', [0,0,0])
                print(f"  Current direction: {current_direction}")
                dir_input = input("  New direction vector (x,y,z, allowed: 1,0,0 or 0,1,0 or 0,0,1, or press Enter to keep current): ").strip()
                
                new_direction = current_direction
                if dir_input:
                    allowed_vectors = [[1,0,0], [0,1,0], [0,0,1]]
                    try:
                        direction = [int(x) for x in dir_input.split(",")]
                        if direction in allowed_vectors:
                            new_direction = direction
                        else:
                            print("❌ Invalid direction. Keeping current direction.")
                    except ValueError:
                        print("❌ Invalid direction format. Keeping current direction.")
                
                # Update the translation
                param_data['translate'][actual_idx]['min'] = new_min
                param_data['translate'][actual_idx]['max'] = new_max
                param_data['translate'][actual_idx]['direction'] = new_direction
                
                print(f"✅ Translation updated: {new_min} to {new_max}")
                break
            else:
                print("Invalid choice.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def modify_existing_rotation(param_name, param_data):
    """Modify an existing rotation."""
    if 'rotate' not in param_data or not param_data['rotate']:
        print("No rotations to modify.")
        return
    
    enabled_rotations = [r for r in param_data['rotate'] if r.get('enabled', False)]
    if not enabled_rotations:
        print("No enabled rotations to modify.")
        return
    
    print("\nSelect rotation to modify:")
    for i, r in enumerate(enabled_rotations, 1):
        print(f"  {i}. Range: {r.get('min', 0)} to {r.get('max', 0)} deg, Axis: {r.get('axis', [0,0,1])}")
    
    while True:
        try:
            choice = int(input("Enter rotation number to modify: ").strip())
            if 1 <= choice <= len(enabled_rotations):
                # Find the actual index in the full list
                actual_idx = param_data['rotate'].index(enabled_rotations[choice-1])
                
                # Get new values
                print("Enter new values (press Enter to keep current value):")
                
                # Min value
                current_min = enabled_rotations[choice-1].get('min', 0)
                new_min_input = input(f"  New min value (current: {current_min}): ").strip()
                new_min = float(new_min_input) if new_min_input else current_min
                
                # Max value
                current_max = enabled_rotations[choice-1].get('max', 0)
                new_max_input = input(f"  New max value (current: {current_max}): ").strip()
                new_max = float(new_max_input) if new_max_input else current_max
                
                if new_max < new_min:
                    print("❌ Invalid range. Ensure max >= min.")
                    continue
                
                # Axis
                current_axis = enabled_rotations[choice-1].get('axis', [0,0,1])
                print(f"  Current axis: {current_axis}")
                axis_input = input("  New axis vector (x,y,z, allowed: 1,0,0 or 0,1,0 or 0,0,1, or press Enter to keep current): ").strip()
                
                new_axis = current_axis
                if axis_input:
                    allowed_vectors = [[1,0,0], [0,1,0], [0,0,1]]
                    try:
                        axis = [int(x) for x in axis_input.split(",")]
                        if axis in allowed_vectors:
                            new_axis = axis
                        else:
                            print("❌ Invalid axis. Keeping current axis.")
                    except ValueError:
                        print("❌ Invalid axis format. Keeping current axis.")
                
                # Update the rotation
                param_data['rotate'][actual_idx]['min'] = new_min
                param_data['rotate'][actual_idx]['max'] = new_max
                param_data['rotate'][actual_idx]['axis'] = new_axis
                
                print(f"✅ Rotation updated: {new_min} to {new_max} deg")
                break
            else:
                print("Invalid choice.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def remove_translation(param_name, param_data):
    """Remove a translation from a parameter."""
    if 'translate' not in param_data or not param_data['translate']:
        print("No translations to remove.")
        return
    
    enabled_translations = [t for t in param_data['translate'] if t.get('enabled', False)]
    if not enabled_translations:
        print("No enabled translations to remove.")
        return
    
    print("\nSelect translation to remove:")
    for i, t in enumerate(enabled_translations, 1):
        print(f"  {i}. Range: {t.get('min', 0)} to {t.get('max', 0)}, Direction: {t.get('direction', [0,0,0])}")
    
    while True:
        try:
            choice = int(input("Enter translation number to remove: ").strip())
            if 1 <= choice <= len(enabled_translations):
                # Find the actual index in the full list and remove it
                actual_idx = param_data['translate'].index(enabled_translations[choice-1])
                removed_translation = param_data['translate'].pop(actual_idx)
                
                print(f"✅ Translation removed: {removed_translation.get('min', 0)} to {removed_translation.get('max', 0)}, Direction: {removed_translation.get('direction', [0,0,0])}")
                break
            else:
                print("Invalid choice.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def remove_rotation(param_name, param_data):
    """Remove a rotation from a parameter."""
    if 'rotate' not in param_data or not param_data['rotate']:
        print("No rotations to remove.")
        return
    
    enabled_rotations = [r for r in param_data['rotate'] if r.get('enabled', False)]
    if not enabled_rotations:
        print("No enabled rotations to remove.")
        return
    
    print("\nSelect rotation to remove:")
    for i, r in enumerate(enabled_rotations, 1):
        print(f"  {i}. Range: {r.get('min', 0)} to {r.get('max', 0)} deg, Axis: {r.get('axis', [0,0,1])}")
    
    while True:
        try:
            choice = int(input("Enter rotation number to remove: ").strip())
            if 1 <= choice <= len(enabled_rotations):
                # Find the actual index in the full list and remove it
                actual_idx = param_data['rotate'].index(enabled_rotations[choice-1])
                removed_rotation = param_data['rotate'].pop(actual_idx)
                
                print(f"✅ Rotation removed: {removed_rotation.get('min', 0)} to {removed_rotation.get('max', 0)} deg, Axis: {removed_rotation.get('axis', [0,0,1])}")
                break
            else:
                print("Invalid choice.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def analysis_menu():
    """
    Analysis sub-menu for viewing simulation results.
    """
    print("\n" + "="*60)
    print("ANALYSIS MENU")
    print("="*60)
    
    # Try to load existing setup to get project folder
    setup_params = load_setup_from_file()
    
    if setup_params is None:
        print("No setup found. Choose an option:")
        print("1. Enter project folder path (assume files are already in place)")
        print("2. Manually specify project folder and data files")
        
        choice = input("\nEnter your choice (1 or 2): ").strip()
        
        if choice == "1":
            project_folder = input("Enter the project folder path: ").strip().strip('"\'')
            if not project_folder:
                print("❌ Project folder is required.")
                return
            # Save the project folder for future use
            save_project_folder(project_folder)
        elif choice == "2":
            project_folder = setup_analysis_with_files()
            if not project_folder:
                return
        else:
            print("❌ Invalid choice.")
            return
    else:
        project_folder = setup_params.get('project_folder', '')
        if not project_folder:
            print("Project folder not found in setup. Choose an option:")
            print("1. Enter project folder path (assume files are already in place)")
            print("2. Manually specify project folder and data files")
            
            choice = input("\nEnter your choice (1 or 2): ").strip()
            
            if choice == "1":
                project_folder = input("Enter the project folder path: ").strip().strip('"\'')
                if not project_folder:
                    print("❌ Project folder is required.")
                    return
                # Save the project folder for future use
                save_project_folder(project_folder)
            elif choice == "2":
                project_folder = setup_analysis_with_files()
                if not project_folder:
                    return
            else:
                print("❌ Invalid choice.")
                return
    
    while True:
        print("\nChoose an analysis option:")
        print("1. View simulation summary")
        print("2. Sensitivity analysis")
        print("3. Data modeling")
        print("4. Optimization")
        print("5. Graphing and visualization")
        print("6. Return to main menu")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == "1":
            view_simulation_summary_menu(project_folder)
        elif choice == "2":
            sensitivity_analysis_menu(project_folder)
        elif choice == "3":
            data_modeling_menu(project_folder)
        elif choice == "4":
            optimization_menu(project_folder)
        elif choice == "5":
            run_graph_menu(project_folder)
        elif choice == "6":
            print("Returning to main menu.")
            return
        else:
            print("Invalid choice. Please enter a number between 1 and 6.")


def save_project_folder(project_folder):
    """
    Save project folder to setup file for future use.
    
    Args:
        project_folder (str): Path to the project folder
    """
    try:
        setup_data = {
            'project_folder': project_folder,
            'setup_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        setup_file = 'setup_config.json'
        import json
        with open(setup_file, 'w') as f:
            json.dump(setup_data, f, indent=4)
        
        print(f"✅ Project folder saved to setup: {project_folder}")
    except Exception as e:
        print(f"⚠️ Warning: Could not save project folder: {e}")


def setup_analysis_with_files():
    """
    Setup analysis by manually specifying project folder and data files.
    The program will organize the files into the correct structure.
    
    Returns:
        str: Project folder path if successful, None if failed
    """
    print("\n" + "="*60)
    print("MANUAL FILE SETUP")
    print("="*60)
    print("This option allows you to specify project folder and data files.")
    print("The program will organize them into the correct structure.")
    print("="*60)
    
    # Get project folder
    print("\n📁 Project folder setup:")
    project_folder = input("Enter the project folder path (where analysis files will be stored): ").strip().strip('"\'')
    
    if not project_folder:
        print("❌ Project folder is required.")
        return None
    
    # Create project folder if it doesn't exist
    import os
    os.makedirs(project_folder, exist_ok=True)
    print(f"✅ Project folder: {project_folder}")
    
    # Get design points CSV file
    print("\n📊 Design points file:")
    design_points_file = input("Enter path to DesignPoints.csv file: ").strip().strip('"\'')
    
    if not design_points_file or not os.path.exists(design_points_file):
        print("❌ Design points file not found or invalid.")
        return None
    
    print(f"✅ Design points file: {design_points_file}")
    
    # Get summary CSV file
    print("\n📈 Summary file:")
    summary_file = input("Enter path to summary CSV file (e.g., summary2.csv): ").strip().strip('"\'')
    
    if not summary_file or not os.path.exists(summary_file):
        print("❌ Summary file not found or invalid.")
        return None
    
    print(f"✅ Summary file: {summary_file}")
    
    # Create required directory structure
    print("\n📁 Creating directory structure...")
    dps_folder = os.path.join(project_folder, "test_files", "dps")
    out_final_folder = os.path.join(project_folder, "test_files", "out_final")
    
    os.makedirs(dps_folder, exist_ok=True)
    os.makedirs(out_final_folder, exist_ok=True)
    
    print(f"✅ Created: {dps_folder}")
    print(f"✅ Created: {out_final_folder}")
    
    # Copy files to project structure
    print("\n📋 Organizing files...")
    
    try:
        import shutil
        
        # Copy design points file
        design_points_dest = os.path.join(dps_folder, "DesignPoints.csv")
        shutil.copy2(design_points_file, design_points_dest)
        print(f"✅ Copied design points to: {design_points_dest}")
        
        # Copy summary file
        summary_dest = os.path.join(out_final_folder, "summary2.csv")
        shutil.copy2(summary_file, summary_dest)
        print(f"✅ Copied summary to: {summary_dest}")
        
        # Create a basic saved_design_points.csv if it doesn't exist
        saved_design_points_file = os.path.join(dps_folder, "saved_design_points.csv")
        if not os.path.exists(saved_design_points_file):
            # Create empty saved design points file
            with open(saved_design_points_file, 'w', newline='') as f:
                f.write("")  # Empty file
            print(f"✅ Created empty saved_design_points.csv")
        
        # Save the project folder for future use
        save_project_folder(project_folder)
        
        print("\n🎉 File organization completed successfully!")
        print(f"📁 Project structure created at: {project_folder}")
        print("✅ Files are now organized and ready for analysis!")
        
        return project_folder
                
    except Exception as e:
        print(f"❌ Error organizing files: {e}")
        print("Please check file paths and permissions.")
        return None


def sensitivity_analysis_menu(project_folder):
    """
    Sensitivity analysis sub-menu for running and viewing sensitivity analysis.
    
    Args:
        project_folder (str): Path to the project folder
    """
    print("\n" + "="*60)
    print("SENSITIVITY ANALYSIS MENU")
    print("="*60)
    
    while True:
        print("\nChoose a sensitivity analysis option:")
        print("1. Run new sensitivity analysis")
        print("2. View existing sensitivity results")
        print("3. Return to analysis menu")
        
        choice = input("\nEnter your choice (1, 2, or 3): ").strip()
        
        if choice == "1":
            run_sensitivity_analysis_menu(project_folder)
        elif choice == "2":
            view_sensitivity_results_menu(project_folder)
        elif choice == "3":
            print("Returning to analysis menu.")
            return
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")


def run_sensitivity_analysis_menu(project_folder):
    """
    Menu for running sensitivity analysis with different options.
    
    Args:
        project_folder (str): Path to the project folder
    """
    print("\n" + "="*50)
    print("RUN SENSITIVITY ANALYSIS")
    print("="*50)
    
    # Check if required data files exist
    required_files = [
        os.path.join(project_folder, "test_files", "dps", "DesignPoints.csv"),
        os.path.join(project_folder, "test_files", "out_final", "summary2.csv")
    ]
    
    missing_files = [f for f in required_files if not os.path.exists(f)]
    if missing_files:
        print("❌ Missing required files:")
        for f in missing_files:
            print(f"   - {f}")
        print("\nPlease run simulations first to generate the required data files.")
        return
    
    print("✅ Required data files found")
    
    while True:
        print("\nChoose analysis type:")
        print("1. Quick analysis (20 bootstrap iterations)")
        print("2. Comprehensive analysis (50 bootstrap iterations)")
        print("3. Custom analysis")
        print("4. Return to sensitivity menu")
        
        choice = input("\nEnter your choice (1, 2, 3, or 4): ").strip()
        
        if choice == "1":
            print("\n🔬 Running quick sensitivity analysis...")
            try:
                from sensitivity_analysis import quick_sensitivity_analysis
                results = quick_sensitivity_analysis(project_folder)
                if results:
                    print("\n🎉 Quick analysis completed successfully!")
                    print(f"📊 Results saved to: {project_folder}/test_files/out_final/sensitivity/")
                else:
                    print("❌ Analysis failed. Please check your data and dependencies.")
            except ImportError as e:
                print(f"❌ Error importing sensitivity analysis module: {e}")
                print("Please ensure sensitivity_analysis.py is in the same directory.")
            except Exception as e:
                print(f"❌ Error running analysis: {e}")
                
        elif choice == "2":
            print("\n🔬 Running comprehensive sensitivity analysis...")
            try:
                from sensitivity_analysis import perform_sensitivity_analysis
                results = perform_sensitivity_analysis(project_folder)
                if results:
                    print("\n🎉 Comprehensive analysis completed successfully!")
                    print(f"📊 Results saved to: {project_folder}/test_files/out_final/sensitivity/")
                else:
                    print("❌ Analysis failed. Please check your data and dependencies.")
            except ImportError as e:
                print(f"❌ Error importing sensitivity analysis module: {e}")
                print("Please ensure sensitivity_analysis.py is in the same directory.")
            except Exception as e:
                print(f"❌ Error running analysis: {e}")
                
        elif choice == "3":
            print("\n🔬 Running custom sensitivity analysis...")
            try:
                # Get custom parameters
                try:
                    n_bootstrap = int(input("Number of bootstrap iterations (default 30): ") or "30")
                    variance_threshold = float(input("Variance threshold (default 0.95): ") or "0.95")
                except ValueError:
                    print("❌ Invalid input. Using default values.")
                    n_bootstrap = 30
                    variance_threshold = 0.95
                
                from sensitivity_analysis import perform_sensitivity_analysis
                results = perform_sensitivity_analysis(
                    project_folder, 
                    n_bootstrap=n_bootstrap, 
                    variance_threshold=variance_threshold
                )
                if results:
                    print("\n🎉 Custom analysis completed successfully!")
                    print(f"📊 Results saved to: {project_folder}/test_files/out_final/sensitivity/")
                else:
                    print("❌ Analysis failed. Please check your data and dependencies.")
            except ImportError as e:
                print(f"❌ Error importing sensitivity analysis module: {e}")
                print("Please ensure sensitivity_analysis.py is in the same directory.")
            except Exception as e:
                print(f"❌ Error running analysis: {e}")
                
        elif choice == "4":
            print("Returning to sensitivity analysis menu.")
            return
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")


def view_sensitivity_results_menu(project_folder):
    """
    Menu for viewing existing sensitivity analysis results.
    
    Args:
        project_folder (str): Path to the project folder
    """
    print("\n" + "="*50)
    print("VIEW SENSITIVITY RESULTS")
    print("="*50)
    
    # Check if results exist
    results_file = os.path.join(project_folder, "test_files", "out_final", "sensitivity", "sensitivity_analysis_results.csv")
    
    if not os.path.exists(results_file):
        print(f"❌ No sensitivity analysis results found at: {results_file}")
        print("Please run the sensitivity analysis first.")
        return
    
    print("✅ Sensitivity analysis results found")
    
    while True:
        print("\nChoose a viewing option:")
        print("1. Interactive results display")
        print("2. View results files")
        print("3. Return to sensitivity menu")
        
        choice = input("\nEnter your choice (1, 2, or 3): ").strip()
        
        if choice == "1":
            print("\n📊 Loading interactive sensitivity analysis results...")
            try:
                from sensitivity_analysis import display_existing_results
                display_existing_results(project_folder)
            except ImportError as e:
                print(f"❌ Error importing sensitivity analysis module: {e}")
                print("Please ensure sensitivity_analysis.py is in the same directory.")
            except Exception as e:
                print(f"❌ Error loading results: {e}")
                
        elif choice == "2":
            print("\n📁 Available sensitivity analysis files:")
            sensitivity_folder = os.path.join(project_folder, "test_files", "out_final", "sensitivity")
            
            files = [
                ("sensitivity_analysis_results.csv", "Detailed results data"),
                ("sensitivity_analysis_plot.png", "4-panel visualization"),
                ("sensitivity_analysis_summary.txt", "Comprehensive report")
            ]
            
            for filename, description in files:
                filepath = os.path.join(sensitivity_folder, filename)
                if os.path.exists(filepath):
                    print(f"✅ {filename} - {description}")
                else:
                    print(f"❌ {filename} - Not found")
            
            print(f"\n📁 Files location: {sensitivity_folder}")
            
        elif choice == "3":
            print("Returning to sensitivity analysis menu.")
            return
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")


def view_simulation_summary(project_folder):
    """
    Display a comprehensive summary of simulation results.
    
    Args:
        project_folder (str): Path to the project folder
    """
    print("\n" + "="*80)
    print("SIMULATION SUMMARY")
    print("="*80)
    
    # Check if required files exist
    dps_folder = os.path.join(project_folder, "test_files", "dps")
    summary_folder = os.path.join(project_folder, "test_files", "out_final")
    
    design_points_file = os.path.join(dps_folder, "DesignPoints.csv")
    failed_points_file = os.path.join(dps_folder, "DesignPoints_failed.csv")
    saved_points_file = os.path.join(dps_folder, "saved_design_points.csv")
    
    # Find summary file (could be summary.csv, summary2.csv, etc.)
    summary_files = []
    if os.path.exists(summary_folder):
        for file in os.listdir(summary_folder):
            if file.startswith("summary") and file.endswith(".csv"):
                summary_files.append(os.path.join(summary_folder, file))
    
    if not summary_files:
        print("❌ No summary files found in out_final folder.")
        print("Make sure simulations have been completed.")
        return
    
    # Use the first summary file found
    summary_file = summary_files[0]
    
    try:
        # Read successful design points
        successful_points = []
        if os.path.exists(design_points_file):
            with open(design_points_file, 'r') as f:
                lines = f.readlines()
                header = lines[0].strip().split(',')
                dp_index = 0  # Track actual design point index
                for i, line in enumerate(lines[1:], 0):
                    if line.strip():
                        values = [float(x.strip()) for x in line.strip().split(',')]
                        successful_points.append({
                            'index': dp_index,
                            'values': values,
                            'params': header
                        })
                        dp_index += 1
        
        # Read failed design points
        failed_points = []
        if os.path.exists(failed_points_file):
            with open(failed_points_file, 'r') as f:
                lines = f.readlines()
                header = lines[0].strip().split(',')
                for i, line in enumerate(lines[1:], 0):
                    if line.strip():
                        values = [float(x.strip()) for x in line.strip().split(',')]
                        failed_points.append({
                            'values': values,
                            'params': header
                        })
        
        # Read saved design points
        saved_point_indices = []
        if os.path.exists(saved_points_file):
            with open(saved_points_file, 'r') as f:
                lines = f.readlines()
                for line in lines[1:]:  # Skip header
                    if line.strip():
                        saved_point_indices.append(int(line.strip()))
        
        # Read summary results
        output_results = {}
        if os.path.exists(summary_file):
            with open(summary_file, 'r') as f:
                lines = f.readlines()
                header = lines[0].strip().split(',')
                
                # Parse output parameters - map columns to design point indices
                output_columns = header[1:]  # Skip first column (parameter names)
                
                # Create mapping from column names to design point indices
                column_to_dp = {}
                for i, col_name in enumerate(output_columns):
                    # Extract design point number from column name (e.g., "out_0.txt" -> 0)
                    if col_name.startswith("out_") and col_name.endswith(".txt"):
                        try:
                            dp_num = int(col_name[4:-4])  # Extract number between "out_" and ".txt"
                            column_to_dp[dp_num] = i
                        except ValueError:
                            continue
                
                for line in lines[1:]:
                    if line.strip():
                        parts = line.strip().split(',')
                        param_name = parts[0]
                        values = {}
                        for i, val in enumerate(parts[1:]):
                            if i < len(output_columns):
                                try:
                                    # Map column index to design point number
                                    dp_num = None
                                    for dp, col_idx in column_to_dp.items():
                                        if col_idx == i:
                                            dp_num = dp
                                            break
                                    if dp_num is not None:
                                        values[dp_num] = float(val) if val.strip() else 0.0
                                except ValueError:
                                    continue
                        output_results[param_name] = values
        
        # Display results
        print(f"📊 Analysis Results from: {os.path.basename(summary_file)}")
        print(f"📁 Project folder: {project_folder}")
        print()
        
        # Successful design points
        if successful_points:
            print("✅ SUCCESSFUL DESIGN POINTS:")
            print("-" * 80)
            
            for point in successful_points:
                # Check if this point is saved
                saved_indicator = "💾 SAVED" if point['index'] in saved_point_indices else ""
                
                print(f"Design Point {point['index']}: {saved_indicator}")
                
                # Display parameter values
                for i, (param, value) in enumerate(zip(point['params'], point['values'])):
                    print(f"  {param}: {value:.6f}")
                
                # Display output results if available
                if output_results:
                    print("  Outputs:")
                    for param_name, values in output_results.items():
                        if point['index'] in values:
                            print(f"    {param_name}: {values[point['index']]:.6f}")
                        else:
                            print(f"    {param_name}: No data available")
                
                print()
        else:
            print("❌ No successful design points found.")
        
        # Failed design points
        if failed_points:
            print("❌ FAILED DESIGN POINTS:")
            print("-" * 80)
            
            for point in failed_points:
                print("Failed Design Point:")
                
                # Display parameter values
                for i, (param, value) in enumerate(zip(point['params'], point['values'])):
                    print(f"  {param}: {value:.6f}")
                
                print()
        else:
            print("✅ No failed design points found.")
        
        # Summary statistics
        print("📈 SUMMARY STATISTICS:")
        print("-" * 80)
        print(f"Total successful design points: {len(successful_points)}")
        print(f"Total failed design points: {len(failed_points)}")
        print(f"Saved design points: {len(saved_point_indices)}")
        
        if saved_point_indices:
            print(f"Saved point indices: {sorted(saved_point_indices)}")
        
        if output_results:
            print(f"Output parameters: {list(output_results.keys())}")
        
        print("="*80)
        
    except Exception as e:
        print(f"❌ Error reading simulation data: {e}")
        print("Please make sure all simulation files are present and properly formatted.")


def view_simulation_summary_menu(project_folder):
    """
    Sub-menu for viewing simulation summary with different display options.
    
    Args:
        project_folder (str): Path to the project folder
    """
    print("\n" + "="*60)
    print("VIEW SIMULATION SUMMARY")
    print("="*60)
    
    while True:
        print("\nChoose a display option:")
        print("1. View in console")
        print("2. Export to out folder")
        print("3. Return to analysis menu")
        
        choice = input("\nEnter your choice (1, 2, or 3): ").strip()
        
        if choice == "1":
            view_simulation_summary(project_folder)
        elif choice == "2":
            export_summary_menu(project_folder)
        elif choice == "3":
            print("Returning to analysis menu.")
            return
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")


def export_summary_menu(project_folder):
    """
    Sub-menu for exporting simulation summary to different formats.
    
    Args:
        project_folder (str): Path to the project folder
    """
    print("\n" + "="*60)
    print("EXPORT SIMULATION SUMMARY")
    print("="*60)
    
    while True:
        print("\nChoose an export format:")
        print("1. Export as CSV")
        print("2. Export as text file")
        print("3. Return to summary menu")
        
        choice = input("\nEnter your choice (1, 2, or 3): ").strip()
        
        if choice == "1":
            export_summary_to_csv(project_folder)
        elif choice == "2":
            export_summary_to_text(project_folder)
        elif choice == "3":
            print("Returning to summary menu.")
            return
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")


def export_summary_to_csv(project_folder):
    """
    Export simulation summary to CSV format with inputs and outputs.
    
    Args:
        project_folder (str): Path to the project folder
    """
    print("\n" + "="*60)
    print("EXPORTING TO CSV")
    print("="*60)
    
    try:
        # Check if required files exist
        dps_folder = os.path.join(project_folder, "test_files", "dps")
        summary_folder = os.path.join(project_folder, "test_files", "out_final")
        output_folder = os.path.join(project_folder, "test_files", "out_final")
        
        design_points_file = os.path.join(dps_folder, "DesignPoints.csv")
        failed_points_file = os.path.join(dps_folder, "DesignPoints_failed.csv")
        saved_points_file = os.path.join(dps_folder, "saved_design_points.csv")
        
        # Find summary file
        summary_files = []
        if os.path.exists(summary_folder):
            for file in os.listdir(summary_folder):
                if file.startswith("summary") and file.endswith(".csv"):
                    summary_files.append(os.path.join(summary_folder, file))
        
        if not summary_files:
            print("❌ No summary files found in out_final folder.")
            return
        
        summary_file = summary_files[0]
        
        # Read data
        successful_points = []
        if os.path.exists(design_points_file):
            with open(design_points_file, 'r') as f:
                lines = f.readlines()
                header = lines[0].strip().split(',')
                dp_index = 0
                for line in lines[1:]:
                    if line.strip():
                        values = [float(x.strip()) for x in line.strip().split(',')]
                        successful_points.append({
                            'index': dp_index,
                            'values': values,
                            'params': header
                        })
                        dp_index += 1
        
        failed_points = []
        if os.path.exists(failed_points_file):
            with open(failed_points_file, 'r') as f:
                lines = f.readlines()
                header = lines[0].strip().split(',')
                for line in lines[1:]:
                    if line.strip():
                        values = [float(x.strip()) for x in line.strip().split(',')]
                        failed_points.append({
                            'values': values,
                            'params': header
                        })
        
        saved_point_indices = []
        if os.path.exists(saved_points_file):
            with open(saved_points_file, 'r') as f:
                lines = f.readlines()
                for line in lines[1:]:
                    if line.strip():
                        saved_point_indices.append(int(line.strip()))
        
        # Read output results
        output_results = {}
        if os.path.exists(summary_file):
            with open(summary_file, 'r') as f:
                lines = f.readlines()
                header = lines[0].strip().split(',')
                output_columns = header[1:]
                
                # Create mapping from column names to design point indices
                column_to_dp = {}
                for i, col_name in enumerate(output_columns):
                    # Extract design point number from column name (e.g., "out_0.txt" -> 0)
                    if col_name.startswith("out_") and col_name.endswith(".txt"):
                        try:
                            dp_num = int(col_name[4:-4])  # Extract number between "out_" and ".txt"
                            column_to_dp[dp_num] = i
                        except ValueError:
                            continue
                
                for line in lines[1:]:
                    if line.strip():
                        parts = line.strip().split(',')
                        param_name = parts[0]
                        values = {}
                        for i, val in enumerate(parts[1:]):
                            if i < len(output_columns):
                                try:
                                    # Map column index to design point number
                                    dp_num = None
                                    for dp, col_idx in column_to_dp.items():
                                        if col_idx == i:
                                            dp_num = dp
                                            break
                                    if dp_num is not None:
                                        values[dp_num] = float(val) if val.strip() else 0.0
                                except ValueError:
                                    continue
                        output_results[param_name] = values
        
        # Create output directory if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
        
        # Export successful design points with outputs
        if successful_points:
            csv_file = os.path.join(output_folder, "simulation_summary_successful.csv")
            with open(csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                
                # Create header
                header_row = ['Design_Point_Index', 'Status', 'Saved']
                for param in successful_points[0]['params']:
                    header_row.append(f"Input_{param}")
                for output_param in output_results.keys():
                    header_row.append(f"Output_{output_param}")
                writer.writerow(header_row)
                
                # Write data rows
                for point in successful_points:
                    row = [point['index'], 'Successful', 'Yes' if point['index'] in saved_point_indices else 'No']
                    
                    # Add input values
                    for value in point['values']:
                        row.append(f"{value:.6f}")
                    
                    # Add output values
                    for output_param, values in output_results.items():
                        if point['index'] in values:
                            row.append(f"{values[point['index']]:.6f}")
                        else:
                            row.append("N/A")
                    
                    writer.writerow(row)
            
            print(f"✅ Successful design points exported to: {csv_file}")
        
        # Export failed design points
        if failed_points:
            csv_file = os.path.join(output_folder, "simulation_summary_failed.csv")
            with open(csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                
                # Create header
                header_row = ['Design_Point_Index', 'Status']
                for param in failed_points[0]['params']:
                    header_row.append(f"Input_{param}")
                writer.writerow(header_row)
                
                # Write data rows
                for i, point in enumerate(failed_points):
                    row = [f"Failed_{i}", 'Failed']
                    
                    # Add input values
                    for value in point['values']:
                        row.append(f"{value:.6f}")
                    
                    writer.writerow(row)
            
            print(f"✅ Failed design points exported to: {csv_file}")
        
        # Export combined summary
        combined_file = os.path.join(output_folder, "simulation_summary_combined.csv")
        with open(combined_file, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Create header
            header_row = ['Design_Point_Index', 'Status', 'Saved']
            if successful_points:
                for param in successful_points[0]['params']:
                    header_row.append(f"Input_{param}")
                for output_param in output_results.keys():
                    header_row.append(f"Output_{output_param}")
            writer.writerow(header_row)
            
            # Write successful points
            for point in successful_points:
                row = [point['index'], 'Successful', 'Yes' if point['index'] in saved_point_indices else 'No']
                
                # Add input values
                for value in point['values']:
                    row.append(f"{value:.6f}")
                
                # Add output values
                for output_param, values in output_results.items():
                    if point['index'] in values:
                        row.append(f"{values[point['index']]:.6f}")
                    else:
                        row.append("N/A")
                
                writer.writerow(row)
            
            # Write failed points
            for i, point in enumerate(failed_points):
                row = [f"Failed_{i}", 'Failed', 'No']
                
                # Add input values
                for value in point['values']:
                    row.append(f"{value:.6f}")
                
                # Add N/A for outputs
                for output_param in output_results.keys():
                    row.append("N/A")
                
                writer.writerow(row)
        
        print(f"✅ Combined summary exported to: {combined_file}")
        print(f"📁 Export location: {output_folder}")
        
    except Exception as e:
        print(f"❌ Error exporting to CSV: {e}")


def export_summary_to_text(project_folder):
    """
    Export simulation summary to a professional text file.
    
    Args:
        project_folder (str): Path to the project folder
    """
    print("\n" + "="*60)
    print("EXPORTING TO TEXT FILE")
    print("="*60)
    
    try:
        # Check if required files exist
        dps_folder = os.path.join(project_folder, "test_files", "dps")
        summary_folder = os.path.join(project_folder, "test_files", "out_final")
        output_folder = os.path.join(project_folder, "test_files", "out_final")
        
        design_points_file = os.path.join(dps_folder, "DesignPoints.csv")
        failed_points_file = os.path.join(dps_folder, "DesignPoints_failed.csv")
        saved_points_file = os.path.join(dps_folder, "saved_design_points.csv")
        
        # Find summary file
        summary_files = []
        if os.path.exists(summary_folder):
            for file in os.listdir(summary_folder):
                if file.startswith("summary") and file.endswith(".csv"):
                    summary_files.append(os.path.join(summary_folder, file))
        
        if not summary_files:
            print("❌ No summary files found in out_final folder.")
            return
        
        summary_file = summary_files[0]
        
        # Read data (same logic as view_simulation_summary)
        successful_points = []
        if os.path.exists(design_points_file):
            with open(design_points_file, 'r') as f:
                lines = f.readlines()
                header = lines[0].strip().split(',')
                dp_index = 0
                for line in lines[1:]:
                    if line.strip():
                        values = [float(x.strip()) for x in line.strip().split(',')]
                        successful_points.append({
                            'index': dp_index,
                            'values': values,
                            'params': header
                        })
                        dp_index += 1
        
        failed_points = []
        if os.path.exists(failed_points_file):
            with open(failed_points_file, 'r') as f:
                lines = f.readlines()
                header = lines[0].strip().split(',')
                for line in lines[1:]:
                    if line.strip():
                        values = [float(x.strip()) for x in line.strip().split(',')]
                        failed_points.append({
                            'values': values,
                            'params': header
                        })
        
        saved_point_indices = []
        if os.path.exists(saved_points_file):
            with open(saved_points_file, 'r') as f:
                lines = f.readlines()
                for line in lines[1:]:
                    if line.strip():
                        saved_point_indices.append(int(line.strip()))
        
        # Read output results
        output_results = {}
        if os.path.exists(summary_file):
            with open(summary_file, 'r') as f:
                lines = f.readlines()
                header = lines[0].strip().split(',')
                output_columns = header[1:]
                
                # Create mapping from column names to design point indices
                column_to_dp = {}
                for i, col_name in enumerate(output_columns):
                    # Extract design point number from column name (e.g., "out_0.txt" -> 0)
                    if col_name.startswith("out_") and col_name.endswith(".txt"):
                        try:
                            dp_num = int(col_name[4:-4])  # Extract number between "out_" and ".txt"
                            column_to_dp[dp_num] = i
                        except ValueError:
                            continue
                
                for line in lines[1:]:
                    if line.strip():
                        parts = line.strip().split(',')
                        param_name = parts[0]
                        values = {}
                        for i, val in enumerate(parts[1:]):
                            if i < len(output_columns):
                                try:
                                    # Map column index to design point number
                                    dp_num = None
                                    for dp, col_idx in column_to_dp.items():
                                        if col_idx == i:
                                            dp_num = dp
                                            break
                                    if dp_num is not None:
                                        values[dp_num] = float(val) if val.strip() else 0.0
                                except ValueError:
                                    continue
                        output_results[param_name] = values
        
        # Create output directory if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
        
        # Generate timestamp for filename
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        text_file = os.path.join(output_folder, f"simulation_summary_{timestamp}.txt")
        
        # Create professional text report
        with open(text_file, 'w') as f:
            f.write("="*100 + "\n")
            f.write("CFD SIMULATION ANALYSIS REPORT\n")
            f.write("="*100 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Project Folder: {project_folder}\n")
            f.write(f"Source Summary File: {os.path.basename(summary_file)}\n")
            f.write("="*100 + "\n\n")
            
            # Executive Summary
            f.write("EXECUTIVE SUMMARY\n")
            f.write("-"*50 + "\n")
            f.write(f"Total Design Points Analyzed: {len(successful_points) + len(failed_points)}\n")
            f.write(f"Successful Design Points: {len(successful_points)}\n")
            f.write(f"Failed Design Points: {len(failed_points)}\n")
            f.write(f"Success Rate: {len(successful_points)/(len(successful_points) + len(failed_points))*100:.1f}%\n")
            f.write(f"Saved Design Points: {len(saved_point_indices)}\n")
            f.write(f"Output Parameters: {len(output_results)}\n")
            f.write("\n")
            
            # Successful Design Points Section
            if successful_points:
                f.write("SUCCESSFUL DESIGN POINTS\n")
                f.write("="*50 + "\n")
                
                for point in successful_points:
                    saved_indicator = "SAVED" if point['index'] in saved_point_indices else "NOT SAVED"
                    f.write(f"\nDesign Point {point['index']} ({saved_indicator})\n")
                    f.write("-"*30 + "\n")
                    
                    # Input parameters
                    f.write("Input Parameters:\n")
                    for param, value in zip(point['params'], point['values']):
                        f.write(f"  {param}: {value:.6f}\n")
                    
                    # Output results
                    if output_results:
                        f.write("Output Results:\n")
                        for param_name, values in output_results.items():
                            if point['index'] in values:
                                f.write(f"  {param_name}: {values[point['index']]:.6f}\n")
                            else:
                                f.write(f"  {param_name}: No data available\n")
                    f.write("\n")
            else:
                f.write("SUCCESSFUL DESIGN POINTS\n")
                f.write("="*50 + "\n")
                f.write("No successful design points found.\n\n")
            
            # Failed Design Points Section
            if failed_points:
                f.write("FAILED DESIGN POINTS\n")
                f.write("="*50 + "\n")
                
                for i, point in enumerate(failed_points):
                    f.write(f"\nFailed Design Point {i+1}\n")
                    f.write("-"*30 + "\n")
                    
                    for param, value in zip(point['params'], point['values']):
                        f.write(f"  {param}: {value:.6f}\n")
                    f.write("\n")
            else:
                f.write("FAILED DESIGN POINTS\n")
                f.write("="*50 + "\n")
                f.write("No failed design points found.\n\n")
            
            # Statistical Analysis
            f.write("STATISTICAL ANALYSIS\n")
            f.write("="*50 + "\n")
            
            if successful_points and output_results:
                f.write("Output Parameter Statistics:\n")
                for param_name, values in output_results.items():
                    if values:
                        valid_values = [v for v in values if v != 0.0]
                        if valid_values:
                            f.write(f"\n{param_name}:\n")
                            f.write(f"  Minimum: {min(valid_values):.6f}\n")
                            f.write(f"  Maximum: {max(valid_values):.6f}\n")
                            f.write(f"  Average: {sum(valid_values)/len(valid_values):.6f}\n")
                            f.write(f"  Range: {max(valid_values) - min(valid_values):.6f}\n")
            
            # Summary
            f.write("\n" + "="*100 + "\n")
            f.write("REPORT SUMMARY\n")
            f.write("="*100 + "\n")
            f.write(f"This report contains analysis results for {len(successful_points) + len(failed_points)} design points.\n")
            f.write(f"Success rate: {len(successful_points)/(len(successful_points) + len(failed_points))*100:.1f}%\n")
            f.write(f"Saved design points: {len(saved_point_indices)}\n")
            if saved_point_indices:
                f.write(f"Saved point indices: {sorted(saved_point_indices)}\n")
            f.write("="*100 + "\n")
        
        print(f"✅ Professional text report exported to: {text_file}")
        print(f"📁 Export location: {output_folder}")
        
    except Exception as e:
        print(f"❌ Error exporting to text file: {e}")


def data_modeling_menu(project_folder):
    """
    Data modeling sub-menu for running and viewing data modeling analysis.
    
    Args:
        project_folder (str): Path to the project folder
    """
    print("\n" + "="*60)
    print("DATA MODELING MENU")
    print("="*60)
    
    while True:
        print("\nChoose a data modeling option:")
        print("1. Import existing model")
        print("2. Run new data modeling")
        print("3. View existing model results")
        print("4. Make predictions")
        print("5. Return to analysis menu")
        
        choice = input("\nEnter your choice (1, 2, 3, 4, or 5): ").strip()
        
        if choice == "1":
            import_model_menu(project_folder)
        elif choice == "2":
            run_data_modeling_menu(project_folder)
        elif choice == "3":
            view_model_results_menu(project_folder)
        elif choice == "4":
            make_predictions_menu(project_folder)
        elif choice == "5":
            print("Returning to analysis menu.")
            return
        else:
            print("Invalid choice. Please enter 1, 2, 3, 4, or 5.")


def optimization_menu(project_folder):
    """
    Optimization sub-menu for running and viewing optimization analysis.
    
    Args:
        project_folder (str): Path to the project folder
    """
    print("\n" + "="*60)
    print("OPTIMIZATION MENU")
    print("="*60)
    
    try:
        # Import the optimization module
        from opti import run_optimization
        
        # Run the optimization menu
        run_optimization(project_folder)
        
    except ImportError as e:
        print(f"❌ Error importing optimization module: {e}")
        print("Please ensure opti.py is in the same directory.")
    except Exception as e:
        print(f"❌ Error running optimization: {e}")


def run_data_modeling_menu(project_folder):
    """
    Menu for running data modeling with different options.
    
    Args:
        project_folder (str): Path to the project folder
    """
    print("\n" + "="*50)
    print("RUN DATA MODELING")
    print("="*50)
    
    # Check if required data files exist
    required_files = [
        os.path.join(project_folder, "test_files", "dps", "DesignPoints.csv"),
        os.path.join(project_folder, "test_files", "out_final", "summary2.csv")
    ]
    
    missing_files = [f for f in required_files if not os.path.exists(f)]
    if missing_files:
        print("❌ Missing required files:")
        for file in missing_files:
            print(f"   - {file}")
        print("\nPlease ensure all required files exist before running data modeling.")
        return
    
    print("✅ All required files found")
    
    try:
        print("\n🔧 Starting data modeling...")
        from model import main as run_model
        import sys
        
        # Temporarily redirect input to provide project path
        original_input = input
        def mock_input(prompt):
            if "Enter project path" in prompt:
                return project_folder
            else:
                return original_input(prompt)
        
        # Replace input function temporarily
        import builtins
        builtins.input = mock_input
        
        try:
            run_model()
        finally:
            # Restore original input function
            builtins.input = original_input
            
    except ImportError as e:
        print(f"❌ Error importing model module: {e}")
        print("Please ensure model.py is in the same directory.")
    except Exception as e:
        print(f"❌ Error running data modeling: {e}")


def view_model_results_menu(project_folder):
    """
    Menu for viewing existing model results.
    
    Args:
        project_folder (str): Path to the project folder
    """
    print("\n" + "="*50)
    print("VIEW MODEL RESULTS")
    print("="*50)
    
    # Check if model results exist
    model_folder = os.path.join(project_folder, "test_files", "out_final", "model")
    
    if not os.path.exists(model_folder):
        print(f"❌ No model results found at: {model_folder}")
        print("Please run the data modeling first.")
        return
    
    print("✅ Model results found")
    
    while True:
        print("\nChoose a viewing option:")
        print("1. View model summary")
        print("2. View prediction results")
        print("3. View model files")
        print("4. View model analysis plot")
        print("5. Return to data modeling menu")
        
        choice = input("\nEnter your choice (1, 2, 3, 4, or 5): ").strip()
        
        if choice == "1":
            view_model_summary(model_folder)
        elif choice == "2":
            view_prediction_results(model_folder)
        elif choice == "3":
            view_model_files(model_folder)
        elif choice == "4":
            view_model_plot(model_folder)
        elif choice == "5":
            print("Returning to data modeling menu.")
            return
        else:
            print("Invalid choice. Please enter 1, 2, 3, 4, or 5.")


def view_model_summary(model_folder):
    """
    Display model summary information.
    
    Args:
        model_folder (str): Path to the model results folder
    """
    print("\n📊 Model Summary:")
    print("="*50)
    
    summary_file = os.path.join(model_folder, "model_summary.json")
    if os.path.exists(summary_file):
        try:
            import json
            with open(summary_file, 'r') as f:
                summary = json.load(f)
            
            model_info = summary.get('model_info', {})
            performance = summary.get('performance', {})
            
            print(f"Best Algorithm: {model_info.get('best_algorithm', 'Unknown')}")
            print(f"R² Score: {performance.get('r2', 'Unknown'):.4f}")
            print(f"RMSE: {performance.get('rmse', 'Unknown'):.6f}")
            print(f"MAE: {performance.get('mae', 'Unknown'):.6f}")
            print(f"Number of samples: {model_info.get('n_samples', 'Unknown')}")
            print(f"Number of inputs: {model_info.get('n_inputs', 'Unknown')}")
            print(f"Number of outputs: {model_info.get('n_outputs', 'Unknown')}")
            print(f"PCA components: {model_info.get('n_components', 'Unknown')}")
            print(f"Explained variance: {performance.get('explained_variance', 'Unknown'):.4f}")
            
        except Exception as e:
            print(f"❌ Error reading model summary: {e}")
    else:
        print("❌ Model summary file not found")


def view_prediction_results(model_folder):
    """
    Display prediction results.
    
    Args:
        model_folder (str): Path to the model results folder
    """
    print("\n📈 Prediction Results:")
    print("="*50)
    
    predictions_file = os.path.join(model_folder, "predictions.csv")
    if os.path.exists(predictions_file):
        try:
            import pandas as pd
            df = pd.read_csv(predictions_file)
            print(f"Found {len(df)} predictions")
            print("\nFirst few predictions:")
            print(df.head())
            
        except Exception as e:
            print(f"❌ Error reading predictions: {e}")
    else:
        print("❌ Predictions file not found")


def view_model_files(model_folder):
    """
    Display available model files.
    
    Args:
        model_folder (str): Path to the model results folder
    """
    print("\n📁 Available model files:")
    print("="*50)
    
    files = [
        ("trained_model.pkl", "Trained model"),
        ("predictions.csv", "Prediction results"),
        ("model_summary.json", "Model summary"),
        ("algorithm_comparison.csv", "Algorithm comparison"),
        ("feature_importance.csv", "Feature importance"),
        ("pca_info.csv", "PCA information"),
        ("model_analysis_plot.png", "Model analysis plot")
    ]
    
    for filename, description in files:
        filepath = os.path.join(model_folder, filename)
        if os.path.exists(filepath):
            print(f"✅ {filename} - {description}")
        else:
            print(f"❌ {filename} - Not found")
    
    print(f"\n📁 Files location: {model_folder}")


def make_predictions_menu(project_folder):
    """
    Menu for making predictions with trained models.
    
    Args:
        project_folder (str): Path to the project folder
    """
    print("\n" + "="*50)
    print("MAKE PREDICTIONS")
    print("="*50)
    
    model_folder = os.path.join(project_folder, "test_files", "out_final", "model")
    model_file = os.path.join(model_folder, "trained_model.pkl")
    
    if not os.path.exists(model_file):
        print(f"❌ No trained model found at: {model_file}")
        print("Please run the data modeling first.")
        return
    
    print("✅ Trained model found")
    
    while True:
        print("\nChoose a prediction option:")
        print("1. Interactive prediction (enter values manually)")
        print("2. Predict from CSV file")
        print("3. Return to data modeling menu")
        
        choice = input("\nEnter your choice (1, 2, or 3): ").strip()
        
        if choice == "1":
            run_interactive_prediction(model_folder)
        elif choice == "2":
            run_file_prediction(model_folder)
        elif choice == "3":
            print("Returning to data modeling menu.")
            return
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")


def run_interactive_prediction(model_folder):
    """
    Run interactive prediction with manual input.
    
    Args:
        model_folder (str): Path to the model results folder
    """
    try:
        from model import predict_new_design
        print("\n🔮 Interactive Prediction:")
        print("Enter design point parameters (press Enter for each parameter):")
        
        # Load model and get parameter names
        import pickle
        with open(os.path.join(model_folder, "trained_model.pkl"), 'rb') as f:
            model_data = pickle.load(f)
        
        # Get parameter names from the model summary JSON file
        try:
            import json
            summary_file = os.path.join(model_folder, "model_summary.json")
            if os.path.exists(summary_file):
                with open(summary_file, 'r') as f:
                    summary_data = json.load(f)
                param_names = summary_data.get('parameters', {}).get('input_names', [])
                if not param_names:
                    raise ValueError("No input names found in summary")
            else:
                raise FileNotFoundError("Model summary not found")
        except Exception as e:
            print(f"Warning: Could not load parameter names from summary: {e}")
            # Fallback: try to get from model data or use generic names
            try:
                n_params = model_data['model']['X_scaler'].n_features_in_
                param_names = [f"Parameter_{i+1}" for i in range(n_params)]
            except:
                param_names = ["Parameter_1", "Parameter_2", "Parameter_3"]  # Final fallback
        
        print(f"\nEnter values for {len(param_names)} parameters:")
        print("="*50)
        values = []
        for i, param in enumerate(param_names):
            while True:
                try:
                    value = float(input(f"{i+1}. {param}: "))
                    values.append(value)
                    break
                except ValueError:
                    print("Please enter a valid number.")
        
        # Get output names for better display
        try:
            if 'summary_data' in locals():
                output_names = summary_data.get('parameters', {}).get('output_names', [])
            else:
                # Load summary data if not already loaded
                import json
                summary_file = os.path.join(model_folder, "model_summary.json")
                with open(summary_file, 'r') as f:
                    summary_data = json.load(f)
                output_names = summary_data.get('parameters', {}).get('output_names', [])
            
            if not output_names:
                output_names = [f"Output_{i+1}" for i in range(len(prediction[0]))]
        except:
            output_names = [f"Output_{i+1}" for i in range(len(prediction[0]))]
        
        # Make prediction - need to create proper structure for predict_new_design
        # model_data contains just the model components, need to wrap it properly
        model_results = {
            'model': model_data,
            'data_info': {
                'input_names': param_names,
                'output_names': output_names
            }
        }
        
        # Convert values to numpy array in the correct format
        import numpy as np
        new_inputs = np.array(values).reshape(1, -1)
        
        prediction = predict_new_design(model_results, new_inputs)
        
        print(f"\n🎯 Prediction Results:")
        print("="*50)
        for i, pred in enumerate(prediction[0]):
            output_name = output_names[i] if i < len(output_names) else f"Output_{i+1}"
            print(f"{output_name}: {pred:.6f}")
            
    except Exception as e:
        print(f"❌ Error making prediction: {e}")


def run_file_prediction(model_folder):
    """
    Run prediction from CSV file.
    
    Args:
        model_folder (str): Path to the model results folder
    """
    try:
        from model import predict_from_file
        
        print("\n📁 File-based Prediction:")
        input_file = input("Enter path to CSV file with design points: ").strip().strip('"\'')
        
        if not os.path.exists(input_file):
            print(f"❌ File not found: {input_file}")
            return
        
        # Load model and create proper structure
        import pickle
        import json
        
        # Load model components
        with open(os.path.join(model_folder, "trained_model.pkl"), 'rb') as f:
            model_data = pickle.load(f)
        
        # Load parameter names from summary
        summary_file = os.path.join(model_folder, "model_summary.json")
        if os.path.exists(summary_file):
            with open(summary_file, 'r') as f:
                summary_data = json.load(f)
            param_names = summary_data.get('parameters', {}).get('input_names', [])
            output_names = summary_data.get('parameters', {}).get('output_names', [])
        else:
            print("❌ Model summary not found. Cannot get parameter names.")
            return
        
        # Create proper model_results structure
        model_results = {
            'model': model_data,
            'data_info': {
                'input_names': param_names,
                'output_names': output_names
            }
        }
        
        # Make predictions using the same logic as interactive prediction
        result_df = predict_from_file(model_results, input_file)
        
        if result_df is not None:
            print(f"✅ Predictions completed successfully!")
            print(f"📁 Output file: {input_file.replace('.csv', '_predictions.csv')}")
        else:
            print("❌ Prediction failed.")
        
    except Exception as e:
        print(f"❌ Error making file predictions: {e}")


def view_model_plot(model_folder):
    """
    Display the model analysis plot.
    
    Args:
        model_folder (str): Path to the model results folder
    """
    print("\n📊 Model Analysis Plot:")
    print("="*50)
    
    plot_file = os.path.join(model_folder, "model_analysis_plot.png")
    
    if not os.path.exists(plot_file):
        print("❌ Model analysis plot not found")
        print("The plot may not have been generated during model training.")
        print("Try running the data modeling again to generate the plot.")
        return
    
    print("✅ Model analysis plot found")
    
    while True:
        print("\nChoose a viewing option:")
        print("1. Display plot in Python (interactive)")
        print("2. Open plot with system default viewer")
        print("3. Show plot file location")
        print("4. Return to model results menu")
        
        choice = input("\nEnter your choice (1, 2, 3, or 4): ").strip()
        
        if choice == "1":
            display_plot_in_python(plot_file)
        elif choice == "2":
            open_plot_with_system(plot_file)
        elif choice == "3":
            show_plot_location(plot_file)
        elif choice == "4":
            print("Returning to model results menu.")
            return
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")


def display_plot_in_python(plot_file):
    """
    Display the plot using Python matplotlib.
    
    Args:
        plot_file (str): Path to the plot file
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.image as mpimg
        
        print("Loading and displaying plot...")
        
        # Load and display the image
        img = mpimg.imread(plot_file)
        plt.figure(figsize=(12, 8))
        plt.imshow(img)
        plt.axis('off')
        plt.title('Model Analysis Plot', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        print("✅ Plot displayed! Close the window to continue.")
        plt.show()
        
    except ImportError:
        print("❌ matplotlib not available. Cannot display plot.")
        print("Try option 2 to open with system default viewer.")
    except Exception as e:
        print(f"❌ Error displaying plot: {e}")


def open_plot_with_system(plot_file):
    """
    Open the plot with the system default image viewer.
    
    Args:
        plot_file (str): Path to the plot file
    """
    try:
        import subprocess
        import platform
        
        print("Opening plot with system default viewer...")
        
        system = platform.system()
        if system == "Windows":
            os.startfile(plot_file)
        elif system == "Darwin":  # macOS
            subprocess.run(["open", plot_file])
        else:  # Linux and others
            subprocess.run(["xdg-open", plot_file])
        
        print("✅ Plot opened with system viewer!")
        
    except Exception as e:
        print(f"❌ Error opening plot: {e}")
        print("You can manually open the file at the location shown in option 3.")


def show_plot_location(plot_file):
    """
    Show the location of the plot file.
    
    Args:
        plot_file (str): Path to the plot file
    """
    print(f"\n📁 Plot file location:")
    print(f"   {plot_file}")
    
    # Check file size
    try:
        file_size = os.path.getsize(plot_file)
        file_size_mb = file_size / (1024 * 1024)
        print(f"📏 File size: {file_size_mb:.2f} MB")
    except:
        print("📏 File size: Unknown")
    
    print(f"\n💡 You can:")
    print(f"   1. Copy this path to open in any image viewer")
    print(f"   2. Navigate to this folder in Windows Explorer")
    print(f"   3. Use option 2 to open with system default viewer")


def import_model_menu(project_folder):
    """
    Menu for importing an existing trained model.
    
    Args:
        project_folder (str): Path to the project folder
    """
    print("\n" + "="*50)
    print("IMPORT EXISTING MODEL")
    print("="*50)
    
    while True:
        print("\nChoose an import option:")
        print("1. Import from another project folder")
        print("2. Import from specific model file")
        print("3. Return to data modeling menu")
        
        choice = input("\nEnter your choice (1, 2, or 3): ").strip()
        
        if choice == "1":
            import_from_project_folder(project_folder)
        elif choice == "2":
            import_from_model_file(project_folder)
        elif choice == "3":
            print("Returning to data modeling menu.")
            return
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")


def import_from_project_folder(project_folder):
    """
    Import model from another project folder.
    
    Args:
        project_folder (str): Path to the current project folder
    """
    print("\n📁 Import from Project Folder:")
    print("="*40)
    
    source_folder = input("Enter path to source project folder: ").strip().strip('"\'')
    
    if not os.path.exists(source_folder):
        print(f"❌ Source folder not found: {source_folder}")
        return
    
    # Look for model in the source folder
    source_model_folder = os.path.join(source_folder, "test_files", "out_final", "model")
    source_model_file = os.path.join(source_model_folder, "trained_model.pkl")
    
    if not os.path.exists(source_model_file):
        print(f"❌ No trained model found in source folder: {source_model_file}")
        print("Please ensure the source project has a trained model.")
        return
    
    # Create target model folder
    target_model_folder = os.path.join(project_folder, "test_files", "out_final", "model")
    os.makedirs(target_model_folder, exist_ok=True)
    
    try:
        # Copy all model files from source to target
        import shutil
        
        model_files = [
            "trained_model.pkl",
            "predictions.csv", 
            "model_summary.json",
            "algorithm_comparison.csv",
            "feature_importance.csv",
            "pca_info.csv"
        ]
        
        copied_files = []
        for filename in model_files:
            source_file = os.path.join(source_model_folder, filename)
            target_file = os.path.join(target_model_folder, filename)
            
            if os.path.exists(source_file):
                shutil.copy2(source_file, target_file)
                copied_files.append(filename)
                print(f"✅ Copied: {filename}")
            else:
                print(f"⚠️ Not found: {filename}")
        
        if copied_files:
            print(f"\n✅ Successfully imported {len(copied_files)} model files!")
            print(f"📁 Target location: {target_model_folder}")
        else:
            print("❌ No model files were copied.")
            
    except Exception as e:
        print(f"❌ Error importing model: {e}")


def import_from_model_file(project_folder):
    """
    Import model from a specific model file.
    
    Args:
        project_folder (str): Path to the current project folder
    """
    print("\n📄 Import from Model File:")
    print("="*40)
    
    model_file = input("Enter path to trained model file (.pkl): ").strip().strip('"\'')
    
    if not os.path.exists(model_file):
        print(f"❌ Model file not found: {model_file}")
        return
    
    if not model_file.endswith('.pkl'):
        print("❌ Please provide a .pkl file (trained model)")
        return
    
    # Create target model folder
    target_model_folder = os.path.join(project_folder, "test_files", "out_final", "model")
    os.makedirs(target_model_folder, exist_ok=True)
    
    try:
        # Test if the model file is valid
        import pickle
        with open(model_file, 'rb') as f:
            model_data = pickle.load(f)
        
        # Copy the model file
        target_model_file = os.path.join(target_model_folder, "trained_model.pkl")
        import shutil
        shutil.copy2(model_file, target_model_file)
        
        print(f"✅ Successfully imported model!")
        print(f"📁 Target location: {target_model_file}")
        
        # Check if other related files exist in the same directory
        source_dir = os.path.dirname(model_file)
        related_files = [
            "predictions.csv",
            "model_summary.json", 
            "algorithm_comparison.csv",
            "feature_importance.csv",
            "pca_info.csv"
        ]
        
        print("\n📋 Checking for related files...")
        for filename in related_files:
            source_file = os.path.join(source_dir, filename)
            target_file = os.path.join(target_model_folder, filename)
            
            if os.path.exists(source_file):
                shutil.copy2(source_file, target_file)
                print(f"✅ Copied: {filename}")
            else:
                print(f"⚠️ Not found: {filename}")
        
    except Exception as e:
        print(f"❌ Error importing model: {e}")
        print("The model file may be corrupted or incompatible.")

















