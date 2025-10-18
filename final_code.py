#Code
from user_input_calc_functions import *
from mesh_to_case_solver import *
from folder_management import *
from solver_setup import *
from sc_files import *
from mesh_scripts import *
from batch_solver import *
from post_process import *

project_folder = user_input_project_folder()

ref_files = user_input_files()

dim = get_simulation_dimension()

meshing_cores = user_input_mesh_cores()
solver_cores = user_input_solver_cores()

spaceclaim_path = find_spaceclaim_exe()

fluent_path = find_fluent_exe()

solver_type = choose_solver_type()

create_folders(project_root=project_folder)

updated_ref_paths = move_all_ref_files(ref_files, project_folder)

named_selections = get_names_from_casefile(casefile_path=updated_ref_paths["case_file"])

geom_parameters_list = choose_named_parameters(named_selections=named_selections)

geom_parameters = define_movement_ranges_with_directions(geom_parameters_list)

design_points_path, num_design_points = get_sample_points_from_ranges(geom_parameters, project_folder)

# Now that we know how many design points will be generated, ask about saving
save_design_points = get_design_points_to_save(num_design_points)

script_path = generate_spaceclaim_script(project_folder, geom_parameters, updated_ref_paths["geometry_file"], geom_parameters_list)

# Ask user for final confirmation before starting calculation
if not start_calculation():
    print("❌ Calculation cancelled. Exiting program.")
    exit()

run_spaceclaim_script_headless(script_path, spaceclaim_path)

clean_journal(updated_ref_paths["mesh_journal"])

generate_meshing_scripts_auto(project_folder, updated_ref_paths["mesh_journal"])

if solver_type == "batch":
    # Traditional batch processing
    print("\n🔄 Starting Batch Processing...")
    run_meshing_scripts(project_folder, fluent_path, meshing_cores)
    
    generate_master_fluent_script(updated_ref_paths["case_journal"], project_folder, dim, solver_cores, save_design_points)
    run_generated_fluent_script(project_folder)
    
elif solver_type == "sequential":
    # Sequential mesh-case processing
    print("\n🔄 Starting Sequential Processing...")
    generate_individual_case_files(updated_ref_paths["case_journal"], project_folder, dim, solver_cores, save_design_points)
    run_fluent_mesh_case(project_folder, fluent_path, meshing_cores)

summarize_fluent_results(project_folder)


