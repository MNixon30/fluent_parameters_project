import os
import shutil
from skopt.sampler import Lhs
from skopt.space import Space
import numpy as np
import json
from ansys.fluent.core.filereader.case_file import CaseFile
import subprocess
import re
import sys
import csv
#Comment

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




def create_folders(project_root):
    """
    Create a structured folder hierarchy inside the specified project directory.

    Parameters:
        project_root (str): Path to the root directory where folders will be created.

    Folders created:
    - ref_files/
        - ref/
        - scripts/
    - test_files/
        - cas/
        - dps/
        - geoms/
        - msh/
        - out/
        - scripts/
    """

    # Define main folders and their respective subfolders
    folders = {
        "ref_files": ["ref", "scripts"],
        "test_files": ["cas", "dps", "geoms", "msh", "out", "scripts", "cas_scripts", "out_final"]
    }

    # Ensure the project root exists
    os.makedirs(project_root, exist_ok=True)

    # Loop over main folders
    for main_folder, subfolders in folders.items():
        # Full path of the main folder (inside the given project root)
        main_path = os.path.join(project_root, main_folder)
        
        # Create the main folder
        os.makedirs(main_path, exist_ok=True)
        
        # Loop over and create each subfolder
        for subfolder in subfolders:
            os.makedirs(os.path.join(main_path, subfolder), exist_ok=True)

    # Function does not return anything
    return None



def move_ref_file(source_file, project_folder):
    """
    Move a file to the project's ref_files/scripts folder.

    Parameters:
        source_file (str): Full path to the source file.
        project_folder (str): Absolute path to the project root folder.

    Returns:
        str: Absolute path of the moved file.
    """

    # Define the relative target path
    relative_target = r"ref_files\ref"

    # Combine the absolute project folder with the relative path
    target_folder = os.path.join(project_folder, relative_target)

    # Ensure the target folder exists
    os.makedirs(target_folder, exist_ok=True)

    # Build the full destination path
    filename = os.path.basename(source_file)
    destination_file = os.path.join(target_folder, filename)

    # Move the file
    shutil.move(source_file, destination_file)

    print(f"✅ File moved: {source_file} → {destination_file}")
    return destination_file




def move_script_file(source_file, project_folder):
    """
    Move a file to the project's ref_files/scripts folder.

    Parameters:
        source_file (str): Full path to the source file.
        project_folder (str): Absolute path to the project root folder.

    Returns:
        str: Absolute path of the moved file.
    """

    # Define the relative target path
    relative_target = r"ref_files\scripts"

    # Combine the absolute project folder with the relative path
    target_folder = os.path.join(project_folder, relative_target)

    # Ensure the target folder exists
    os.makedirs(target_folder, exist_ok=True)

    # Build the full destination path
    filename = os.path.basename(source_file)
    destination_file = os.path.join(target_folder, filename)

    # Move the file
    shutil.move(source_file, destination_file)

    print(f"✅ File moved: {source_file} → {destination_file}")
    return destination_file



def update_file_paths_relative_to_project(file_paths, project_folder, relative_folders):
    """
    Create a new dictionary with updated file paths in project-relative folders,
    without moving the files.

    Parameters:
        file_paths (dict): Original dictionary of file paths.
        project_folder (str): Absolute path to the project root.
        relative_folders (dict): Dictionary mapping file keys to relative folders inside project_folder.

    Returns:
        dict: Same keys as `file_paths`, values are new absolute paths.
    """
    updated_paths = {}
    
    for key, original_path in file_paths.items():
        if key not in relative_folders:
            raise KeyError(f"No relative folder specified for '{key}'")
        
        filename = os.path.basename(original_path)
        target_folder = os.path.join(project_folder, relative_folders[key])
        new_path = os.path.join(target_folder, filename)
        updated_paths[key] = new_path

    return updated_paths



