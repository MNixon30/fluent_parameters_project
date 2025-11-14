#Asks the user for inputs to create the refinment_model json file to store infomation

import os
import json
import re
import pandas as pd

try:
    import h5py
    H5PY_AVAILABLE = True
except ImportError:
    H5PY_AVAILABLE = False


def get_model_outputs(rif_folder):
    """
    Read a summary2.csv-formatted file from rif_folder/out_final and return it.

    Args:
        rif_folder (str): Path to the rif_0 archive folder (e.g., .../test_files/rif_0_YYYYMMDD_HHMMSS)

    Returns:
        list[str]: Unique output parameter names (may be empty if not found)
    """
    try:
        out_final_dir = os.path.join(rif_folder, "out_final")
        summary_path = os.path.join(out_final_dir, "summary2.csv")

        if not os.path.exists(summary_path):
            print(f"[WARNING] summary2.csv not found at: {summary_path}")
            return []

        df = pd.read_csv(summary_path)

        # Basic validation for expected columns
        expected_cols = {"Design Point", "Output Parameter", "Value"}
        missing = expected_cols - set(df.columns)
        if missing:
            print(f"[WARNING] summary2.csv missing expected columns: {sorted(missing)}")

        # Extract unique output parameter names
        if "Output Parameter" in df.columns:
            outputs = sorted(pd.Series(df["Output Parameter"].astype(str)).dropna().unique().tolist())
        else:
            outputs = []

        print(f"[SUCCESS] Loaded summary2.csv from: {summary_path}")
        print(f"[DATA] Output parameters detected: {outputs}")
        return outputs

    except Exception as e:
        print(f"[ERROR] Failed to read model outputs: {e}")
        return []

def get_model_inputs(rif_folder):
    """
    Read a DesignPoints.csv-like file from rif_folder/dps and return it.

    Args:
        rif_folder (str): Path to the rif_0 archive folder (e.g., .../test_files/rif_0_YYYYMMDD_HHMMSS)

    Returns:
        list[str]: Input parameter names (column names) excluding design point/index columns
    """
    try:
        dps_dir = os.path.join(rif_folder, "dps")
        dps_path = os.path.join(dps_dir, "DesignPoints.csv")

        if not os.path.exists(dps_path):
            print(f"[WARNING] DesignPoints.csv not found at: {dps_path}")
            return []

        df = pd.read_csv(dps_path)

        if df.empty or len(df.columns) == 0:
            print("[WARNING] DesignPoints.csv is empty or has no columns")

        # Determine input parameter columns: exclude design point/index columns
        cols = [c for c in df.columns if str(c).strip().lower() not in {"design point", "design_point", "index"} and not str(c).startswith("Unnamed")] 
        inputs = [str(c) for c in cols]

        print(f"[SUCCESS] Loaded DesignPoints.csv from: {dps_path}")
        print(f"[DATA] Input parameters detected: {inputs}")
        return inputs

    except Exception as e:
        print(f"[ERROR] Failed to read model inputs: {e}")
        return []


def _find_solution_config(project_folder):
    """Locate solution_config.json either in project folder or current working directory."""
    candidate_paths = [
        os.path.join(project_folder, "solution_config.json"),
        os.path.join(os.getcwd(), "solution_config.json"),
    ]
    seen = set()
    for path in candidate_paths:
        if path and path not in seen and os.path.exists(path):
            return path
        seen.add(path)
    return None


def _detect_case_file_path(project_folder):
    """Attempt to find a case file path for extracting output parameters."""
    # First, check solution_config.json
    solution_config_path = _find_solution_config(project_folder)
    if solution_config_path:
        try:
            with open(solution_config_path, "r") as f:
                solution_config = json.load(f)
            updated_paths = solution_config.get("updated_ref_paths", {})
            case_path = updated_paths.get("case_file") or solution_config.get("case_file")
            if case_path and os.path.exists(case_path):
                return case_path
        except Exception as exc:
            print(f"[WARNING] Failed to parse solution_config.json: {exc}")

    # Fallback: search within common project subdirectories
    search_dirs = [
        project_folder,
        os.path.join(project_folder, "ref"),
        os.path.join(project_folder, "ref", "scripts"),
        os.path.join(project_folder, "ref_files"),
        os.path.join(project_folder, "ref_files", "ref"),
        os.path.join(project_folder, "ref_files", "scripts"),
        os.path.join(project_folder, "test_files", "ref"),
        os.path.join(project_folder, "test_files", "ref", "scripts"),
    ]

    for base_dir in search_dirs:
        if not os.path.isdir(base_dir):
            continue
        for root, _, files in os.walk(base_dir):
            for name in files:
                lower = name.lower()
                if lower.endswith(".cas") or lower.endswith(".cas.h5"):
                    case_path = os.path.join(root, name)
                    print(f"[INFO] Found case file candidate: {case_path}")
                    return case_path

    return None


