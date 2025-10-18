"""
Setup:
-User defines project folder
-User defines the 5 files required to run the simulation    -> use a ttk notebook
-User defined the simulation dimension (2D or 3D)
-User defines cpu cores for meshing and solving (seperatly)
-User defines spaceclaim and fluent locations (or auto detects them)
-Finally the user chooses the solver type (batch or sequential)

"""

#project files
# from final_code import * # idk man

# GUI libraries
from tkinter import ttk, filedialog, messagebox
from ttkthemes import ThemedTk # pip install ttkthemes

"""
Open file explorer to select a directory
"""
def selectFolderCallBack():
    filedialog.askdirectory()

"""
Display the GUi window for setup
"""
def showSetupWindow(window):
    assert isinstance(window, ThemedTk)
    ttk.Button(window, text="Select Folder", command=selectFolderCallBack).pack()
    # messagebox.askyesno(title="title", message='msg')
    return


# Window setup
window = ThemedTk(theme="breeze")
window.title("Fluent Parameters");
window.geometry("800x600")
# window.minsize(400, 400) # TODO



# d_bug: test element
# ttk.Button(window, text="Quit", command=window.destroy).grid(column = 0, row = 1  )


# showSetupWindow(window)
window.mainloop()