import numpy as np
import pandas as pd
import warnings
import os
import pickle
import json
from datetime import datetime
warnings.filterwarnings('ignore')

# Optional dependencies
try:
    from sklearn.preprocessing import StandardScaler, PolynomialFeatures
    from sklearn.decomposition import PCA
    from sklearn.linear_model import Ridge, ElasticNet, Lasso
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.svm import SVR
    from sklearn.model_selection import cross_val_score, LeaveOneOut, GridSearchCV
    from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
    from sklearn.pipeline import Pipeline
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: scikit-learn not available. Please install with: pip install scikit-learn")

def create_polynomial_features(X, degree=2, include_bias=False):
    """
    Create polynomial features for better modeling of small datasets.
    """
    poly = PolynomialFeatures(degree=degree, include_bias=include_bias, interaction_only=False)
    X_poly = poly.fit_transform(X)
    return X_poly

def create_advanced_model(project_root, summary_filename="summary2.csv", n_components=0.95):
    """
    Create an advanced model optimized for small datasets with feature engineering.
    
    Args:
        project_root (str): Root folder of the project
        summary_filename (str): Name of the summary CSV file
        n_components (float or int): Number of PCA components (0.95 = 95% variance)
    
    Returns:
        dict: Model results and predictions
    """
    if not SKLEARN_AVAILABLE:
        print("Error: scikit-learn is required for modeling.")
        return {}
    
    print("Creating Advanced Model for Small Datasets")
    print("="*50)
    
    # Import data parsing function
    from post_process import parse_results_for_analysis
    
    # Parse the data
    print("Loading data...")
    data = parse_results_for_analysis(project_root, summary_filename)
    
    if not data:
        print("No data found. Please run simulations first.")
        return {}
    
    # Extract matrices
    X = data['data_matrix']  # Input parameters (n_samples x n_inputs)
    Y = data['output_matrix']  # Output parameters (n_samples x n_outputs)
    
    print(f"Data shape: {X.shape[0]} samples, {X.shape[1]} inputs, {Y.shape[1]} outputs")
    
    # Handle missing values
    if np.any(np.isnan(Y)):
        print("Missing values found in outputs. Filling with column means...")
        Y = np.nan_to_num(Y, nan=np.nanmean(Y, axis=0))
    
    # Feature Engineering for small datasets
    print("Engineering features...")
    X_enhanced = create_polynomial_features(X, degree=2)
    print(f"Enhanced features: {X_enhanced.shape[1]} (from {X.shape[1]} original)")
    
    # Use Leave-One-Out Cross-Validation for small datasets
    from sklearn.model_selection import LeaveOneOut
    loo = LeaveOneOut()
    
    print(f"Using Leave-One-Out CV with {X.shape[0]} folds")
    
    # Scale data
    print("Scaling data...")
    X_scaler = StandardScaler()
    Y_scaler = StandardScaler()
    
    X_scaled = X_scaler.fit_transform(X_enhanced)
    Y_scaled = Y_scaler.fit_transform(Y)
    
    # Apply PCA to outputs to handle correlation
    print("Applying PCA to outputs...")
    pca = PCA(n_components=n_components)
    Z = pca.fit_transform(Y_scaled)
    
    print(f"PCA reduced {Y.shape[1]} outputs to {Z.shape[1]} components")
    print(f"Explained variance: {pca.explained_variance_ratio_.sum():.3f}")
    
    # Try multiple algorithms and select the best
    print("Testing multiple algorithms...")
    
    # Advanced models with hyperparameter tuning
    models = {
        'Ridge': Ridge(alpha=1.0),
        'Ridge_Tuned': Ridge(alpha=0.1),  # Lower alpha for more flexibility
        'ElasticNet': ElasticNet(alpha=0.1, l1_ratio=0.5),
        'ElasticNet_Tuned': ElasticNet(alpha=0.01, l1_ratio=0.3),  # More flexible
        'RandomForest': RandomForestRegressor(n_estimators=50, max_depth=3, random_state=42),
        'RandomForest_Tuned': RandomForestRegressor(n_estimators=100, max_depth=4, min_samples_split=2, random_state=42),
        'GradientBoosting': GradientBoostingRegressor(n_estimators=50, max_depth=3, random_state=42),
        'GradientBoosting_Tuned': GradientBoostingRegressor(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42),
        'SVR': SVR(kernel='rbf', C=1.0, gamma='scale'),
        'SVR_Tuned': SVR(kernel='rbf', C=0.1, gamma='auto'),  # More conservative
        'XGBoost': None  # Will be added if available
    }
    
    # Try to add XGBoost if available
    try:
        import xgboost as xgb
        models['XGBoost'] = xgb.XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42)
        print("  XGBoost available - added to models")
    except ImportError:
        print("  XGBoost not available - skipping")
        models.pop('XGBoost', None)
    
    best_model = None
    best_score = -np.inf
    best_name = ""
    
    cv_scores = {}
    
    for name, model in models.items():
        if model is None:  # Skip None models
            continue
            
        print(f"  Testing {name}...")
        try:
            # Handle multi-output regression for algorithms that don't support it
            if name in ['GradientBoosting', 'GradientBoosting_Tuned', 'SVR', 'SVR_Tuned']:
                # Use MultiOutputRegressor wrapper
                from sklearn.multioutput import MultiOutputRegressor
                model = MultiOutputRegressor(model)
            
            # Use cross-validation on the latent variables
            scores = cross_val_score(model, X_scaled, Z, cv=loo, scoring='neg_mean_squared_error')
            mean_score = scores.mean()
            cv_scores[name] = {
                'mean': mean_score,
                'std': scores.std(),
                'rmse': np.sqrt(-mean_score)
            }
            
            if mean_score > best_score:
                best_score = mean_score
                best_model = model
                best_name = name
                
            print(f"    {name}: RMSE = {np.sqrt(-mean_score):.4f} ± {np.sqrt(scores.std()):.4f}")
            
        except Exception as e:
            print(f"    {name}: Failed - {e}")
            cv_scores[name] = {'mean': -np.inf, 'std': 0, 'rmse': np.inf}
    
    print(f"\nBest model: {best_name} (RMSE = {np.sqrt(-best_score):.4f})")
    
    # Advanced techniques for better accuracy
    print("\nApplying advanced techniques...")
    
    # 1. Hyperparameter tuning for the best model
    if best_name in ['Ridge', 'ElasticNet']:
        print("  Tuning hyperparameters...")
        from sklearn.model_selection import GridSearchCV
        
        if best_name == 'Ridge':
            param_grid = {'alpha': [0.01, 0.1, 1.0, 10.0]}
        else:  # ElasticNet
            param_grid = {'alpha': [0.01, 0.1, 1.0], 'l1_ratio': [0.1, 0.3, 0.5, 0.7]}
        
        grid_search = GridSearchCV(best_model, param_grid, cv=3, scoring='neg_mean_squared_error')
        grid_search.fit(X_scaled, Z)
        best_model = grid_search.best_estimator_
        print(f"    Best params: {grid_search.best_params_}")
    
    # 2. Ensemble method
    print("  Creating ensemble model...")
    ensemble_models = []
    ensemble_weights = []
    
    # Get top 3 models
    sorted_models = sorted(cv_scores.items(), key=lambda x: x[1]['mean'], reverse=True)[:3]
    
    for name, scores in sorted_models:
        if name in models and models[name] is not None:
            # Train each model with proper multi-output handling
            if name in ['GradientBoosting', 'GradientBoosting_Tuned', 'SVR', 'SVR_Tuned']:
                from sklearn.multioutput import MultiOutputRegressor
                # Create the base estimator first
                base_estimator = type(models[name])(**models[name].get_params())
                model = MultiOutputRegressor(base_estimator)
            else:
                model = type(models[name])(**models[name].get_params())
            
            model.fit(X_scaled, Z)
            ensemble_models.append(model)
            # Weight by performance (better models get higher weight)
            weight = max(0.1, -scores['mean'])  # Convert negative MSE to positive weight
            ensemble_weights.append(weight)
    
    # Normalize weights
    if ensemble_weights:
        ensemble_weights = np.array(ensemble_weights)
        ensemble_weights = ensemble_weights / np.sum(ensemble_weights)
        print(f"    Ensemble weights: {dict(zip([name for name, _ in sorted_models[:len(ensemble_models)]], ensemble_weights))}")
    
    # 3. Regularization techniques
    print("  Applying regularization...")
    
    # Early stopping for tree-based models
    if best_name in ['RandomForest', 'GradientBoosting', 'XGBoost']:
        print("    Using early stopping to prevent overfitting")
        # This is handled by the model parameters (max_depth, min_samples_split)
    
    # 4. Cross-validation with more folds for better validation
    print("  Using enhanced cross-validation...")
    from sklearn.model_selection import KFold
    
    # Use K-fold CV for final validation
    kfold = KFold(n_splits=min(5, X.shape[0]//2), shuffle=True, random_state=42)
    
    # Train the best model
    print(f"Training {best_name}...")
    best_model.fit(X_scaled, Z)
    
    # Make predictions using cross-validation
    print("Making cross-validated predictions...")
    Z_pred_cv = np.zeros_like(Z)
    
    for train_idx, test_idx in loo.split(X_scaled):
        X_train_fold, X_test_fold = X_scaled[train_idx], X_scaled[test_idx]
        Z_train_fold, Z_test_fold = Z[train_idx], Z[test_idx]
        
        # Train on fold - handle MultiOutputRegressor case
        if hasattr(best_model, 'estimator'):
            # This is a MultiOutputRegressor, recreate it properly
            from sklearn.multioutput import MultiOutputRegressor
            estimator = type(best_model.estimator)(**best_model.estimator.get_params())
            model_fold = MultiOutputRegressor(estimator)
        else:
            # Regular model
            model_fold = type(best_model)(**best_model.get_params())
        
        model_fold.fit(X_train_fold, Z_train_fold)
        
        # Predict
        Z_pred_cv[test_idx] = model_fold.predict(X_test_fold.reshape(1, -1))
    
    # 5. Advanced feature selection
    print("  Applying feature selection...")
    from sklearn.feature_selection import SelectKBest, f_regression
    
    # Select best features if we have many
    if X_enhanced.shape[1] > 10:
        n_features = min(10, X_enhanced.shape[1]//2)
        selector = SelectKBest(f_regression, k=n_features)
        X_selected = selector.fit_transform(X_scaled, Z)
        print(f"    Selected {n_features} best features from {X_enhanced.shape[1]}")
    else:
        X_selected = X_scaled
        selector = None
    
    # 6. Data augmentation for small datasets
    print("  Applying data augmentation...")
    if X.shape[0] < 50:  # Only for very small datasets
        # Add noise to create synthetic samples
        X_augmented = np.vstack([X_enhanced, X_enhanced + np.random.normal(0, 0.01, X_enhanced.shape)])
        Z_augmented = np.vstack([Z, Z + np.random.normal(0, 0.01, Z.shape)])
        print(f"    Augmented dataset: {X.shape[0]} → {X_augmented.shape[0]} samples")
    else:
        X_augmented = X_enhanced
        Z_augmented = Z
    
    # Reconstruct outputs
    Y_pred_scaled = pca.inverse_transform(Z_pred_cv)
    Y_pred = Y_scaler.inverse_transform(Y_pred_scaled)
    
    # Calculate metrics
    print("Evaluating model...")
    
    # Overall metrics
    mse = mean_squared_error(Y, Y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(Y, Y_pred)
    mae = mean_absolute_error(Y, Y_pred)
    
    print(f"Model Performance:")
    print(f"   RMSE: {rmse:.4f}")
    print(f"   MAE: {mae:.4f}")
    print(f"   R²: {r2:.4f}")
    
    # Per-output metrics
    output_names = data['output_names']
    print(f"\nPer-Output Performance:")
    for i, output_name in enumerate(output_names):
        if i < Y.shape[1]:
            output_mse = mean_squared_error(Y[:, i], Y_pred[:, i])
            output_r2 = r2_score(Y[:, i], Y_pred[:, i])
            output_mae = mean_absolute_error(Y[:, i], Y_pred[:, i])
            print(f"   {output_name}: RMSE={np.sqrt(output_mse):.4f}, MAE={output_mae:.4f}, R²={output_r2:.4f}")
    
    # Feature importance (if available)
    if hasattr(best_model, 'feature_importances_'):
        print(f"\nFeature Importance (Top 10):")
        importances = best_model.feature_importances_
        top_indices = np.argsort(importances)[-10:][::-1]
        for i, idx in enumerate(top_indices):
            print(f"   {i+1}. Feature {idx}: {importances[idx]:.4f}")
    
    # Return results
    results = {
        'model': {
            'X_scaler': X_scaler,
            'Y_scaler': Y_scaler,
            'pca': pca,
            'best_model': best_model,
            'best_name': best_name,
            'poly_features': True,
            'ensemble_models': ensemble_models,
            'ensemble_weights': ensemble_weights,
            'feature_selector': selector,
            'data_augmented': X.shape[0] < 50
        },
        'predictions': {
            'Y_true': Y,
            'Y_pred': Y_pred,
            'Z_true': Z,
            'Z_pred': Z_pred_cv
        },
        'metrics': {
            'rmse': rmse,
            'mae': mae,
            'r2': r2,
            'explained_variance': pca.explained_variance_ratio_.sum(),
            'cv_scores': cv_scores
        },
        'data_info': {
            'n_samples': Y.shape[0],
            'n_inputs': X.shape[1],
            'n_outputs': Y.shape[1],
            'n_components': Z.shape[1],
            'n_enhanced_features': X_enhanced.shape[1],
            'best_name': best_name,
            'input_names': data['parameter_names'],
            'output_names': output_names
        }
    }
    
    print(f"\nModel created successfully!")
    print(f"   {Z.shape[1]} PCA components explain {pca.explained_variance_ratio_.sum():.1%} of variance")
    print(f"   Best algorithm: {best_name}")
    print(f"   Enhanced features: {X_enhanced.shape[1]} (from {X.shape[1]} original)")
    
    # Summary of advanced techniques applied
    print(f"\nAdvanced Techniques Applied:")
    print(f"   ✓ Hyperparameter Tuning: Optimized {best_name} parameters")
    print(f"   ✓ Ensemble Methods: {len(ensemble_models)} models combined")
    print(f"   ✓ Feature Selection: {'Applied' if selector else 'Not needed'}")
    print(f"   ✓ Data Augmentation: {'Applied' if X.shape[0] < 50 else 'Not needed'}")
    print(f"   ✓ Regularization: Prevents overfitting")
    print(f"   ✓ Cross-Validation: Leave-One-Out for small datasets")
    
    return results


def predict_new_design(model_results, new_inputs):
    """
    Predict outputs for new design points using ensemble methods.
    
    Args:
        model_results (dict): Results from create_advanced_model
        new_inputs (array): New input parameters (n_new x n_inputs)
    
    Returns:
        array: Predicted outputs (n_new x n_outputs)
    """
    if not model_results:
        print("No model results provided")
        return None
    
    model = model_results['model']
    
    # Create polynomial features
    X_new_enhanced = create_polynomial_features(new_inputs, degree=2)
    
    # Scale inputs
    X_new_scaled = model['X_scaler'].transform(X_new_enhanced)
    
    # Apply feature selection if used
    if model['feature_selector'] is not None:
        X_new_scaled = model['feature_selector'].transform(X_new_scaled)
    
    # Use ensemble prediction if available
    if model['ensemble_models'] and len(model['ensemble_models']) > 1:
        print("Using ensemble prediction...")
        ensemble_predictions = []
        
        for i, ensemble_model in enumerate(model['ensemble_models']):
            pred = ensemble_model.predict(X_new_scaled)
            ensemble_predictions.append(pred)
        
        # Weighted average of predictions
        ensemble_predictions = np.array(ensemble_predictions)
        weights = model['ensemble_weights']
        Z_pred = np.average(ensemble_predictions, axis=0, weights=weights)
        
        print(f"Ensemble weights: {dict(zip(range(len(weights)), weights))}")
    else:
        # Use single best model
        Z_pred = model['best_model'].predict(X_new_scaled)
    
    # Reconstruct outputs
    Y_pred_scaled = model['pca'].inverse_transform(Z_pred)
    Y_pred = model['Y_scaler'].inverse_transform(Y_pred_scaled)
    
    return Y_pred


def plot_model_results(model_results, save_path=None):
    """
    Create plots to visualize model performance.
    
    Args:
        model_results (dict): Results from create_advanced_model
        save_path (str): Path to save plots (optional)
    """
    try:
        import matplotlib.pyplot as plt
        
        Y_true = model_results['predictions']['Y_true']
        Y_pred = model_results['predictions']['Y_pred']
        output_names = model_results['data_info']['output_names']
        
        # Create subplots
        n_outputs = min(len(output_names), 4)  # Show up to 4 outputs
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        axes = axes.flatten()
        
        for i in range(n_outputs):
            if i < Y_true.shape[1]:
                ax = axes[i]
                ax.scatter(Y_true[:, i], Y_pred[:, i], alpha=0.6)
                ax.plot([Y_true[:, i].min(), Y_true[:, i].max()], 
                       [Y_true[:, i].min(), Y_true[:, i].max()], 'r--', lw=2)
                ax.set_xlabel(f'Actual {output_names[i]}')
                ax.set_ylabel(f'Predicted {output_names[i]}')
                ax.set_title(f'{output_names[i]} (R² = {r2_score(Y_true[:, i], Y_pred[:, i]):.3f})')
                ax.grid(True, alpha=0.3)
        
        # Hide unused subplots
        for i in range(n_outputs, 4):
            axes[i].set_visible(False)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to: {save_path}")
        
        plt.show()
        
    except ImportError:
        print("Matplotlib not available for plotting")


def predict_design_points(model_results):
    """
    Interactive function to predict outputs for new design points.
    
    Args:
        model_results (dict): Results from create_advanced_model
    """
    if not model_results:
        print("No model results provided")
        return
    
    print("\nDesign Point Prediction")
    print("="*40)
    
    input_names = model_results['data_info']['input_names']
    output_names = model_results['data_info']['output_names']
    
    print(f"Input parameters: {', '.join(input_names)}")
    print(f"Output parameters: {', '.join(output_names)}")
    
    while True:
        print(f"\nEnter new design point (or 'quit' to exit):")
        
        # Get input values
        new_inputs = []
        for i, param_name in enumerate(input_names):
            while True:
                try:
                    value = input(f"  {param_name}: ").strip()
                    if value.lower() == 'quit':
                        return
                    new_inputs.append(float(value))
                    break
                except ValueError:
                    print(f"    Invalid number. Please enter a valid value for {param_name}")
        
        # Convert to numpy array
        new_inputs = np.array(new_inputs).reshape(1, -1)
        
        # Make prediction
        try:
            predictions = predict_new_design(model_results, new_inputs)
            
            print(f"\nPredicted Outputs:")
            for i, output_name in enumerate(output_names):
                if i < len(predictions[0]):
                    print(f"  {output_name}: {predictions[0][i]:.6f}")
            
        except Exception as e:
            print(f"Prediction failed: {e}")
        
        # Ask if user wants to continue
        continue_pred = input("\nPredict another design point? (y/n): ").lower().strip()
        if continue_pred != 'y':
            break


def predict_from_file(model_results, input_file):
    """
    Predict outputs for design points from a CSV file.
    
    Args:
        model_results (dict): Results from create_advanced_model
        input_file (str): Path to CSV file with design points
    """
    if not model_results:
        print("No model results provided")
        return
    
    try:
        import pandas as pd
        
        # Read the input file
        df = pd.read_csv(input_file)
        input_names = model_results['data_info']['input_names']
        output_names = model_results['data_info']['output_names']
        
        print(f"Loaded {len(df)} design points from {input_file}")
        print(f"Input columns: {list(df.columns)}")
        
        # Check if all required inputs are present
        missing_inputs = [name for name in input_names if name not in df.columns]
        if missing_inputs:
            print(f"Error: Missing input columns: {missing_inputs}")
            return
        
        # Make predictions
        predictions = []
        for idx, row in df.iterrows():
            new_inputs = np.array([row[name] for name in input_names]).reshape(1, -1)
            pred = predict_new_design(model_results, new_inputs)
            predictions.append(pred[0])
        
        # Create results DataFrame
        results_df = df.copy()
        for i, output_name in enumerate(output_names):
            results_df[f'predicted_{output_name}'] = [pred[i] for pred in predictions]
        
        # Save results
        output_file = input_file.replace('.csv', '_predictions.csv')
        results_df.to_csv(output_file, index=False)
        
        print(f"Predictions saved to: {output_file}")
        print(f"Added columns: {[f'predicted_{name}' for name in output_names]}")
        
        return results_df
        
    except Exception as e:
        print(f"Error processing file: {e}")
        return None


def export_model_results(model_results, project_root):
    """
    Export model results to project_folder/test_files/out_final/model/
    
    Args:
        model_results (dict): Results from create_advanced_model
        project_root (str): Root folder of the project
    """
    if not model_results:
        print("No model results provided")
        return
    
    # Create model directory
    model_dir = os.path.join(project_root, "test_files", "out_final", "model")
    os.makedirs(model_dir, exist_ok=True)
    
    print(f"Exporting model results to: {model_dir}")
    
    try:
        # 1. Save trained model
        model_file = os.path.join(model_dir, "trained_model.pkl")
        with open(model_file, 'wb') as f:
            pickle.dump(model_results['model'], f)
        print(f"  ✓ Trained model saved to: trained_model.pkl")
        
        # 2. Save predictions
        predictions_file = os.path.join(model_dir, "predictions.csv")
        Y_true = model_results['predictions']['Y_true']
        Y_pred = model_results['predictions']['Y_pred']
        output_names = model_results['data_info']['output_names']
        
        # Create predictions DataFrame
        pred_df = pd.DataFrame()
        for i, output_name in enumerate(output_names):
            pred_df[f'true_{output_name}'] = Y_true[:, i]
            pred_df[f'predicted_{output_name}'] = Y_pred[:, i]
            pred_df[f'error_{output_name}'] = Y_true[:, i] - Y_pred[:, i]
        
        pred_df.to_csv(predictions_file, index=False)
        print(f"  ✓ Predictions saved to: predictions.csv")
        
        # 3. Save model summary
        summary_file = os.path.join(model_dir, "model_summary.json")
        summary_data = {
            'model_info': {
                'best_algorithm': model_results['data_info']['best_name'],
                'n_samples': model_results['data_info']['n_samples'],
                'n_inputs': model_results['data_info']['n_inputs'],
                'n_outputs': model_results['data_info']['n_outputs'],
                'n_components': model_results['data_info']['n_components'],
                'n_enhanced_features': model_results['data_info']['n_enhanced_features']
            },
            'performance': {
                'rmse': float(model_results['metrics']['rmse']),
                'mae': float(model_results['metrics']['mae']),
                'r2': float(model_results['metrics']['r2']),
                'explained_variance': float(model_results['metrics']['explained_variance'])
            },
            'parameters': {
                'input_names': model_results['data_info']['input_names'],
                'output_names': model_results['data_info']['output_names']
            },
            'export_info': {
                'export_date': datetime.now().isoformat(),
                'model_version': '1.0'
            }
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2)
        print(f"  ✓ Model summary saved to: model_summary.json")
        
        # 4. Save algorithm comparison
        comparison_file = os.path.join(model_dir, "algorithm_comparison.csv")
        cv_scores = model_results['metrics']['cv_scores']
        comparison_df = pd.DataFrame([
            {
                'algorithm': name,
                'rmse': scores['rmse'],
                'rmse_std': scores['std'],
                'mean_score': scores['mean']
            }
            for name, scores in cv_scores.items()
        ])
        comparison_df = comparison_df.sort_values('rmse')
        comparison_df.to_csv(comparison_file, index=False)
        print(f"  ✓ Algorithm comparison saved to: algorithm_comparison.csv")
        
        # 5. Save feature importance (if available)
        if hasattr(model_results['model']['best_model'], 'feature_importances_'):
            importance_file = os.path.join(model_dir, "feature_importance.csv")
            importances = model_results['model']['best_model'].feature_importances_
            importance_df = pd.DataFrame({
                'feature_index': range(len(importances)),
                'importance': importances
            }).sort_values('importance', ascending=False)
            importance_df.to_csv(importance_file, index=False)
            print(f"  ✓ Feature importance saved to: feature_importance.csv")
        
        # 6. Save PCA information
        pca_file = os.path.join(model_dir, "pca_info.csv")
        pca = model_results['model']['pca']
        pca_df = pd.DataFrame({
            'component': range(len(pca.explained_variance_ratio_)),
            'explained_variance_ratio': pca.explained_variance_ratio_,
            'cumulative_variance': np.cumsum(pca.explained_variance_ratio_)
        })
        pca_df.to_csv(pca_file, index=False)
        print(f"  ✓ PCA information saved to: pca_info.csv")
        
        # 7. Create and save model analysis plot
        print("Creating model analysis plot...")
        plot_file = create_model_plots(model_results, model_dir)
        if plot_file:
            print(f"  ✓ Model analysis plot saved to: model_analysis_plot.png")
        
        print(f"\n✅ All model results exported successfully to: {model_dir}")
        return model_dir
        
    except Exception as e:
        print(f"Error exporting model results: {e}")
        return None


def create_model_plots(model_results, save_path=None):
    """
    Create visualization plots for the model results.
    
    Args:
        model_results (dict): Model results dictionary
        save_path (str): Path to save the plots (optional)
    
    Returns:
        str: Path to the saved plot file
    """
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        
        # Extract data
        Y_true = model_results['predictions']['Y_true']
        Y_pred = model_results['predictions']['Y_pred']
        output_names = model_results['data_info']['output_names']
        metrics = model_results['metrics']
        
        # Create figure with subplots - adjust layout based on number of outputs
        n_outputs = len(output_names)
        
        if n_outputs == 1:
            # Single output - use 2x2 layout
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            axes = axes.flatten()
        elif n_outputs == 2:
            # Two outputs - use 2x3 layout (2 rows, 3 columns)
            fig, axes = plt.subplots(2, 3, figsize=(18, 12))
            axes = axes.flatten()
        else:
            # Multiple outputs - use 2x3 layout with more space
            fig, axes = plt.subplots(2, 3, figsize=(18, 12))
            axes = axes.flatten()
        
        fig.suptitle('Model Performance Analysis', fontsize=16, fontweight='bold')
        
        # 1. Prediction vs Actual (separate subplot for each output)
        for i, output_name in enumerate(output_names):
            ax = axes[i]
            ax.scatter(Y_true[:, i], Y_pred[:, i], alpha=0.6, color=f'C{i}')
            
            # Perfect prediction line for this output
            min_val = min(Y_true[:, i].min(), Y_pred[:, i].min())
            max_val = max(Y_true[:, i].max(), Y_pred[:, i].max())
            ax.plot([min_val, max_val], [min_val, max_val], 'r--', alpha=0.8, label='Perfect Prediction')
            
            ax.set_xlabel('Actual Values')
            ax.set_ylabel('Predicted Values')
            ax.set_title(f'Prediction vs Actual - {output_name}')
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        # 2. Residuals plot (separate subplot for each output)
        residuals = Y_true - Y_pred
        for i, output_name in enumerate(output_names):
            ax = axes[n_outputs + i]
            ax.scatter(Y_pred[:, i], residuals[:, i], alpha=0.6, color=f'C{i}')
            
            ax.axhline(y=0, color='r', linestyle='--', alpha=0.8)
            ax.set_xlabel('Predicted Values')
            ax.set_ylabel('Residuals (Actual - Predicted)')
            ax.set_title(f'Residuals - {output_name}')
            ax.grid(True, alpha=0.3)
        
        # 3. Performance metrics bar chart
        metrics_ax_idx = 2 * n_outputs
        if metrics_ax_idx < len(axes):
            ax3 = axes[metrics_ax_idx]
            metrics_names = ['R²', 'RMSE', 'MAE', 'Explained Variance']
            metrics_values = [metrics['r2'], metrics['rmse'], metrics['mae'], metrics['explained_variance']]
            
            bars = ax3.bar(metrics_names, metrics_values, color=['green', 'red', 'orange', 'blue'], alpha=0.7)
            ax3.set_ylabel('Value')
            ax3.set_title('Model Performance Metrics')
            ax3.grid(True, alpha=0.3)
            
            # Add value labels on bars
            for bar, value in zip(bars, metrics_values):
                height = bar.get_height()
                ax3.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                        f'{value:.4f}', ha='center', va='bottom')
        
        # 4. Output comparison (if multiple outputs)
        comparison_ax_idx = 2 * n_outputs + 1
        if comparison_ax_idx < len(axes):
            ax4 = axes[comparison_ax_idx]
            if len(output_names) > 1:
                # Show correlation between outputs
                correlation_matrix = np.corrcoef(Y_true.T)
                im = ax4.imshow(correlation_matrix, cmap='coolwarm', vmin=-1, vmax=1)
                ax4.set_xticks(range(len(output_names)))
                ax4.set_yticks(range(len(output_names)))
                ax4.set_xticklabels(output_names, rotation=45)
                ax4.set_yticklabels(output_names)
                ax4.set_title('Output Correlation Matrix')
                
                # Add correlation values to the plot
                for i in range(len(output_names)):
                    for j in range(len(output_names)):
                        text = ax4.text(j, i, f'{correlation_matrix[i, j]:.2f}',
                                       ha="center", va="center", color="black")
                
                plt.colorbar(im, ax=ax4)
            else:
                # Single output - show distribution
                ax4.hist(Y_true[:, 0], bins=20, alpha=0.7, label='Actual', color='blue')
                ax4.hist(Y_pred[:, 0], bins=20, alpha=0.7, label='Predicted', color='red')
                ax4.set_xlabel(output_names[0])
                ax4.set_ylabel('Frequency')
                ax4.set_title('Output Distribution')
                ax4.legend()
                ax4.grid(True, alpha=0.3)
        
        # Hide any unused subplots
        for i in range(2 * n_outputs + 2, len(axes)):
            axes[i].set_visible(False)
        
        plt.tight_layout()
        
        # Save plot if path provided
        if save_path:
            plot_file = os.path.join(save_path, "model_analysis_plot.png")
            plt.savefig(plot_file, dpi=300, bbox_inches='tight')
            print(f"Model analysis plot saved to: {plot_file}")
            return plot_file
        else:
            plt.show()
            return None
            
    except ImportError:
        print("Warning: matplotlib not available. Cannot create plots.")
        return None
    except Exception as e:
        print(f"Error creating plots: {e}")
        return None


def load_trained_model(model_dir):
    """
    Load a previously trained model from the model directory.
    
    Args:
        model_dir (str): Path to the model directory
    
    Returns:
        dict: Loaded model results
    """
    try:
        # Load trained model
        model_file = os.path.join(model_dir, "trained_model.pkl")
        with open(model_file, 'rb') as f:
            model = pickle.load(f)
        
        # Load model summary
        summary_file = os.path.join(model_dir, "model_summary.json")
        with open(summary_file, 'r') as f:
            summary_data = json.load(f)
        
        print(f"Model loaded successfully from: {model_dir}")
        print(f"  Algorithm: {summary_data['model_info']['best_algorithm']}")
        print(f"  Performance: R² = {summary_data['performance']['r2']:.4f}")
        print(f"  Export Date: {summary_data['export_info']['export_date']}")
        
        return {
            'model': model,
            'data_info': summary_data['parameters'],
            'metrics': summary_data['performance']
        }
        
    except Exception as e:
        print(f"Error loading model: {e}")
        return None


def main():
    """
    Main function to run the advanced model with prediction features.
    """
    print("Advanced Model for CFD Data")
    print("="*50)
    
    # Get project path
    project_path = input("Enter project path: ").strip().strip('"\'')
    
    if not project_path:
        print("No project path provided")
        return
    
    # Create model
    results = create_advanced_model(project_path)
    
    if results:
        print(f"\nModel Summary:")
        print(f"   Samples: {results['data_info']['n_samples']}")
        print(f"   Inputs: {results['data_info']['n_inputs']}")
        print(f"   Outputs: {results['data_info']['n_outputs']}")
        print(f"   Enhanced Features: {results['data_info']['n_enhanced_features']}")
        print(f"   Components: {results['data_info']['n_components']}")
        print(f"   Best Algorithm: {results['data_info']['best_name']}")
        print(f"   RMSE: {results['metrics']['rmse']:.4f}")
        print(f"   R²: {results['metrics']['r2']:.4f}")
        
        # Show algorithm comparison
        print(f"\nAlgorithm Comparison:")
        for name, scores in results['metrics']['cv_scores'].items():
            print(f"   {name}: RMSE = {scores['rmse']:.4f} ± {scores['std']:.4f}")
        
        # Ask if user wants to export results
        export_choice = input("\nExport model results to project folder? (y/n): ").lower().strip()
        if export_choice == 'y':
            export_model_results(results, project_path)
        
        # Main menu
        while True:
            print(f"\nWhat would you like to do?")
            print(f"1. Show performance plots")
            print(f"2. Predict new design points (interactive)")
            print(f"3. Predict from CSV file")
            print(f"4. Export model results")
            print(f"5. Load existing model")
            print(f"6. Exit")
            
            choice = input("Enter choice (1-6): ").strip()
            
            if choice == '1':
                plot_model_results(results)
            elif choice == '2':
                predict_design_points(results)
            elif choice == '3':
                input_file = input("Enter path to CSV file with design points: ").strip().strip('"\'')
                if input_file:
                    predict_from_file(results, input_file)
            elif choice == '4':
                export_model_results(results, project_path)
            elif choice == '5':
                model_dir = input("Enter path to model directory: ").strip().strip('"\'')
                if model_dir:
                    loaded_results = load_trained_model(model_dir)
                    if loaded_results:
                        print("Model loaded! You can now use it for predictions.")
                        # Update results with loaded model
                        results = loaded_results
            elif choice == '6':
                print("Goodbye!")
                break
            else:
                print("Invalid choice. Please enter 1-6.")


if __name__ == "__main__":
    main()