def _extract_outputs_from_case(case_path):
    """Read Fluent case file and extract report definition parameter names."""
    if not H5PY_AVAILABLE:
        print("[WARNING] h5py not available; cannot read output parameters from case file.")
        return []

    try:
        with h5py.File(case_path, "r") as case:
            try:
                ramp = case["settings"]["Rampant Variables"][0].decode("utf-8", "ignore")
            except KeyError:
                print(f"[WARNING] Rampant Variables section not found in case file: {case_path}")
                return []
    except Exception as exc:
        print(f"[WARNING] Failed to open case file '{case_path}': {exc}")
        return []

    outputs = set()
    needle = "report-definition-parameter"
    pos = ramp.find(needle)
    while pos != -1:
        segment = ramp[pos : pos + 600]
        match = re.search(r'name \(value \. "([^"]+)"\)', segment)
        if match:
            outputs.add(match.group(1))
        pos = ramp.find(needle, pos + 1)

    # Include named expressions (often store outputs like center_of_pressure_x)
    for match in re.finditer(r'named-expressions\s*\(\(\((.*?)\)\)\)', ramp, re.DOTALL):
        block = match.group(1)
        for name_match in re.finditer(r'\(name\s*\.\s*"([^"]+)"\)', block):
            outputs.add(name_match.group(1))

    # Include explicit output parameter blocks
    for match in re.finditer(r'output-parameters\s*\((.*?)\)\)\)', ramp, re.DOTALL):
        block = match.group(1)
        for name_match in re.finditer(r'\(name\s*\(\s*value\s*\.\s*"([^"]+)"\)', block):
            outputs.add(name_match.group(1))

    # Filter out generic entries that are unlikely to be output parameters
    filtered_outputs = sorted(
        name for name in outputs
        if name and " " not in name and not name.lower().startswith(("original", "pre-"))
    )

    if filtered_outputs:
        print(f"[SUCCESS] Extracted output parameters from case file: {', '.join(filtered_outputs)}")
    else:
        print(f"[WARNING] No report-definition parameters found in case file: {case_path}")
    return filtered_outputs



