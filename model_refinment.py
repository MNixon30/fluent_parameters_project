"""Model refinement helpers."""

import os
import shutil
import json
import pickle
from datetime import datetime
import numpy as np
import pandas as pd
from scipy.optimize import differential_evolution, dual_annealing
from scipy.spatial.distance import cdist

from model import *
from folder_management import *

def create_model_refinment(project_folder):
    """Create the advanced model for refinement using the provided project folder."""
    results = create_advanced_model(project_root=project_folder)
    if results:
        export_model_results(results, project_folder)
    return None


def move_ref_files(project_folder):
    """
    Move all immediate subfolders under project_folder/test_files into a rif_0 archive folder.

    Behavior:
    - Creates test_files/rif_0_<timestamp>/
    - Moves each subfolder of test_files (except existing rif_* archives) into that rif folder
    - Recreates empty folders with the same names under test_files

    Args:
        project_folder (str): Project root folder

    Returns:
        str | bool: Path to created rif folder on success, False on failure
    """
    try:
        test_files_dir = os.path.join(project_folder, "test_files")
        if not os.path.isdir(test_files_dir):
            print(f"[ERROR] test_files directory not found: {test_files_dir}")
            return False

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rif_folder = os.path.join(test_files_dir, f"rif_0_{timestamp}")
        os.makedirs(rif_folder, exist_ok=True)
        print(f"[INFO] Moving project files to: {rif_folder}")

        moved_folders = []
        for entry in os.listdir(test_files_dir):
            source_path = os.path.join(test_files_dir, entry)
            if not os.path.isdir(source_path):
                continue
            if entry.lower().startswith("rif_"):
                # Skip existing rif archives
                continue

            dest_path = os.path.join(rif_folder, entry)
            try:
                shutil.move(source_path, dest_path)
                print(f"[SUCCESS] Moved {entry}/ to {os.path.basename(rif_folder)}/")
                moved_folders.append(entry)
            except Exception as e:
                print(f"[WARNING] Failed moving {entry}/: {e}")

        # Recreate empty folders with the same names
        if moved_folders:
            print("\n[INFO] Creating new empty folders...")
        for name in moved_folders:
            new_folder = os.path.join(test_files_dir, name)
            try:
                os.makedirs(new_folder, exist_ok=True)
                print(f"[SUCCESS] Created empty {name}/ folder")
            except Exception as e:
                print(f"[WARNING] Could not recreate {name}/: {e}")

        print(f"\n[SUCCESS] Successfully processed {len(moved_folders)} folders to {os.path.basename(rif_folder)}/")
        print(f"[INFO] Location: {rif_folder}")
        return rif_folder

    except Exception as e:
        print(f"[ERROR] Error moving files: {e}")
        return False



