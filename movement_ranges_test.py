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


parameters = ["lower_wing", "upper_wing"]

dict_test = define_movement_ranges_with_directions(parameters)




import os
import numpy as np
from skopt.sampler import Lhs  # or the Lhs class you are using
from skopt.space import Space
# from your LHS library: from some_lhs_module import Lhs, Space

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


get_sample_points_from_ranges(dict_test, r"C:\Users\mitch\Ravens_Racing_CFD\0temp_test", 20)



import os
import json

def generate_spaceclaim_script(folder_path, movement_info, geom_path, design_points_path=None):
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
    body_parts = ['lower_wing', 'upper_wing']
    
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


generate_spaceclaim_script(r"C:\Users\mitch\Ravens_Racing_CFD\0temp_test", dict_test, r"C:\Users\mitch\Ravens_Racing_CFD\z_Project_Test\First_Test.scdocx")