def refinment_inputs(project_folder):
    """
    Interactive function to create and edit refinement configuration JSON file.
    
    This function:
    - Reads output parameters from get_model_outputs
    - Collects acquisition weights from user (defaults: 0.6 gradient, 0.4 variance)
    - Allows user to specify localization areas based on output parameters
    - Saves all settings to a JSON configuration file
    - Provides an editable menu system
    
    Args:
        project_folder (str): Path to the project folder (refinement can be configured before rif exists)
        
    Returns:
        str: Path to the created/updated JSON config file, or None on error
    """
    
    # Load output parameters
    print("\n" + "="*60)
    print("REFINEMENT INPUTS CONFIGURATION")
    print("="*60)
    print(f"\nAttempting to load output parameters from project: {project_folder}")
    
    # Try to read outputs from existing project artifacts
    output_params_set = set()
    try:
        # Common location if available later
        summary_path = os.path.join(project_folder, "test_files", "out_final", "summary2.csv")
        if os.path.exists(summary_path):
            df_out = pd.read_csv(summary_path)
            if "Output Parameter" in df_out.columns:
                summary_outputs = pd.Series(df_out["Output Parameter"].astype(str)).dropna().unique().tolist()
                output_params_set.update(summary_outputs)
                print(f"[SUCCESS] Found output parameters in summary2.csv: {', '.join(summary_outputs)}")
    except Exception as e:
        print(f"[WARNING] Could not auto-detect outputs: {e}")
    
    case_file_path = _detect_case_file_path(project_folder)
    if case_file_path:
        case_outputs = _extract_outputs_from_case(case_file_path)
        if case_outputs:
            output_params_set.update(case_outputs)
        else:
            print("[INFO] Case file detected but no outputs extracted.")
    else:
        print("[INFO] No case file found for automatic output detection.")

    output_params = sorted(output_params_set)

    if not output_params:
        manual = input("No outputs detected yet. Enter output parameter names (comma-separated) or press Enter to skip: ").strip()
        if manual:
            output_params = [s.strip() for s in manual.split(',') if s.strip()]
            print(f"[INFO] Using user-provided outputs: {', '.join(output_params)}")
        else:
            print("[INFO] Proceeding without predefined outputs. You can still configure other settings and add areas later.")
    
    # Config path is saved to the project folder (rif folder may not exist yet)
    config_path = os.path.join(project_folder, "refinement_config.json")
    
    # Load existing config if it exists
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            print(f"\n[INFO] Loaded existing configuration from: {config_path}")
        except Exception as e:
            print(f"[WARNING] Failed to load existing config: {e}")
            print("[INFO] Starting with fresh configuration")
    
    # Initialize default values
    if 'acquisition_weights' not in config:
        config['acquisition_weights'] = {
            'gradient_weight': 0.6,
            'variance_weight': 0.4
        }
    
    if 'localization_areas' not in config:
        config['localization_areas'] = []
    
    if 'localization_enabled' not in config:
        config['localization_enabled'] = False
    
    if 'diversity_settings' not in config:
        config['diversity_settings'] = {
            'min_distance': 0.1,  # Minimum normalized distance between design points
            'distance_metric': 'euclidean'  # 'euclidean' or 'manhattan'
        }
    
    if 'number_of_refinement_points' not in config:
        config['number_of_refinement_points'] = 10
    
    if 'optimization_settings' not in config:
        config['optimization_settings'] = {
            'pre_samples': None,  # Will default to max(30, number_of_refinement_points * 2)
            'max_optimize_candidates': None,  # Will default to min(3, number_of_refinement_points)
            'max_iterations': 15,
            'max_diversity_attempts': 30,
            'region_tightness': 0.15  # Default: 15% of parameter range around promising regions
        }
    
    # Main menu loop
    while True:
        print("\n" + "="*60)
        print("REFINEMENT CONFIGURATION MENU")
        print("="*60)
        print("\nCurrent Settings:")
        print(f"  Acquisition Weights:")
        print(f"    - Gradient: {config['acquisition_weights']['gradient_weight']:.2f}")
        print(f"    - Variance: {config['acquisition_weights']['variance_weight']:.2f}")
        print(f"  Localization: {'ENABLED' if config['localization_enabled'] else 'DISABLED'}")
        print(f"  Localization Areas: {len(config['localization_areas'])}")
        print(f"  Minimum Distance: {config['diversity_settings']['min_distance']:.3f}")
        print(f"  Number of Refinement Points: {config['number_of_refinement_points']}")
        
        # Show optimization settings
        opt_settings = config.get('optimization_settings', {})
        number_of_dps = config.get('number_of_refinement_points', 10)
        default_pre_samples = max(30, number_of_dps * 2)
        default_max_optimize = min(3, number_of_dps)
        pre_samples = opt_settings.get('pre_samples', None)
        max_optimize = opt_settings.get('max_optimize_candidates', None)
        region_tightness = opt_settings.get('region_tightness', 0.15)
        print(f"  Pre-samples: {pre_samples if pre_samples else f'Default ({default_pre_samples})'}")
        print(f"  Max Optimize Candidates: {max_optimize if max_optimize else f'Default ({default_max_optimize})'}")
        print(f"  Region Tightness: {region_tightness:.3f} ({region_tightness*100:.1f}% of range)")
        
        print("\nMenu Options:")
        print("1. Configure Acquisition Weights")
        print("2. Setup Localization Areas")
        print("3. Configure Diversity Settings")
        print("4. Set Number of Refinement Points")
        print("5. Configure Optimization Settings")
        print("6. View Current Configuration")
        print("7. Save and Exit")
        print("8. Exit Without Saving")
        
        choice = input("\nEnter your choice (1-8): ").strip()
        
        if choice == '1':
            config = _configure_acquisition_weights(config)
        elif choice == '2':
            config = _configure_localization_areas(config, output_params)
        elif choice == '3':
            config = _configure_diversity_settings(config)
        elif choice == '4':
            config = _configure_refinement_points(config)
        elif choice == '5':
            config = _configure_optimization_settings(config)
        elif choice == '6':
            _view_configuration(config)
        elif choice == '7':
            if _save_configuration(config, config_path):
                return config_path
            else:
                print("[ERROR] Failed to save configuration. Please try again.")
        elif choice == '8':
            confirm = input("Exit without saving? All changes will be lost. (yes/no): ").strip().lower()
            if confirm in ['yes', 'y']:
                print("[INFO] Exiting without saving changes.")
                return None
        else:
            print("[ERROR] Invalid choice. Please enter 1-8.")


