import os
from ansys.fluent.core.filereader.case_file import CaseFile
import numpy as np
from skopt.sampler import Lhs
from skopt.space import Space


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





def get_sample_points_from_ranges(movement_ranges, project_folder: str, n_points: int = None):
    """
    Generate Latin Hypercube Sample points within bounds defined in movement_ranges
    and save to CSV with descriptive headers. Provides option to add custom design points.

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

    print(f"\n📊 Design Points Generation from Movement Ranges:")
    print(f"Parameters: {len(headers)} movement dimensions")
    for i, (header, low, high) in enumerate(zip(headers, lower_bounds, upper_bounds)):
        print(f"  {header}: [{low}, {high}]")

    # Ask user for generation method
    print("\nChoose generation method:")
    print("1. Generate random Latin Hypercube samples")
    print("2. Add custom design points manually")
    print("3. Both (generate random + add custom)")
    
    while True:
        choice = input("Choose option (1, 2, or 3): ").strip()
        if choice in ["1", "2", "3"]:
            break
        print("❌ Invalid choice. Please enter 1, 2, or 3.")

    all_points = []

    # Generate random points if option 1 or 3
    if choice in ["1", "3"]:
        # Prompt user if n_points not provided
        if n_points is None:
            while True:
                try:
                    n_points = int(input("Enter the number of random design points to generate: ").strip())
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
        random_points = lhs_generator.generate(space.dimensions, n_points)
        all_points.extend(random_points)
        print(f"✅ Generated {n_points} random design points")

    # Add custom points if option 2 or 3
    if choice in ["2", "3"]:
        print(f"\n📝 Adding custom design points:")
        print(f"Enter values for each parameter (space-separated), or 'done' to finish")
        print(f"Parameters: {', '.join(headers)}")
        print(f"Example: {' '.join([str((low+high)/2) for low, high in zip(lower_bounds, upper_bounds)])}")
        
        custom_count = 0
        while True:
            user_input = input(f"Custom point {custom_count + 1} (or 'done'): ").strip()
            if user_input.lower() == 'done':
                break
                
            try:
                values = [float(x.strip()) for x in user_input.split()]
                if len(values) != len(lower_bounds):
                    print(f"❌ Need exactly {len(lower_bounds)} values. Got {len(values)}.")
                    continue
                
                # Check bounds and warn if outside, but accept anyway
                warnings = []
                for i, (val, low, high, header) in enumerate(zip(values, lower_bounds, upper_bounds, headers)):
                    if not (low <= val <= high):
                        warnings.append(f"{header} value {val} is outside bounds [{low}, {high}]")
                
                # Accept the point regardless of bounds
                all_points.append(values)
                custom_count += 1
                
                if warnings:
                    print(f"⚠️ Added custom point {custom_count} with warnings:")
                    for warning in warnings:
                        print(f"   {warning}")
                    print(f"   Point: {values}")
                else:
                    print(f"✅ Added custom point {custom_count}: {values}")
                    
            except ValueError:
                print("❌ Invalid input. Enter space-separated numbers.")
        
        print(f"✅ Added {custom_count} custom design points")

    if not all_points:
        print("❌ No design points generated. Exiting.")
        return None

    # Output folder
    dps_folder = os.path.join(project_folder, "test_files", "dps")
    os.makedirs(dps_folder, exist_ok=True)

    # Convert to numpy array and save CSV
    points_array = np.array(all_points)
    file_path = os.path.join(dps_folder, "DesignPoints.csv")
    np.savetxt(file_path, points_array, delimiter=",", header=",".join(headers), comments='')

    print(f"\n✅ Total {len(all_points)} design points saved to: {file_path}")
    return file_path, len(all_points)


