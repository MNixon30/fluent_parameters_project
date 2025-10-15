import ansys.fluent.core as pyfluent

#IMPORTANT INFOMATION
# ----------------------------
# Journal PyFluent recordings must be made when doing sessions
# ----------------------------


# ----------------------------
# Choose UI mode:
# 'gui'          -> Full Fluent GUI
# 'hidden_gui'   -> Runs Fluent in background
# 'no_gui'       -> No GUI at all
# ----------------------------
UI_MODE = "gui"  # Change to "gui" if you want the full GUI

# ----------------------------
# Choose FLUENT mode:
# 'meshing'          -> Opens meshing
# 'solver'           -> Opens solver
# ----------------------------
FLUENT_MODE = "solver"

try:
    # Launch Fluent
    session = pyfluent.launch_fluent(
        ui_mode=UI_MODE, 
        mode = FLUENT_MODE, 
        precision='single', 
        processor_count=2,
        dimension=3)
    print(f"Fluent {FLUENT_MODE} launched successfully in {UI_MODE} mode.")

    session.journal.start(file_name="rear_wing_solver.py")
    input("\nPress enter when you want to stop the journal...") #Inputs only required for VS Code IDE NOT in jupyter
    session.journal.stop()
    
    # Keep Python alive so Fluent stays running
    input("\nPress Enter to exit and close Fluent...")

except Exception as e:
    print("Error launching Fluent:", e)