def _configure_acquisition_weights(config):
    """Configure acquisition weights through user input."""
    print("\n" + "="*60)
    print("ACQUISITION WEIGHTS CONFIGURATION")
    print("="*60)
    print("\nAcquisition weights determine the balance between:")
    print("  - Gradient weight: Preference for areas with high gradients (exploitation)")
    print("  - Variance weight: Preference for areas with high uncertainty (exploration)")
    print("\nDefault values: Gradient=0.6, Variance=0.4")
    
    current_grad = config['acquisition_weights']['gradient_weight']
    current_var = config['acquisition_weights']['variance_weight']
    
    print(f"\nCurrent weights: Gradient={current_grad:.2f}, Variance={current_var:.2f}")
    
    while True:
        try:
            grad_input = input(f"\nEnter gradient weight (current: {current_grad:.2f}, press Enter to keep): ").strip()
            if grad_input == '':
                gradient_weight = current_grad
            else:
                gradient_weight = float(grad_input)
                if gradient_weight < 0:
                    print("[ERROR] Gradient weight must be >= 0")
                    continue
            
            var_input = input(f"Enter variance weight (current: {current_var:.2f}, press Enter to keep): ").strip()
            if var_input == '':
                variance_weight = current_var
            else:
                variance_weight = float(var_input)
                if variance_weight < 0:
                    print("[ERROR] Variance weight must be >= 0")
                    continue
            
            # Normalize weights
            total = gradient_weight + variance_weight
            if total == 0:
                print("[ERROR] At least one weight must be > 0")
                continue
            
            normalized_grad = gradient_weight / total
            normalized_var = variance_weight / total
            
            config['acquisition_weights']['gradient_weight'] = normalized_grad
            config['acquisition_weights']['variance_weight'] = normalized_var
            
            print(f"\n[SUCCESS] Acquisition weights updated:")
            print(f"  Gradient: {normalized_grad:.3f}")
            print(f"  Variance: {normalized_var:.3f}")
            print(f"  Total: {normalized_grad + normalized_var:.3f}")
            
            return config
            
        except ValueError:
            print("[ERROR] Please enter a valid number")
        except Exception as e:
            print(f"[ERROR] An error occurred: {e}")


def _configure_localization_areas(config, output_params):
    """Configure localization areas through user input."""
    print("\n" + "="*60)
    print("LOCALIZATION AREAS CONFIGURATION")
    print("="*60)
    print("\nLocalization allows you to focus refinement points on specific regions")
    print("of the design space, such as:")
    print("  - Maximum downforce regions")
    print("  - Minimum drag regions")
    print("  - Target value regions")
    
    # Ask if user wants to enable localization
    current_enabled = config.get('localization_enabled', False)
    print(f"\nCurrent status: {'ENABLED' if current_enabled else 'DISABLED'}")
    
    enable_choice = input("\nEnable localization? (yes/no, press Enter to keep current): ").strip().lower()
    if enable_choice in ['yes', 'y']:
        config['localization_enabled'] = True
        localization_enabled = True
    elif enable_choice in ['no', 'n']:
        config['localization_enabled'] = False
        localization_enabled = False
    else:
        localization_enabled = current_enabled
        config['localization_enabled'] = current_enabled
    
    if not localization_enabled:
        print("[INFO] Localization disabled. No areas will be configured.")
        # Clear existing areas
        config['localization_areas'] = []
        return config
    
    # Manage localization areas
    while True:
        print("\n" + "-"*60)
        print("LOCALIZATION AREAS MENU")
        print("-"*60)
        print(f"\nCurrent areas ({len(config['localization_areas'])}):")
        
        for i, area in enumerate(config['localization_areas'], 1):
            print(f"  {i}. {area.get('name', 'Unnamed Area')}")
            print(f"     Output: {area.get('output_parameter', 'N/A')}")
            print(f"     Target: {area.get('target_type', 'N/A')}")
            if area.get('target_value') is not None:
                print(f"     Value: {area['target_value']}")
            print(f"     Weight: {area.get('weight', 1.0):.2f}")
        
        print("\nOptions:")
        print("1. Add New Localization Area")
        print("2. Edit Existing Area")
        print("3. Delete Area")
        print("4. Done (Return to Main Menu)")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            config = _add_localization_area(config, output_params)
        elif choice == '2':
            config = _edit_localization_area(config, output_params)
        elif choice == '3':
            config = _delete_localization_area(config)
        elif choice == '4':
            break
        else:
            print("[ERROR] Invalid choice. Please enter 1-4.")
    
    return config


