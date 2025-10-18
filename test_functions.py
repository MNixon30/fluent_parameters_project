import os
from skopt.sampler import Lhs
from skopt.space import Space
import numpy as np
import subprocess
import multiprocessing
from user_input_calc_functions import *







def run_meshing_scripts(project_root, fluent_path, meshing_cores):
    """
    Runs all Fluent 2D meshing journal scripts stored in <project_root>\test_files\scripts automatically.
    
    Parameters:
        project_root (str): Root folder of the project.
    """
    script_folder = os.path.join(project_root, "test_files", "scripts")

    if not os.path.exists(script_folder):
        print(f"⚠️ Folder not found: {script_folder}")
        return

    # Find all .jou files in the folder
    script_paths = [os.path.join(script_folder, f)
                    for f in os.listdir(script_folder)
                    if f.endswith(".jou")]

    if not script_paths:
        print(f"⚠️ No .jou scripts found in {script_folder}")
        return

    fluent_exe = fluent_path

    # Define the geoms folder for cleanup
    geoms_folder = os.path.join(project_root, "test_files", "geoms")

    for script in script_paths:
        print(f"🌀 Running meshing script: {os.path.basename(script)}")
        subprocess.run([fluent_exe,
                        "3d",
                        "-meshing",    # Explicit meshing mode
                        "-hidden",
                        "-g",     
                        f"-t{meshing_cores}",         # Number of threads
                        "-i", script]) # Input journal
        print(f"✅ Finished: {os.path.basename(script)}")
        
        # Clean up .fmd files created by Fluent to save space
        if os.path.exists(geoms_folder):
            fmd_files = [f for f in os.listdir(geoms_folder) if f.lower().endswith('.fmd')]
            for fmd_file in fmd_files:
                fmd_path = os.path.join(geoms_folder, fmd_file)
                try:
                    os.remove(fmd_path)
                    print(f"🗑️ Deleted .fmd file: {fmd_file}")
                except Exception as e:
                     print(f"⚠️ Could not delete {fmd_file}: {e}")






