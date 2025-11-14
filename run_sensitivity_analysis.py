#!/usr/bin/env python3
"""
Example script to run sensitivity analysis on CFD simulation results.

This script demonstrates how to use the sensitivity analysis module
to identify which input parameters most affect the multivariate outputs.
"""

import os
import json
from sensitivity_analysis import perform_sensitivity_analysis, quick_sensitivity_analysis


def _resolve_project_root() -> str:
    """
    Resolve the project root from setup_config.json or prompt the user.
    """
    setup_path = os.path.join(os.getcwd(), "setup_config.json")
    if os.path.exists(setup_path):
        try:
            with open(setup_path, "r") as f:
                setup_params = json.load(f)
            project_folder = setup_params.get("project_folder")
            if project_folder:
                return project_folder
        except Exception as exc:
            print(f"[WARNING] Failed to read setup_config.json: {exc}")

    while True:
        project_root = input("Enter project root path: ").strip()
        if project_root:
            return project_root

def main():
    """
    Run sensitivity analysis on the Rear Wing Study project.
    """
    print("🚀 CFD Sensitivity Analysis")
    print("="*50)
    
    # Set the project root directory
    project_root = _resolve_project_root()
    
    # Check if project directory exists
    if not os.path.exists(project_root):
        print(f"❌ Project directory not found: {project_root}")
        print("Please update the project_root path in this script.")
        return
    
    # Check if required data files exist
    required_files = [
        os.path.join(project_root, "test_files", "dps", "DesignPoints.csv"),
        os.path.join(project_root, "test_files", "out_final", "summary2.csv")
    ]
    
    missing_files = [f for f in required_files if not os.path.exists(f)]
    if missing_files:
        print("❌ Missing required files:")
        for f in missing_files:
            print(f"   - {f}")
        print("\nPlease run simulations first to generate the required data files.")
        return
    
    print(f"📁 Project directory: {project_root}")
    print("✅ Required data files found")
    
    # Choose analysis type
    print("\nChoose analysis type:")
    print("1. Quick analysis (20 bootstrap iterations)")
    print("2. Comprehensive analysis (50 bootstrap iterations)")
    print("3. Custom analysis")
    print("4. Display existing results (no new analysis)")
    
    choice = input("\nEnter your choice (1, 2, 3, or 4): ").strip()
    
    if choice == "1":
        print("\n🔬 Running quick sensitivity analysis...")
        results = quick_sensitivity_analysis(project_root)
        
    elif choice == "2":
        print("\n🔬 Running comprehensive sensitivity analysis...")
        results = perform_sensitivity_analysis(project_root)
        
    elif choice == "3":
        print("\n🔬 Running custom sensitivity analysis...")
        
        # Get custom parameters
        try:
            n_bootstrap = int(input("Number of bootstrap iterations (default 30): ") or "30")
            variance_threshold = float(input("Variance threshold (default 0.95): ") or "0.95")
        except ValueError:
            print("❌ Invalid input. Using default values.")
            n_bootstrap = 30
            variance_threshold = 0.95
        
        results = perform_sensitivity_analysis(
            project_root, 
            n_bootstrap=n_bootstrap, 
            variance_threshold=variance_threshold
        )
        
    elif choice == "4":
        print("\n📊 Displaying existing sensitivity analysis results...")
        from sensitivity_analysis import display_existing_results
        display_existing_results(project_root)
        return
        
    else:
        print("❌ Invalid choice. Exiting.")
        return
    
    # Display results
    if results:
        print("\n🎉 Analysis completed successfully!")
        print(f"📊 Results saved to: {results['results_path']}")
        print(f"📈 Plot saved to: {results['plot_path']}")
        
        # Display top 5 most important parameters
        print("\n🏆 Top 5 Most Important Input Parameters:")
        print("-" * 50)
        for i, (_, row) in enumerate(results['results_df'].head(5).iterrows()):
            print(f"{i+1}. {row['Input_Parameter']}: {row['Mean_Importance']:.4f} ± {row['Std_Importance']:.4f}")
        
        # Display interpretation
        print("\n📋 Interpretation:")
        print("- Higher importance values indicate parameters that have greater influence on outputs")
        print("- The uncertainty (±) shows how robust the importance ranking is")
        print("- Parameters affecting multiple output modes (PCs) will have higher aggregated importance")
        
    else:
        print("❌ Analysis failed. Please check your data and dependencies.")
        print("\nRequired packages:")
        print("- scikit-learn: pip install scikit-learn")
        print("- matplotlib: pip install matplotlib")
        print("- pandas: pip install pandas")
        print("- numpy: pip install numpy")
        print("- seaborn (optional): pip install seaborn")

if __name__ == "__main__":
    main()