def _add_localization_area(config, output_params):
    """Add a new localization area."""
    print("\n" + "-"*60)
    print("ADD LOCALIZATION AREA")
    print("-"*60)
    
    if not output_params:
        # Allow manual entry if outputs aren't known yet
        while True:
            selected_param = input("Enter output parameter name (e.g., Downforce): ").strip()
            if selected_param:
                break
            print("[ERROR] Output parameter name cannot be empty")
    else:
        # Select from available list
        print("\nAvailable output parameters:")
        for i, param in enumerate(output_params, 1):
            print(f"  {i}. {param}")
        
        while True:
            try:
                param_choice = input(f"\nSelect output parameter (1-{len(output_params)}): ").strip()
                param_idx = int(param_choice) - 1
                if 0 <= param_idx < len(output_params):
                    selected_param = output_params[param_idx]
                    break
                else:
                    print(f"[ERROR] Please enter a number between 1 and {len(output_params)}")
            except ValueError:
                print("[ERROR] Please enter a valid number")
    
    # Select target type
    print("\nTarget Type Options:")
    print("  1. Maximum - Focus on regions with maximum values")
    print("  2. Minimum - Focus on regions with minimum values")
    print("  3. Target Value - Focus on regions near a specific value")
    
    while True:
        try:
            target_choice = input("\nSelect target type (1-3): ").strip()
            if target_choice == '1':
                target_type = 'maximum'
                target_value = None
                break
            elif target_choice == '2':
                target_type = 'minimum'
                target_value = None
                break
            elif target_choice == '3':
                target_type = 'target_value'
                while True:
                    try:
                        target_value = float(input("Enter target value: ").strip())
                        break
                    except ValueError:
                        print("[ERROR] Please enter a valid number")
                break
            else:
                print("[ERROR] Please enter 1, 2, or 3")
        except Exception:
            print("[ERROR] Please enter a valid number")
    
    # Get area name
    area_name = input("\nEnter a name for this area (or press Enter for default): ").strip()
    if not area_name:
        area_name = f"{selected_param}_{target_type}"
    
    # Get weight
    while True:
        try:
            weight_input = input("\nEnter weight for this area (default: 1.0, press Enter to use default): ").strip()
            if weight_input == '':
                weight = 1.0
            else:
                weight = float(weight_input)
                if weight < 0:
                    print("[ERROR] Weight must be >= 0")
                    continue
            break
        except ValueError:
            print("[ERROR] Please enter a valid number")
    
    # Create area dictionary
    new_area = {
        'name': area_name,
        'output_parameter': selected_param,
        'target_type': target_type,
        'target_value': target_value,
        'weight': weight
    }
    
    config['localization_areas'].append(new_area)
    print(f"\n[SUCCESS] Added localization area: {area_name}")
    
    return config


def _edit_localization_area(config, output_params):
    """Edit an existing localization area."""
    areas = config.get('localization_areas', [])
    
    if not areas:
        print("[ERROR] No localization areas to edit")
        return config
    
    print("\nSelect area to edit:")
    for i, area in enumerate(areas, 1):
        print(f"  {i}. {area.get('name', 'Unnamed Area')}")
    
    while True:
        try:
            choice = input(f"\nSelect area (1-{len(areas)}): ").strip()
            area_idx = int(choice) - 1
            if 0 <= area_idx < len(areas):
                break
            else:
                print(f"[ERROR] Please enter a number between 1 and {len(areas)}")
        except ValueError:
            print("[ERROR] Please enter a valid number")
    
    area = areas[area_idx]
    
    print(f"\nEditing area: {area.get('name', 'Unnamed Area')}")
    print("\nWhat would you like to edit?")
    print("1. Name")
    print("2. Output Parameter")
    print("3. Target Type/Value")
    print("4. Weight")
    
    edit_choice = input("\nEnter your choice (1-4): ").strip()
    
    if edit_choice == '1':
        new_name = input(f"Enter new name (current: {area.get('name', '')}): ").strip()
        if new_name:
            area['name'] = new_name
            print("[SUCCESS] Name updated")
    elif edit_choice == '2':
        print("\nAvailable output parameters:")
        for i, param in enumerate(output_params, 1):
            print(f"  {i}. {param}")
        while True:
            try:
                param_choice = input(f"Select output parameter (1-{len(output_params)}): ").strip()
                param_idx = int(param_choice) - 1
                if 0 <= param_idx < len(output_params):
                    area['output_parameter'] = output_params[param_idx]
                    print("[SUCCESS] Output parameter updated")
                    break
                else:
                    print(f"[ERROR] Please enter a number between 1 and {len(output_params)}")
            except ValueError:
                print("[ERROR] Please enter a valid number")
    elif edit_choice == '3':
        print("\nTarget Type Options:")
        print("  1. Maximum")
        print("  2. Minimum")
        print("  3. Target Value")
        target_choice = input("\nSelect target type (1-3): ").strip()
        if target_choice == '1':
            area['target_type'] = 'maximum'
            area['target_value'] = None
        elif target_choice == '2':
            area['target_type'] = 'minimum'
            area['target_value'] = None
        elif target_choice == '3':
            area['target_type'] = 'target_value'
            while True:
                try:
                    target_value = float(input("Enter target value: ").strip())
                    area['target_value'] = target_value
                    break
                except ValueError:
                    print("[ERROR] Please enter a valid number")
        print("[SUCCESS] Target type updated")
    elif edit_choice == '4':
        while True:
            try:
                weight_input = input(f"Enter new weight (current: {area.get('weight', 1.0):.2f}): ").strip()
                weight = float(weight_input)
                if weight < 0:
                    print("[ERROR] Weight must be >= 0")
                    continue
                area['weight'] = weight
                print("[SUCCESS] Weight updated")
                break
            except ValueError:
                print("[ERROR] Please enter a valid number")
    
    return config


