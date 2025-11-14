import os
import json

def generate_spaceclaim_script(folder_path, movement_info, geom_path, geom_params, design_points_path=None, save_design_points=None):
    """
    Generate a robust SpaceClaim IronPython script that applies translations and rotations
    based on design points and movement_info with comprehensive error handling.

    Parameters:
        folder_path (str): Absolute path to the project folder.
        movement_info (dict): Dictionary containing translation/rotation info.
        geom_path (str): Path to the base geometry file.
        geom_params (list): List of geometry parameter names.
        design_points_path (str, optional): Path to the CSV of design points.
            If None, defaults to <folder_path>/test_files/dps/DesignPoints.csv
        save_design_points (list, optional): List of design point indices to save.
            If None, will read from saved_design_points.csv file.
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
    
    # Handle saved design points
    if save_design_points is None:
        # Try to read from saved_design_points.csv file
        saved_dp_file = os.path.join(folder_path, "test_files", "dps", "saved_design_points.csv")
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
                print("Loaded saved design points from CSV: {}".format(save_design_points))
            except Exception as e:
                print("Error reading saved design points file: {}".format(e))
                save_design_points = []
        else:
            save_design_points = []
    
    # Convert save_design_points to JSON string for embedding in the script
    save_design_points_str = json.dumps(save_design_points, indent=4)

    # Template for SpaceClaim script
    script_content = '''# IronPython SpaceClaim Script - Robust Version
# Python Script, API Version = V252

import csv
import os
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
    body_parts = ''' + str(geom_params) + '''
    
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

def apply_design_point_values(design_point, enabled_moves, movement_info, design_point_idx):
    """
    Apply design point values directly (no successive differences).
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








def should_save_design_point(original_idx, save_design_points, failed_indices):
    """Check if a design point should be saved based on original index and failures."""
    if not save_design_points:
        return False
    
    # Count how many failed points are before this original index
    failed_before = sum(1 for failed_idx in failed_indices if failed_idx < original_idx)
    
    # Skip if this point itself failed
    if original_idx in failed_indices:
        return False
    
    # Calculate the adjusted index
    adjusted_idx = original_idx - failed_before
    
    # Check if this adjusted index is in the save list
    return adjusted_idx in save_design_points

def get_adjusted_save_index(original_idx, save_design_points, failed_indices):
    """Get the adjusted save index for a design point."""
    if not save_design_points:
        return None
    
    # Count how many failed points are before this original index
    failed_before = sum(1 for failed_idx in failed_indices if failed_idx < original_idx)
    
    # Skip if this point itself failed
    if original_idx in failed_indices:
        return None
    
    # Calculate the adjusted index
    adjusted_idx = original_idx - failed_before
    
    # Check if this adjusted index is in the save list
    if adjusted_idx in save_design_points:
        return adjusted_idx
    
    return None