def get_names_from_casefile(casefile_path):
    """
    Extract surface (zone) names from an offline Fluent case file (.cas.h5)
    without needing a live solver session.

    Parameters:
        casefile_path (str): Full path to the .cas.h5 file.

    Returns:
        list of str: Names of all surfaces/zones in the mesh.
    """
    # Import CaseFile reader from PyFluent
    

    # Initialize the case file reader
    reader = CaseFile(case_file_name=casefile_path)

    # Extract the mesh from the case file
    mesh_reader = reader.get_mesh()

    # Get the list of surface names (zones)
    surface_names = mesh_reader.get_surface_names()

    # Print the zones for user information
    print("\n✅ Zones (surfaces) found in the case file:")
    for name in surface_names:
        print(f"  - {name}")

    return surface_names




def choose_named_parameters(named_selections):
    """
    Ask the user which named selections should be treated as geometrical parameters.

    Parameters:
        named_selections (list of str): List of available named selections.

    Returns:
        list of str: Subset of named selections chosen by the user.
    """
    print("\nAvailable named selections:")
    for i, name in enumerate(named_selections, start=1):
        print(f"  {i}. {name}")
    
    chosen_parameters = []

    print("\nEnter the numbers of the named selections you want to use as parameters, separated by commas (e.g., 1,3,5):")
    while True:
        user_input = input("Your choice: ").strip()
        if not user_input:
            print("❌ Input cannot be empty. Please enter at least one number.")
            continue
        
        try:
            # Split input by commas and convert to indices
            indices = [int(x.strip()) for x in user_input.split(",")]
            if any(i < 1 or i > len(named_selections) for i in indices):
                print(f"❌ Invalid numbers. Enter values between 1 and {len(named_selections)}.")
                continue
            
            # Create the list of chosen named selections
            chosen_parameters = [named_selections[i-1] for i in indices]
            break
        except ValueError:
            print("❌ Invalid input. Enter numbers separated by commas (e.g., 1,2,4).")
    
    print("\n✅ Named selections chosen as parameters:")
    for name in chosen_parameters:
        print(f"  - {name}")
    
    return chosen_parameters