def _delete_localization_area(config):
    """Delete a localization area."""
    areas = config.get('localization_areas', [])
    
    if not areas:
        print("[ERROR] No localization areas to delete")
        return config
    
    print("\nSelect area to delete:")
    for i, area in enumerate(areas, 1):
        print(f"  {i}. {area.get('name', 'Unnamed Area')}")
    
    while True:
        try:
            choice = input(f"\nSelect area to delete (1-{len(areas)}): ").strip()
            area_idx = int(choice) - 1
            if 0 <= area_idx < len(areas):
                deleted = areas.pop(area_idx)
                print(f"[SUCCESS] Deleted area: {deleted.get('name', 'Unnamed Area')}")
                break
            else:
                print(f"[ERROR] Please enter a number between 1 and {len(areas)}")
        except ValueError:
            print("[ERROR] Please enter a valid number")
    
    return config


def _configure_diversity_settings(config):
    """Configure diversity settings for design point spacing."""
    print("\n" + "="*60)
    print("DIVERSITY SETTINGS CONFIGURATION")
    print("="*60)
    print("\nDiversity settings control the minimum distance between design points.")
    print("This ensures design points are spread out and not too close to each other.")
    
    current_min_dist = config['diversity_settings']['min_distance']
    current_metric = config['diversity_settings']['distance_metric']
    
    print(f"\nCurrent settings:")
    print(f"  Minimum Distance: {current_min_dist:.3f} (normalized, 0-1 range)")
    print(f"  Distance Metric: {current_metric}")
    print("\nNote: Minimum distance is normalized (0-1).")
    print("  - 0.05 = very close points allowed (tight clustering)")
    print("  - 0.1 = moderate spacing (default)")
    print("  - 0.2 = wide spacing (very spread out)")
    
    while True:
        try:
            dist_input = input(f"\nEnter minimum distance (current: {current_min_dist:.3f}, press Enter to keep): ").strip()
            if dist_input == '':
                min_distance = current_min_dist
            else:
                min_distance = float(dist_input)
                if min_distance < 0 or min_distance > 1:
                    print("[ERROR] Minimum distance must be between 0 and 1")
                    continue
            
            print("\nDistance Metric Options:")
            print("  1. Euclidean (default) - standard distance")
            print("  2. Manhattan - sum of absolute differences")
            
            metric_choice = input(f"\nSelect distance metric (1-2, press Enter for {current_metric}): ").strip()
            if metric_choice == '1' or (metric_choice == '' and current_metric == 'euclidean'):
                distance_metric = 'euclidean'
            elif metric_choice == '2' or (metric_choice == '' and current_metric == 'manhattan'):
                distance_metric = 'manhattan'
            else:
                distance_metric = current_metric
            
            config['diversity_settings']['min_distance'] = min_distance
            config['diversity_settings']['distance_metric'] = distance_metric
            
            print(f"\n[SUCCESS] Diversity settings updated:")
            print(f"  Minimum Distance: {min_distance:.3f}")
            print(f"  Distance Metric: {distance_metric}")
            
            return config
            
        except ValueError:
            print("[ERROR] Please enter a valid number")
        except Exception as e:
            print(f"[ERROR] An error occurred: {e}")


def _configure_refinement_points(config):
    """Configure the number of refinement points through user input."""
    print("\n" + "="*60)
    print("NUMBER OF REFINEMENT POINTS CONFIGURATION")
    print("="*60)
    print("\nThis setting determines how many new design points will be generated")
    print("for the refinement iteration.")
    
    current_value = config.get('number_of_refinement_points', 10)
    print(f"\nCurrent value: {current_value}")
    print(f"Default: 10")
    
    while True:
        try:
            user_input = input(f"\nEnter number of refinement points (current: {current_value}, press Enter to keep): ").strip()
            if user_input == '':
                number_of_points = current_value
            else:
                number_of_points = int(user_input)
                if number_of_points < 1:
                    print("[ERROR] Number of refinement points must be >= 1")
                    continue
                if number_of_points > 1000:
                    confirm = input(f"[WARNING] You entered {number_of_points} points. This may take a long time. Continue? (yes/no): ").strip().lower()
                    if confirm not in ['yes', 'y']:
                        continue
            
            config['number_of_refinement_points'] = number_of_points
            
            print(f"\n[SUCCESS] Number of refinement points updated: {number_of_points}")
            
            return config
            
        except ValueError:
            print("[ERROR] Please enter a valid integer number")
        except Exception as e:
            print(f"[ERROR] An error occurred: {e}")


