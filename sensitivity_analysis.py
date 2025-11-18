import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# Optional dependencies
try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.inspection import permutation_importance
    from sklearn.model_selection import cross_val_score
    from sklearn.metrics import r2_score, mean_squared_error
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: scikit-learn not available. Please install with: pip install scikit-learn")

try:
    import seaborn as sns
    SEABORN_AVAILABLE = True
except ImportError:
    SEABORN_AVAILABLE = False
    print("Warning: seaborn not available. Some plots may be less styled.")

def perform_sensitivity_analysis(project_root, n_bootstrap=50, variance_threshold=0.95, random_state=42):
    """
    Perform comprehensive sensitivity analysis following best-practice methodology:
    PCA → Surrogate → Importance → Aggregate
    
    Args:
        project_root (str): Path to the project folder
        n_bootstrap (int): Number of bootstrap iterations for uncertainty quantification
        variance_threshold (float): Fraction of variance to retain in PCA (default: 0.95)
        random_state (int): Random seed for reproducibility
    
    Returns:
        dict: Complete sensitivity analysis results
    """
    if not SKLEARN_AVAILABLE:
        print("❌ Error: scikit-learn is required for sensitivity analysis.")
        print("Please install with: pip install scikit-learn")
        return {}
    
    print("🔬 Starting Comprehensive Sensitivity Analysis")
    print("="*60)
    
    # Step 1: Prepare data using post-processing functions
    from post_process import parse_results_for_analysis
    
    print("📊 Step 1: Preparing data...")
    data = parse_results_for_analysis(project_root)
    
    if not data:
        print("❌ No analysis data found. Please run simulations first.")
        return {}
    
    # Extract matrices
    X = data['data_matrix']  # Input parameters (n_samples × n_inputs)
    Y = data['output_matrix']  # Output parameters (n_samples × n_outputs)
    input_names = data['parameter_names']
    output_names = data['output_names']
    
    # Validate data
    if X.shape[0] == 0:
        print("❌ Error: No samples found in data matrix.")
        return {}
    if X.shape[1] == 0:
        print("❌ Error: No input parameters found.")
        return {}
    if Y.shape[1] == 0:
        print("❌ Error: No output parameters found.")
        return {}
    if len(input_names) != X.shape[1]:
        print(f"⚠️ Warning: Mismatch between input_names ({len(input_names)}) and X columns ({X.shape[1]})")
    if len(output_names) != Y.shape[1]:
        print(f"⚠️ Warning: Mismatch between output_names ({len(output_names)}) and Y columns ({Y.shape[1]})")
    
    print(f"   📈 Data shape: {X.shape[0]} samples, {X.shape[1]} inputs, {Y.shape[1]} outputs")
    print(f"   🔧 Input parameters: {input_names}")
    print(f"   📊 Output parameters: {output_names}")
    
    # Standardize inputs
    scaler_X = StandardScaler()
    X_scaled = scaler_X.fit_transform(X)
    
    # Center outputs (important for PCA)
    # Handle NaN values in output matrix
    if np.any(np.isnan(Y)):
        print("⚠️ Warning: NaN values detected in output matrix. Replacing with column means.")
        Y = np.nan_to_num(Y, nan=np.nanmean(Y, axis=0))
    Y_centered = Y - np.mean(Y, axis=0)
    
    print("✅ Data preparation complete")
    
    # Step 2: Inspect outputs
    print("\n📊 Step 2: Inspecting output correlations...")
    correlation_matrix = np.corrcoef(Y_centered.T)
    
    print("   Output correlation matrix:")
    corr_df = pd.DataFrame(correlation_matrix, 
                          index=output_names, 
                          columns=output_names)
    print(corr_df.round(3))
    
    # Step 3: PCA on outputs
    print(f"\n🔍 Step 3: Performing PCA on outputs (retain {variance_threshold*100}% variance)...")
    
    pca = PCA()
    PC_scores = pca.fit_transform(Y_centered)
    explained_variance_ratio = pca.explained_variance_ratio_
    cumulative_variance = np.cumsum(explained_variance_ratio)
    
    # Choose number of components to retain
    # Find first component that reaches variance threshold
    threshold_indices = np.where(cumulative_variance >= variance_threshold)[0]
    if len(threshold_indices) > 0:
        n_components = threshold_indices[0] + 1
    else:
        # If no component reaches threshold, use all components
        n_components = len(explained_variance_ratio)
    n_components = max(1, min(n_components, len(explained_variance_ratio)))  # At least 1, at most all components
    
    print(f"   📊 Total variance explained by {n_components} components: {cumulative_variance[n_components-1]:.3f}")
    print(f"   📈 Individual component variances: {explained_variance_ratio[:n_components]}")
    print(f"   🔍 Total components available: {len(explained_variance_ratio)}")
    print(f"   📊 All variance ratios: {explained_variance_ratio}")
    
    # Retain only the selected components
    PC_scores_retained = PC_scores[:, :n_components]
    PC_loadings = pca.components_[:n_components, :]
    
    # Step 4: Build surrogate models
    print(f"\n🤖 Step 4: Building surrogate models for {n_components} principal components...")
    
    surrogate_models = []
    model_scores = []
    
    for i in range(n_components):
        print(f"   Training model for PC{i+1}...")
        
        # Train Random Forest for this PC
        rf = RandomForestRegressor(n_estimators=100, random_state=random_state)
        rf.fit(X_scaled, PC_scores_retained[:, i])
        
        # Cross-validation score
        cv_scores = cross_val_score(rf, X_scaled, PC_scores_retained[:, i], cv=5, scoring='r2')
        model_scores.append(cv_scores.mean())
        
        print(f"     R² score: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
        
        surrogate_models.append(rf)
    
    print("✅ Surrogate models trained")
    
    # Step 5: Compute feature importances
    print("\n📊 Step 5: Computing feature importances...")
    
    importance_matrix = np.zeros((len(input_names), n_components))
    
    for i, (model, pc_scores) in enumerate(zip(surrogate_models, PC_scores_retained.T)):
        print(f"   Computing importances for PC{i+1}...")
        
        # Permutation importance
        perm_importance = permutation_importance(
            model, X_scaled, pc_scores, 
            n_repeats=10, random_state=random_state
        )
        
        importance_matrix[:, i] = perm_importance.importances_mean
    
    print("✅ Feature importances computed")
    
    # Step 6: Aggregate importances
    print("\n📊 Step 6: Aggregating importances across principal components...")
    
    # Variance-weighted aggregation
    weights = explained_variance_ratio[:n_components]
    weights = weights / weights.sum()  # Normalize to sum to 1
    
    aggregated_importance = np.dot(importance_matrix, weights)
    
    # Create results dataframe
    results_df = pd.DataFrame({
        'Input_Parameter': input_names,
        'Aggregated_Importance': aggregated_importance
    })
    
    # Sort by importance (descending)
    results_df = results_df.sort_values('Aggregated_Importance', ascending=False)
    
    # Assign ranks after sorting
    results_df['Rank'] = range(1, len(input_names) + 1)
    
    print("   📊 Top 5 most important inputs:")
    for _, row in results_df.head().iterrows():
        print(f"     {row['Rank']}. {row['Input_Parameter']}: {row['Aggregated_Importance']:.4f}")
    
    # Step 7: Bootstrap uncertainty quantification
    print(f"\n🔄 Step 7: Bootstrap uncertainty quantification ({n_bootstrap} iterations)...")
    
    bootstrap_results = []
    
    for b in range(n_bootstrap):
        if (b + 1) % 10 == 0:
            print(f"   Bootstrap iteration {b+1}/{n_bootstrap}")
        
        # Bootstrap sample
        n_samples = X_scaled.shape[0]
        bootstrap_indices = np.random.choice(n_samples, size=n_samples, replace=True)
        
        X_boot = X_scaled[bootstrap_indices]
        Y_boot = Y_centered[bootstrap_indices]
        
        # PCA on bootstrap sample
        pca_boot = PCA()
        PC_scores_boot = pca_boot.fit_transform(Y_boot)
        explained_var_boot = pca_boot.explained_variance_ratio_
        
        # Use same number of components
        PC_scores_boot_retained = PC_scores_boot[:, :n_components]
        
        # Train models and compute importances
        bootstrap_importance = np.zeros((len(input_names), n_components))
        
        for i in range(n_components):
            rf_boot = RandomForestRegressor(n_estimators=50, random_state=random_state)
            rf_boot.fit(X_boot, PC_scores_boot_retained[:, i])
            
            perm_importance_boot = permutation_importance(
                rf_boot, X_boot, PC_scores_boot_retained[:, i],
                n_repeats=5, random_state=random_state
            )
            
            bootstrap_importance[:, i] = perm_importance_boot.importances_mean
        
        # Aggregate
        weights_boot = explained_var_boot[:n_components]
        weights_boot = weights_boot / weights_boot.sum()
        
        aggregated_boot = np.dot(bootstrap_importance, weights_boot)
        bootstrap_results.append(aggregated_boot)
    
    # Compute bootstrap statistics
    bootstrap_array = np.array(bootstrap_results)
    mean_importance = np.mean(bootstrap_array, axis=0)
    std_importance = np.std(bootstrap_array, axis=0)
    
    # Map bootstrap results to the sorted parameter order
    # Note: results_df.index contains the original parameter indices (0, 1, 2, ...)
    # which correspond to the original order in input_names. After sorting, these
    # indices are preserved, so we can use them to index into mean_importance/std_importance
    # which are also in the original parameter order.
    sorted_indices = results_df.index.tolist()
    
    # Verify we have the right number of parameters
    if len(sorted_indices) != len(mean_importance):
        raise ValueError(f"Mismatch: {len(sorted_indices)} parameters in results_df but {len(mean_importance)} in bootstrap results")
    
    # Update results with uncertainty (maintain sorted order)
    results_df['Mean_Importance'] = mean_importance[sorted_indices]
    results_df['Std_Importance'] = std_importance[sorted_indices]
    # Add small epsilon to prevent division by zero
    results_df['Coefficient_of_Variation'] = std_importance[sorted_indices] / (mean_importance[sorted_indices] + 1e-10)
    
    print("✅ Bootstrap analysis complete")
    
    # Step 8: Create visualizations
    print("\n📊 Step 8: Creating visualizations...")
    
    # Create sensitivity subfolder
    sensitivity_folder = f"{project_root}/test_files/out_final/sensitivity"
    import os
    os.makedirs(sensitivity_folder, exist_ok=True)
    print(f"   📁 Created sensitivity folder: {sensitivity_folder}")
    
    # Define file paths in sensitivity subfolder
    results_path = f"{sensitivity_folder}/sensitivity_analysis_results.csv"
    plot_path = f"{sensitivity_folder}/sensitivity_analysis_plot.png"
    text_path = f"{sensitivity_folder}/sensitivity_analysis_summary.txt"
    
    # Save files immediately after analysis completes
    print("\n💾 Saving analysis results...")
    
    # Save CSV results
    results_df.to_csv(results_path, index=False)
    print(f"   📊 Results saved: {results_path}")
    
    # Save text summary
    save_text_summary(results_df, input_names, output_names, 
                     explained_variance_ratio, n_components, correlation_matrix, 
                     model_scores, n_bootstrap, text_path)
    print(f"   📄 Text summary saved: {text_path}")
    
    print("✅ CSV and text files saved successfully!")
    
    # Create and save plot immediately
    print("\n📊 Creating and saving plot...")
    create_and_save_plot(results_df, input_names, output_names, 
                        explained_variance_ratio, n_components, correlation_matrix, 
                        importance_matrix, plot_path)
    print(f"   📈 Plot saved: {plot_path}")
    print("✅ All files saved successfully!")
    
    # Display results in Python
    display_results_in_python(results_df, input_names, output_names, 
                           explained_variance_ratio, n_components, correlation_matrix, project_root)
    
    # Show final results summary after display options
    print("\n" + "="*80)
    print("📊 FINAL SENSITIVITY ANALYSIS SUMMARY")
    print("="*80)
    
    print(f"📊 Dataset: {X.shape[0]} samples, {X.shape[1]} inputs, {Y.shape[1]} outputs")
    print(f"🔍 PCA: {n_components} components retained ({cumulative_variance[n_components-1]:.1%} variance)")
    print(f"🤖 Surrogate models: Average R² = {np.mean(model_scores):.3f}")
    print(f"🔄 Bootstrap: {n_bootstrap} iterations completed")
    
    print(f"\n🏆 Top 3 Most Important Inputs:")
    for i, (_, row) in enumerate(results_df.head(3).iterrows()):
        cv = row['Coefficient_of_Variation']
        stability = "High" if cv < 0.2 else "Medium" if cv < 0.5 else "Low"
        print(f"   {i+1}. {row['Input_Parameter']}: {row['Mean_Importance']:.4f} ± {row['Std_Importance']:.4f} (Stability: {stability})")
    
    print(f"\n📁 Files saved:")
    print(f"   📊 Results: {results_path}")
    print(f"   📈 Plot: {plot_path}")
    print(f"   📄 Summary: {text_path}")
    
    print(f"\n💡 Next steps:")
    print(f"   1. Focus optimization on the top 3 parameters")
    print(f"   2. Use stable parameters for reliable design decisions")
    print(f"   3. Consider fixing low-impact parameters to reduce design space")
    
    # Plot already created and saved above - no need to recreate
    
    # Step 9: Interpretation and summary
    print("\n📋 Step 9: Analysis Summary")
    print("="*40)
    
    print(f"📊 Dataset: {X.shape[0]} samples, {X.shape[1]} inputs, {Y.shape[1]} outputs")
    print(f"🔍 PCA: {n_components} components retained ({cumulative_variance[n_components-1]:.1%} variance)")
    print(f"🤖 Surrogate models: Average R² = {np.mean(model_scores):.3f}")
    print(f"🔄 Bootstrap: {n_bootstrap} iterations completed")
    
    print(f"\n🏆 Top 3 Most Important Inputs:")
    for i, (_, row) in enumerate(results_df.head(3).iterrows()):
        cv = row['Coefficient_of_Variation']
        stability = "High" if cv < 0.2 else "Medium" if cv < 0.5 else "Low"
        print(f"   {i+1}. {row['Input_Parameter']}: {row['Mean_Importance']:.4f} ± {row['Std_Importance']:.4f} (Stability: {stability})")
    
    # Files already saved above - no need to save again
    
    # Return comprehensive results
    results = {
        'input_names': input_names,
        'output_names': output_names,
        'results_df': results_df,
        'importance_matrix': importance_matrix,
        'explained_variance_ratio': explained_variance_ratio,
        'n_components': n_components,
        'model_scores': model_scores,
        'correlation_matrix': correlation_matrix,
        'bootstrap_results': bootstrap_array,
        'plot_path': plot_path,
        'results_path': results_path
    }
    
    print("\n✅ Sensitivity analysis complete!")
    return results


def display_results_in_python(results_df, input_names, output_names, 
                            explained_variance_ratio, n_components, correlation_matrix, project_root=None):
    """
    Display sensitivity analysis results in Python with interactive options.
    
    Args:
        results_df (pd.DataFrame): Results dataframe with importance rankings
        input_names (list): List of input parameter names
        output_names (list): List of output parameter names
        explained_variance_ratio (np.array): PCA explained variance ratios
        n_components (int): Number of retained components
        correlation_matrix (np.array): Output correlation matrix
    """
    print("\n" + "="*80)
    print("📊 SENSITIVITY ANALYSIS RESULTS - INTERACTIVE DISPLAY")
    print("="*80)
    
    while True:
        print("\nChoose what to display:")
        print("1. 📈 Importance Rankings (Top 10)")
        print("2. 📊 Complete Results Table")
        print("3. 🔍 Parameter Details")
        print("4. 📋 PCA Analysis Summary")
        print("5. 🔗 Output Correlations")
        print("6. 📊 Statistical Summary")
        print("7. 🎯 Optimization Recommendations")
        print("8. 📈 View Analysis Plot (JPEG)")
        print("9. 📊 Correlation Heatmap")
        print("10. 📁 Export Options")
        print("11. ↩️ Return to Results Summary")
        
        choice = input("\nEnter your choice (1-11): ").strip()
        
        if choice == "1":
            display_importance_rankings(results_df)
        elif choice == "2":
            display_complete_results(results_df)
        elif choice == "3":
            display_parameter_details(results_df, input_names)
        elif choice == "4":
            display_pca_summary(explained_variance_ratio, n_components)
        elif choice == "5":
            display_output_correlations(correlation_matrix, output_names)
        elif choice == "6":
            display_statistical_summary(results_df)
        elif choice == "7":
            display_optimization_recommendations(results_df)
        elif choice == "8":
            if project_root is not None:
                display_analysis_plot(project_root)
            else:
                print("❌ Project root not available. Cannot display plot.")
        elif choice == "9":
            display_correlation_heatmap(correlation_matrix, output_names)
        elif choice == "10":
            display_export_options()
        elif choice == "11":
            print("👋 Returning to results summary...")
            return
        else:
            print("❌ Invalid choice. Please enter 1-11.")


def display_importance_rankings(results_df):
    """Display top 10 importance rankings with detailed information."""
    print("\n🏆 TOP 10 MOST IMPORTANT INPUT PARAMETERS")
    print("-" * 60)
    print(f"{'Rank':<4} {'Parameter':<25} {'Importance':<12} {'Uncertainty':<12} {'Stability':<10}")
    print("-" * 60)
    
    for _, row in results_df.head(10).iterrows():
        cv = row['Coefficient_of_Variation']
        stability = "High" if cv < 0.2 else "Medium" if cv < 0.5 else "Low"
        print(f"{row['Rank']:<4} {row['Input_Parameter']:<25} "
              f"{row['Mean_Importance']:<12.4f} {row['Std_Importance']:<12.4f} {stability:<10}")


def display_complete_results(results_df):
    """Display complete results table."""
    print("\n📊 COMPLETE SENSITIVITY ANALYSIS RESULTS")
    print("=" * 80)
    
    # Format the dataframe for better display
    display_df = results_df.copy()
    display_df['Mean_Importance'] = display_df['Mean_Importance'].round(4)
    display_df['Std_Importance'] = display_df['Std_Importance'].round(4)
    display_df['Coefficient_of_Variation'] = display_df['Coefficient_of_Variation'].round(3)
    
    print(display_df.to_string(index=False))


def display_parameter_details(results_df, input_names):
    """Display detailed information for a specific parameter."""
    print("\n🔍 PARAMETER DETAILS")
    print("-" * 40)
    
    # Show available parameters
    print("Available parameters:")
    for i, param in enumerate(input_names, 1):
        print(f"{i}. {param}")
    
    try:
        choice = int(input("\nEnter parameter number: ")) - 1
        if 0 <= choice < len(input_names):
            param_name = input_names[choice]
            param_row = results_df[results_df['Input_Parameter'] == param_name].iloc[0]
            
            print(f"\n📊 Details for {param_name}:")
            print(f"   Rank: {param_row['Rank']}")
            print(f"   Importance: {param_row['Mean_Importance']:.4f} ± {param_row['Std_Importance']:.4f}")
            print(f"   Coefficient of Variation: {param_row['Coefficient_of_Variation']:.3f}")
            
            # Interpretation
            importance = param_row['Mean_Importance']
            uncertainty = param_row['Std_Importance']
            
            if importance > 0.5:
                impact = "HIGH"
            elif importance > 0.2:
                impact = "MEDIUM"
            else:
                impact = "LOW"
            
            if uncertainty / importance < 0.2:
                reliability = "HIGH"
            elif uncertainty / importance < 0.5:
                reliability = "MEDIUM"
            else:
                reliability = "LOW"
            
            print(f"\n🎯 Interpretation:")
            print(f"   Impact on outputs: {impact}")
            print(f"   Ranking reliability: {reliability}")
            
        else:
            print("❌ Invalid parameter number.")
    except ValueError:
        print("❌ Please enter a valid number.")


def display_pca_summary(explained_variance_ratio, n_components):
    """Display PCA analysis summary."""
    print("\n📋 PCA ANALYSIS SUMMARY")
    print("-" * 40)
    
    print(f"Number of components retained: {n_components}")
    print(f"Total variance explained: {sum(explained_variance_ratio[:n_components]):.1%}")
    print(f"Total components available: {len(explained_variance_ratio)}")
    
    print(f"\nIndividual component contributions:")
    for i in range(min(n_components, len(explained_variance_ratio))):
        print(f"   PC{i+1}: {explained_variance_ratio[i]:.1%}")
    
    print(f"\nCumulative variance:")
    cumulative = 0
    for i in range(min(n_components, len(explained_variance_ratio))):
        cumulative += explained_variance_ratio[i]
        print(f"   PC{i+1}: {cumulative:.1%}")
    
    # Show all components if there are more than retained
    if len(explained_variance_ratio) > n_components:
        print(f"\nAll components (including unused):")
        for i in range(len(explained_variance_ratio)):
            status = "✓" if i < n_components else "✗"
            print(f"   PC{i+1}: {explained_variance_ratio[i]:.1%} {status}")


def display_output_correlations(correlation_matrix, output_names):
    """Display output parameter correlations."""
    print("\n🔗 OUTPUT PARAMETER CORRELATIONS")
    print("-" * 50)
    
    corr_df = pd.DataFrame(correlation_matrix, 
                         index=output_names, 
                         columns=output_names)
    
    print(corr_df.round(3).to_string())
    
    # Find strongest correlations
    print(f"\n🔍 Strongest correlations (|r| > 0.5):")
    for i in range(len(output_names)):
        for j in range(i+1, len(output_names)):
            corr_val = correlation_matrix[i, j]
            if abs(corr_val) > 0.5:
                direction = "positive" if corr_val > 0 else "negative"
                print(f"   {output_names[i]} ↔ {output_names[j]}: {corr_val:.3f} ({direction})")


def display_statistical_summary(results_df):
    """Display statistical summary of the analysis."""
    print("\n📊 STATISTICAL SUMMARY")
    print("-" * 40)
    
    importance_values = results_df['Mean_Importance']
    uncertainty_values = results_df['Std_Importance']
    
    print(f"Number of parameters analyzed: {len(results_df)}")
    print(f"Importance range: {importance_values.min():.4f} - {importance_values.max():.4f}")
    print(f"Mean importance: {importance_values.mean():.4f}")
    print(f"Standard deviation: {importance_values.std():.4f}")
    
    print(f"\nUncertainty statistics:")
    print(f"   Mean uncertainty: {uncertainty_values.mean():.4f}")
    print(f"   Max uncertainty: {uncertainty_values.max():.4f}")
    print(f"   Min uncertainty: {uncertainty_values.min():.4f}")
    
    # Stability analysis
    stable_params = len(results_df[results_df['Coefficient_of_Variation'] < 0.2])
    print(f"\nStability analysis:")
    print(f"   Highly stable parameters (CV < 0.2): {stable_params}/{len(results_df)}")
    print(f"   Stability rate: {stable_params/len(results_df):.1%}")


def display_optimization_recommendations(results_df):
    """Display optimization recommendations based on results."""
    print("\n🎯 OPTIMIZATION RECOMMENDATIONS")
    print("-" * 50)
    
    # Top 3 most important
    top_3 = results_df.head(3)
    print("🥇 Primary optimization targets:")
    for _, row in top_3.iterrows():
        print(f"   • {row['Input_Parameter']} (importance: {row['Mean_Importance']:.4f})")
    
    # Stable parameters
    stable_params = results_df[results_df['Coefficient_of_Variation'] < 0.2]
    print(f"\n🔒 Stable parameters (reliable rankings):")
    for _, row in stable_params.iterrows():
        print(f"   • {row['Input_Parameter']} (CV: {row['Coefficient_of_Variation']:.3f})")
    
    # Low importance parameters
    low_importance = results_df[results_df['Mean_Importance'] < 0.1]
    if len(low_importance) > 0:
        print(f"\n🔧 Parameters with low impact (consider fixing):")
        for _, row in low_importance.iterrows():
            print(f"   • {row['Input_Parameter']} (importance: {row['Mean_Importance']:.4f})")
    
    print(f"\n💡 Strategy:")
    print(f"   1. Focus optimization on top 3 parameters")
    print(f"   2. Use stable parameters for reliable design decisions")
    print(f"   3. Consider fixing low-impact parameters to reduce design space")


def display_analysis_plot(project_root):
    """Display the sensitivity analysis plot (JPEG image)."""
    import os
    
    plot_path = os.path.join(project_root, "test_files", "out_final", "sensitivity", "sensitivity_analysis_plot.png")
    
    if not os.path.exists(plot_path):
        print(f"❌ Analysis plot not found at: {plot_path}")
        print("Please run the sensitivity analysis first to generate the plot.")
        return
    
    try:
        # Try to display the image using matplotlib
        img = plt.imread(plot_path)
        
        # Create a new figure to display the image
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.imshow(img)
        ax.axis('off')  # Hide axes
        ax.set_title('Sensitivity Analysis Results', fontsize=16, fontweight='bold')
        
        # Add some information about the plot
        print(f"\n📈 SENSITIVITY ANALYSIS PLOT")
        print("-" * 40)
        print(f"Plot file: {plot_path}")
        print("The plot contains 4 panels:")
        print("1. Top-left: Importance ranking (horizontal bar chart)")
        print("2. Top-right: Importance heatmap (inputs × PCs)")
        print("3. Bottom-left: PCA explained variance")
        print("4. Bottom-right: Output correlations")
        print("\nDisplaying plot...")
        
        plt.tight_layout()
        plt.show()
        
        print("✅ Plot displayed successfully!")
        
    except Exception as e:
        print(f"❌ Error displaying plot: {e}")
        print("The plot file exists but cannot be displayed.")
        print(f"Plot location: {plot_path}")


def display_correlation_heatmap(correlation_matrix, output_names):
    """Display correlation heatmap as a matplotlib figure."""
    print(f"\n📊 CORRELATION HEATMAP")
    print("-" * 40)
    
    try:
        # Create correlation heatmap
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Create correlation dataframe
        corr_df = pd.DataFrame(correlation_matrix, 
                             index=output_names, 
                             columns=output_names)
        
        # Create heatmap
        if SEABORN_AVAILABLE:
            sns.heatmap(corr_df, annot=True, fmt='.3f', cmap='RdBu_r', 
                       center=0, ax=ax, cbar_kws={'label': 'Correlation Coefficient'})
        else:
            # Fallback to matplotlib
            im = ax.imshow(corr_df.values, cmap='RdBu_r', aspect='auto', vmin=-1, vmax=1)
            ax.set_xticks(range(len(corr_df.columns)))
            ax.set_yticks(range(len(corr_df.index)))
            ax.set_xticklabels(corr_df.columns, rotation=45)
            ax.set_yticklabels(corr_df.index)
            
            # Add colorbar
            cbar = plt.colorbar(im, ax=ax)
            cbar.set_label('Correlation Coefficient')
            
            # Add text annotations
            for i in range(len(corr_df.index)):
                for j in range(len(corr_df.columns)):
                    text_color = 'white' if abs(corr_df.iloc[i, j]) > 0.5 else 'black'
                    ax.text(j, i, f'{corr_df.iloc[i, j]:.2f}', 
                           ha='center', va='center', color=text_color, fontsize=10)
        
        ax.set_title('Output Parameter Correlations', fontsize=14, fontweight='bold')
        ax.set_xlabel('Output Parameters', fontsize=12)
        ax.set_ylabel('Output Parameters', fontsize=12)
        
        plt.tight_layout()
        plt.show()
        
        # Print correlation summary
        print("Correlation Summary:")
        print("-" * 20)
        
        # Find strongest correlations
        strong_correlations = []
        for i in range(len(output_names)):
            for j in range(i+1, len(output_names)):
                corr_val = correlation_matrix[i, j]
                if abs(corr_val) > 0.3:  # Show correlations > 0.3
                    strong_correlations.append((output_names[i], output_names[j], corr_val))
        
        if strong_correlations:
            print("Strong correlations (|r| > 0.3):")
            for param1, param2, corr_val in strong_correlations:
                direction = "positive" if corr_val > 0 else "negative"
                strength = "strong" if abs(corr_val) > 0.7 else "moderate"
                print(f"  • {param1} ↔ {param2}: {corr_val:.3f} ({strength} {direction})")
        else:
            print("No strong correlations found (all |r| ≤ 0.3)")
        
        print("✅ Correlation heatmap displayed successfully!")
        
    except Exception as e:
        print(f"❌ Error creating correlation heatmap: {e}")
        print("Falling back to text-based correlation display...")
        display_output_correlations(correlation_matrix, output_names)


def display_export_options():
    """Display export options."""
    print("\n📁 EXPORT OPTIONS")
    print("-" * 30)
    print("Available export formats:")
    print("1. CSV file (detailed results)")
    print("2. Text report (summary)")
    print("3. Plot (visualization)")
    print("4. JSON (structured data)")
    print("\nNote: Files are automatically saved during analysis.")
    print("Check the 'out_final' folder in your project directory.")


def display_existing_results(project_root):
    """
    Display results from existing sensitivity analysis files.
    
    Args:
        project_root (str): Path to the project folder
    """
    import os
    
    results_file = os.path.join(project_root, "test_files", "out_final", "sensitivity", "sensitivity_analysis_results.csv")
    
    if not os.path.exists(results_file):
        print(f"❌ No sensitivity analysis results found at: {results_file}")
        print("Please run the sensitivity analysis first.")
        return
    
    try:
        # Load existing results
        results_df = pd.read_csv(results_file)
        
        # Get other data from the project
        from post_process import parse_results_for_analysis
        data = parse_results_for_analysis(project_root)
        
        if data:
            input_names = data['parameter_names']
            output_names = data['output_names']
            
            # Create dummy correlation matrix and PCA data for display
            correlation_matrix = np.eye(len(output_names))
            explained_variance_ratio = np.array([0.8, 0.2])  # Dummy values
            n_components = 2
            
            print("📊 Loading existing sensitivity analysis results...")
            display_results_in_python(results_df, input_names, output_names, 
                                   explained_variance_ratio, n_components, correlation_matrix, project_root)
            
            # Show summary after display options
            print("\n" + "="*80)
            print("📊 SENSITIVITY ANALYSIS RESULTS SUMMARY")
            print("="*80)
            
            print(f"📊 Dataset: {len(results_df)} parameters analyzed")
            print(f"🔍 Analysis completed with existing results")
            
            print(f"\n🏆 Top 3 Most Important Inputs:")
            for i, (_, row) in enumerate(results_df.head(3).iterrows()):
                cv = row['Coefficient_of_Variation']
                stability = "High" if cv < 0.2 else "Medium" if cv < 0.5 else "Low"
                print(f"   {i+1}. {row['Input_Parameter']}: {row['Mean_Importance']:.4f} ± {row['Std_Importance']:.4f} (Stability: {stability})")
            
            print(f"\n📁 Files available:")
            print(f"   📊 Results: {results_file}")
            plot_path = os.path.join(project_root, "test_files", "out_final", "sensitivity", "sensitivity_analysis_plot.png")
            if os.path.exists(plot_path):
                print(f"   📈 Plot: {plot_path}")
            text_path = os.path.join(project_root, "test_files", "out_final", "sensitivity", "sensitivity_analysis_summary.txt")
            if os.path.exists(text_path):
                print(f"   📄 Summary: {text_path}")
            
            print(f"\n💡 Next steps:")
            print(f"   1. Focus optimization on the top 3 parameters")
            print(f"   2. Use stable parameters for reliable design decisions")
            print(f"   3. Consider fixing low-impact parameters to reduce design space")
        else:
            print("❌ Could not load project data. Please check your data files.")
            
    except Exception as e:
        print(f"❌ Error loading results: {e}")


def save_text_summary(results_df, input_names, output_names, 
                     explained_variance_ratio, n_components, correlation_matrix, 
                     model_scores, n_bootstrap, text_path):
    """
    Save a comprehensive text summary of the sensitivity analysis.
    
    Args:
        results_df (pd.DataFrame): Results dataframe with importance rankings
        input_names (list): List of input parameter names
        output_names (list): List of output parameter names
        explained_variance_ratio (np.array): PCA explained variance ratios
        n_components (int): Number of retained components
        correlation_matrix (np.array): Output correlation matrix
        model_scores (list): R² scores for surrogate models
        n_bootstrap (int): Number of bootstrap iterations
        text_path (str): Path to save the text file
    """
    from datetime import datetime
    
    with open(text_path, 'w', encoding='utf-8') as f:
        f.write("SENSITIVITY ANALYSIS SUMMARY REPORT\n")
        f.write("=" * 50 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Analysis overview
        f.write("ANALYSIS OVERVIEW\n")
        f.write("-" * 20 + "\n")
        f.write(f"Number of samples: {len(results_df)}\n")
        f.write(f"Number of inputs: {len(input_names)}\n")
        f.write(f"Number of outputs: {len(output_names)}\n")
        f.write(f"Bootstrap iterations: {n_bootstrap}\n")
        f.write(f"PCA components retained: {n_components}\n")
        f.write(f"Total variance explained: {sum(explained_variance_ratio[:n_components]):.1%}\n\n")
        
        # Input parameters
        f.write("INPUT PARAMETERS\n")
        f.write("-" * 20 + "\n")
        for i, param in enumerate(input_names, 1):
            f.write(f"{i}. {param}\n")
        f.write("\n")
        
        # Output parameters
        f.write("OUTPUT PARAMETERS\n")
        f.write("-" * 20 + "\n")
        for i, param in enumerate(output_names, 1):
            f.write(f"{i}. {param}\n")
        f.write("\n")
        
        # PCA analysis
        f.write("PCA ANALYSIS\n")
        f.write("-" * 20 + "\n")
        f.write(f"Components retained: {n_components}\n")
        f.write(f"Total variance explained: {sum(explained_variance_ratio[:n_components]):.1%}\n\n")
        
        f.write("Individual component contributions:\n")
        for i in range(n_components):
            f.write(f"  PC{i+1}: {explained_variance_ratio[i]:.1%}\n")
        f.write("\n")
        
        # Surrogate model performance
        f.write("SURROGATE MODEL PERFORMANCE\n")
        f.write("-" * 30 + "\n")
        f.write(f"Average R² score: {np.mean(model_scores):.3f}\n")
        f.write(f"Model performance: {'Excellent' if np.mean(model_scores) > 0.9 else 'Good' if np.mean(model_scores) > 0.7 else 'Fair'}\n\n")
        
        # Importance rankings
        f.write("PARAMETER IMPORTANCE RANKINGS\n")
        f.write("-" * 30 + "\n")
        f.write(f"{'Rank':<4} {'Parameter':<25} {'Importance':<12} {'Uncertainty':<12} {'Stability':<10}\n")
        f.write("-" * 70 + "\n")
        
        for _, row in results_df.iterrows():
            cv = row['Coefficient_of_Variation']
            stability = "High" if cv < 0.2 else "Medium" if cv < 0.5 else "Low"
            f.write(f"{row['Rank']:<4} {row['Input_Parameter']:<25} "
                   f"{row['Mean_Importance']:<12.4f} {row['Std_Importance']:<12.4f} {stability:<10}\n")
        f.write("\n")
        
        # Top 3 recommendations
        f.write("TOP 3 OPTIMIZATION TARGETS\n")
        f.write("-" * 30 + "\n")
        for i, (_, row) in enumerate(results_df.head(3).iterrows()):
            f.write(f"{i+1}. {row['Input_Parameter']}\n")
            f.write(f"   Importance: {row['Mean_Importance']:.4f} ± {row['Std_Importance']:.4f}\n")
            f.write(f"   Stability: {'High' if row['Coefficient_of_Variation'] < 0.2 else 'Medium' if row['Coefficient_of_Variation'] < 0.5 else 'Low'}\n\n")
        
        # Output correlations
        f.write("OUTPUT PARAMETER CORRELATIONS\n")
        f.write("-" * 30 + "\n")
        corr_df = pd.DataFrame(correlation_matrix, index=output_names, columns=output_names)
        f.write(corr_df.round(3).to_string())
        f.write("\n\n")
        
        # Strong correlations
        f.write("STRONG CORRELATIONS (|r| > 0.5)\n")
        f.write("-" * 30 + "\n")
        strong_correlations = []
        for i in range(len(output_names)):
            for j in range(i+1, len(output_names)):
                corr_val = correlation_matrix[i, j]
                if abs(corr_val) > 0.5:
                    strong_correlations.append((output_names[i], output_names[j], corr_val))
        
        if strong_correlations:
            for param1, param2, corr_val in strong_correlations:
                direction = "positive" if corr_val > 0 else "negative"
                strength = "strong" if abs(corr_val) > 0.7 else "moderate"
                f.write(f"• {param1} ↔ {param2}: {corr_val:.3f} ({strength} {direction})\n")
        else:
            f.write("No strong correlations found (all |r| ≤ 0.5)\n")
        f.write("\n")
        
        # Optimization recommendations
        f.write("OPTIMIZATION RECOMMENDATIONS\n")
        f.write("-" * 30 + "\n")
        f.write("1. PRIMARY TARGETS (Top 3 parameters):\n")
        for i, (_, row) in enumerate(results_df.head(3).iterrows()):
            f.write(f"   • {row['Input_Parameter']} (importance: {row['Mean_Importance']:.4f})\n")
        
        # Stable parameters
        stable_params = results_df[results_df['Coefficient_of_Variation'] < 0.2]
        if len(stable_params) > 0:
            f.write("\n2. STABLE PARAMETERS (reliable rankings):\n")
            for _, row in stable_params.iterrows():
                f.write(f"   • {row['Input_Parameter']} (CV: {row['Coefficient_of_Variation']:.3f})\n")
        
        # Low importance parameters
        low_importance = results_df[results_df['Mean_Importance'] < 0.1]
        if len(low_importance) > 0:
            f.write("\n3. LOW-IMPACT PARAMETERS (consider fixing):\n")
            for _, row in low_importance.iterrows():
                f.write(f"   • {row['Input_Parameter']} (importance: {row['Mean_Importance']:.4f})\n")
        
        f.write("\n4. STRATEGY:\n")
        f.write("   • Focus optimization on top 3 parameters\n")
        f.write("   • Use stable parameters for reliable design decisions\n")
        f.write("   • Consider fixing low-impact parameters to reduce design space\n")
        f.write("   • Monitor correlation between outputs during optimization\n\n")
        
        # File information
        f.write("FILES GENERATED\n")
        f.write("-" * 20 + "\n")
        f.write(f"• Results CSV: sensitivity_analysis_results.csv\n")
        f.write(f"• Analysis Plot: sensitivity_analysis_plot.png\n")
        f.write(f"• Summary Report: sensitivity_analysis_summary.txt (this file)\n\n")
        
        f.write("END OF REPORT\n")
        f.write("=" * 50 + "\n")


def create_and_save_plot(results_df, input_names, output_names, 
                        explained_variance_ratio, n_components, correlation_matrix, 
                        importance_matrix, plot_path):
    """
    Create and save the sensitivity analysis plot.
    
    Args:
        results_df (pd.DataFrame): Results dataframe with importance rankings
        input_names (list): List of input parameter names
        output_names (list): List of output parameter names
        explained_variance_ratio (np.array): PCA explained variance ratios
        n_components (int): Number of retained components
        correlation_matrix (np.array): Output correlation matrix
        importance_matrix (np.array): Importance matrix for heatmap
        plot_path (str): Path to save the plot
    """
    # Set up the plotting style
    plt.style.use('default')
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Sensitivity Analysis Results', fontsize=16, fontweight='bold')
    
    # 1. Aggregated importance ranking
    ax1 = axes[0, 0]
    y_pos = np.arange(len(input_names))
    bars = ax1.barh(y_pos, results_df['Mean_Importance'], 
                    xerr=results_df['Std_Importance'], 
                    capsize=5, alpha=0.7)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(results_df['Input_Parameter'])
    ax1.set_xlabel('Aggregated Importance')
    ax1.set_title('Input Parameter Importance Ranking')
    ax1.invert_yaxis()
    
    # Color bars by importance (handle division by zero)
    max_importance = results_df['Mean_Importance'].max()
    if max_importance > 0:
        colors = plt.cm.viridis(results_df['Mean_Importance'] / max_importance)
    else:
        colors = plt.cm.viridis(np.zeros(len(results_df)))
    for bar, color in zip(bars, colors):
        bar.set_color(color)
    
    # 2. Importance heatmap (inputs × PCs)
    ax2 = axes[0, 1]
    importance_df = pd.DataFrame(importance_matrix, 
                                index=input_names, 
                                columns=[f'PC{i+1}' for i in range(n_components)])
    
    if SEABORN_AVAILABLE:
        sns.heatmap(importance_df, annot=True, fmt='.3f', cmap='viridis', ax=ax2)
    else:
        # Fallback to matplotlib
        im = ax2.imshow(importance_df.values, cmap='viridis', aspect='auto')
        ax2.set_xticks(range(len(importance_df.columns)))
        ax2.set_yticks(range(len(importance_df.index)))
        ax2.set_xticklabels(importance_df.columns)
        ax2.set_yticklabels(importance_df.index)
        plt.colorbar(im, ax=ax2)
        
        # Add text annotations
        for i in range(len(importance_df.index)):
            for j in range(len(importance_df.columns)):
                ax2.text(j, i, f'{importance_df.iloc[i, j]:.3f}', 
                        ha='center', va='center', color='white')
    
    ax2.set_title('Importance Matrix (Inputs × Principal Components)')
    ax2.set_xlabel('Principal Components')
    ax2.set_ylabel('Input Parameters')
    
    # 3. PCA explained variance
    ax3 = axes[1, 0]
    
    # Ensure we have enough components to display
    n_components_to_show = min(len(explained_variance_ratio), 10)  # Show up to 10 components
    x_positions = range(1, n_components_to_show + 1)
    variance_values = explained_variance_ratio[:n_components_to_show]
    
    bars = ax3.bar(x_positions, variance_values, alpha=0.7, color='skyblue', edgecolor='navy')
    
    # Highlight retained components
    for i in range(min(n_components, n_components_to_show)):
        bars[i].set_color('lightcoral')
        bars[i].set_edgecolor('darkred')
    
    # Add vertical line for retained components
    if n_components <= n_components_to_show:
        ax3.axvline(x=n_components, color='red', linestyle='--', linewidth=2,
                    label=f'Retained: {n_components} components')
    
    ax3.set_xlabel('Principal Component')
    ax3.set_ylabel('Explained Variance Ratio')
    ax3.set_title('PCA Explained Variance')
    ax3.legend()
    
    # Add value labels on bars (only if values are positive)
    for i, (x, y) in enumerate(zip(x_positions, variance_values)):
        if y > 0:
            ax3.text(x, y + 0.01, f'{y:.3f}', ha='center', va='bottom', fontsize=8)
    
    # 4. Output correlation heatmap
    ax4 = axes[1, 1]
    corr_df = pd.DataFrame(correlation_matrix, 
                         index=output_names, 
                         columns=output_names)
    
    if SEABORN_AVAILABLE:
        sns.heatmap(corr_df, annot=True, fmt='.2f', cmap='RdBu_r', center=0, ax=ax4)
    else:
        # Fallback to matplotlib
        im = ax4.imshow(corr_df.values, cmap='RdBu_r', aspect='auto', vmin=-1, vmax=1)
        ax4.set_xticks(range(len(corr_df.columns)))
        ax4.set_yticks(range(len(corr_df.index)))
        ax4.set_xticklabels(corr_df.columns)
        ax4.set_yticklabels(corr_df.index)
        plt.colorbar(im, ax=ax4)
        
        # Add text annotations
        for i in range(len(corr_df.index)):
            for j in range(len(corr_df.columns)):
                ax4.text(j, i, f'{corr_df.iloc[i, j]:.2f}', 
                        ha='center', va='center', 
                        color='white' if abs(corr_df.iloc[i, j]) > 0.5 else 'black')
    
    ax4.set_title('Output Parameter Correlations')
    
    plt.tight_layout()
    
    # Save the plot
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()  # Close the figure to free memory


def quick_sensitivity_analysis(project_root):
    """
    Quick sensitivity analysis with default settings.
    
    Args:
        project_root (str): Path to the project folder
    
    Returns:
        dict: Sensitivity analysis results
    """
    return perform_sensitivity_analysis(project_root, n_bootstrap=20, variance_threshold=0.95)


