import os
import shutil

def create_folders(project_root):
    """
    Create a structured folder hierarchy inside the specified project directory.

    Parameters:
        project_root (str): Path to the root directory where folders will be created.

    Folders created:
    - ref_files/
        - ref/
        - scripts/
    - test_files/
        - cas/
        - dps/
        - geoms/
        - msh/
        - out/
        - scripts/
    """

    # Define main folders and their respective subfolders
    folders = {
        "ref_files": ["ref", "scripts"],
        "test_files": ["cas", "dps", "geoms", "msh", "out", "scripts", "cas_scripts", "out_final"]
    }

    # Ensure the project root exists
    os.makedirs(project_root, exist_ok=True)

    # Loop over main folders
    for main_folder, subfolders in folders.items():
        # Full path of the main folder (inside the given project root)
        main_path = os.path.join(project_root, main_folder)
        
        # Create the main folder
        os.makedirs(main_path, exist_ok=True)
        
        # Loop over and create each subfolder
        for subfolder in subfolders:
            os.makedirs(os.path.join(main_path, subfolder), exist_ok=True)

    # Function does not return anything
    return None



def move_ref_file(source_file, project_folder):
    """
    Move a file to the project's ref_files/scripts folder.

    Parameters:
        source_file (str): Full path to the source file.
        project_folder (str): Absolute path to the project root folder.

    Returns:
        str: Absolute path of the moved file.
    """

    # Define the relative target path
    relative_target = r"ref_files\ref"

    # Combine the absolute project folder with the relative path
    target_folder = os.path.join(project_folder, relative_target)

    # Ensure the target folder exists
    os.makedirs(target_folder, exist_ok=True)

    # Build the full destination path
    filename = os.path.basename(source_file)
    destination_file = os.path.join(target_folder, filename)

    # Move the file
    shutil.move(source_file, destination_file)

    print(f"✅ File moved: {source_file} → {destination_file}")
    return destination_file




def move_script_file(source_file, project_folder):
    """
    Move a file to the project's ref_files/scripts folder.

    Parameters:
        source_file (str): Full path to the source file.
        project_folder (str): Absolute path to the project root folder.

    Returns:
        str: Absolute path of the moved file.
    """

    # Define the relative target path
    relative_target = r"ref_files\scripts"

    # Combine the absolute project folder with the relative path
    target_folder = os.path.join(project_folder, relative_target)

    # Ensure the target folder exists
    os.makedirs(target_folder, exist_ok=True)

    # Build the full destination path
    filename = os.path.basename(source_file)
    destination_file = os.path.join(target_folder, filename)

    # Move the file
    shutil.move(source_file, destination_file)

    print(f"✅ File moved: {source_file} → {destination_file}")
    return destination_file


def update_file_paths_relative_to_project(file_paths, project_folder, relative_folders):
    """
    Create a new dictionary with updated file paths in project-relative folders,
    without moving the files.

    Parameters:
        file_paths (dict): Original dictionary of file paths.
        project_folder (str): Absolute path to the project root.
        relative_folders (dict): Dictionary mapping file keys to relative folders inside project_folder.

    Returns:
        dict: Same keys as `file_paths`, values are new absolute paths.
    """
    updated_paths = {}
    
    for key, original_path in file_paths.items():
        if key not in relative_folders:
            raise KeyError(f"No relative folder specified for '{key}'")
        
        filename = os.path.basename(original_path)
        target_folder = os.path.join(project_folder, relative_folders[key])
        new_path = os.path.join(target_folder, filename)
        updated_paths[key] = new_path

    return updated_paths


def move_all_ref_files(ref_files, project_folder):
    """
    Move all reference files to their appropriate project folders.
    
    Parameters:
        ref_files (dict): Dictionary of file paths
        project_folder (str): Project root folder path
    
    Returns:
        dict: Updated file paths relative to project folder
    """
    # Move reference files
    for key in ["case_file", "geometry_file", "mesh_file"]:
        move_ref_file(ref_files[key], project_folder=project_folder)
    
    # Move script files
    for key in ["mesh_journal", "case_journal"]:
        move_script_file(ref_files[key], project_folder=project_folder)
    
    # Define relative folder mappings
    relative_folders = {
        "geometry_file": r"ref_files\ref",
        "mesh_file": r"ref_files\ref",
        "case_file": r"ref_files\ref",
        "mesh_journal": r"ref_files\scripts",
        "case_journal": r"ref_files\scripts"
    }
    
    # Update file paths to be relative to project
    updated_ref_paths = update_file_paths_relative_to_project(ref_files, project_folder, relative_folders)
    
    return updated_ref_paths