def _configure_optimization_settings(config):
    """Configure optimization settings for candidate sampling and optimization."""
    print("\n" + "="*60)
    print("OPTIMIZATION SETTINGS CONFIGURATION")
    print("="*60)
    print("\nThese settings control the optimization process for generating refinement points:")
    print("  - Pre-samples: Number of candidate points to evaluate before optimization")
    print("  - Max Optimize Candidates: Maximum number of candidates to optimize")
    print("  - Max Iterations: Maximum iterations for differential evolution optimization")
    print("  - Max Diversity Attempts: Maximum attempts to find diverse points")
    print("  - Region Tightness: How tightly design points cluster around found max/min regions")
    print("    (0.05 = very tight, 0.15 = default, 0.3 = loose, 1.0 = full range)")
    
    number_of_dps = config.get('number_of_refinement_points', 10)
    opt_settings = config.get('optimization_settings', {})
    
    # Get current values
    current_pre_samples = opt_settings.get('pre_samples', None)
    current_max_optimize = opt_settings.get('max_optimize_candidates', None)
    current_max_iter = opt_settings.get('max_iterations', 15)
    current_max_diversity = opt_settings.get('max_diversity_attempts', 30)
    current_region_tightness = opt_settings.get('region_tightness', 0.15)
    
    # Calculate defaults
    default_pre_samples = max(30, number_of_dps * 2)
    default_max_optimize = min(3, number_of_dps)
    
    print(f"\nCurrent settings:")
    print(f"  Pre-samples: {current_pre_samples if current_pre_samples else f'Default ({default_pre_samples})'}")
    print(f"  Max Optimize Candidates: {current_max_optimize if current_max_optimize else f'Default ({default_max_optimize})'}")
    print(f"  Max Iterations: {current_max_iter}")
    print(f"  Max Diversity Attempts: {current_max_diversity}")
    print(f"  Region Tightness: {current_region_tightness:.3f} ({current_region_tightness*100:.1f}% of parameter range)")
    
    print(f"\nDefaults (based on {number_of_dps} refinement points):")
    print(f"  Pre-samples: {default_pre_samples} (max(30, {number_of_dps} * 2))")
    print(f"  Max Optimize Candidates: {default_max_optimize} (min(3, {number_of_dps}))")
    print(f"  Max Iterations: 15")
    print(f"  Max Diversity Attempts: 30")
    print(f"  Region Tightness: 0.15 (15% of parameter range)")
    
    while True:
        try:
            # Pre-samples
            pre_samples_input = input(f"\nEnter pre-samples (current: {current_pre_samples if current_pre_samples else 'Default'}, press Enter to use default): ").strip()
            if pre_samples_input == '':
                pre_samples = None  # Will use default
            else:
                pre_samples = int(pre_samples_input)
                if pre_samples < 1:
                    print("[ERROR] Pre-samples must be >= 1")
                    continue
            
            # Max optimize candidates
            max_optimize_input = input(f"Enter max optimize candidates (current: {current_max_optimize if current_max_optimize else 'Default'}, press Enter to use default): ").strip()
            if max_optimize_input == '':
                max_optimize = None  # Will use default
            else:
                max_optimize = int(max_optimize_input)
                if max_optimize < 1:
                    print("[ERROR] Max optimize candidates must be >= 1")
                    continue
            
            # Max iterations
            max_iter_input = input(f"Enter max iterations (current: {current_max_iter}, press Enter to keep): ").strip()
            if max_iter_input == '':
                max_iter = current_max_iter
            else:
                max_iter = int(max_iter_input)
                if max_iter < 1:
                    print("[ERROR] Max iterations must be >= 1")
                    continue
                if max_iter > 200:
                    confirm = input(f"[WARNING] {max_iter} iterations may take a long time. Continue? (yes/no): ").strip().lower()
                    if confirm not in ['yes', 'y']:
                        continue
            
            # Max diversity attempts
            max_diversity_input = input(f"Enter max diversity attempts (current: {current_max_diversity}, press Enter to keep): ").strip()
            if max_diversity_input == '':
                max_diversity = current_max_diversity
            else:
                max_diversity = int(max_diversity_input)
                if max_diversity < 1:
                    print("[ERROR] Max diversity attempts must be >= 1")
                    continue
            
            # Region tightness
            region_tightness_input = input(f"Enter region tightness (current: {current_region_tightness:.3f}, press Enter to keep): ").strip()
            if region_tightness_input == '':
                region_tightness = current_region_tightness
            else:
                region_tightness = float(region_tightness_input)
                if region_tightness < 0.01:
                    print("[ERROR] Region tightness must be >= 0.01 (1% of range)")
                    continue
                if region_tightness > 1.0:
                    print("[ERROR] Region tightness should be <= 1.0 (100% of range)")
                    continue
            
            # Update config
            opt_settings['pre_samples'] = pre_samples
            opt_settings['max_optimize_candidates'] = max_optimize
            opt_settings['max_iterations'] = max_iter
            opt_settings['max_diversity_attempts'] = max_diversity
            opt_settings['region_tightness'] = region_tightness
            config['optimization_settings'] = opt_settings
            
            print(f"\n[SUCCESS] Optimization settings updated:")
            print(f"  Pre-samples: {pre_samples if pre_samples else f'Default ({default_pre_samples})'}")
            print(f"  Max Optimize Candidates: {max_optimize if max_optimize else f'Default ({default_max_optimize})'}")
            print(f"  Max Iterations: {max_iter}")
            print(f"  Max Diversity Attempts: {max_diversity}")
            print(f"  Region Tightness: {region_tightness:.3f} ({region_tightness*100:.1f}% of parameter range)")
            
            return config
            
        except ValueError:
            print("[ERROR] Please enter a valid integer number")
        except Exception as e:
            print(f"[ERROR] An error occurred: {e}")