def define_movement_ranges_with_directions(parameters):
    """
    Ask the user for each parameter if it will be translated or rotated,
    and collect min/max for each movement along with direction/axis.
    Allows multiple movements per type along principal axes only (x, y, z).

    Parameters:
        parameters (list of str): Named selections chosen as geometrical parameters.

    Returns:n
        dict: Keys are named selections, values are dicts with movement ranges and directions.
              Example:
              {
                  "Upper_Wing": {
                      "translate": [
                          {"enabled": True, "min": 0.0, "max": 10.0, "direction": [1,0,0]},
                          {"enabled": True, "min": 0.0, "max": 5.0, "direction": [0,1,0]}
                      ],
                      "rotate": [
                          {"enabled": True, "min": 0.0, "max": 15.0, "axis": [0,0,1]}
                      ]
                  },
                  ...
              }
    """
    movement_info = {}

    allowed_vectors = [[1,0,0], [0,1,0], [0,0,1]]

    print("\nDefine movement ranges and directions for each parameter:\n")
    
    for name in parameters:
        print(f"\nParameter: {name}")

        # --- Translation ---
        translations = []
        existing_directions = []

        while True:
            translate_input = input("  Add a translation? (y/n): ").strip().lower()
            if translate_input not in ["y", "n"]:
                print("❌ Invalid input. Enter 'y' or 'n'.")
                continue
            if translate_input == "n":
                break
            
            # Min/Max
            while True:
                try:
                    tmin = float(input("    Translation min value: ").strip())
                    tmax = float(input("    Translation max value: ").strip())
                    if tmax < tmin:
                        print("❌ Invalid range. Ensure max >= min.")
                        continue
                    break
                except ValueError:
                    print("❌ Enter numeric values only.")

            # Direction
            while True:
                try:
                    dir_input = input("    Translation direction vector (x,y,z, allowed: 1,0,0 or 0,1,0 or 0,0,1): ").strip()
                    direction = [int(x) for x in dir_input.split(",")]
                    if direction not in allowed_vectors:
                        print("❌ Invalid direction. Must be one of: [1,0,0], [0,1,0], [0,0,1]")
                        continue
                    if direction in existing_directions:
                        print("❌ This direction has already been entered. Use a different direction.")
                        continue
                    existing_directions.append(direction)
                    break
                except ValueError:
                    print("❌ Invalid input. Enter integers separated by commas.")

            translations.append({"enabled": True, "min": tmin, "max": tmax, "direction": direction})

        if not translations:
            translations = [{"enabled": False, "min": 0.0, "max": 0.0, "direction": [0,0,0]}]

        # --- Rotation ---
        rotations = []
        existing_axes = []

        while True:
            rotate_input = input("  Add a rotation? (y/n): ").strip().lower()
            if rotate_input not in ["y", "n"]:
                print("❌ Invalid input. Enter 'y' or 'n'.")
                continue
            if rotate_input == "n":
                break
            
            # Min/Max
            while True:
                try:
                    rmin = float(input("    Rotation min value (deg): ").strip())
                    rmax = float(input("    Rotation max value (deg): ").strip())
                    if rmax < rmin:
                        print("❌ Invalid range. Ensure max >= min.")
                        continue
                    break
                except ValueError:
                    print("❌ Enter numeric values only.")

            # Axis
            while True:
                try:
                    axis_input = input("    Rotation axis vector (x,y,z, allowed: 1,0,0 or 0,1,0 or 0,0,1): ").strip()
                    axis = [int(x) for x in axis_input.split(",")]
                    if axis not in allowed_vectors:
                        print("❌ Invalid axis. Must be one of: [1,0,0], [0,1,0], [0,0,1]")
                        continue
                    if axis in existing_axes:
                        print("❌ This axis has already been entered. Use a different axis.")
                        continue
                    existing_axes.append(axis)
                    break
                except ValueError:
                    print("❌ Invalid input. Enter integers separated by commas.")

            rotations.append({"enabled": True, "min": rmin, "max": rmax, "axis": axis})

        if not rotations:
            rotations = [{"enabled": False, "min": 0.0, "max": 0.0, "axis": [0,0,0]}]

        # Store info
        movement_info[name] = {
            "translate": translations,
            "rotate": rotations
        }
    
    print("\n✅ Movement ranges and directions defined for all parameters.")
    print(movement_info)
    return movement_info


#Not-Used Function
def extract_lower_upper_values_with_mapping(movement_ranges):
    """
    Organize movement range data into two lists: lower and upper values,
    and print a mapping of list indices to parameters and movement types.

    Parameters:
        movement_ranges (dict): Output from define_movement_ranges_simple()
    
    Returns:
        tuple: (lower_values, upper_values)
               Each is a list of floats in order for enabled movements only.
    """
    lower_values = []
    upper_values = []
    mapping = []

    for name, moves in movement_ranges.items():
        # Translation (only if enabled)
        if moves["translate"]["enabled"]:
            lower_values.append(moves["translate"]["min"])
            upper_values.append(moves["translate"]["max"])
            mapping.append(f"{name} - translate")
        
        # Rotation (only if enabled)
        if moves["rotate"]["enabled"]:
            lower_values.append(moves["rotate"]["min"])
            upper_values.append(moves["rotate"]["max"])
            mapping.append(f"{name} - rotate")
    
    # Print mapping
    print("\nIndex mapping of lists (lower_values and upper_values):")
    for idx, desc in enumerate(mapping):
        print(f"  Index {idx}: {desc}")
    
    return lower_values, upper_values