def create_refinment_dps(project_folder, rif_folder):
    """
    Create refinement design points using a trained model and refinement configuration.
    
    This function:
    - Loads the model from rif_folder/out_final/model
    - Loads refinement_config.json from rif_folder
    - Loads parameter ranges from solution_config.json
    - Generates design points using acquisition function (gradient + uncertainty)
    - Uses numerical methods for gradient computation (finite differences)
    - Ensures design points have minimum distance (diversity constraint)
    - Saves design points to project_folder/test_files/dps/DesignPoints.csv
    
    Args:
        project_folder (str): Project root folder
        rif_folder (str): Path to rif_0 archive folder
        
    Returns:
        str | None: Path to saved DesignPoints.csv on success, None on error
    """
    print("\n" + "="*60)
    print("CREATING REFINEMENT DESIGN POINTS")
    print("="*60)
    
    try:
        # Ensure required dependencies are available before proceeding
        try:
            import sklearn  # noqa: F401
        except ImportError:
            print("[ERROR] scikit-learn is required to load the trained model.")
            print("        Please install it with: pip install scikit-learn")
            return None

        # 1. Load model
        print("\n[1/6] Loading model...")
        model_dir = os.path.join(rif_folder, "out_final", "model")
        model_path = os.path.join(model_dir, "trained_model.pkl")
        
        if not os.path.exists(model_path):
            print(f"[ERROR] Model not found at: {model_path}")
            return None
        
        with open(model_path, 'rb') as f:
            model_dict = pickle.load(f)
        
        # Load model summary for input/output names
        summary_path = os.path.join(model_dir, "model_summary.json")
        if os.path.exists(summary_path):
            with open(summary_path, 'r') as f:
                summary_data = json.load(f)
            input_names = summary_data['parameters']['input_names']
            output_names = summary_data['parameters']['output_names']
        else:
            print("[WARNING] Model summary not found. Attempting to infer input/output names from model.")
            # Try to infer from model structure (this may not always work)
            input_names = [f"input_{i}" for i in range(len(model_dict.get('X_scaler', []).feature_names_in_))]
            output_names = [f"output_{i}" for i in range(model_dict.get('pca', []).n_components if model_dict.get('pca') else 1)]
        
        print(f"[SUCCESS] Model loaded. Inputs: {len(input_names)}, Outputs: {len(output_names)}")
        
        # 2. Load refinement config
        print("\n[2/6] Loading refinement configuration...")
        refinement_config_path = os.path.join(project_folder, "refinement_config.json")
        if not os.path.exists(refinement_config_path):
            # Fallback to rif folder (legacy location)
            legacy_path = os.path.join(rif_folder, "refinement_config.json")
            if os.path.exists(legacy_path):
                print(f"[INFO] Project-level refinement config not found. Using rif folder config at: {legacy_path}")
                refinement_config_path = legacy_path
            else:
                print("[ERROR] Refinement config not found in project folder or rif folder.")
                print(f"  Checked: {os.path.join(project_folder, 'refinement_config.json')}")
                print(f"           {legacy_path}")
                return None
        
        with open(refinement_config_path, 'r') as f:
            refinement_config = json.load(f)
        
        acquisition_weights = refinement_config.get('acquisition_weights', {'gradient_weight': 0.6, 'variance_weight': 0.4})
        diversity_settings = refinement_config.get('diversity_settings', {'min_distance': 0.1, 'distance_metric': 'euclidean'})
        localization_enabled = refinement_config.get('localization_enabled', False)
        localization_areas = refinement_config.get('localization_areas', [])
        number_of_dps = refinement_config.get('number_of_refinement_points', 10)
        
        print(f"[SUCCESS] Refinement config loaded. Gradient: {acquisition_weights['gradient_weight']:.2f}, Variance: {acquisition_weights['variance_weight']:.2f}")
        print(f"[INFO] Number of refinement points: {number_of_dps}")
        
        # 3. Load parameter ranges from solution_config.json in working directory
        print("\n[3/6] Loading parameter ranges...")
        solution_config_path = os.path.join(os.getcwd(), "solution_config.json")
        
        if not os.path.exists(solution_config_path):
            print(f"[ERROR] Solution config not found at: {solution_config_path}")
            return None
        
        with open(solution_config_path, 'r') as f:
            solution_config = json.load(f)
        
        # Extract parameter ranges from solution_config
        geom_params = solution_config.get('geom_parameters', {})
        
        if not geom_params:
            print("[WARNING] No geom_parameters found in solution_config.json")
        
        # Axis mapping: X=(1,0,0), Y=(0,1,0), Z=(0,0,1)
        axis_map = {
            (1, 0, 0): 'X',
            (0, 1, 0): 'Y',
            (0, 0, 1): 'Z'
        }
        
        param_ranges = {}
        for input_name in input_names:
            # Parse input name format: "param_name_translate_X" or "param_name_rotate_Z"
            # Try to match the format used in DesignPoints.csv generation
            found = False
            
            # Try to match each parameter in geom_params
            for base_param_name, param_data in geom_params.items():
                # Check if input_name starts with base_param_name
                if input_name.startswith(base_param_name):
                    # Check for translate
                    if '_translate_' in input_name:
                        axis_label = input_name.split('_translate_')[-1]
                        if 'translate' in param_data:
                            for trans in param_data['translate']:
                                if trans.get('enabled', False):
                                    # Check if axis matches
                                    direction = tuple(trans.get('direction', [0, 0, 0]))
                                    if axis_map.get(direction) == axis_label:
                                        param_ranges[input_name] = {
                                            'min': trans.get('min', 0),
                                            'max': trans.get('max', 0)
                                        }
                                        found = True
                                        print(f"  {input_name}: [{param_ranges[input_name]['min']}, {param_ranges[input_name]['max']}] (translate)")
                                        break
                    
                    # Check for rotate
                    elif '_rotate_' in input_name:
                        axis_label = input_name.split('_rotate_')[-1]
                        if 'rotate' in param_data:
                            for rot in param_data['rotate']:
                                if rot.get('enabled', False):
                                    # Check if axis matches
                                    axis = tuple(rot.get('axis', [0, 0, 1]))
                                    if axis_map.get(axis) == axis_label:
                                        param_ranges[input_name] = {
                                            'min': rot.get('min', 0),
                                            'max': rot.get('max', 0)
                                        }
                                        found = True
                                        print(f"  {input_name}: [{param_ranges[input_name]['min']}, {param_ranges[input_name]['max']}] (rotate)")
                                        break
                    
                    if found:
                        break
            
            # If not found, try direct match (for backward compatibility)
            if not found:
                if input_name in geom_params:
                    param_data = geom_params[input_name]
                    # Extract min/max from all enabled translate and rotate
                    mins, maxs = [], []
                    
                    if 'translate' in param_data:
                        for trans in param_data['translate']:
                            if trans.get('enabled', False):
                                mins.append(trans.get('min', 0))
                                maxs.append(trans.get('max', 0))
                    
                    if 'rotate' in param_data:
                        for rot in param_data['rotate']:
                            if rot.get('enabled', False):
                                mins.append(rot.get('min', 0))
                                maxs.append(rot.get('max', 0))
                    
                    if mins and maxs:
                        param_ranges[input_name] = {'min': min(mins), 'max': max(maxs)}
                        found = True
                        print(f"  {input_name}: [{param_ranges[input_name]['min']}, {param_ranges[input_name]['max']}] (combined)")
            
            # Fallback to default if still not found
            if not found:
                param_ranges[input_name] = {'min': -1.0, 'max': 1.0}
                print(f"[WARNING] Parameter {input_name} not found in solution config, using default: [-1.0, 1.0]")
        
        # Build bounds for optimization
        bounds = [(param_ranges[name]['min'], param_ranges[name]['max']) for name in input_names]
        
        print(f"[SUCCESS] Parameter ranges loaded for {len(bounds)} parameters")
        
        # 4. Helper functions for model prediction
        # Import create_polynomial_features from model
        from model import create_polynomial_features
        
        def predict_model(x):
            """Predict outputs using the loaded model."""
            try:
                x_array = np.array(x).reshape(1, -1)
                
                # Apply polynomial features if available
                # Note: poly_features is saved as True (flag), not the actual transformer
                if model_dict.get('poly_features'):
                    X_poly = create_polynomial_features(x_array, degree=2)
                else:
                    X_poly = x_array
                
                # Scale inputs
                if model_dict.get('X_scaler') is not None:
                    X_scaled = model_dict['X_scaler'].transform(X_poly)
                else:
                    X_scaled = X_poly
                
                # Feature selection if available
                if model_dict.get('feature_selector') is not None:
                    X_scaled = model_dict['feature_selector'].transform(X_scaled)
                
                # Predict
                if model_dict.get('ensemble_models') and len(model_dict['ensemble_models']) > 1:
                    ensemble_preds = [m.predict(X_scaled) for m in model_dict['ensemble_models']]
                    ensemble_preds = np.array(ensemble_preds)
                    weights = model_dict.get('ensemble_weights', np.ones(len(ensemble_preds)) / len(ensemble_preds))
                    Z_pred = np.average(ensemble_preds, axis=0, weights=weights)
                else:
                    Z_pred = model_dict['best_model'].predict(X_scaled)
                
                # Inverse PCA
                if model_dict.get('pca') is not None:
                    Y_pred_scaled = model_dict['pca'].inverse_transform(Z_pred)
                else:
                    Y_pred_scaled = Z_pred
                
                # Inverse output scaling
                if model_dict.get('Y_scaler') is not None:
                    Y_pred = model_dict['Y_scaler'].inverse_transform(Y_pred_scaled)
                else:
                    Y_pred = Y_pred_scaled
                
                return Y_pred[0]
            except Exception as e:
                print(f"[ERROR] Prediction failed: {e}")
                return np.zeros(len(output_names))
        
        def predict_with_uncertainty(x):
            """Predict outputs with uncertainty estimation (optimized to reuse preprocessing)."""
            try:
                prediction = predict_model(x)
                
                # Simple uncertainty estimation: use standard deviation across ensemble
                if model_dict.get('ensemble_models') and len(model_dict['ensemble_models']) > 1:
                    x_array = np.array(x).reshape(1, -1)
                    
                    # Reuse preprocessing from predict_model by doing it once
                    if model_dict.get('poly_features'):
                        X_poly = create_polynomial_features(x_array, degree=2)
                    else:
                        X_poly = x_array
                    
                    if model_dict.get('X_scaler') is not None:
                        X_scaled = model_dict['X_scaler'].transform(X_poly)
                    else:
                        X_scaled = X_poly
                    
                    if model_dict.get('feature_selector') is not None:
                        X_scaled = model_dict['feature_selector'].transform(X_scaled)
                    
                    # Predict with all ensemble models
                    ensemble_preds = [m.predict(X_scaled) for m in model_dict['ensemble_models']]
                    ensemble_preds = np.array(ensemble_preds)
                    
                    # Calculate uncertainty as std across ensemble
                    if model_dict.get('pca') is not None:
                        Y_preds_scaled = [model_dict['pca'].inverse_transform(p) for p in ensemble_preds]
                    else:
                        Y_preds_scaled = ensemble_preds
                    
                    if model_dict.get('Y_scaler') is not None:
                        Y_preds = [model_dict['Y_scaler'].inverse_transform(ys) for ys in Y_preds_scaled]
                    else:
                        Y_preds = Y_preds_scaled
                    
                    uncertainty = np.std(Y_preds, axis=0).mean()
                else:
                    # Fallback: use fixed uncertainty (faster)
                    uncertainty = 0.1
                
                return prediction, uncertainty
            except Exception as e:
                print(f"[ERROR] Uncertainty prediction failed: {e}")
                return predict_model(x), 0.1
        
        def calculate_gradient(x, step_size=0.01, target_output_idx=0, use_all_dims=True):
            """Calculate gradient using central difference method.
            
            Args:
                x: Input point
                step_size: Step size for finite difference
                target_output_idx: Index of output to optimize
                use_all_dims: If False, only calculate gradient for subset of dimensions (faster)
            """
            gradient = np.zeros(len(x))
            x_array = np.array(x)
            
            # For speed: if use_all_dims is False, only compute gradient for every other dimension
            dims_to_compute = range(len(x)) if use_all_dims else range(0, len(x), 2)
            
            for i in dims_to_compute:
                x_plus = x_array.copy()
                x_minus = x_array.copy()
                
                # Clamp to bounds
                x_plus[i] = min(x_plus[i] + step_size, bounds[i][1])
                x_minus[i] = max(x_minus[i] - step_size, bounds[i][0])
                
                pred_plus = predict_model(x_plus)
                pred_minus = predict_model(x_minus)
                
                if len(pred_plus) > target_output_idx:
                    gradient[i] = (pred_plus[target_output_idx] - pred_minus[target_output_idx]) / (2 * step_size)
            
            # If we skipped dimensions, interpolate
            if not use_all_dims and len(x) > 2:
                for i in range(len(x)):
                    if i not in dims_to_compute:
                        # Interpolate from neighbors
                        neighbors = [j for j in dims_to_compute if abs(j - i) <= 1]
                        if neighbors:
                            gradient[i] = np.mean([gradient[j] for j in neighbors])
            
            return gradient
        
        # Flag to track whether we're in optimization phase (fewer candidates = full gradient)
        optimization_phase = False
        
        def localization_objective(x, area_list=None):
            """Compute objective value for localization areas (lower is better)."""
            if not localization_enabled or not localization_areas:
                return None
            
            try:
                preds, _ = predict_with_uncertainty(x)
            except Exception:
                return None
            
            selected_areas = area_list if area_list is not None else localization_areas
            best_value = None
            
            for area in selected_areas:
                if not area:
                    continue
                target_type = area.get('target_type', 'maximum')
                output_param = area.get('output_parameter')
                resolved_name = resolve_output_name(output_param, output_names)
                if not resolved_name:
                    continue
                
                output_idx = output_names.index(resolved_name)
                if output_idx >= len(preds):
                    continue
                
                weight = max(area.get('weight', 1.0), 1e-6)
                
                if target_type == 'maximum':
                    value = -preds[output_idx] / weight
                elif target_type == 'minimum':
                    value = preds[output_idx] / weight
                elif target_type == 'target_value':
                    target_value = area.get('target_value', 0.0)
                    value = abs(preds[output_idx] - target_value) / weight
                else:
                    continue
                
                if best_value is None or value < best_value:
                    best_value = value
            
            return best_value
        
        def acquisition_function(x, skip_gradient=False):
            """Calculate acquisition function value at point x.
            
            Args:
                skip_gradient: If True, skip gradient calculation entirely (much faster)
            """
            try:
                # Get predictions and uncertainty
                predictions, uncertainty = predict_with_uncertainty(x)
                
                # Calculate gradient magnitude (for first output or average)
                # Skip gradient during pre-sampling for speed (use uncertainty only)
                gradient_magnitude = 0.0
                if not skip_gradient and len(output_names) > 0:
                    # Only compute gradient during optimization phase
                    if optimization_phase:
                        gradient = calculate_gradient(x, target_output_idx=0, use_all_dims=True)
                        gradient_magnitude = np.linalg.norm(gradient)
                
                # Apply localization if enabled
                if localization_enabled and localization_areas:
                    total_acquisition = 0.0
                    total_weight = 0.0
                    
                    for area in localization_areas:
                        weight = area.get('weight', 1.0)
                        output_param = area.get('output_parameter', output_names[0] if output_names else 'output')
                        target_type = area.get('target_type', 'maximum')
                        
                        # Find output index (resolve aliases/fuzzy)
                        resolved_name = resolve_output_name(output_param, output_names)
                        output_idx = output_names.index(resolved_name) if resolved_name in output_names else 0
                        
                        if output_idx < len(predictions):
                            param_pred = predictions[output_idx]
                            
                            # For pre-sampling (skip_gradient=True), use simpler acquisition based on prediction value
                            if skip_gradient:
                                # Simple acquisition based on predicted value and uncertainty
                                if target_type == 'maximum':
                                    # Favor high predicted values with high uncertainty
                                    area_acquisition = (param_pred * 0.7 + uncertainty * 0.3) * weight
                                elif target_type == 'minimum':
                                    # Favor low predicted values with high uncertainty
                                    # Normalize prediction to 0-1 range for better scaling, then invert
                                    # Use strong negative weight to ensure low values dominate
                                    # Assuming predictions are normalized or can be scaled
                                    # For minimum: higher acquisition = lower predicted value
                                    # Use exponential decay to strongly favor low values
                                    area_acquisition = (uncertainty * 0.3 - param_pred * 1.5) * weight
                                elif target_type == 'target_value':
                                    target_value = area.get('target_value', 0.0)
                                    distance_to_target = abs(param_pred - target_value)
                                    # Favor points close to target with high uncertainty
                                    area_acquisition = (uncertainty / (1.0 + distance_to_target)) * weight
                                else:
                                    area_acquisition = uncertainty * weight
                            else:
                                # Full acquisition with gradient (during optimization)
                                area_gradient = calculate_gradient(x, target_output_idx=output_idx, use_all_dims=True)
                                area_gradient_magnitude = np.linalg.norm(area_gradient)
                                
                                # Get current prediction to check gradient direction
                                current_pred = param_pred
                                
                                if len(area_gradient) > 0:
                                    if target_type == 'maximum':
                                        # Favor high gradient magnitude AND high predicted value
                                        # Move in direction of positive gradient (uphill)
                                        directional_gradient = area_gradient_magnitude
                                        area_acquisition = (acquisition_weights['gradient_weight'] * directional_gradient + 
                                                          acquisition_weights['variance_weight'] * uncertainty +
                                                          0.5 * current_pred) * 1.2
                                    elif target_type == 'minimum':
                                        # For minimum: we want to move in direction that DECREASES output
                                        # Calculate a "downhill" component: favor points where we can move to lower values
                                        # The gradient points in direction of increase, so for minimum we want:
                                        # 1. High gradient magnitude (steep slope = potential for big improvement)
                                        # 2. Negative direction (going downhill)
                                        # 3. Low predicted value (already near minimum)
                                        
                                        # Calculate "downhill potential": how much we can decrease by moving opposite gradient
                                        # Use negative of gradient dot product with itself (scaled) to favor downhill movement
                                        # For minimum, we want to maximize: -gradient_magnitude (to go opposite direction)
                                        # But we still want exploration (uncertainty) and already-low values
                                        
                                        # Strongly favor low predicted values
                                        low_value_bonus = -2.0 * current_pred  # Strong penalty for high values
                                        
                                        # For gradient: we want to explore areas with steep slopes (high magnitude)
                                        # but we'll optimize in the negative gradient direction
                                        exploration_bonus = area_gradient_magnitude  # Still explore steep regions
                                        
                                        area_acquisition = (acquisition_weights['gradient_weight'] * exploration_bonus + 
                                                          acquisition_weights['variance_weight'] * uncertainty +
                                                          low_value_bonus) * 1.5
                                    elif target_type == 'target_value':
                                        target_value = area.get('target_value', 0.0)
                                        distance_to_target = abs(current_pred - target_value)
                                        area_acquisition = (acquisition_weights['gradient_weight'] * area_gradient_magnitude + 
                                                          acquisition_weights['variance_weight'] * uncertainty) * (1.0 / (1.0 + distance_to_target))
                                    else:
                                        area_acquisition = (acquisition_weights['gradient_weight'] * area_gradient_magnitude + 
                                                          acquisition_weights['variance_weight'] * uncertainty)
                                else:
                                    # Fallback if gradient calculation fails
                                    if target_type == 'minimum':
                                        area_acquisition = (uncertainty * 0.3 - param_pred * 1.5) * weight
                                    else:
                                        area_acquisition = uncertainty * weight
                            
                            total_acquisition += area_acquisition
                            total_weight += weight
                    
                    if total_weight > 0:
                        return total_acquisition / total_weight
                
                # Fallback: simple acquisition
                return (acquisition_weights['gradient_weight'] * gradient_magnitude + 
                       acquisition_weights['variance_weight'] * uncertainty)
                
            except Exception as e:
                print(f"[ERROR] Acquisition function failed: {e}")
                return 0.0
        
        def resolve_output_name(requested_name, available_names):
            """Resolve a possibly inexact output name to the closest available canonical name.
            Tries exact, case-insensitive, and fuzzy matching.
            """
            try:
                if not requested_name or not available_names:
                    return None
                # Exact match
                if requested_name in available_names:
                    return requested_name
                # Case-insensitive exact
                lower_map = {n.lower(): n for n in available_names}
                if requested_name.lower() in lower_map:
                    return lower_map[requested_name.lower()]
                # Simple fuzzy using difflib
                import difflib
                match = difflib.get_close_matches(requested_name, available_names, n=1, cutoff=0.6)
                if match:
                    return match[0]
            except Exception:
                pass
            return None

        # 5. Generate design points
        print(f"\n[4/6] Generating {number_of_dps} design points...")
        min_distance = diversity_settings['min_distance']
        distance_metric = diversity_settings.get('distance_metric', 'euclidean')
        
        # Normalize bounds for distance calculation
        bounds_array = np.array(bounds)
        range_sizes = bounds_array[:, 1] - bounds_array[:, 0]
        
        generated_points = []
        acquisition_values = []
        
        # Get optimization settings from config (with defaults for speed)
        optimization_settings = refinement_config.get('optimization_settings', {})
        
        # Handle None values (user chose to use defaults) by calculating them
        pre_samples_raw = optimization_settings.get('pre_samples', None)
        if pre_samples_raw is None:
            # Much fewer pre-samples for speed (was 5x, now 2x)
            n_samples = max(30, number_of_dps * 2)  # Reduced from 5x to 2x
        else:
            n_samples = pre_samples_raw
        
        max_optimize_raw = optimization_settings.get('max_optimize_candidates', None)
        if max_optimize_raw is None:
            # Optimize fewer candidates (was +5, now just top 3)
            n_optimize = min(3, number_of_dps)  # Reduced from +5 to max 3
        else:
            n_optimize = max_optimize_raw
        
        max_iter = optimization_settings.get('max_iterations', 15)  # Reduced from 25 to 15
        max_diversity_attempts = optimization_settings.get('max_diversity_attempts', 30)  # Reduced from 50 to 30
        
        # STEP 1: Find promising regions (for maximum/minimum/target_value targets)
        # If localization is enabled, first find the general area based on target_type
        promising_regions = []
        if localization_enabled and localization_areas:
            print(f"  Step 1: Finding promising regions for optimization targets...")
            for area in localization_areas:
                target_type = area.get('target_type', 'maximum')
                output_param = area.get('output_parameter')
                # Resolve to nearest known output name
                resolved_name = resolve_output_name(output_param, output_names)
                if not resolved_name:
                    continue
                output_idx = output_names.index(resolved_name)
                
                # Use differential evolution for global search
                from scipy.optimize import differential_evolution
                
                # Create objective function based on target_type
                if target_type == 'maximum':
                    print(f"    Searching for MAXIMUM {output_param}...")
                    def find_optimum_region(x):
                        """Find the point that maximizes the predicted output."""
                        preds, _ = predict_with_uncertainty(x)
                        if output_idx < len(preds):
                            return -preds[output_idx]  # Negative because we minimize
                        return 0.0
                
                elif target_type == 'minimum':
                    print(f"    Searching for MINIMUM {output_param}...")
                    def find_optimum_region(x):
                        """Find the point that minimizes the predicted output."""
                        preds, _ = predict_with_uncertainty(x)
                        if output_idx < len(preds):
                            return preds[output_idx]  # Positive, we minimize
                        return 0.0
                
                elif target_type == 'target_value':
                    target_value = area.get('target_value', 0.0)
                    print(f"    Searching for TARGET VALUE {output_param} = {target_value}...")
                    def find_optimum_region(x):
                        """Find the point closest to the target value."""
                        preds, _ = predict_with_uncertainty(x)
                        if output_idx < len(preds):
                            # Minimize distance to target
                            distance = abs(preds[output_idx] - target_value)
                            return distance
                        return float('inf')
                
                else:
                    # Unknown target type, skip
                    print(f"    [WARNING] Unknown target_type '{target_type}' for {output_param}, skipping global search")
                    continue
                
                # Run global optimization to find promising region
                result = differential_evolution(
                    find_optimum_region,
                    bounds,
                    maxiter=30,  # Enough to find general region
                    seed=42,
                    atol=1e-1,
                    tol=1e-1
                )
                
                if result.success:
                    optimal_point = result.x
                    optimal_pred, _ = predict_with_uncertainty(optimal_point)
                    if output_idx < len(optimal_pred):
                        if target_type == 'target_value':
                            distance = abs(optimal_pred[output_idx] - target_value)
                            print(f"    Found {target_type} region: predicted {output_param} = {optimal_pred[output_idx]:.6f} (distance to target: {distance:.6f})")
                        else:
                            print(f"    Found {target_type} region: predicted {output_param} = {optimal_pred[output_idx]:.6f}")
                        promising_regions.append({
                            'point': optimal_point,
                            'output_idx': output_idx,
                            'target_type': target_type,
                            'output_param': resolved_name,
                            'predicted_value': optimal_pred[output_idx],
                            'target_value': area.get('target_value') if target_type == 'target_value' else None,
                            'weight': area.get('weight', 1.0),
                            'area_ref': area
                        })
                else:
                    print(f"    [WARNING] Global search for {target_type} {output_param} did not converge")
        
        # STEP 1B: Direct local optimization for each localization area
        area_points_added = 0
        if localization_enabled and localization_areas:
            print("  Step 1b: Local optimization for localization areas...")
            from scipy.optimize import minimize
            
            for area in localization_areas:
                if len(generated_points) >= number_of_dps:
                    break
                
                resolved_name = resolve_output_name(area.get('output_parameter'), output_names)
                if not resolved_name:
                    continue
                
                # Use promising region as a starting point if available, else mid-point of bounds
                region_match = next((reg for reg in promising_regions if reg.get('area_ref') is area), None)
                if region_match:
                    start_point = np.array(region_match['point'])
                else:
                    start_point = np.array([(b[0] + b[1]) / 2.0 for b in bounds])
                
                def objective_fn(x):
                    value = localization_objective(x, [area])
                    if value is not None:
                        return value
                    return -acquisition_function(x, skip_gradient=False)
                
                try:
                    result = minimize(
                        objective_fn,
                        start_point,
                        method='L-BFGS-B',
                        bounds=bounds,
                        options={'maxiter': max_iter, 'ftol': 1e-3}
                    )
                    
                    if not result.success:
                        continue
                    
                    candidate_point = result.x
                    
                    # Diversity check
                    is_diverse = True
                    if generated_points:
                        normalized_point = (candidate_point - bounds_array[:, 0]) / range_sizes
                        normalized_existing = (np.array(generated_points) - bounds_array[:, 0]) / range_sizes
                        
                        if distance_metric == 'euclidean':
                            distances = np.linalg.norm(normalized_existing - normalized_point, axis=1)
                        else:
                            distances = np.sum(np.abs(normalized_existing - normalized_point), axis=1)
                        
                        if np.min(distances) < min_distance:
                            is_diverse = False
                    
                    if is_diverse:
                        generated_points.append(candidate_point.tolist())
                        acq_val = acquisition_function(candidate_point, skip_gradient=False)
                        acquisition_values.append(acq_val)
                        area_points_added += 1
                        print(f"    Added point for area '{area.get('name', resolved_name)}'")
                
                except Exception as e:
                    print(f"    [WARNING] Failed to optimize localization area '{area.get('name', resolved_name)}': {e}")
                    continue
        
        # STEP 2: Pre-sampling with focus on promising regions
        print(f"  Step 2: Pre-sampling {n_samples} candidate points (optimizing top {n_optimize})...")
        
        # Generate random candidates - SKIP GRADIENT during pre-sampling for speed
        optimization_phase = False  # Pre-sampling phase - no gradient
        candidates = []
        
        # If we have promising regions, focus some candidates around them
        if promising_regions:
            # 50% of candidates around promising regions, 50% random
            n_focused = n_samples // 2
            n_random = n_samples - n_focused
            
            # Get region tightness from config (default 0.15 = 15% of range, tighter than before)
            region_tightness = optimization_settings.get('region_tightness', 0.15)
            
            # Generate focused candidates around promising regions
            for region in promising_regions:
                region_point = region['point']
                for _ in range(n_focused // len(promising_regions)):
                    # Generate point near the promising region with configurable spread
                    candidate = []
                    for i in range(len(bounds)):
                        # Random point within region_tightness% of the range centered on promising region
                        center = region_point[i]
                        spread = (bounds[i][1] - bounds[i][0]) * region_tightness
                        candidate_val = np.random.normal(center, spread)
                        # Clamp to bounds
                        candidate.append(np.clip(candidate_val, bounds[i][0], bounds[i][1]))
                    acq_val = acquisition_function(candidate, skip_gradient=True)
                    candidates.append((candidate, acq_val))
            
            # Generate random candidates for the rest
            for _ in range(n_random):
                candidate = [np.random.uniform(bounds[i][0], bounds[i][1]) for i in range(len(bounds))]
                acq_val = acquisition_function(candidate, skip_gradient=True)
                candidates.append((candidate, acq_val))
        else:
            # No promising regions, use all random
            for _ in range(n_samples):
                candidate = [np.random.uniform(bounds[i][0], bounds[i][1]) for i in range(len(bounds))]
                acq_val = acquisition_function(candidate, skip_gradient=True)
                candidates.append((candidate, acq_val))
        
        # Sort by acquisition value
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        print(f"  Optimizing top {min(n_optimize, len(candidates))} candidates...")
        
        # Set optimization phase flag for full gradient calculation
        optimization_phase = True
        
        # Optimize top candidates and add if diverse enough
        optimized_count = 0
        for candidate, _ in candidates[:n_optimize]:
            try:
                # Use simpler, faster optimization with fewer iterations
                from scipy.optimize import minimize
                
                def objective_function(x):
                    loc_val = localization_objective(x)
                    if loc_val is not None:
                        return loc_val
                    return -acquisition_function(x, skip_gradient=False)
                
                # Try L-BFGS-B first (faster than differential evolution)
                result = minimize(
                    objective_function,
                    candidate,
                    method='L-BFGS-B',
                    bounds=bounds,
                    options={'maxiter': max_iter, 'ftol': 1e-2}
                )
                
                if not result.success:
                    # Fallback to differential evolution if L-BFGS-B fails
                    result = differential_evolution(
                        objective_function,
                        bounds,
                        maxiter=max_iter,
                        seed=42,
                        atol=1e-2,
                        tol=1e-2
                    )
                
                optimized_point = result.x
                acq_val = acquisition_function(optimized_point, skip_gradient=False)
                optimized_count += 1
                
                # Check diversity constraint
                is_diverse = True
                if generated_points:
                    # Normalize for distance calculation
                    normalized_point = (optimized_point - bounds_array[:, 0]) / range_sizes
                    normalized_existing = (np.array(generated_points) - bounds_array[:, 0]) / range_sizes
                    
                    if distance_metric == 'euclidean':
                        distances = np.linalg.norm(normalized_existing - normalized_point, axis=1)
                    else:  # manhattan
                        distances = np.sum(np.abs(normalized_existing - normalized_point), axis=1)
                    
                    min_existing_distance = np.min(distances)
                    if min_existing_distance < min_distance:
                        is_diverse = False
                
                if is_diverse:
                    generated_points.append(optimized_point.tolist())
                    acquisition_values.append(acq_val)
                    print(f"  Added point {len(generated_points)}/{number_of_dps} (acq: {acq_val:.6f})")
                    
                    if len(generated_points) >= number_of_dps:
                        break
            
            except Exception as e:
                print(f"[WARNING] Optimization failed for a candidate: {e}")
                continue
        
        # If we don't have enough points, use remaining top candidates (fast approach)
        if len(generated_points) < number_of_dps:
            print(f"  Using additional top candidates to reach {number_of_dps} points...")
            for candidate, acq_val in candidates[n_optimize:]:
                if len(generated_points) >= number_of_dps:
                    break
                
                # Check diversity
                is_diverse = True
                if generated_points:
                    normalized_point = (np.array(candidate) - bounds_array[:, 0]) / range_sizes
                    normalized_existing = (np.array(generated_points) - bounds_array[:, 0]) / range_sizes
                    
                    if distance_metric == 'euclidean':
                        distances = np.linalg.norm(normalized_existing - normalized_point, axis=1)
                    else:
                        distances = np.sum(np.abs(normalized_existing - normalized_point), axis=1)
                    
                    if np.min(distances) < min_distance:
                        is_diverse = False
                
                if is_diverse:
                    generated_points.append(candidate)
                    acquisition_values.append(acq_val)
                    print(f"  Added point {len(generated_points)}/{number_of_dps} from top candidates")
        
        # If we still don't have enough points, generate random ones that satisfy diversity
        while len(generated_points) < number_of_dps:
            print(f"  Generating additional diverse point ({len(generated_points)+1}/{number_of_dps})...")
            found = False
            
            for attempt in range(max_diversity_attempts):
                candidate = [np.random.uniform(bounds[i][0], bounds[i][1]) for i in range(len(bounds))]
                
                # Check diversity
                is_diverse = True
                if generated_points:
                    normalized_point = (np.array(candidate) - bounds_array[:, 0]) / range_sizes
                    normalized_existing = (np.array(generated_points) - bounds_array[:, 0]) / range_sizes
                    
                    if distance_metric == 'euclidean':
                        distances = np.linalg.norm(normalized_existing - normalized_point, axis=1)
                    else:
                        distances = np.sum(np.abs(normalized_existing - normalized_point), axis=1)
                    
                    if np.min(distances) < min_distance:
                        is_diverse = False
                
                if is_diverse:
                    generated_points.append(candidate)
                    # Skip gradient for random points (use uncertainty only)
                    acq_val = acquisition_function(candidate, skip_gradient=True)
                    acquisition_values.append(acq_val)
                    found = True
                    break
            
            if not found:
                # Relax constraint if we can't find diverse points
                print(f"  [WARNING] Could not find diverse point, relaxing constraint...")
                min_distance *= 0.9
        
        print(f"[SUCCESS] Generated {len(generated_points)} design points")
        
        # 6. Save design points
        print("\n[5/6] Saving design points...")
        dps_dir = os.path.join(project_folder, "test_files", "dps")
        os.makedirs(dps_dir, exist_ok=True)
        
        # Create DataFrame (without Design Point column for consistency)
        df = pd.DataFrame(generated_points, columns=input_names)
        
        dps_path = os.path.join(dps_dir, "DesignPoints.csv")
        df.to_csv(dps_path, index=False)
        
        print(f"[SUCCESS] Design points saved to: {dps_path}")
        print(f"  Shape: {df.shape}")
        print(f"  Columns: {list(df.columns)}")
        
        print("\n[6/6] Summary:")
        print(f"  Generated: {len(generated_points)} design points")
        print(f"  Average acquisition value: {np.mean(acquisition_values):.6f}")
        print(f"  Min distance: {min_distance:.3f}")
        print(f"  Distance metric: {distance_metric}")
        
        return dps_path
        
    except Exception as e:
        print(f"[ERROR] Failed to create refinement design points: {e}")
        import traceback
        traceback.print_exc()
        return None


def final_file_move(project_folder):
    """
    Archive the latest refinement results into a new rif folder.

    This scans ``project_folder/test_files`` for existing ``rif_<index>_*`` archives,
    determines the next available rif index, and moves every file/folder in
    ``test_files`` (except the existing rif archives) into the new archive.
    Empty placeholder folders are recreated so the workflow can continue cleanly.

    Args:
        project_folder (str): Absolute path to the project root.

    Returns:
        str | bool: Path to the newly created rif folder on success, False on failure.
    """
    try:
        test_files_dir = os.path.join(project_folder, "test_files")
        if not os.path.isdir(test_files_dir):
            print(f"[ERROR] test_files directory not found: {test_files_dir}")
            return False

        existing_rif_dirs = []
        highest_index = -1

        for entry in os.listdir(test_files_dir):
            entry_path = os.path.join(test_files_dir, entry)
            if not os.path.isdir(entry_path):
                continue

            if entry.lower().startswith("rif_"):
                existing_rif_dirs.append(entry_path)
                parts = entry.split("_")
                if len(parts) >= 2:
                    try:
                        idx = int(parts[1])
                        highest_index = max(highest_index, idx)
                    except ValueError:
                        continue

        next_index = highest_index + 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_rif_name = f"rif_{next_index}_{timestamp}"
        new_rif_path = os.path.join(test_files_dir, new_rif_name)
        os.makedirs(new_rif_path, exist_ok=True)

        print(f"[INFO] Archiving refined results to {new_rif_name}/")

        moved_items = []
        for entry in os.listdir(test_files_dir):
            if entry.lower().startswith("rif_"):
                # Skip all existing rif archives (including the one we just created)
                continue

            source_path = os.path.join(test_files_dir, entry)
            destination_path = os.path.join(new_rif_path, entry)

            try:
                shutil.move(source_path, destination_path)
                moved_items.append((entry, os.path.isdir(destination_path)))
                print(f"[SUCCESS] Moved {entry} -> {new_rif_name}/{entry}")
            except Exception as exc:
                print(f"[WARNING] Failed to move {entry}: {exc}")

        # Recreate empty placeholders for moved directories so subsequent runs start cleanly
        for entry, was_directory in moved_items:
            if not was_directory:
                continue

            placeholder_path = os.path.join(test_files_dir, entry)
            try:
                os.makedirs(placeholder_path, exist_ok=True)
            except Exception as exc:
                print(f"[WARNING] Could not recreate placeholder for {entry}: {exc}")

        print(f"\n[SUCCESS] Final refinement files archived in: {new_rif_path}")
        if moved_items:
            moved_names = ", ".join(name for name, _ in moved_items)
            print(f"[INFO] Items archived: {moved_names}")
        else:
            print("[INFO] No refinement files were moved (test_files already empty).")

        return new_rif_path

    except Exception as exc:
        print(f"[ERROR] Failed to archive refinement files: {exc}")
        return False


def summerize_refinment_results(project_folder):
    """
    Aggregate refinement design points and summary outputs across all rif folders.

    Creates consolidated DesignPoints and summary2 CSVs under test_files/dps and
    test_files/out_final respectively, ensuring that input rows align with output columns.

    Args:
        project_folder (str): Absolute path to the project root.

    Returns:
        dict: Paths to the aggregated CSVs, or an empty dict on failure.
    """
    test_files_dir = os.path.join(project_folder, "test_files")
    if not os.path.isdir(test_files_dir):
        print(f"[ERROR] test_files directory not found: {test_files_dir}")
        return {}

    rif_dirs = []
    for entry in sorted(os.listdir(test_files_dir)):
        if entry.lower().startswith("rif_"):
            rif_path = os.path.join(test_files_dir, entry)
            if os.path.isdir(rif_path):
                rif_dirs.append(rif_path)

    if not rif_dirs:
        print("[WARNING] No refinement (rif_*) folders found to summarize.")
        return {}

    combined_inputs = []
    combined_outputs = None
    output_index = None
    global_dp_counter = 0

    for rif_path in rif_dirs:
        dps_path = os.path.join(rif_path, "dps", "DesignPoints.csv")
        summary_path = os.path.join(rif_path, "out_final", "summary2.csv")

        if not os.path.exists(dps_path) or not os.path.exists(summary_path):
            print(f"[INFO] Skipping {os.path.basename(rif_path)} (missing DesignPoints or summary2).")
            continue

        try:
            dp_df = pd.read_csv(dps_path)
        except Exception as exc:
            print(f"[WARNING] Failed to read {dps_path}: {exc}")
            continue

        try:
            summary_df = pd.read_csv(summary_path).set_index("Output Parameter")
        except Exception as exc:
            print(f"[WARNING] Failed to read {summary_path}: {exc}")
            continue

        # Read failed design points if they exist
        failed_dp_indices = set()
        failed_dp_path = os.path.join(rif_path, "dps", "failed_design_points.csv")
        if os.path.exists(failed_dp_path):
            try:
                failed_df = pd.read_csv(failed_dp_path)
                if 'design_point_index' in failed_df.columns:
                    failed_dp_indices = set(failed_df['design_point_index'].astype(int).tolist())
                    if failed_dp_indices:
                        print(f"[INFO] Found {len(failed_dp_indices)} failed design point(s) in {os.path.basename(rif_path)}: {sorted(failed_dp_indices)}")
            except Exception as exc:
                print(f"[WARNING] Failed to read failed_design_points.csv from {rif_path}: {exc}")

        # If no failed points found in dps folder, check out_final folder
        if not failed_dp_indices:
            failed_dp_summary_path = os.path.join(rif_path, "out_final", "failed_design_points_summary.csv")
            if os.path.exists(failed_dp_summary_path):
                try:
                    failed_summary_df = pd.read_csv(failed_dp_summary_path)
                    # Try different possible column names
                    dp_col = None
                    for col in ['Design Point', 'design_point_index', 'design_point', 'Design Point Index']:
                        if col in failed_summary_df.columns:
                            dp_col = col
                            break
                    if dp_col:
                        failed_dp_indices = set(failed_summary_df[dp_col].astype(int).tolist())
                        if failed_dp_indices:
                            print(f"[INFO] Found {len(failed_dp_indices)} failed design point(s) in {os.path.basename(rif_path)} (from summary): {sorted(failed_dp_indices)}")
                except Exception as exc:
                    print(f"[WARNING] Failed to read failed_design_points_summary.csv from {rif_path}: {exc}")

        # Filter out failed design points from DesignPoints.csv and summary2.csv
        if failed_dp_indices:
            original_dp_count = len(dp_df)
            original_col_count = summary_df.shape[1]
            
            # Filter DesignPoints.csv: rows are 0-indexed, so row index = design point index
            successful_mask = ~pd.Series(range(len(dp_df))).isin(failed_dp_indices)
            dp_df = dp_df[successful_mask].reset_index(drop=True)
            
            # Filter summary2.csv: columns are named like "out_0.txt", "out_1.txt", etc.
            # Extract design point index from column names and filter
            successful_columns = []
            for col in summary_df.columns:
                # Try to extract design point index from column name (e.g., "out_0.txt" -> 0)
                if isinstance(col, str) and col.startswith("out_") and col.endswith(".txt"):
                    try:
                        dp_idx = int(col.replace("out_", "").replace(".txt", ""))
                        if dp_idx not in failed_dp_indices:
                            successful_columns.append(col)
                    except ValueError:
                        # If we can't parse the index, include the column (safe fallback)
                        successful_columns.append(col)
                else:
                    # If column name doesn't match expected pattern (e.g., "Output Parameter"), include it
                    successful_columns.append(col)
            
            summary_df = summary_df[successful_columns]
            
            filtered_dp_count = original_dp_count - len(dp_df)
            filtered_col_count = original_col_count - summary_df.shape[1]
            
            if len(failed_dp_indices) > 0:
                print(f"[INFO] Filtered {filtered_dp_count} failed design point(s) from DesignPoints.csv (keeping {len(dp_df)}/{original_dp_count})")
                if filtered_col_count > 0:
                    print(f"[INFO] Filtered {filtered_col_count} failed design point(s) from summary2.csv (keeping {summary_df.shape[1]}/{original_col_count} columns)")

        if combined_outputs is None:
            combined_outputs = pd.DataFrame(index=summary_df.index)
            output_index = summary_df.index
        else:
            missing_outputs = summary_df.index.difference(output_index)
            if not missing_outputs.empty:
                print(f"[WARNING] Summary file in {rif_path} has unexpected outputs: {', '.join(missing_outputs)}")
            summary_df = summary_df.reindex(output_index)

        # Rename summary columns to maintain global alignment with design points
        renamed_columns = {}
        for column in summary_df.columns:
            new_name = f"out_{global_dp_counter}.txt"
            renamed_columns[column] = new_name
            global_dp_counter += 1

        summary_df = summary_df.rename(columns=renamed_columns)

        # Make sure the number of design points matches the number of output columns
        if len(dp_df) != summary_df.shape[1]:
            print(
                f"[WARNING] Mismatch in {os.path.basename(rif_path)}:"
                f" {len(dp_df)} design points vs {summary_df.shape[1]} output columns."
            )
            print(f"[WARNING] This may indicate inconsistent filtering. Attempting to align by column count...")
            # If there's a mismatch after filtering, align by minimum count
            min_count = min(len(dp_df), summary_df.shape[1])
            if min_count > 0:
                dp_df = dp_df.head(min_count)
                summary_df = summary_df.iloc[:, :min_count]
                print(f"[INFO] Aligned to {min_count} design points/columns for {os.path.basename(rif_path)}")
            else:
                print(f"[WARNING] Skipping {os.path.basename(rif_path)} - no data after alignment.")
                continue
        
        # Only append if we have successful design points
        if len(dp_df) > 0 and summary_df.shape[1] > 0:
            combined_inputs.append(dp_df)
            combined_outputs = pd.concat([combined_outputs, summary_df], axis=1)
        else:
            print(f"[WARNING] Skipping {os.path.basename(rif_path)} - no successful design points after filtering.")

    if not combined_inputs or combined_outputs is None:
        print("[WARNING] No refinement data found to summarize.")
        return {}

    # Save aggregated design points
    aggregated_inputs = pd.concat(combined_inputs, ignore_index=True)
    dps_output_dir = os.path.join(test_files_dir, "dps")
    os.makedirs(dps_output_dir, exist_ok=True)
    aggregated_dps_path = os.path.join(dps_output_dir, "DesignPoints.csv")
    aggregated_inputs.to_csv(aggregated_dps_path, index=False)

    # Save aggregated summary2
    out_final_dir = os.path.join(test_files_dir, "out_final")
    os.makedirs(out_final_dir, exist_ok=True)
    aggregated_summary_path = os.path.join(out_final_dir, "summary2.csv")
    combined_outputs = combined_outputs.reset_index()
    combined_outputs.rename(columns={"index": "Output Parameter"}, inplace=True)
    combined_outputs.to_csv(aggregated_summary_path, index=False)

    print("[SUCCESS] Refinement results summarized.")
    print(f"  Design points: {aggregated_dps_path}")
    print(f"  Summary2:      {aggregated_summary_path}")

    return {
        "design_points": aggregated_dps_path,
        "summary": aggregated_summary_path,
    }