def _view_configuration(config):
    """Display the current configuration in detail."""
    print("\n" + "="*60)
    print("CURRENT CONFIGURATION")
    print("="*60)
    
    print("\nAcquisition Weights:")
    weights = config.get('acquisition_weights', {})
    print(f"  Gradient Weight: {weights.get('gradient_weight', 0.6):.3f}")
    print(f"  Variance Weight: {weights.get('variance_weight', 0.4):.3f}")
    
    print(f"\nLocalization:")
    print(f"  Enabled: {config.get('localization_enabled', False)}")
    
    areas = config.get('localization_areas', [])
    print(f"  Number of Areas: {len(areas)}")
    
    print(f"\nDiversity Settings:")
    diversity = config.get('diversity_settings', {})
    print(f"  Minimum Distance: {diversity.get('min_distance', 0.1):.3f}")
    print(f"  Distance Metric: {diversity.get('distance_metric', 'euclidean')}")
    
    print(f"\nRefinement Points:")
    print(f"  Number of Points: {config.get('number_of_refinement_points', 10)}")
    
    print(f"\nOptimization Settings:")
    opt_settings = config.get('optimization_settings', {})
    number_of_dps = config.get('number_of_refinement_points', 10)
    default_pre_samples = max(30, number_of_dps * 2)
    default_max_optimize = min(3, number_of_dps)
    pre_samples = opt_settings.get('pre_samples', None)
    max_optimize = opt_settings.get('max_optimize_candidates', None)
    print(f"  Pre-samples: {pre_samples if pre_samples else f'Default ({default_pre_samples})'}")
    print(f"  Max Optimize Candidates: {max_optimize if max_optimize else f'Default ({default_max_optimize})'}")
    print(f"  Max Iterations: {opt_settings.get('max_iterations', 15)}")
    print(f"  Max Diversity Attempts: {opt_settings.get('max_diversity_attempts', 30)}")
    print(f"  Region Tightness: {opt_settings.get('region_tightness', 0.15):.3f} ({opt_settings.get('region_tightness', 0.15)*100:.1f}% of range)")
    
    if areas:
        print("\n  Localization Areas:")
        for i, area in enumerate(areas, 1):
            print(f"\n    Area {i}: {area.get('name', 'Unnamed')}")
            print(f"      Output Parameter: {area.get('output_parameter', 'N/A')}")
            print(f"      Target Type: {area.get('target_type', 'N/A')}")
            if area.get('target_value') is not None:
                print(f"      Target Value: {area['target_value']}")
            print(f"      Weight: {area.get('weight', 1.0):.2f}")
    
    input("\nPress Enter to return to main menu...")


def _save_configuration(config, config_path):
    """Save configuration to JSON file."""
    try:
        # Ensure directory exists
        dir_path = os.path.dirname(config_path)
        if dir_path:  # Only create directory if path is not empty
            os.makedirs(dir_path, exist_ok=True)
        
        # Save to JSON
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n[SUCCESS] Configuration saved to: {config_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save configuration: {e}")
        return False

    