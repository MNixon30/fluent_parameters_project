#Code
from user_input_calc_functions import *

project_folder = user_input_project_folder()

ref_files = user_input_files()

dim = get_simulation_dimension()

create_folders(project_root=project_folder)


for key in ["case_file", "geometry_file", "mesh_file"]:
    move_ref_file(ref_files[key], project_folder=project_folder)

for key in ["mesh_journal", "case_journal"]:
    move_script_file(ref_files[key], project_folder=project_folder)

relative_folders = {
    "geometry_file": r"ref_files\ref",
    "mesh_file": r"ref_files\ref",
    "case_file": r"ref_files\ref",
    "mesh_journal": r"ref_files\scripts",
    "case_journal": r"ref_files\scripts"
}

updated_ref_paths = update_file_paths_relative_to_project(ref_files, project_folder, relative_folders)

named_selections = get_names_from_casefile(casefile_path=updated_ref_paths["case_file"])

geom_parameters_list = choose_named_parameters(named_selections=named_selections)

geom_parameters = define_movement_ranges_with_directions(geom_parameters_list)

#lower_values, upper_values = extract_lower_upper_values_with_mapping(geom_parameters)

#get_sample_points(lower_values, upper_values, project_folder)
get_sample_points_from_ranges(geom_parameters, project_folder)

script_path = generate_spaceclaim_script(project_folder, geom_parameters, updated_ref_paths["geometry_file"], geom_parameters_list)

spaceclaim_path = find_spaceclaim_exe()

run_spaceclaim_script_headless(script_path, spaceclaim_path)

clean_journal(updated_ref_paths["mesh_journal"])

generate_meshing_scripts_auto(project_folder, updated_ref_paths["mesh_journal"])

fluent_path = find_fluent_exe()

run_meshing_scripts(project_folder, fluent_path)

generate_master_fluent_script(updated_ref_paths["case_journal"], project_folder, dim)

run_generated_fluent_script(project_folder)

summarize_fluent_results(project_folder)