#Not_Used_Function
def get_sample_points(lower_bounds: list, upper_bounds: list, project_folder: str, n_points: int = None):
    """
    Generate Latin Hypercube Sample points within given bounds and save to CSV.
    
    Parameters:
        lower_bounds (list of float): Lower bounds for each parameter.
        upper_bounds (list of float): Upper bounds for each parameter.
        project_folder (str): Absolute path to the project root.
        n_points (int, optional): Number of design points to generate.
            If None, prompts the user to input a number.
    
    Output:
        Saves 'DesignPoints.csv' in '<project_folder>/test_files/dps'.
    """
    # Validate bounds
    if len(lower_bounds) != len(upper_bounds):
        raise ValueError("Lower and upper bounds must have the same length")

    # Prompt user if n_points not provided
    if n_points is None:
        while True:
            try:
                n_points = int(input("Enter the number of design points to generate: ").strip())
                if n_points <= 0:
                    print("❌ Number of points must be a positive integer.")
                    continue
                break
            except ValueError:
                print("❌ Invalid input. Please enter a positive integer.")

    # Define the parameter space
    space = Space([(float(low), float(high)) for low, high in zip(lower_bounds, upper_bounds)])

    # Generate Latin Hypercube Samples
    lhs_generator = Lhs(lhs_type='classic', criterion='maximin')
    points = lhs_generator.generate(space.dimensions, n_points)

    # Define output folder based on project_folder
    dps_folder = os.path.join(project_folder, "test_files", "dps")
    os.makedirs(dps_folder, exist_ok=True)

    # Save the sample points to CSV
    file_path = os.path.join(dps_folder, "DesignPoints.csv")
    np.savetxt(file_path, points, delimiter=",",
               header=",".join([f"Param{i+1}" for i in range(len(lower_bounds))]),
               comments='')

    print(f"\n✅ {n_points} design points saved to: {file_path}")
    return file_path  # return the path in case you need it



def get_sample_points_from_ranges(movement_ranges, project_folder: str, n_points: int = None):
    """
    Generate Latin Hypercube Sample points within bounds defined in movement_ranges
    and save to CSV with descriptive headers.

    Parameters:
        movement_ranges (dict): Output from define_movement_ranges_with_directions().
        project_folder (str): Absolute path to project root.
        n_points (int, optional): Number of design points to generate.
            If None, prompts the user.
    
    Output:
        Saves 'DesignPoints.csv' in '<project_folder>/test_files/dps'.
    """
    lower_bounds = []
    upper_bounds = []
    headers = []

    axis_map = {(1,0,0): "X", (0,1,0): "Y", (0,0,1): "Z"}

    for param_name, moves in movement_ranges.items():
        # Translations
        for t_move in moves["translate"]:
            if t_move["enabled"]:
                lower_bounds.append(t_move["min"])
                upper_bounds.append(t_move["max"])
                axis_label = axis_map.get(tuple(t_move["direction"]), str(t_move["direction"]))
                headers.append(f"{param_name}_translate_{axis_label}")
        
        # Rotations
        for r_move in moves["rotate"]:
            if r_move["enabled"]:
                lower_bounds.append(r_move["min"])
                upper_bounds.append(r_move["max"])
                axis_label = axis_map.get(tuple(r_move["axis"]), str(r_move["axis"]))
                headers.append(f"{param_name}_rotate_{axis_label}")

    if len(lower_bounds) == 0:
        raise ValueError("No enabled movements found in movement_ranges.")

    # Prompt user if n_points not provided
    if n_points is None:
        while True:
            try:
                n_points = int(input("Enter the number of design points to generate: ").strip())
                if n_points <= 0:
                    print("❌ Number of points must be a positive integer.")
                    continue
                break
            except ValueError:
                print("❌ Invalid input. Please enter a positive integer.")

    # Define the parameter space
    space = Space([(low, high) for low, high in zip(lower_bounds, upper_bounds)])

    # Generate Latin Hypercube Samples
    lhs_generator = Lhs(lhs_type='classic', criterion='maximin')
    points = lhs_generator.generate(space.dimensions, n_points)

    # Output folder
    dps_folder = os.path.join(project_folder, "test_files", "dps")
    os.makedirs(dps_folder, exist_ok=True)

    # Save CSV
    file_path = os.path.join(dps_folder, "DesignPoints.csv")
    np.savetxt(file_path, points, delimiter=",", header=",".join(headers), comments='')

    print(f"\n✅ {n_points} design points saved to: {file_path}")
    return file_path



