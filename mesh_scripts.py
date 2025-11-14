import os
import re

def clean_journal(journal_path):
    """
    Removes GUI/CX commands from a Fluent journal so it can run headless.
    """
    with open(journal_path, "r") as f:
        content = f.read()

    # Remove lines starting with (cx-...) or (handle-key ...) or (dolly-camera ...)
    content_clean = re.sub(r"^\(cx-[^\n]*\)|^\(dolly-camera[^\n]*\)|^\(handle-key[^\n]*\)\n?", "", content, flags=re.MULTILINE)

    with open(journal_path, "w") as f:
        f.write(content_clean)




def generate_meshing_scripts_auto(project_root, journal_template,
                                  geom_folder=r"test_files\geoms",
                                  script_folder=r"test_files\scripts",
                                  mesh_folder=r"test_files\msh",
                                  ):
    """
    Automatically generates Fluent journal scripts for all geometries.
    Replaces:
      - the hard-coded FileName line in the template with each geometry path
      - the Export Fluent 2D Mesh output path with a mesh_path
      - Input the absolute path of project root and absolute path of journal file
    """
    geom_folder = os.path.join(project_root, geom_folder)
    script_folder = os.path.join(project_root, script_folder)
    mesh_folder = os.path.join(project_root, mesh_folder)
    

    os.makedirs(script_folder, exist_ok=True)
    os.makedirs(mesh_folder, exist_ok=True)

    # Load template once
    with open(journal_template, "r") as f:
        template = f.read()

    # Find geometry files
    geom_files = [f for f in os.listdir(geom_folder) if f.endswith((".scdoc", ".scdocx", ".dsco"))]

    created_scripts = []

    for geom_file in geom_files:
        geom_path = os.path.join(geom_folder, geom_file).replace("\\", "/")
        mesh_path = os.path.join(mesh_folder, geom_file.rsplit(".", 1)[0] + ".msh.h5").replace("\\", "/")

        # 1️⃣ Replace geometry FileName in Load CAD Geometry
        journal_content = re.sub(
            r"(r'FileName': r')[^']+(')",
            fr"\1{geom_path}\2",
            template
        )

        # 2️⃣ Add mesh export command if not present
        if "Export Fluent" not in journal_content and "file/write-mesh" not in journal_content:
            # Determine workflow type and add appropriate export command
            if "2D Meshing" in journal_content:
                # For 2D workflows, use the workflow task
                export_command = f"""
(%py-exec "workflow.TaskObject['Export Fluent 2D Mesh'].Arguments.set_state({{r'FileName': r'{mesh_path}'}})")
(%py-exec "workflow.TaskObject['Export Fluent 2D Mesh'].Execute()")
/exit y
"""
            else:
                # For 3D workflows, use the direct Fluent command
                export_command = f"""
/file/write-mesh {mesh_path}
/exit y
"""
            journal_content += export_command
        else:
            # Replace existing mesh export path
            if "Export Fluent" in journal_content:
                # Replace workflow task export
                journal_content = re.sub(
                    r"(workflow\.TaskObject\['Export Fluent [23]D Mesh'\]\.Arguments\.set_state\()([^)]+)\)",
                    fr"\1{{r'FileName': r'{mesh_path}'}})",
                    journal_content
                )
            else:
                # Replace direct file command
                journal_content = re.sub(
                    r"(/file/write-mesh\s+)[^\s\n]+",
                    fr"\1{mesh_path}",
                    journal_content
                )

        # Save per-geometry journal
        journal_name = geom_file.rsplit(".", 1)[0] + "_mesh.jou"
        journal_path = os.path.join(script_folder, journal_name)

        with open(journal_path, "w") as jf:
            jf.write(journal_content)

        created_scripts.append(journal_path)
        print(f"✅ Created meshing script: {journal_name}")

    return created_scripts