#Folder Generation for automation

import os
folders = {
    "ref_files": ["ref", "scripts"],
    "test_files": ["cas", "dps", "geoms", "msh", "out"]
}
current_dir = os.getcwd()
for main_folder, subfolders in folders.items():
    main_path = os.path.join(current_dir, main_folder)
    os.makedirs(main_path, exist_ok=True)  # Create main folder
    for subfolder in subfolders:
        os.makedirs(os.path.join(main_path, subfolder), exist_ok=True)