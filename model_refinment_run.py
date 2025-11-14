import os
from typing import Optional

from user_input_calc_functions import load_setup_from_file
from model_refinment import create_model_refinment, move_ref_files, create_refinment_dps


def _get_project_folder() -> str:
    setup_params = load_setup_from_file()
    if setup_params and setup_params.get("project_folder"):
        return setup_params["project_folder"]

    while True:
        project_folder = input("Enter project folder path: ").strip()
        if project_folder:
            return project_folder


def _find_latest_rif_folder(project_folder: str) -> Optional[str]:
    test_files_dir = os.path.join(project_folder, "test_files")
    if not os.path.isdir(test_files_dir):
        return None

    rif_candidates = []
    for entry in os.listdir(test_files_dir):
        if entry.lower().startswith("rif_"):
            full_path = os.path.join(test_files_dir, entry)
            if os.path.isdir(full_path):
                rif_candidates.append((os.path.getmtime(full_path), full_path))

    if not rif_candidates:
        return None

    rif_candidates.sort(reverse=True)
    return rif_candidates[0][1]


def main():
    project_folder = _get_project_folder()
    print(f"Using project folder: {project_folder}")

    print("\nCreating refinement model...")
    create_model_refinment(project_folder)

    print("\nArchiving base run files...")
    rif_folder = move_ref_files(project_folder)
    if not rif_folder:
        raise RuntimeError("Failed to create rif archive folder.")
    print(f"Refinement archive created at: {rif_folder}")

    print("\nGenerating refinement design points...")
    create_refinment_dps(project_folder, rif_folder)


if __name__ == "__main__":
    main()