def generate_spaceclaim_script(folder_path, movement_info, geom_path, geom_params, design_points_path=None):
    """
    Generate a SpaceClaim IronPython script that applies translations and rotations
    based on design points and movement_info (multi-axis compatible).

    Parameters:
        folder_path (str): Absolute path to the project folder.
        movement_info (dict): Dictionary containing translation/rotation info.
        design_points_path (str, optional): Path to the CSV of design points.
            If None, defaults to <folder_path>/test_files/dps/DesignPoints.csv
    """
    # Paths for script and geometries
    scripts_folder = os.path.join(folder_path, "ref_files", "scripts")
    os.makedirs(scripts_folder, exist_ok=True)
    script_path = os.path.join(scripts_folder, "apply_design_points.py")

    geoms_folder = os.path.join(folder_path, "test_files", "geoms")
    os.makedirs(geoms_folder, exist_ok=True)

    # Default design points path if not provided
    if design_points_path is None:
        design_points_path = os.path.join(folder_path, "test_files", "dps", "DesignPoints.csv")

    # Convert movement_info dict to JSON string for embedding in the script
    movement_info_str = json.dumps(movement_info, indent=4)

    # Template for SpaceClaim script
    script_content = f'''# IronPython SpaceClaim Script
# Python Script, API Version = V252

import csv
import os
from collections import OrderedDict
true = True
false = False

def open_file(file_path):
    DocumentOpen.Execute(file_path, FileSettings1)
    return None

def read_design_points(file_path):
    points = []
    with open(file_path, 'r') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            points.append([float(x) for x in row])
    return points

def successive_differences(points):
    if not points:
        return []
    out = [points[0]]
    for i in range(1, len(points)):
        prev = points[i-1]
        cur = points[i]
        if len(prev) != len(cur):
            raise ValueError("All points must have the same number of dimensions")
        diff = [cur[j] - prev[j] for j in range(len(cur))]
        out.append(diff)
    return out

def create_selection(named_selection_name):
    return Selection.CreateByGroups(SelectionType.Primary, named_selection_name)

def vector_to_dir(vector):
    x, y, z = vector
    if x != 0 and y == 0 and z == 0:
        return Direction.DirX
    elif x == 0 and y != 0 and z == 0:
        return Direction.DirY
    elif x == 0 and y == 0 and z != 0:
        return Direction.DirZ
    else:
        raise ValueError("Vector is not aligned with a principal axis")

def rotate_selection(selection, axis_vector, angle_deg):
    anchor = Move.GetAnchorPoint(selection)
    axis_dir = vector_to_dir(axis_vector)
    axis = Line.Create(anchor, axis_dir)
    options = MoveOptions()
    return Move.Rotate(selection, axis, DEG(angle_deg), options)

def translate_selection(selection, direction_vector, distance_mm):
    direction = vector_to_dir(direction_vector)
    options = MoveOptions()
    return Move.Translate(selection, direction, MM(distance_mm), options)

    

def parse_movement_info(movement_info):
    """
    Parses movement information and returns a list of tuples representing
    enabled movements.
    
    Args:
        movement_info (dict): A dictionary with body parts as keys, each containing
                            'translate' and 'rotate' lists with movement definitions.
    
    Returns:
        list: A list of tuples in the format (movement_type, body_part, index)
              for each enabled movement, in order of body parts and movement types.
    """
    movements = []
    
    # Define body parts in the desired order
    # (IronPython doesn't preserve dict insertion order, so we specify it explicitly)
    body_parts = {geom_params}
    
    # Iterate through each body part in sorted order
    for body_part in body_parts:
        movement_types = movement_info[body_part]
        
        # For each body part, process translate first, then rotate
        for movement_type in ['translate', 'rotate']:
            if movement_type in movement_types:
                movements_list = movement_types[movement_type]
                
                # Iterate through each movement entry with its index
                for index, movement in enumerate(movements_list):
                    # Only include if enabled
                    if movement.get('enabled', False):
                        movements.append((movement_type, body_part, index))
    
    return movements








def main():
    base_geom_file = r"{geom_path}"
    design_points_file = r"{design_points_path}"
    save_folder = r"{geoms_folder}"
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    DocumentOpen.Execute(base_geom_file)

    design_points = read_design_points(design_points_file)
    deltas = successive_differences(design_points)

    movement_info = {movement_info_str}

    # Build a list of enabled movements (multi-axis compatible)
    enabled_moves = parse_movement_info(movement_info)

    for idx, dp in enumerate(deltas):
        for col_idx, (move_type, name, sub_idx) in enumerate(enabled_moves):
            value = dp[col_idx]
            selection = create_selection(name)

            if move_type == "translate":
                move_info = movement_info[name]["translate"][sub_idx]
                translate_selection(selection, move_info["direction"], value)
            elif move_type == "rotate":
                move_info = movement_info[name]["rotate"][sub_idx]
                rotate_selection(selection, move_info["axis"], value)

        # Save geometry as SpaceClaim document (.scdoc)
        save_path = os.path.join(save_folder, "Geom_dp{{}}.scdoc".format(idx))
        options = ExportOptions.Create()
        DocumentSave.Execute(save_path, options)
        print("Saved:", save_path)

main()
'''

    # Write the script to file
    with open(script_path, 'w') as f:
        f.write(script_content)

    print(f"✅ SpaceClaim script created at: {script_path}")
    print(f"✅ Geometries will be saved to: {geoms_folder}")
    return script_path


