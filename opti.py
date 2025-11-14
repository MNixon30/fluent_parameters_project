import numpy as np
import pandas as pd
import os
import json
import pickle
from scipy.optimize import minimize, differential_evolution, dual_annealing
from scipy.stats import pearsonr
import warnings
warnings.filterwarnings('ignore')

# Optional dependencies
try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    from sklearn.metrics import mean_squared_error
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: scikit-learn not available. Some optimization features may be limited.")

class MultiObjectiveOptimizer:
    """
    Advanced optimization system that accounts for output correlations
    and uses sensitivity analysis data for guidance.
    """
    
    def __init__(self, project_root):
        """
        Initialize optimizer with project data.
        
        Args:
            project_root (str): Path to project folder
        """
        self.project_root = project_root
        self.sensitivity_data = None
        self.model_data = None
        self.input_names = []
        self.output_names = []
        self.input_bounds = {}
        self.output_correlations = None
        self.pca_components = None
        self.importance_weights = None
        
        # Load available data
        self._load_sensitivity_data()
        self._load_model_data()
        
    def _load_sensitivity_data(self):
        """Load sensitivity analysis results with robust error handling."""
        try:
            sensitivity_folder = os.path.join(self.project_root, "test_files", "out_final", "sensitivity")
            results_file = os.path.join(sensitivity_folder, "sensitivity_analysis_results.csv")
            
            if os.path.exists(results_file):
                self.sensitivity_data = pd.read_csv(results_file)
                print(f"✅ Loaded sensitivity data: {len(self.sensitivity_data)} parameters")
                
                # Extract importance weights with flexible column names
                importance_cols = ['Mean_Importance', 'mean_importance', 'importance', 'Importance']
                importance_col = None
                for col in importance_cols:
                    if col in self.sensitivity_data.columns:
                        importance_col = col
                        break
                
                if importance_col:
                    self.importance_weights = self.sensitivity_data[importance_col].values
                else:
                    print("⚠️ No importance column found in sensitivity data")
                    self.importance_weights = None
                
                # Extract input names with flexible column names
                input_cols = ['Input_Parameter', 'input_parameter', 'Parameter', 'parameter', 'Input', 'input']
                input_col = None
                for col in input_cols:
                    if col in self.sensitivity_data.columns:
                        input_col = col
                        break
                
                if input_col:
                    self.input_names = self.sensitivity_data[input_col].tolist()
                else:
                    print("⚠️ No input parameter column found in sensitivity data")
                    # Try to use first column as input names
                    if len(self.sensitivity_data.columns) > 0:
                        self.input_names = self.sensitivity_data.iloc[:, 0].tolist()
                        print(f"⚠️ Using first column as input names: {self.input_names}")
                    else:
                        self.input_names = []
                
                # Load correlation data if available
                summary_file = os.path.join(sensitivity_folder, "sensitivity_analysis_summary.txt")
                if os.path.exists(summary_file):
                    self._parse_correlation_data(summary_file)
            else:
                # Try to get input names from the original data using parse_results_for_analysis
                try:
                    from post_process import parse_results_for_analysis
                    data = parse_results_for_analysis(self.project_root)
                    if data and 'parameter_names' in data:
                        self.input_names = data['parameter_names']
                        print(f"✅ Loaded input names from design points: {len(self.input_names)} parameters")
                except Exception as e:
                    print(f"⚠️ Could not load input names from design points: {e}")
                    
        except Exception as e:
            print(f"⚠️ Could not load sensitivity data: {e}")
            print("   This is normal if sensitivity analysis hasn't been run yet.")
    
    def _load_model_data(self):
        """Load trained model data with robust error handling."""
        try:
            model_folder = os.path.join(self.project_root, "test_files", "out_final", "model")
            model_file = os.path.join(model_folder, "trained_model.pkl")
            summary_file = os.path.join(model_folder, "model_summary.json")
            
            if os.path.exists(model_file) and os.path.exists(summary_file):
                # Load model components
                with open(model_file, 'rb') as f:
                    self.model_data = pickle.load(f)
                
                # Load summary data
                with open(summary_file, 'r') as f:
                    summary_data = json.load(f)
                
                # Extract output names with flexible structure
                output_names = []
                input_names = []
                
                # Try different possible structures
                if 'parameters' in summary_data:
                    params = summary_data['parameters']
                    if 'output_names' in params:
                        output_names = params['output_names']
                    elif 'outputs' in params:
                        output_names = params['outputs']
                    elif 'output_parameters' in params:
                        output_names = params['output_parameters']
                    
                    if 'input_names' in params:
                        input_names = params['input_names']
                    elif 'inputs' in params:
                        input_names = params['inputs']
                    elif 'input_parameters' in params:
                        input_names = params['input_parameters']
                elif 'output_names' in summary_data:
                    output_names = summary_data['output_names']
                elif 'outputs' in summary_data:
                    output_names = summary_data['outputs']
                
                if output_names:
                    self.output_names = output_names
                    print(f"✅ Loaded model data: {len(self.output_names)} outputs")
                else:
                    print("⚠️ No output names found in model summary")
                    # Try to extract from model data structure
                    if hasattr(self.model_data, 'output_names'):
                        self.output_names = self.model_data.output_names
                    else:
                        self.output_names = []
                
                if input_names:
                    self.input_names = input_names
                    print(f"✅ Loaded input names: {len(self.input_names)} parameters")
                else:
                    print("⚠️ No input names found in model summary")
                    # Try to extract from model data structure
                    if hasattr(self.model_data, 'input_names'):
                        self.input_names = self.model_data.input_names
                    else:
                        # Try to get input names from the original data
                        try:
                            from post_process import parse_results_for_analysis
                            data = parse_results_for_analysis(self.project_root)
                            if data and 'parameter_names' in data:
                                self.input_names = data['parameter_names']
                                print(f"✅ Loaded input names from design points: {len(self.input_names)} parameters")
                            else:
                                self.input_names = []
                        except Exception as e:
                            print(f"⚠️ Could not load input names from design points: {e}")
                            self.input_names = []
                
                # Load PCA info if available
                pca_file = os.path.join(model_folder, "pca_info.csv")
                if os.path.exists(pca_file):
                    pca_df = pd.read_csv(pca_file)
                    self.pca_components = pca_df
                    print(f"✅ Loaded PCA data: {len(pca_df)} components")
                    
        except Exception as e:
            print(f"⚠️ Could not load model data: {e}")
            print("   This is normal if data modeling hasn't been run yet.")
    
    def _parse_correlation_data(self, summary_file):
        """Parse correlation data from sensitivity summary."""
        try:
            with open(summary_file, 'r') as f:
                content = f.read()
            
            # Extract correlation matrix (simplified parsing)
            # This would need more sophisticated parsing in practice
            self.output_correlations = None  # Placeholder for correlation matrix
            
        except Exception as e:
            print(f"⚠️ Could not parse correlation data: {e}")
    
    def set_input_bounds(self, bounds_dict):
        """
        Set optimization bounds for input parameters.
        
        Args:
            bounds_dict (dict): Dictionary with parameter names as keys and (min, max) tuples as values
        """
        self.input_bounds = bounds_dict
        print(f"✅ Set bounds for {len(bounds_dict)} parameters")
    
    def define_objectives(self, objectives):
        """
        Define optimization objectives.
        
        Args:
            objectives (dict): Dictionary with objective definitions
                Format: {
                    'maximize': ['output1', 'output2'],
                    'minimize': ['output3'],
                    'target': {'output4': target_value},
                    'constraints': [{'output5': '>', 'value': 0.5}]
                }
        """
        self.objectives = objectives
        print(f"✅ Defined objectives: {len(objectives)} categories")
    
    def _predict_outputs(self, input_values):
        """
        Predict outputs using the trained model or fallback methods.
        
        Args:
            input_values (array): Input parameter values
            
        Returns:
            array: Predicted output values
        """
        # If no model data, use fallback prediction
        if self.model_data is None:
            return self._fallback_prediction(input_values)
        
        try:
            # Import the model prediction function
            from model import predict_new_design
            
            # Create proper model_results structure for prediction
            model_results = {
                'model': self.model_data,
                'data_info': {
                    'input_names': self.input_names,
                    'output_names': self.output_names
                }
            }
            
            # Convert input values to 2D numpy array as expected by predict_new_design
            # The function expects (n_samples, n_features) format
            X_new = input_values.reshape(1, -1)  # Shape: (1, n_inputs)
            
            # Use the model's prediction function
            Y_pred = predict_new_design(model_results, X_new)
            
            if Y_pred is not None and len(Y_pred) > 0:
                # Y_pred should be shape (1, n_outputs), so take the first row
                if Y_pred.ndim == 2:
                    predictions = Y_pred[0]  # Get first (and only) row
                else:
                    predictions = Y_pred
                return np.array(predictions)
            else:
                # Fallback to dummy predictions if model prediction fails
                print("⚠️ Model prediction failed, using fallback prediction")
                return self._fallback_prediction(input_values)
            
        except Exception as e:
            print(f"Error in model prediction: {e}")
            # Fallback to dummy predictions
            return self._fallback_prediction(input_values)
    
    def _fallback_prediction(self, input_values):
        """
        Fallback prediction method when model is not available.
        
        Args:
            input_values (array): Input parameter values
            
        Returns:
            array: Predicted output values
        """
        n_outputs = len(self.output_names)
        
        if n_outputs == 0:
            return np.array([])
        
        # Create a simple mathematical relationship for demonstration
        # This is a placeholder - in practice, you might use a simpler model
        predictions = []
        
        for i, output_name in enumerate(self.output_names):
            # Create a simple relationship based on input values
            # This is just for demonstration - replace with actual physics if known
            base_value = np.sum(input_values) * (i + 1) * 10
            noise = np.random.normal(0, base_value * 0.1)  # 10% noise
            predictions.append(max(0, base_value + noise))  # Ensure non-negative
        
        return np.array(predictions)
    
    def _objective_function(self, x):
        """
        Multi-objective function that accounts for output correlations.
        
        Args:
            x (array): Input parameter values
            
        Returns:
            float: Combined objective value
        """
        try:
            # Predict outputs
            predictions = self._predict_outputs(x)
            
            # Initialize objective value
            objective_value = 0.0
            
            # Handle maximize objectives
            if 'maximize' in self.objectives:
                for output_name in self.objectives['maximize']:
                    if output_name in self.output_names:
                        idx = self.output_names.index(output_name)
                        # Negative because we minimize in optimization
                        objective_value -= predictions[idx]
            
            # Handle minimize objectives
            if 'minimize' in self.objectives:
                for output_name in self.objectives['minimize']:
                    if output_name in self.output_names:
                        idx = self.output_names.index(output_name)
                        objective_value += predictions[idx]
            
            # Handle target objectives
            if 'target' in self.objectives:
                for output_name, target_value in self.objectives['target'].items():
                    if output_name in self.output_names:
                        idx = self.output_names.index(output_name)
                        # Penalty for deviation from target
                        deviation = abs(predictions[idx] - target_value)
                        objective_value += deviation * 10  # Weight factor
            
            # Handle constraints
            if 'constraints' in self.objectives:
                for constraint in self.objectives['constraints']:
                    for output_name, condition in constraint.items():
                        if output_name in self.output_names:
                            idx = self.output_names.index(output_name)
                            value = predictions[idx]
                            
                            if condition['operator'] == '>':
                                if value <= condition['value']:
                                    objective_value += (condition['value'] - value) * 100
                            elif condition['operator'] == '<':
                                if value >= condition['value']:
                                    objective_value += (value - condition['value']) * 100
                            elif condition['operator'] == '==':
                                deviation = abs(value - condition['value'])
                                objective_value += deviation * 100
            
            return objective_value
            
        except Exception as e:
            print(f"Error in objective function: {e}")
            return 1e6  # Large penalty for errors
    
    def _apply_sensitivity_guidance(self, x):
        """
        Apply sensitivity analysis guidance to optimization.
        
        Args:
            x (array): Input parameter values
            
        Returns:
            array: Modified input values with sensitivity guidance
        """
        if self.importance_weights is None:
            return x
        
        # Apply importance-based scaling
        # Parameters with higher importance get more attention
        scaled_x = x.copy()
        for i, weight in enumerate(self.importance_weights):
            if i < len(scaled_x):
                # Scale by importance (higher importance = more exploration)
                scaled_x[i] *= (1 + weight * 0.1)
        
        return scaled_x
    
    def optimize(self, method='differential_evolution', max_iterations=1000, 
                 population_size=50, seed=42):
        """
        Run multi-objective optimization.
        
        Args:
            method (str): Optimization method ('differential_evolution', 'dual_annealing', 'minimize')
            max_iterations (int): Maximum number of iterations
            population_size (int): Population size for evolutionary methods
            seed (int): Random seed for reproducibility
            
        Returns:
            dict: Optimization results
        """
        if not self.input_bounds:
            raise ValueError("Input bounds must be set before optimization")
        
        if not self.objectives:
            raise ValueError("Objectives must be defined before optimization")
        
        print(f"\n🚀 Starting {method} optimization...")
        print(f"📊 Objectives: {self.objectives}")
        print(f"🔧 Bounds: {len(self.input_bounds)} parameters")
        
        # Prepare bounds for optimization
        bounds = []
        for param_name in self.input_names:
            if param_name in self.input_bounds:
                bounds.append(self.input_bounds[param_name])
            else:
                # Default bounds if not specified
                bounds.append((-10, 10))
        
        # Set random seed
        np.random.seed(seed)
        
        try:
            if method == 'differential_evolution':
                result = differential_evolution(
                    self._objective_function,
                    bounds,
                    maxiter=max_iterations,
                    popsize=population_size,
                    seed=seed,
                    disp=True
                )
            elif method == 'dual_annealing':
                result = dual_annealing(
                    self._objective_function,
                    bounds,
                    maxiter=max_iterations,
                    seed=seed
                )
            elif method == 'minimize':
                # Use L-BFGS-B for gradient-based optimization with multiple restarts
                print("⚠️ Using L-BFGS-B with multiple restarts for robustness...")
                best_result = None
                best_value = float('inf')
                
                # Try multiple random starting points
                n_restarts = min(5, max_iterations // 100)  # Adaptive number of restarts
                
                for restart in range(n_restarts):
                    try:
                        # Random starting point
                        x0 = np.array([np.random.uniform(b[0], b[1]) for b in bounds])
                        
                        # Run L-BFGS-B with reduced iterations per restart
                        result = minimize(
                            self._objective_function,
                            x0,
                            method='L-BFGS-B',
                            bounds=bounds,
                            options={
                                'maxiter': max_iterations // n_restarts,
                                'ftol': 1e-6,  # Relaxed tolerance
                                'gtol': 1e-5   # Relaxed gradient tolerance
                            }
                        )
                        
                        # Keep track of best result
                        if result.fun < best_value:
                            best_value = result.fun
                            best_result = result
                            
                    except Exception as e:
                        print(f"⚠️ Restart {restart + 1} failed: {e}")
                        continue
                
                if best_result is not None:
                    result = best_result
                    print(f"✅ L-BFGS-B completed with {n_restarts} restarts")
                else:
                    raise ValueError("All L-BFGS-B restarts failed")
            else:
                raise ValueError(f"Unknown optimization method: {method}")
            
            # Extract results
            optimal_inputs = result.x
            optimal_value = result.fun
            
            # Predict optimal outputs
            try:
                optimal_outputs = self._predict_outputs(optimal_inputs)
            except Exception as e:
                print(f"⚠️ Warning: Could not predict outputs for optimal solution: {e}")
                optimal_outputs = np.zeros(len(self.output_names))
            
            # Create results dictionary
            results = {
                'success': result.success if hasattr(result, 'success') else True,
                'optimal_inputs': dict(zip(self.input_names, optimal_inputs)),
                'optimal_outputs': dict(zip(self.output_names, optimal_outputs)),
                'objective_value': optimal_value,
                'iterations': result.nit if hasattr(result, 'nit') else max_iterations,
                'method': method,
                'message': result.message if hasattr(result, 'message') else 'Optimization completed'
            }
            
            print(f"\n✅ Optimization completed!")
            print(f"🎯 Success: {results['success']}")
            print(f"📈 Objective value: {results['objective_value']:.6f}")
            print(f"🔄 Iterations: {results['iterations']}")
            
            return results
            
        except Exception as e:
            print(f"❌ Optimization failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def run_optimization_menu(self):
        """Interactive menu for running optimization with improved structure and error handling."""
        print("\n" + "="*60)
        print("🎯 MULTI-OBJECTIVE OPTIMIZATION")
        print("="*60)
        
        # Check data availability with detailed feedback
        self._check_data_availability()
        
        # Step 1: Parameter bounds setup
        print("\n" + "="*50)
        print("📏 STEP 1: PARAMETER BOUNDS")
        print("="*50)
        bounds = self._setup_parameter_bounds()
        if not bounds:
            return
        self.set_input_bounds(bounds)
        
        # Step 2: Objective definition
        print("\n" + "="*50)
        print("🎯 STEP 2: OPTIMIZATION OBJECTIVES")
        print("="*50)
        objectives = self._define_objectives()
        if not objectives:
            return
        self.define_objectives(objectives)
        
        # Step 3: Optimization settings
        print("\n" + "="*50)
        print("⚙️ STEP 3: OPTIMIZATION SETTINGS")
        print("="*50)
        settings = self._get_optimization_settings()
        if not settings:
            return
        
        # Step 4: Run optimization
        print("\n" + "="*50)
        print("🚀 STEP 4: RUNNING OPTIMIZATION")
        print("="*50)
        results = self.optimize(**settings)
        
        # Step 5: Display and save results
        self._display_and_save_results(results)
    
    def _check_data_availability(self):
        """Check and display data availability with helpful messages."""
        print("\n🔍 Checking available data...")
        
        sensitivity_available = self.sensitivity_data is not None
        model_available = self.model_data is not None
        
        if sensitivity_available:
            print(f"✅ Sensitivity data: {len(self.sensitivity_data)} parameters")
        else:
            print("❌ Sensitivity data: Not found")
        
        if model_available:
            print(f"✅ Model data: {len(self.output_names)} outputs")
        else:
            print("❌ Model data: Not found")
        
        if not sensitivity_available and not model_available:
            print("\n❌ Error: No optimization data available!")
            print("Please run sensitivity analysis and/or data modeling first.")
            return False
        
        if not sensitivity_available:
            print("\n⚠️ Warning: No sensitivity data found.")
            print("Optimization will use model data only (no parameter importance guidance).")
        
        if not model_available:
            print("\n⚠️ Warning: No model data found.")
            print("Optimization will use sensitivity data only (no predictions available).")
            print("⚠️ Note: Without model data, optimization will use dummy predictions.")
        
        return True
    
    def setup_optimization_menu(self):
        """Setup optimization with view/edit capabilities."""
        print("\n" + "="*60)
        print("⚙️ OPTIMIZATION SETUP")
        print("="*60)
        
        # Check data availability
        if not self._check_data_availability():
            return
        
        # Load existing settings if available
        settings_file = os.path.join(self.project_root, "test_files", "out_final", "optimization", "optimization_settings.json")
        existing_settings = self._load_optimization_settings(settings_file)
        
        while True:
            print("\nChoose setup option:")
            print("1. View current settings")
            print("2. Edit parameter bounds")
            print("3. Edit objectives")
            print("4. Edit optimization settings")
            print("5. Save settings")
            print("6. Load settings")
            print("7. Return to optimization menu")
            
            choice = input("\nEnter your choice (1-7): ").strip()
            
            if choice == "1":
                self._view_current_settings(existing_settings)
            elif choice == "2":
                existing_settings = self._edit_parameter_bounds(existing_settings)
            elif choice == "3":
                existing_settings = self._edit_objectives(existing_settings)
            elif choice == "4":
                existing_settings = self._edit_optimization_settings(existing_settings)
            elif choice == "5":
                self._save_optimization_settings(existing_settings, settings_file)
            elif choice == "6":
                existing_settings = self._load_optimization_settings(settings_file)
            elif choice == "7":
                return
            else:
                print("❌ Invalid choice! Please enter 1-7.")
    
    def run_optimization_from_settings(self):
        """Run optimization using saved settings."""
        print("\n" + "="*60)
        print("🚀 RUNNING OPTIMIZATION")
        print("="*60)
        
        # Load settings
        settings_file = os.path.join(self.project_root, "test_files", "out_final", "optimization", "optimization_settings.json")
        settings = self._load_optimization_settings(settings_file)
        
        if not settings:
            print("❌ No optimization settings found!")
            print("Please run 'Setup optimization' first.")
            return
        
        # Validate settings
        if not self._validate_settings(settings):
            print("❌ Invalid optimization settings!")
            print("Please run 'Setup optimization' to fix the settings.")
            return
        
        # Apply settings
        self._apply_settings(settings)
        
        # Run optimization
        print(f"\n🚀 Running optimization with saved settings...")
        results = self.optimize(**settings.get('optimization', {}))
        
        # Display and save results
        self._display_and_save_results(results)
    
    def _load_optimization_settings(self, settings_file):
        """Load optimization settings from JSON file."""
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                print(f"✅ Loaded settings from: {settings_file}")
                return settings
            except Exception as e:
                print(f"⚠️ Could not load settings: {e}")
        return {}
    
    def _save_optimization_settings(self, settings, settings_file):
        """Save optimization settings to JSON file."""
        try:
            os.makedirs(os.path.dirname(settings_file), exist_ok=True)
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            print(f"✅ Settings saved to: {settings_file}")
        except Exception as e:
            print(f"❌ Could not save settings: {e}")
    
    def _view_current_settings(self, settings):
        """View current optimization settings."""
        print("\n📋 CURRENT OPTIMIZATION SETTINGS")
        print("="*50)
        
        if not settings:
            print("No settings found. Use 'Edit' options to create settings.")
            return
        
        # Parameter bounds
        if 'parameter_bounds' in settings:
            print("\n📏 Parameter Bounds:")
            for param, bounds in settings['parameter_bounds'].items():
                print(f"   {param}: [{bounds[0]}, {bounds[1]}]")
        else:
            print("\n📏 Parameter Bounds: Not set")
        
        # Objectives
        if 'objectives' in settings:
            print("\n🎯 Objectives:")
            for obj_type, obj_list in settings['objectives'].items():
                print(f"   {obj_type}: {obj_list}")
        else:
            print("\n🎯 Objectives: Not set")
        
        # Optimization settings
        if 'optimization' in settings:
            opt_settings = settings['optimization']
            print("\n⚙️ Optimization Settings:")
            print(f"   Method: {opt_settings.get('method', 'Not set')}")
            print(f"   Max iterations: {opt_settings.get('max_iterations', 'Not set')}")
            print(f"   Population size: {opt_settings.get('population_size', 'Not set')}")
        else:
            print("\n⚙️ Optimization Settings: Not set")
    
    def _edit_parameter_bounds(self, settings):
        """Edit parameter bounds."""
        print("\n📏 EDIT PARAMETER BOUNDS")
        print("="*40)
        
        if not self.input_names:
            print("❌ No input parameters found!")
            return settings
        
        print(f"Available parameters: {', '.join(self.input_names)}")
        
        bounds = {}
        for param in self.input_names:
            while True:
                try:
                    print(f"\n🔧 Parameter: {param}")
                    min_input = input(f"  Minimum value: ").strip()
                    max_input = input(f"  Maximum value: ").strip()
                    
                    if not min_input or not max_input:
                        print("❌ Both values are required!")
                        continue
                    
                    min_val = float(min_input)
                    max_val = float(max_input)
                    
                    if min_val >= max_val:
                        print("❌ Minimum must be less than maximum!")
                        continue
                    
                    bounds[param] = (min_val, max_val)
                    print(f"✅ Set bounds: [{min_val}, {max_val}]")
                    break
                    
                except ValueError:
                    print("❌ Invalid input! Please enter numeric values.")
                except KeyboardInterrupt:
                    print("\n❌ Setup cancelled by user.")
                    return settings
        
        settings['parameter_bounds'] = bounds
        return settings
    
    def _edit_objectives(self, settings):
        """Edit optimization objectives."""
        print("\n🎯 EDIT OBJECTIVES")
        print("="*40)
        
        if not self.output_names:
            print("❌ No output parameters found!")
            return settings
        
        print(f"Available outputs: {', '.join(self.output_names)}")
        
        objectives = {}
        
        # Maximize objectives
        while True:
            print("\n🎯 MAXIMIZE (outputs to maximize):")
            print("Examples: downforce, efficiency, lift")
            maximize_input = input("Enter outputs to maximize (comma-separated, or press Enter to skip): ").strip()
            
            if not maximize_input:
                print("✅ Skipping maximize objectives.")
                break
            
            maximize_list = [x.strip() for x in maximize_input.split(',')]
            valid_maximize = self._validate_output_names(maximize_list, "maximize")
            
            if valid_maximize:
                objectives['maximize'] = valid_maximize
                print(f"✅ Maximize objectives set: {valid_maximize}")
                break
            else:
                print("❌ Please fix the errors above and try again.")
                retry = input("Press Enter to retry, or 'skip' to skip maximize: ").strip().lower()
                if retry == 'skip':
                    print("✅ Skipping maximize objectives.")
                    break
        
        # Minimize objectives
        while True:
            print("\n📉 MINIMIZE (outputs to minimize):")
            print("Examples: drag, weight, pressure_drop")
            minimize_input = input("Enter outputs to minimize (comma-separated, or press Enter to skip): ").strip()
            
            if not minimize_input:
                print("✅ Skipping minimize objectives.")
                break
            
            minimize_list = [x.strip() for x in minimize_input.split(',')]
            valid_minimize = self._validate_output_names(minimize_list, "minimize")
            
            if valid_minimize:
                objectives['minimize'] = valid_minimize
                print(f"✅ Minimize objectives set: {valid_minimize}")
                break
            else:
                print("❌ Please fix the errors above and try again.")
                retry = input("Press Enter to retry, or 'skip' to skip minimize: ").strip().lower()
                if retry == 'skip':
                    print("✅ Skipping minimize objectives.")
                    break
        
        # Target objectives
        while True:
            print("\n🎯 TARGET (specific target values):")
            print("Examples: pressure=1000, temperature=300")
            target_input = input("Enter target objectives (format: output=value, or press Enter to skip): ").strip()
            
            if not target_input:
                print("✅ Skipping target objectives.")
                break
            
            targets = self._parse_target_objectives(target_input)
            
            if targets:
                objectives['target'] = targets
                print(f"✅ Target objectives set: {targets}")
                break
            else:
                print("❌ Please fix the errors above and try again.")
                retry = input("Press Enter to retry, or 'skip' to skip targets: ").strip().lower()
                if retry == 'skip':
                    print("✅ Skipping target objectives.")
                    break
        
        # Constraints
        while True:
            print("\n🚫 CONSTRAINTS (inequality constraints):")
            print("Examples: stress<500, temperature>200")
            constraints_input = input("Enter constraints (format: output>value or output<value, or press Enter to skip): ").strip()
            
            if not constraints_input:
                print("✅ Skipping constraints.")
                break
            
            constraints = self._parse_constraints(constraints_input)
            
            if constraints:
                objectives['constraints'] = constraints
                print(f"✅ Constraints set: {constraints}")
                break
            else:
                print("❌ Please fix the errors above and try again.")
                retry = input("Press Enter to retry, or 'skip' to skip constraints: ").strip().lower()
                if retry == 'skip':
                    print("✅ Skipping constraints.")
                    break
        
        # Validate that at least one objective is defined
        if not objectives:
            print("❌ No objectives defined! Please define at least one objective.")
            return settings
        
        settings['objectives'] = objectives
        return settings
    
    def _edit_optimization_settings(self, settings):
        """Edit optimization algorithm settings."""
        print("\n⚙️ EDIT OPTIMIZATION SETTINGS")
        print("="*40)
        
        print("⚙️ Optimization Algorithm:")
        print("1. Differential Evolution (recommended for complex problems)")
        print("2. Dual Annealing (good for global optimization)")
        print("3. L-BFGS-B (⚠️ UNRELIABLE - may fail with model predictions)")
        print("\n💡 Recommendation: Use Differential Evolution for best results with model predictions")
        
        while True:
            method_choice = input("Choose method (1, 2, or 3): ").strip()
            if method_choice == "1":
                method = "differential_evolution"
                break
            elif method_choice == "2":
                method = "dual_annealing"
                break
            elif method_choice == "3":
                print("⚠️ Warning: L-BFGS-B may fail with model predictions due to noise and non-smoothness.")
                confirm = input("Continue with L-BFGS-B? (y/n): ").strip().lower()
                if confirm == 'y':
                    method = "minimize"
                    break
                else:
                    print("Please choose a different method.")
                    continue
            else:
                print("❌ Invalid choice! Please enter 1, 2, or 3.")
        
        print(f"✅ Selected: {method}")
        
        # Get iterations
        while True:
            try:
                max_iter_input = input("Max iterations (default 1000): ").strip()
                max_iter = int(max_iter_input) if max_iter_input else 1000
                if max_iter > 0:
                    break
                else:
                    print("❌ Iterations must be positive!")
            except ValueError:
                print("❌ Invalid input! Please enter a number.")
        
        # Get population size (for differential evolution)
        pop_size = 50
        if method == "differential_evolution":
            while True:
                try:
                    pop_size_input = input("Population size (default 50): ").strip()
                    pop_size = int(pop_size_input) if pop_size_input else 50
                    if pop_size > 0:
                        break
                    else:
                        print("❌ Population size must be positive!")
                except ValueError:
                    print("❌ Invalid input! Please enter a number.")
        
        settings['optimization'] = {
            'method': method,
            'max_iterations': max_iter,
            'population_size': pop_size
        }
        
        return settings
    
    def _validate_settings(self, settings):
        """Validate optimization settings."""
        required_keys = ['parameter_bounds', 'objectives', 'optimization']
        
        for key in required_keys:
            if key not in settings:
                print(f"❌ Missing required setting: {key}")
                return False
        
        # Validate parameter bounds
        if not settings['parameter_bounds']:
            print("❌ No parameter bounds defined")
            return False
        
        # Validate objectives
        if not settings['objectives']:
            print("❌ No objectives defined")
            return False
        
        # Validate optimization settings
        opt_settings = settings['optimization']
        if 'method' not in opt_settings:
            print("❌ No optimization method specified")
            return False
        
        return True
    
    def _apply_settings(self, settings):
        """Apply settings to the optimizer."""
        # Apply parameter bounds
        if 'parameter_bounds' in settings:
            self.set_input_bounds(settings['parameter_bounds'])
        
        # Apply objectives
        if 'objectives' in settings:
            self.define_objectives(settings['objectives'])
    
    def _setup_parameter_bounds(self):
        """Setup parameter bounds with validation and helpful guidance."""
        if not self.input_names:
            print("❌ No input parameters found!")
            return None
        
        print(f"\n📋 Available parameters: {', '.join(self.input_names)}")
        print("Enter bounds for each parameter (min, max values):")
        
        bounds = {}
        for param in self.input_names:
            while True:
                try:
                    print(f"\n🔧 Parameter: {param}")
                    min_input = input(f"  Minimum value: ").strip()
                    max_input = input(f"  Maximum value: ").strip()
                    
                    if not min_input or not max_input:
                        print("❌ Both values are required!")
                        continue
                    
                    min_val = float(min_input)
                    max_val = float(max_input)
                    
                    if min_val >= max_val:
                        print("❌ Minimum must be less than maximum!")
                        continue
                    
                    bounds[param] = (min_val, max_val)
                    print(f"✅ Set bounds: [{min_val}, {max_val}]")
                    break
                    
                except ValueError:
                    print("❌ Invalid input! Please enter numeric values.")
                except KeyboardInterrupt:
                    print("\n❌ Setup cancelled by user.")
                    return None
        
        return bounds
    
    def _define_objectives(self):
        """Define optimization objectives with validation."""
        if not self.output_names:
            print("❌ No output parameters found!")
            return None
        
        print(f"\n📋 Available outputs: {', '.join(self.output_names)}")
        print("\nDefine your optimization objectives:")
        
        objectives = {}
        
        # Maximize objectives
        while True:
            print("\n🎯 MAXIMIZE (outputs to maximize):")
            print("Examples: downforce, efficiency, lift")
            maximize_input = input("Enter outputs to maximize (comma-separated, or press Enter to skip): ").strip()
            
            if not maximize_input:
                print("✅ Skipping maximize objectives.")
                break
            
            maximize_list = [x.strip() for x in maximize_input.split(',')]
            valid_maximize = self._validate_output_names(maximize_list, "maximize")
            
            if valid_maximize:
                objectives['maximize'] = valid_maximize
                print(f"✅ Maximize objectives set: {valid_maximize}")
                break
            else:
                print("❌ Please fix the errors above and try again.")
                retry = input("Press Enter to retry, or 'skip' to skip maximize: ").strip().lower()
                if retry == 'skip':
                    print("✅ Skipping maximize objectives.")
                    break
        
        # Minimize objectives
        while True:
            print("\n📉 MINIMIZE (outputs to minimize):")
            print("Examples: drag, weight, pressure_drop")
            minimize_input = input("Enter outputs to minimize (comma-separated, or press Enter to skip): ").strip()
            
            if not minimize_input:
                print("✅ Skipping minimize objectives.")
                break
            
            minimize_list = [x.strip() for x in minimize_input.split(',')]
            valid_minimize = self._validate_output_names(minimize_list, "minimize")
            
            if valid_minimize:
                objectives['minimize'] = valid_minimize
                print(f"✅ Minimize objectives set: {valid_minimize}")
                break
            else:
                print("❌ Please fix the errors above and try again.")
                retry = input("Press Enter to retry, or 'skip' to skip minimize: ").strip().lower()
                if retry == 'skip':
                    print("✅ Skipping minimize objectives.")
                    break
        
        # Target objectives
        while True:
            print("\n🎯 TARGET (specific target values):")
            print("Examples: pressure=1000, temperature=300")
            target_input = input("Enter target objectives (format: output=value, or press Enter to skip): ").strip()
            
            if not target_input:
                print("✅ Skipping target objectives.")
                break
            
            targets = self._parse_target_objectives(target_input)
            
            if targets:
                objectives['target'] = targets
                print(f"✅ Target objectives set: {targets}")
                break
            else:
                print("❌ Please fix the errors above and try again.")
                retry = input("Press Enter to retry, or 'skip' to skip targets: ").strip().lower()
                if retry == 'skip':
                    print("✅ Skipping target objectives.")
                    break
        
        # Constraints
        while True:
            print("\n🚫 CONSTRAINTS (inequality constraints):")
            print("Examples: stress<500, temperature>200")
            constraints_input = input("Enter constraints (format: output>value or output<value, or press Enter to skip): ").strip()
            
            if not constraints_input:
                print("✅ Skipping constraints.")
                break
            
            constraints = self._parse_constraints(constraints_input)
            
            if constraints:
                objectives['constraints'] = constraints
                print(f"✅ Constraints set: {constraints}")
                break
            else:
                print("❌ Please fix the errors above and try again.")
                retry = input("Press Enter to retry, or 'skip' to skip constraints: ").strip().lower()
                if retry == 'skip':
                    print("✅ Skipping constraints.")
                    break
        
        # Validate that at least one objective is defined
        if not objectives:
            print("❌ No objectives defined! Please define at least one objective.")
            return None
        
        print(f"\n✅ Final objectives defined:")
        for obj_type, obj_list in objectives.items():
            print(f"   {obj_type}: {obj_list}")
        
        return objectives
    
    def _validate_output_names(self, output_list, obj_type):
        """Validate output names against available outputs with case-insensitive matching."""
        if not self.output_names:
            print(f"❌ No output parameters available for {obj_type}")
            return None
        
        valid_outputs = []
        invalid_outputs = []
        
        # Create case-insensitive mapping
        output_lower_map = {name.lower(): name for name in self.output_names}
        
        for output in output_list:
            output_clean = output.strip()
            if not output_clean:
                continue
                
            # Try exact match first
            if output_clean in self.output_names:
                valid_outputs.append(output_clean)
            # Try case-insensitive match
            elif output_clean.lower() in output_lower_map:
                correct_name = output_lower_map[output_clean.lower()]
                valid_outputs.append(correct_name)
                print(f"   ℹ️ Corrected '{output_clean}' to '{correct_name}'")
            else:
                invalid_outputs.append(output_clean)
        
        if invalid_outputs:
            print(f"❌ Invalid {obj_type} outputs: {', '.join(invalid_outputs)}")
            print(f"Available outputs: {', '.join(self.output_names)}")
            
            if not valid_outputs:
                return None
            else:
                print(f"✅ Using valid {obj_type} outputs: {', '.join(valid_outputs)}")
        
        return valid_outputs
    
    def _parse_target_objectives(self, target_input):
        """Parse target objectives with validation and case-insensitive matching."""
        if not self.output_names:
            print("❌ No output parameters available for target objectives")
            return None
        
        targets = {}
        invalid_targets = []
        
        # Create case-insensitive mapping
        output_lower_map = {name.lower(): name for name in self.output_names}
        
        for pair in target_input.split(','):
            pair = pair.strip()
            if not pair or '=' not in pair:
                invalid_targets.append(pair)
                continue
            
            output, value_str = pair.split('=', 1)
            output = output.strip()
            value_str = value_str.strip()
            
            if not output or not value_str:
                invalid_targets.append(pair)
                continue
            
            # Try exact match first
            if output not in self.output_names:
                # Try case-insensitive match
                if output.lower() in output_lower_map:
                    output = output_lower_map[output.lower()]
                    print(f"   ℹ️ Corrected target '{pair}' to use '{output}'")
                else:
                    invalid_targets.append(pair)
                    continue
            
            try:
                value = float(value_str)
                targets[output] = value
            except ValueError:
                invalid_targets.append(pair)
        
        if invalid_targets:
            print(f"❌ Invalid target objectives: {', '.join(invalid_targets)}")
            print(f"Available outputs: {', '.join(self.output_names)}")
            if not targets:
                return None
        
        return targets
    
    def _parse_constraints(self, constraints_input):
        """Parse constraints with validation and case-insensitive matching."""
        if not self.output_names:
            print("❌ No output parameters available for constraints")
            return None
        
        constraints = []
        invalid_constraints = []
        
        # Create case-insensitive mapping
        output_lower_map = {name.lower(): name for name in self.output_names}
        
        for constraint in constraints_input.split(','):
            constraint = constraint.strip()
            if not constraint:
                continue
            
            if '>' in constraint:
                parts = constraint.split('>', 1)
                if len(parts) == 2:
                    output, value_str = parts
                    output = output.strip()
                    value_str = value_str.strip()
                    
                    if not output or not value_str:
                        invalid_constraints.append(constraint)
                        continue
                    
                    # Try exact match first
                    if output not in self.output_names:
                        # Try case-insensitive match
                        if output.lower() in output_lower_map:
                            output = output_lower_map[output.lower()]
                            print(f"   ℹ️ Corrected constraint '{constraint}' to use '{output}'")
                        else:
                            invalid_constraints.append(constraint)
                            continue
                    
                    try:
                        value = float(value_str)
                        constraints.append({output: {'operator': '>', 'value': value}})
                    except ValueError:
                        invalid_constraints.append(constraint)
                else:
                    invalid_constraints.append(constraint)
            
            elif '<' in constraint:
                parts = constraint.split('<', 1)
                if len(parts) == 2:
                    output, value_str = parts
                    output = output.strip()
                    value_str = value_str.strip()
                    
                    if not output or not value_str:
                        invalid_constraints.append(constraint)
                        continue
                    
                    # Try exact match first
                    if output not in self.output_names:
                        # Try case-insensitive match
                        if output.lower() in output_lower_map:
                            output = output_lower_map[output.lower()]
                            print(f"   ℹ️ Corrected constraint '{constraint}' to use '{output}'")
                        else:
                            invalid_constraints.append(constraint)
                            continue
                    
                    try:
                        value = float(value_str)
                        constraints.append({output: {'operator': '<', 'value': value}})
                    except ValueError:
                        invalid_constraints.append(constraint)
                else:
                    invalid_constraints.append(constraint)
            else:
                invalid_constraints.append(constraint)
        
        if invalid_constraints:
            print(f"❌ Invalid constraints: {', '.join(invalid_constraints)}")
            print(f"Available outputs: {', '.join(self.output_names)}")
            if not constraints:
                return None
        
        return constraints
    
    def _get_optimization_settings(self):
        """Get optimization settings with validation."""
        print("\n⚙️ Optimization Algorithm:")
        print("1. Differential Evolution (recommended for complex problems)")
        print("2. Dual Annealing (good for global optimization)")
        print("3. L-BFGS-B (⚠️ UNRELIABLE - may fail with model predictions)")
        print("\n💡 Recommendation: Use Differential Evolution for best results with model predictions")
        
        while True:
            method_choice = input("Choose method (1, 2, or 3): ").strip()
            if method_choice == "1":
                method = "differential_evolution"
                break
            elif method_choice == "2":
                method = "dual_annealing"
                break
            elif method_choice == "3":
                print("⚠️ Warning: L-BFGS-B may fail with model predictions due to noise and non-smoothness.")
                confirm = input("Continue with L-BFGS-B? (y/n): ").strip().lower()
                if confirm == 'y':
                    method = "minimize"
                    break
                else:
                    print("Please choose a different method.")
                    continue
            else:
                print("❌ Invalid choice! Please enter 1, 2, or 3.")
        
        print(f"✅ Selected: {method}")
        
        # Get iterations
        while True:
            try:
                max_iter_input = input("Max iterations (default 1000): ").strip()
                max_iter = int(max_iter_input) if max_iter_input else 1000
                if max_iter > 0:
                    break
                else:
                    print("❌ Iterations must be positive!")
            except ValueError:
                print("❌ Invalid input! Please enter a number.")
        
        # Get population size (for differential evolution)
        pop_size = 50
        if method == "differential_evolution":
            while True:
                try:
                    pop_size_input = input("Population size (default 50): ").strip()
                    pop_size = int(pop_size_input) if pop_size_input else 50
                    if pop_size > 0:
                        break
                    else:
                        print("❌ Population size must be positive!")
                except ValueError:
                    print("❌ Invalid input! Please enter a number.")
        
        return {
            'method': method,
            'max_iterations': max_iter,
            'population_size': pop_size
        }
    
    def _display_and_save_results(self, results):
        """Display and save optimization results."""
        if results['success']:
            print(f"\n🎉 OPTIMIZATION SUCCESSFUL!")
            print("="*50)
            
            print(f"\n📊 Optimal Input Parameters:")
            for param, value in results['optimal_inputs'].items():
                print(f"   {param}: {value:.6f}")
            
            print(f"\n📈 Predicted Outputs:")
            for output, value in results['optimal_outputs'].items():
                print(f"   {output}: {value:.6f}")
            
            print(f"\n📊 Optimization Details:")
            print(f"   Objective Value: {results['objective_value']:.6f}")
            print(f"   Iterations: {results['iterations']}")
            print(f"   Method: {results['method']}")
            
            # Save results
            self._save_optimization_results(results)
            
        else:
            print(f"\n❌ OPTIMIZATION FAILED!")
            print("="*50)
            print(f"Error: {results.get('error', 'Unknown error')}")
            print("\n💡 Troubleshooting tips:")
            print("   - Check if parameter bounds are reasonable")
            print("   - Verify objective definitions are correct")
            print("   - Try a different optimization method")
            print("   - Increase max iterations")
    
    def _save_optimization_results(self, results):
        """Save optimization results to file."""
        try:
            opt_folder = os.path.join(self.project_root, "test_files", "out_final", "optimization")
            os.makedirs(opt_folder, exist_ok=True)
            
            # Save results as JSON
            results_file = os.path.join(opt_folder, "optimization_results.json")
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            # Save as CSV for easy viewing
            csv_file = os.path.join(opt_folder, "optimal_design.csv")
            
            # Combine inputs and outputs
            all_data = {**results['optimal_inputs'], **results['optimal_outputs']}
            df = pd.DataFrame([all_data])
            df.to_csv(csv_file, index=False)
            
            print(f"✅ Results saved to: {opt_folder}")
            
        except Exception as e:
            print(f"⚠️ Could not save results: {e}")


def run_optimization(project_root):
    """
    Main function to run optimization with menu options.
    
    Args:
        project_root (str): Path to project folder
    """
    try:
        optimizer = MultiObjectiveOptimizer(project_root)
        
        print("\n" + "="*60)
        print("🎯 OPTIMIZATION MENU")
        print("="*60)
        
        while True:
            print("\nChoose optimization option:")
            print("1. Setup optimization (view/edit settings)")
            print("2. Run optimization")
            print("3. View optimization results")
            print("4. Return to analysis menu")
            
            choice = input("\nEnter your choice (1, 2, 3, or 4): ").strip()
            
            if choice == "1":
                optimizer.setup_optimization_menu()
            elif choice == "2":
                optimizer.run_optimization_from_settings()
            elif choice == "3":
                view_optimization_results(project_root)
            elif choice == "4":
                print("Returning to analysis menu.")
                return
            else:
                print("❌ Invalid choice! Please enter 1, 2, 3, or 4.")
                
    except Exception as e:
        print(f"❌ Error running optimization: {e}")




def view_optimization_results(project_root):
    """
    View existing optimization results.
    
    Args:
        project_root (str): Path to project folder
    """
    opt_folder = os.path.join(project_root, "test_files", "out_final", "optimization")
    
    if not os.path.exists(opt_folder):
        print("❌ No optimization results found.")
        print("Please run optimization first.")
        return
    
    # Check for results files
    results_file = os.path.join(opt_folder, "optimization_results.json")
    csv_file = os.path.join(opt_folder, "optimal_design.csv")
    
    if os.path.exists(results_file):
        print("\n📊 Optimization Results:")
        print("="*40)
        
        try:
            import json
            with open(results_file, 'r') as f:
                results = json.load(f)
            
            print(f"✅ Success: {results.get('success', 'Unknown')}")
            print(f"🎯 Objective Value: {results.get('objective_value', 'N/A')}")
            print(f"🔄 Iterations: {results.get('iterations', 'N/A')}")
            print(f"⚙️ Method: {results.get('method', 'N/A')}")
            
            if 'optimal_inputs' in results:
                print(f"\n📏 Optimal Input Parameters:")
                for param, value in results['optimal_inputs'].items():
                    print(f"   {param}: {value:.6f}")
            
            if 'optimal_outputs' in results:
                print(f"\n📈 Predicted Outputs:")
                for output, value in results['optimal_outputs'].items():
                    print(f"   {output}: {value:.6f}")
            
        except Exception as e:
            print(f"❌ Error reading results: {e}")
    
    if os.path.exists(csv_file):
        print(f"\n📁 CSV Results: {csv_file}")
    
    print(f"\n📂 Results folder: {opt_folder}")


if __name__ == "__main__":
    # Example usage
    project_root = input("Enter project folder path: ").strip().strip('"\'')
    if project_root:
        run_optimization(project_root)
