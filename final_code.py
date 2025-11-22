#Code
from user_input_calc_functions import workflow_selection_menu, main_menu

# Main program entry point
if __name__ == "__main__":
    # First, select workflow type
    workflow_type = workflow_selection_menu()
    # Then, launch main menu with selected workflow
    main_menu(workflow_type=workflow_type)