def find_spaceclaim_exe():
    """
    Locate the SpaceClaim executable on a Windows PC.

    Returns:
        str: Full path to SpaceClaim.exe if found, else None.
    """
    exe_name = "SpaceClaim.exe"

    # Common installation directories
    likely_dirs = [
        r"C:\Program Files\ANSYS Inc",
        r"C:\Program Files (x86)\ANSYS Inc",
        r"C:\Program Files",
        r"C:\Program Files (x86)"
    ]

    # Search likely directories first
    for base_dir in likely_dirs:
        for root, dirs, files in os.walk(base_dir):
            if exe_name in files:
                return os.path.join(root, exe_name)

    # Optional: fallback to full C: drive (slower)
    for root, dirs, files in os.walk(r"C:\\"):
        if exe_name in files:
            return os.path.join(root, exe_name)

    # If not found
    return None




def run_spaceclaim_script_headless(script_path, spaceclaim_exe):
    """
    Runs a SpaceClaim script in headless mode (no GUI).

    Parameters
    ----------
    script_path : str
        Full path to the SpaceClaim script (.py or .scscript)
    spaceclaim_exe : str,
        Full path to SpaceClaim executable. 
    """
    import os
    import subprocess

    # Ensure script path is absolute and exists
    script_path = os.path.abspath(script_path)
    if not os.path.exists(script_path):
        raise FileNotFoundError(f"Script not found: {script_path}")

    # Ensure SpaceClaim executable exists
    spaceclaim_exe = os.path.abspath(spaceclaim_exe)
    if not os.path.exists(spaceclaim_exe):
        raise FileNotFoundError(f"SpaceClaim executable not found: {spaceclaim_exe}")

    # Command to launch SpaceClaim headless
    cmd = [
        spaceclaim_exe,
        f"/RunScript={script_path}",
        "/Headless=True",
        "/Splash=False",
        "/Welcome=False",
        "/ExitAfterScript=True"
    ]

    print(f"Running SpaceClaim headless script:\n{script_path}")
    subprocess.run(cmd, check=True)



