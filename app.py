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
Sidebar element for all pages
"""
def getSidebar(window):
    sidebar = ttk.Frame(window, width=window.winfo_reqwidth(), height=window.winfo_reqheight())

    SIDEBAR_WIDTH = 25
    ttk.Label(window, text="Label test 1", width=SIDEBAR_WIDTH, anchor="center").grid(column = 0, row = 0, pady=5)
    ttk.Button(window, text="Setup", width=SIDEBAR_WIDTH, command=showSetupWindow(window)).grid(column = 0, row = 1, pady=5)
    return sidebar

"""
Display the "setup" GUI page
"""
def showSetupWindow(window):
    assert isinstance(window, ThemedTk)
    # ttk.Button(window, text="Select Folder", command=selectFolderCallBack).pack()
    # messagebox.askyesno(title="title", message='msg')
    return


# Window setup
window = ThemedTk(theme="breeze")
window.title("Fluent Parameters");
window.geometry("800x600")
# window.minsize(400, 400) # TODO


# BEGIN TEST
# content = ttk.Frame(window, width=800, height=600)
# frame = ttk.Frame(content,  borderwidth=5, relief="ridge", width=200, height=200)
# namelbl = ttk.Label(content, text="Name")
# name = ttk.Entry(content)

# onevar = True
# twovar = True
# threevar = True
# one = ttk.Checkbutton(content, text="One", variable=onevar, onvalue=True)
# two = ttk.Checkbutton(content, text="Two", variable=twovar, onvalue=True)
# three = ttk.Checkbutton(content, text="Three", variable=threevar, onvalue=True)
# ok = ttk.Button(content, text="Okay")
# cancel = ttk.Button(content, text="Cancel")

# content.grid(column=0, row=0)
# frame.grid(column=0, row=0, columnspan=3, rowspan=2)
# namelbl.grid(column=3, row=0, columnspan=2)
# name.grid(column=3, row=1, columnspan=2)
# one.grid(column=0, row=5)
# two.grid(column=1, row=5)
# three.grid(column=2, row=5)
# ok.grid(column=3, row=5)
# cancel.grid(column=4, row=5)

#END


# d_bug: test element
# ttk.Button(window, text="Quit", command=window.destroy).grid(column = 0, row = 1  )


# showSetupWindow(window)
getSidebar(window)
window.mainloop()