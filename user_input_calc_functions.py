import os
from skopt.sampler import Lhs
from skopt.space import Space
from ansys.fluent.core.filereader.case_file import CaseFile



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
        "geometry_file": {"prompt": "Enter the geometry file path:", "ext": None},
        "mesh_file": {"prompt": "Enter the mesh file path (.msh):", "ext": [".msh", ".msh.h5"]},
        "case_file": {"prompt": "Enter the case file path (.cas or .cas.h5):", "ext": [".cas", ".cas.h5"]},
        "mesh_journal": {"prompt": "Enter the mesh journal file path (.jou):", "ext": [".jou", ""]},
        "case_journal": {"prompt": "Enter the case journal file path (.jou):", "ext": [".jou", ""]}
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


def get_design_points_to_save(num_design_points):
    """
    Asks the user which design points should have case and data files saved.
    
    Args:
        num_design_points (int): Total number of design points that will be generated
    
    Returns:
        list: List of design point indices (1-based) to save, or None if none selected.
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
            return None
        elif choice in ['y', 'yes']:
            break
        else:
            print("❌ Please enter 'y' for yes or 'n' for no.")
    
    print(f"\nEnter the design point numbers you want to save (1-based indexing, 1-{num_design_points}).")
    print("Examples:")
    print("• Single point: 1")
    print("• Multiple points: 1,3,5")
    print("• Range: 1-5")
    print("• Mixed: 1,3-5,8")
    
    while True:
        input_str = input("\nEnter design points to save: ").strip()
        
        if not input_str:
            print("❌ Please enter at least one design point number.")
            continue
            
        try:
            design_points = parse_design_points_input(input_str, num_design_points)
            if design_points:
                print(f"✅ Will save case/data files for design points: {design_points}")
                return design_points
            else:
                print("❌ No valid design points found. Please try again.")
        except ValueError as e:
            print(f"❌ Invalid input: {e}")
            print("Please use format like: 1,3,5 or 1-5 or 1,3-5,8")


def parse_design_points_input(input_str, max_design_points):
    """
    Parse user input for design points to save.
    Supports formats like: 1,3,5 or 1-5 or 1,3-5,8
    
    Args:
        input_str (str): User input string
        max_design_points (int): Maximum number of design points available
        
    Returns:
        list: Sorted list of unique design point indices
    """
    design_points = set()
    
    # Split by comma and process each part
    parts = input_str.split(',')
    
    for part in parts:
        part = part.strip()
        
        if '-' in part:
            # Handle range (e.g., "1-5")
            try:
                start, end = map(int, part.split('-'))
                if start <= end:
                    if start < 1 or end > max_design_points:
                        raise ValueError(f"Range {part} exceeds valid range (1-{max_design_points})")
                    design_points.update(range(start, end + 1))
                else:
                    raise ValueError(f"Invalid range: {part}")
            except ValueError:
                raise ValueError(f"Invalid range format: {part}")
        else:
            # Handle single number
            try:
                num = int(part)
                if num > 0 and num <= max_design_points:
                    design_points.add(num)
                elif num <= 0:
                    raise ValueError(f"Design point must be positive: {num}")
                else:
                    raise ValueError(f"Design point {num} exceeds maximum ({max_design_points})")
            except ValueError:
                raise ValueError(f"Invalid number: {part}")
    
    # Final validation
    if design_points:
        invalid_points = [p for p in design_points if p > max_design_points]
        if invalid_points:
            raise ValueError(f"Design points {invalid_points} exceed maximum ({max_design_points})")
    
    return sorted(list(design_points)) if design_points else None



































