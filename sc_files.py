import os
import json

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