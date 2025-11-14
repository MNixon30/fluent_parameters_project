import os
import csv
import re


def summarize_fluent_results(project_root: str, output_filename="summary2.csv"):
    """
    Summarizes all numeric results from Fluent output files in
    <project_root>/test_files/out and writes a combined CSV file
    in <project_root>/test_files/out_final.

    Args:
        project_root (str): Root folder of the project.
        output_filename (str): Name of the output summary file.
    """
    input_folder = os.path.join(project_root, "test_files", "out")
    output_folder = os.path.join(project_root, "test_files", "out_final")
    os.makedirs(output_folder, exist_ok=True)

    output_files = [f for f in os.listdir(input_folder) if f.lower().endswith(".txt")]
    if not output_files:
        print(f"No output files found in {input_folder}")
        return

    all_results = {}
    parameters_order = []

    # Correct regex to capture full scientific notation numbers
    pattern = re.compile(r"(\S+)\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)")

    # Read each output file (sort numerically by design point number)
    def sort_by_design_point(filename):
        # Extract design point number from filename (e.g., "out_0.txt" -> 0, "out_10.txt" -> 10)
        match = re.search(r'out_(\d+)\.txt', filename)
        return int(match.group(1)) if match else 0
    
    for file_name in sorted(output_files, key=sort_by_design_point):
        file_path = os.path.join(input_folder, file_name)
        results = {}
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                match = pattern.search(line)
                if match:
                    param, value = match.groups()
                    results[param] = float(value)
                    if param not in parameters_order:
                        parameters_order.append(param)
        all_results[file_name] = results

    # Save summary CSV
    summary_path = os.path.join(output_folder, output_filename)
    with open(summary_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        # Header row (sort files numerically by design point)
        sorted_files = sorted(all_results.keys(), key=sort_by_design_point)
        writer.writerow(["Output Parameter"] + sorted_files)
        # For each parameter, write its value from each file
        for param in parameters_order:
            row = [param]
            for file_name in sorted_files:
                row.append(all_results[file_name].get(param, ""))
            writer.writerow(row)

    print(f"\n✅ Summary of all results saved to: {summary_path}")


def parse_design_points(project_root: str):
    """
    Parse the DesignPoints.csv file to extract parameter values for each design point.
    
    Args:
        project_root (str): Root folder of the project.
    
    Returns:
        tuple: (parameter_names, design_points_data) where:
            - parameter_names: List of parameter names
            - design_points_data: List of dictionaries with design point data
    """
    design_points_file = os.path.join(project_root, "test_files", "dps", "DesignPoints.csv")
    
    if not os.path.exists(design_points_file):
        print(f"❌ DesignPoints.csv not found at: {design_points_file}")
        return [], []
    
    parameter_names = []
    design_points_data = []
    
    try:
        with open(design_points_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            
            # Read header row to get parameter names
            parameter_names = next(reader)
            
            # Read each design point
            for dp_idx, row in enumerate(reader):
                if row:  # Skip empty rows
                    dp_data = {
                        'design_point': dp_idx,
                        'parameters': {}
                    }
                    
                    # Add parameter values
                    for i, param_name in enumerate(parameter_names):
                        if i < len(row):
                            try:
                                dp_data['parameters'][param_name] = float(row[i])
                            except ValueError:
                                dp_data['parameters'][param_name] = None
                    
                    design_points_data.append(dp_data)
        
        print(f"Parsed {len(design_points_data)} design points with {len(parameter_names)} parameters")
        return parameter_names, design_points_data
        
    except Exception as e:
        print(f"Error parsing DesignPoints.csv: {e}")
        return [], []


def parse_results_for_analysis(project_root: str, summary_filename="summary2.csv"):
    """
    Parse the output summary file and design points into a workable format for 
    sensitivity analysis, optimization, and regression.
    
    Args:
        project_root (str): Root folder of the project.
        summary_filename (str): Name of the summary CSV file.
    
    Returns:
        dict: Structured data containing:
            - 'design_points': List of design point data with parameters
            - 'outputs': Dictionary of output parameters with values for each design point
            - 'parameter_names': List of input parameter names
            - 'output_names': List of output parameter names
            - 'data_matrix': 2D array for machine learning (design_points x parameters)
            - 'output_matrix': 2D array for machine learning (design_points x outputs)
    """
    # Parse design points
    parameter_names, design_points_data = parse_design_points(project_root)
    
    if not design_points_data:
        print("No design points found")
        return {}
    
    # Read summary file
    summary_path = os.path.join(project_root, "test_files", "out_final", summary_filename)
    
    if not os.path.exists(summary_path):
        print(f"Summary file not found at: {summary_path}")
        return {}
    
    try:
        with open(summary_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            
            # Read header to get output file names
            header = next(reader)
            output_files = header[1:]  # Skip 'Output Parameter' column
            
            # Read output data
            outputs = {}
            output_names = []
            
            for row in reader:
                if row:
                    param_name = row[0]
                    output_names.append(param_name)
                    outputs[param_name] = {}
                    
                    for i, value_str in enumerate(row[1:]):
                        if i < len(output_files):
                            try:
                                outputs[param_name][output_files[i]] = float(value_str) if value_str else None
                            except ValueError:
                                outputs[param_name][output_files[i]] = None
        
        # Create structured data for analysis
        analysis_data = {
            'design_points': design_points_data,
            'outputs': outputs,
            'parameter_names': parameter_names,
            'output_names': output_names,
            'data_matrix': [],
            'output_matrix': []
        }
        
        # Create data matrices for machine learning
        # Rows = Design points, Columns = Parameters/Outputs
        for dp_data in design_points_data:
            # Input parameters row (one row per design point)
            param_row = []
            for param_name in parameter_names:
                param_row.append(dp_data['parameters'].get(param_name, 0.0))
            analysis_data['data_matrix'].append(param_row)
            
            # Output parameters row (one row per design point)
            output_row = []
            for output_name in output_names:
                # Find corresponding output file for this design point
                output_file = f"out_{dp_data['design_point']}.txt"
                if output_file in outputs[output_name]:
                    output_row.append(outputs[output_name][output_file])
                else:
                    print(f"Missing output for design point {dp_data['design_point']}, output {output_name}, file {output_file}")
                    output_row.append(None)
            analysis_data['output_matrix'].append(output_row)
        
        # Convert to numpy arrays for easier manipulation
        try:
            import numpy as np
            analysis_data['data_matrix'] = np.array(analysis_data['data_matrix'])
            analysis_data['output_matrix'] = np.array(analysis_data['output_matrix'])
            
            print(f"   Input matrix shape: {analysis_data['data_matrix'].shape} (rows=design_points, cols=parameters)")
            print(f"   Output matrix shape: {analysis_data['output_matrix'].shape} (rows=design_points, cols=outputs)")
        except ImportError:
            print("   NumPy not available - matrices stored as lists")
        
        print(f"Parsed data for analysis:")
        print(f"   Design points: {len(design_points_data)}")
        print(f"   Input parameters: {len(parameter_names)}")
        print(f"   Output parameters: {len(output_names)}")
        print(f"   Data matrix shape: {len(analysis_data['data_matrix'])} x {len(parameter_names)}")
        print(f"   Output matrix shape: {len(analysis_data['output_matrix'])} x {len(output_names)}")
        
        return analysis_data
        
    except Exception as e:
        print(f"Error parsing summary file: {e}")
        return {}







def _resolve_project_root():
    """
    Attempt to resolve the project root automatically using setup_config.json.
    Falls back to prompting the user if the file is not available.
    """
    setup_path = os.path.join(os.getcwd(), "setup_config.json")
    if os.path.exists(setup_path):
        try:
            import json

            with open(setup_path, "r") as f:
                setup_params = json.load(f)
            project_root = setup_params.get("project_folder")
            if project_root:
                return project_root
        except Exception as exc:
            print(f"[WARNING] Failed to read setup_config.json: {exc}")

    while True:
        project_root = input("Enter project root path: ").strip()
        if project_root:
            return project_root


if __name__ == "__main__":
    root = _resolve_project_root()
    data = parse_results_for_analysis(root)
    if data:
        if "output_matrix" in data:
            print(data["output_matrix"])
        if "data_matrix" in data:
            print(data["data_matrix"])