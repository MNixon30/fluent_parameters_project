# IronPython SpaceClaim Script - Robust Version
# Python Script, API Version = V252

import csv
import os
import sys
from collections import OrderedDict
import traceback

true = True
false = False

def open_file(file_path):
    """Open a SpaceClaim document file."""
    try:
        DocumentOpen.Execute(file_path)
        return True
    except Exception as e:
        print("ERROR: Failed to open file {}: {}".format(file_path, e))
        return False

def read_design_points(file_path):
    """Read design points from CSV file with error handling."""
    points = []
    try:
        with open(file_path, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)  # Store header for later use
            for row_num, row in enumerate(reader, start=2):  # Start at 2 because we skipped header
                try:
                    points.append([float(x) for x in row])
                except ValueError as e:
                    print("WARNING: Skipping invalid row {} in {}: {}".format(row_num, file_path, e))
                    continue
        return points, header
    except Exception as e:
        print("ERROR: Failed to read design points from {}: {}".format(file_path, e))
        return [], None

def write_design_points(file_path, points, header):
    """Write design points to CSV file, overwriting the original."""
    try:
        # IronPython doesn't support newline parameter, use basic open
        with open(file_path, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for point in points:
                writer.writerow(point)
        print("Updated design points file: {}".format(file_path))
        return True
    except Exception as e:
        print("ERROR: Failed to write design points to {}: {}".format(file_path, e))
        return False

def write_failed_design_points(design_points_file, failed_indices, all_design_points, header):
    """Write failed design points to a separate CSV file."""
    try:
        # Create filename for failed design points
        base_path = os.path.dirname(design_points_file)
        base_name = os.path.basename(design_points_file)
        name_without_ext = os.path.splitext(base_name)[0]
        failed_file_path = os.path.join(base_path, "{}_failed.csv".format(name_without_ext))
        
        # Get failed design points
        failed_points = []
        for idx in failed_indices:
            if idx < len(all_design_points):
                failed_points.append(all_design_points[idx])
        
        # Write failed design points to CSV
        with open(failed_file_path, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for point in failed_points:
                writer.writerow(point)
        
        print("Failed design points saved to: {}".format(failed_file_path))
        return True
    except Exception as e:
        print("ERROR: Failed to write failed design points to {}: {}".format(failed_file_path, e))
        return False

def apply_design_point_values(design_point, enabled_moves, movement_info, design_point_idx):
    """
    Apply design point values directly (no successive differences).
    
    Args:
        design_point (list): The actual design point values
        enabled_moves (list): List of enabled movements
        movement_info (dict): Movement configuration
        design_point_idx (int): Index of the design point
    
    Returns:
        bool: True if successful, False if failed
    """
    print("Processing design point {}...".format(design_point_idx))
    
    try:
        for col_idx, (move_type, name, sub_idx) in enumerate(enabled_moves):
            if col_idx >= len(design_point):
                print("ERROR: Not enough values in design point for movement {} of {}".format(move_type, name))
                return False
                
            value = design_point[col_idx]
            print("  Applying {} to {}: {}".format(move_type, name, value))
            
            # Create selection
            selection = create_selection(name)
            if selection is None:
                print("ERROR: Failed to create selection for {}".format(name))
                return False
            
            # Apply movement
            success = False
            if move_type == "translate":
                move_info = movement_info[name]["translate"][sub_idx]
                success = translate_selection(selection, move_info["direction"], value)
            elif move_type == "rotate":
                move_info = movement_info[name]["rotate"][sub_idx]
                success = rotate_selection(selection, move_info["axis"], value)
            
            if not success:
                print("ERROR: Failed to apply {} to {}".format(move_type, name))
                return False
        
        return True
        
    except Exception as e:
        print("ERROR: Unexpected error processing design point {}: {}".format(design_point_idx, e))
        print("Traceback: {}".format(traceback.format_exc()))
        return False

def create_selection(named_selection_name):
    """Create a selection by named selection with error handling."""
    try:
        return Selection.CreateByGroups(SelectionType.Primary, named_selection_name)
    except Exception as e:
        print("ERROR: Failed to create selection for '{}': {}".format(named_selection_name, e))
        return None

def vector_to_dir(vector):
    """Convert vector to SpaceClaim direction with error handling."""
    try:
        x, y, z = vector
        if x != 0 and y == 0 and z == 0:
            return Direction.DirX
        elif x == 0 and y != 0 and z == 0:
            return Direction.DirY
        elif x == 0 and y == 0 and z != 0:
            return Direction.DirZ
        else:
            raise ValueError("Vector {} is not aligned with a principal axis".format(vector))
    except Exception as e:
        print("ERROR: Invalid vector {}: {}".format(vector, e))
        return None

def rotate_selection(selection, axis_vector, angle_deg):
    """Rotate selection with error handling."""
    try:
        anchor = Move.GetAnchorPoint(selection)
        axis_dir = vector_to_dir(axis_vector)
        if axis_dir is None:
            return False
        axis = Line.Create(anchor, axis_dir)
        options = MoveOptions()
        result = Move.Rotate(selection, axis, DEG(angle_deg), options)
        return result is not None
    except Exception as e:
        print("ERROR: Failed to rotate selection: {}".format(e))
        return False

def translate_selection(selection, direction_vector, distance_mm):
    """Translate selection with error handling."""
    try:
        direction = vector_to_dir(direction_vector)
        if direction is None:
            return False
        options = MoveOptions()
        result = Move.Translate(selection, direction, MM(distance_mm), options)
        return result is not None
    except Exception as e:
        print("ERROR: Failed to translate selection: {}".format(e))
        return False

def parse_movement_info(movement_info):
    """
    Parses movement information and returns a list of tuples representing
    enabled movements.
    """
    movements = []
    
    # Define body parts in the desired order
    body_parts = ['upper_wing', 'lower_wing']
    
    # Iterate through each body part in sorted order
    for body_part in body_parts:
        if body_part not in movement_info:
            print("WARNING: Body part '{}' not found in movement_info".format(body_part))
            continue
            
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


def save_geometry(design_point_idx, save_folder):
    """Save the current geometry with error handling."""
    try:
        save_path = os.path.join(save_folder, "Geom_dp{}.scdoc".format(design_point_idx))
        options = ExportOptions.Create()
        DocumentSave.Execute(save_path, options)
        print("  Saved: {}".format(save_path))
        return True
    except Exception as e:
        print("ERROR: Failed to save geometry for design point {}: {}".format(design_point_idx, e))
        return False

def _load_setup_defaults():
    """
    Attempt to load default paths from setup_config.json in the current working directory.
    Returns a dictionary with keys: project_folder, geometry_file, design_points_file, geoms_folder.
    """
    setup_path = os.path.join(os.getcwd(), "setup_config.json")
    if not os.path.exists(setup_path):
        return {}

    try:
        import json

        with open(setup_path, "r") as f:
            setup_params = json.load(f)
    except Exception as exc:
        print(f"[WARNING] Failed to parse setup_config.json: {exc}")
        return {}

    project_folder = setup_params.get("project_folder")
    ref_files = setup_params.get("ref_files", {})

    defaults = {}
    if project_folder:
        defaults["project_folder"] = project_folder
        defaults["design_points_file"] = os.path.join(
            project_folder, "test_files", "dps", "DesignPoints.csv"
        )
        defaults["geoms_folder"] = os.path.join(project_folder, "test_files", "geoms")

    if ref_files.get("geometry_file"):
        defaults["geometry_file"] = ref_files["geometry_file"]

    return defaults


def main(
    base_geom_file=None,
    design_points_file=None,
    save_folder=None,
    movement_info=None,
):
    """Main function with robust error handling and CSV adjustment."""
    defaults = _load_setup_defaults()

    base_geom_file = base_geom_file or defaults.get("geometry_file")
    design_points_file = design_points_file or defaults.get("design_points_file")
    save_folder = save_folder or defaults.get("geoms_folder")

    if not base_geom_file or not design_points_file or not save_folder:
        raise ValueError(
            "base_geom_file, design_points_file, and save_folder must be provided. "
            "Ensure setup_config.json contains the required paths or pass them explicitly."
        )
    
    # Create save folder if it doesn't exist
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)
        print("Created save folder: {}".format(save_folder))

    # Open base geometry
    print("Opening base geometry...")
    if not open_file(base_geom_file):
        print("FATAL ERROR: Cannot open base geometry file")
        return False

    # Read design points
    print("Reading design points...")
    design_points, header = read_design_points(design_points_file)
    if not design_points:
        print("FATAL ERROR: No valid design points found")
        return False
    
    print("Found {} design points".format(len(design_points)))

    # Movement configuration
    if movement_info is None:
        movement_info = {
            "upper_wing": {
                "translate": [
                    {
                        "enabled": True,
                        "min": -40.0,
                        "max": 40.0,
                        "direction": [1, 0, 0],
                    }
                ],
                "rotate": [
                    {
                        "enabled": True,
                        "min": -3.0,
                        "max": 3.0,
                        "axis": [0, 0, 1],
                    }
                ],
            },
            "lower_wing": {
                "translate": [
                    {
                        "enabled": False,
                        "min": 0.0,
                        "max": 0.0,
                        "direction": [0, 0, 0],
                    }
                ],
                "rotate": [
                    {
                        "enabled": True,
                        "min": -3.0,
                        "max": 3.0,
                        "axis": [0, 0, 1],
                    }
                ],
            },
        }

    # Build list of enabled movements
    enabled_moves = parse_movement_info(movement_info)
    print("Found {} enabled movements".format(len(enabled_moves)))
    
    # Track successful and failed design points
    successful_points = []
    failed_indices = []
    successful_count = 0  # Counter for sequential naming
    
    print("\n" + "="*60)
    print("PROCESSING DESIGN POINTS")
    print("="*60)
    
    # Process each design point
    for idx, design_point in enumerate(design_points):
        print("\n--- Design Point {} ---".format(idx))
        
        # Reset to base geometry for each design point
        print("  Resetting to base geometry...")
        if not open_file(base_geom_file):
            print("ERROR: Failed to reset to base geometry for design point {}".format(idx))
            failed_indices.append(idx)
            continue
        
        # Apply the design point values directly
        success = apply_design_point_values(design_point, enabled_moves, movement_info, idx)
        
        if success:
            # Save the geometry with sequential naming
            if save_geometry(successful_count, save_folder):
                successful_points.append(design_points[idx])
                print("  ✅ Design point {} completed successfully (saved as geom_dp{})".format(idx, successful_count))
                successful_count += 1  # Increment counter for next successful point
            else:
                print("  ❌ Design point {} failed to save".format(idx))
                failed_indices.append(idx)
        else:
            print("  ❌ Design point {} failed to apply".format(idx))
            failed_indices.append(idx)
    
    # Report results
    print("\n" + "="*60)
    print("PROCESSING COMPLETE")
    print("="*60)
    print("Total design points: {}".format(len(design_points)))
    print("Successful: {} (saved as geom_dp0 to geom_dp{})".format(len(successful_points), len(successful_points)-1))
    print("Failed: {}".format(len(failed_indices)))
    
    if failed_indices:
        print("Failed design point indices: {}".format(failed_indices))
    
    # Update CSV file if there were failures
    if failed_indices:
        print("\nUpdating design points file to remove {} failed points...".format(len(failed_indices)))
        if write_design_points(design_points_file, successful_points, header):
            print("✅ Design points file updated successfully")
        else:
            print("❌ Failed to update design points file")
        
        # Save failed design points to separate file
        print("\nSaving failed design points to separate file...")
        if write_failed_design_points(design_points_file, failed_indices, design_points, header):
            print("✅ Failed design points file created successfully")
        else:
            print("❌ Failed to create failed design points file")
    else:
        print("\n✅ All design points processed successfully - no CSV update needed")
    
    print("\nRobust processing complete!")
    return True

# Run the main function directly for IronPython/SpaceClaim
try:
    success = main()
    if not success:
        print("Script completed with errors")
except Exception as e:
    print("FATAL ERROR: Script crashed: {}".format(e))
    print("Traceback: {}".format(traceback.format_exc()))
