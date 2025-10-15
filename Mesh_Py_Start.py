import ansys.fluent.core as pyfluent

session = pyfluent.launch_fluent(
        ui_mode='gui', 
        mode = 'meshing', 
        precision='double', 
        processor_count=2,
        dimension=3)

workflow = session.workflow
meshing = session.meshing


#Optional Loop

folder_path = Path("C:/Users/mitch/Ravens_Racing_CFD/Front_Wing_Study/geoms_files/dp0/Geom-2/DM")
counter = 0
for file in folder_path.rglob("*.*"): 
        counter += 1
        workflow = session.workflow
        meshing = session.meshing
        preferences = session.preferences
        load_path = file.as_posix()
        save_path = r"C:\Users\mitch\Ravens_Racing_CFD\Front_Wing_Study\geoms_files\dp0\Mesh\Mesh-1_{:02d}.msh.h5".format(counter)