def adjust_saved_design_points_file(design_points_file, failed_indices):
    """Adjust the saved design points file based on failed design points."""
    try:
        # Get the directory of the design points file
        dps_folder = os.path.dirname(design_points_file)
        saved_dp_file = os.path.join(dps_folder, "saved_design_points.csv")
        
        # Check if saved design points file exists
        if not os.path.exists(saved_dp_file):
            print("No saved design points file found - nothing to adjust")
            return True
        
        # Read the original saved design points
        with open(saved_dp_file, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)  # Skip header
            original_saved_points = []
            for row in reader:
                if row:  # Skip empty rows
                    original_saved_points.append(int(row[0]))
        
        if not original_saved_points:
            print("No saved design points found - nothing to adjust")
            return True
        
        # Calculate adjusted indices
        adjusted_saved_points = []
        for original_idx in original_saved_points:
            # Count how many failed points are before this saved point
            failed_before = sum(1 for failed_idx in failed_indices if failed_idx < original_idx)
            
            # Skip if this saved point itself failed
            if original_idx in failed_indices:
                print("Saved design point {} failed - removing from save list".format(original_idx))
                continue
            
            # Calculate new index
            new_idx = original_idx - failed_before
            adjusted_saved_points.append(new_idx)
        
        # Write the adjusted saved design points
        with open(saved_dp_file, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(['design_point_index'])  # Header
            for dp in adjusted_saved_points:
                writer.writerow([dp])
        
        print("Adjusted saved design points: {} -> {}".format(original_saved_points, adjusted_saved_points))
        return True
        
    except Exception as e:
        print("ERROR: Failed to adjust saved design points file: {}".format(e))
        return False

def main():
    """Main function with robust error handling and CSV adjustment."""
    # Configuration
    base_geom_file = r"''' + geom_path + '''"
    design_points_file = r"''' + design_points_path + '''"
    save_folder = r"''' + geoms_folder + '''"
    
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
    design_points, header = read_design_points(design_points_file)
    if not design_points:
        print("FATAL ERROR: No valid design points found")
        return False
    
    print("Found {} design points".format(len(design_points)))
    
    # Movement configuration
    movement_info = ''' + movement_info_str + '''
    
    # Saved design points configuration
    save_design_points = ''' + save_design_points_str + '''
    print("Design points to save: {}".format(save_design_points))

    # Build list of enabled movements
    enabled_moves = parse_movement_info(movement_info)
    print("Found {} enabled movements".format(len(enabled_moves)))
    
    # Track successful and failed design points
    successful_points = []
    failed_indices = []
    successful_count = 0  # Counter for sequential naming
    
    print("\\n" + "="*60)
    print("PROCESSING DESIGN POINTS")
    print("="*60)
    
    # Process each design point
    for idx, design_point in enumerate(design_points):
        print("\\n--- Design Point {} ---".format(idx))
        
        # Reset to base geometry for each design point
        print("  Resetting to base geometry...")
        if not open_file(base_geom_file):
            print("ERROR: Failed to reset to base geometry for design point {}".format(idx))
            failed_indices.append(idx)
            continue
        
        # Apply the design point values directly
        success = apply_design_point_values(design_point, enabled_moves, movement_info, idx)
        
        if success:
            # Check if this design point should be saved
            should_save = should_save_design_point(idx, save_design_points, failed_indices)
            
            # Save the geometry with sequential naming
            if save_geometry(successful_count, save_folder):
                successful_points.append(design_points[idx])
                print("  [SUCCESS] Design point {} completed successfully (saved as geom_dp{})".format(idx, successful_count))
                if should_save:
                    print("  [SAVE] This design point will be saved for case/data files")
                successful_count += 1  # Increment counter for next successful point
            else:
                print("  [FAILED] Design point {} failed to save".format(idx))
                failed_indices.append(idx)
        else:
            print("  [FAILED] Design point {} failed to apply".format(idx))
            failed_indices.append(idx)
    
    # Report results
    print("\\n" + "="*60)
    print("PROCESSING COMPLETE")
    print("="*60)
    print("Total design points: {}".format(len(design_points)))
    print("Successful: {} (saved as geom_dp0 to geom_dp{})".format(len(successful_points), len(successful_points)-1))
    print("Failed: {}".format(len(failed_indices)))
    
    if failed_indices:
        print("Failed design point indices: {}".format(failed_indices))
    
    # Update CSV file if there were failures
    if failed_indices:
        print("\\nUpdating design points file to remove {} failed points...".format(len(failed_indices)))
        if write_design_points(design_points_file, successful_points, header):
            print("[SUCCESS] Design points file updated successfully")
        else:
            print("[FAILED] Failed to update design points file")
        
        # Save failed design points to separate file
        print("\\nSaving failed design points to separate file...")
        if write_failed_design_points(design_points_file, failed_indices, design_points, header):
            print("[SUCCESS] Failed design points file created successfully")
        else:
            print("[FAILED] Failed to create failed design points file")
        
        # Adjust saved design points file based on failures
        print("\\nAdjusting saved design points file based on failures...")
        if adjust_saved_design_points_file(design_points_file, failed_indices):
            print("[SUCCESS] Saved design points file adjusted successfully")
        else:
            print("[FAILED] Failed to adjust saved design points file")
    else:
        print("\\n[SUCCESS] All design points processed successfully - no CSV update needed")
    
    print("\\nRobust processing complete!")
    return True

# Run the main function directly for IronPython/SpaceClaim
try:
    success = main()
    if not success:
        print("Script completed with errors")
except Exception as e:
    print("FATAL ERROR: Script crashed: {}".format(e))
    print("Traceback: {}".format(traceback.format_exc()))
'''

    # Write the script to file
    with open(script_path, 'w') as f:
        f.write(script_content)

    print("[SUCCESS] Robust SpaceClaim script created at: {}".format(script_path))
    print("[SUCCESS] Geometries will be saved to: {}".format(geoms_folder))
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
        raise FileNotFoundError("Script not found: {}".format(script_path))

    # Ensure SpaceClaim executable exists
    spaceclaim_exe = os.path.abspath(spaceclaim_exe)
    if not os.path.exists(spaceclaim_exe):
        raise FileNotFoundError("SpaceClaim executable not found: {}".format(spaceclaim_exe))

    # Command to launch SpaceClaim headless
    cmd = [
        spaceclaim_exe,
        "/RunScript={}".format(script_path),
        "/Headless=True",
        "/Splash=False",
        "/Welcome=False",
        "/ExitAfterScript=True"
    ]

    print("Running SpaceClaim headless script:\n{}".format(script_path))
    subprocess.run(cmd, check=True)