def clean_journal(journal_path):
    """
    Removes GUI/CX commands from a Fluent journal so it can run headless.
    """
    with open(journal_path, "r") as f:
        content = f.read()

    # Remove lines starting with (cx-...) or (handle-key ...) or (dolly-camera ...)
    content_clean = re.sub(r"^\(cx-[^\n]*\)|^\(dolly-camera[^\n]*\)|^\(handle-key[^\n]*\)\n?", "", content, flags=re.MULTILINE)

    with open(journal_path, "w") as f:
        f.write(content_clean)




def generate_meshing_scripts_auto(project_root, journal_template,
                                  geom_folder=r"test_files\geoms",
                                  script_folder=r"test_files\scripts",
                                  mesh_folder=r"test_files\msh",
                                  ):
    """
    Automatically generates Fluent journal scripts for all geometries.
    Replaces:
      - the hard-coded FileName line in the template with each geometry path
      - the Export Fluent 2D Mesh output path with a mesh_path
      - Input the absolute path of project root and absolute path of journal file
    """
    geom_folder = os.path.join(project_root, geom_folder)
    script_folder = os.path.join(project_root, script_folder)
    mesh_folder = os.path.join(project_root, mesh_folder)
    

    os.makedirs(script_folder, exist_ok=True)
    os.makedirs(mesh_folder, exist_ok=True)

    # Load template once
    with open(journal_template, "r") as f:
        template = f.read()

    # Find geometry files
    geom_files = [f for f in os.listdir(geom_folder) if f.endswith((".scdoc", ".scdocx", ".dsco"))]

    created_scripts = []

    for geom_file in geom_files:
        geom_path = os.path.join(geom_folder, geom_file).replace("\\", "/")
        mesh_path = os.path.join(mesh_folder, geom_file.rsplit(".", 1)[0] + ".msh.h5").replace("\\", "/")

        # 1️⃣ Replace geometry FileName in Load CAD Geometry
        journal_content = re.sub(
            r"(r'FileName': r')[^']+(')",
            fr"\1{geom_path}\2",
            template
        )

        # 2️⃣ Replace Export Fluent 2D Mesh path (handles None or existing path)
        journal_content = re.sub(
            r"(workflow\.TaskObject\['Export Fluent 2D Mesh'\]\.Arguments\.set_state\()([^)]+)\)",
            fr"\1{{r'FileName': r'{mesh_path}'}})",
            journal_content
        )

        # Save per-geometry journal
        journal_name = geom_file.rsplit(".", 1)[0] + "_mesh.jou"
        journal_path = os.path.join(script_folder, journal_name)

        with open(journal_path, "w") as jf:
            jf.write(journal_content)

        created_scripts.append(journal_path)
        print(f"✅ Created meshing script: {journal_name}")

    return created_scripts




def find_fluent_exe():
    """
    Locate the Fluent executable on a Windows PC.

    Returns:
        str: Full path to fluent.exe if found, else None.
    """
    exe_name = "fluent.exe"

    # Common installation directories
    likely_dirs = [
        r"C:\Program Files\ANSYS Inc",
        r"C:\Program Files (x86)\ANSYS Inc",
        r"C:\Program Files",
        r"C:\Program Files (x86)"
    ]

    # Search likely directories first
    for base_dir in likely_dirs:
        for root, dirs, files in os.walk(base_dir):
            if exe_name in files:
                return os.path.join(root, exe_name)

    # Optional: fallback to full C: drive (slower)
    for root, dirs, files in os.walk(r"C:\\"):
        if exe_name in files:
            return os.path.join(root, exe_name)

    # If not found
    return None



def run_meshing_scripts(project_root, fluent_path):
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

    for script in script_paths:
        print(f"🌀 Running meshing script: {os.path.basename(script)}")
        subprocess.run([fluent_exe,
                        "3d",
                        "-meshing",    # Explicit meshing mode
                        "-hidden",
                        "-g",     
                        "-t2",         # Number of threads
                        "-i", script]) # Input journal
        print(f"✅ Finished: {os.path.basename(script)}")




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

    print(f"[DONE] Output saved to: {{output_file}}")
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






















