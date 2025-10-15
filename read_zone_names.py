import re
import csv
import os

def gather_zone_names(solver):
    """
    Return sorted list of unique zone names (boundary + cell) by trying several PyFluent APIs.
    Pass an active solver session (pyfluent session object).
    """
    names = set()

    # 1) Try mesh.settings tree: solver.settings.mesh.boundary / cell_zone child_names()
    try:
        mesh_settings = solver.settings.mesh
        # boundary zones (if available in this settings tree)
        if hasattr(mesh_settings, "boundary") and hasattr(mesh_settings.boundary, "child_names"):
            try:
                boundary_children = mesh_settings.boundary.child_names()
                names.update(boundary_children or [])
            except Exception:
                pass
        # cell zones
        if hasattr(mesh_settings, "cell_zone") and hasattr(mesh_settings.cell_zone, "child_names"):
            try:
                cell_children = mesh_settings.cell_zone.child_names()
                names.update(cell_children or [])
            except Exception:
                pass
    except Exception:
        # not fatal; just move to next method
        print("1 did not work")
        pass

    # 2) Try solver.setup boundary_conditions state
    try:
        setup = solver.setup
        # get_state returns nested dicts of BC types -> {zone_name: <...>}
        bc_state = setup.boundary_conditions.get_state()
        if isinstance(bc_state, dict):
            for bc_type, zone_dict in bc_state.items():
                if isinstance(zone_dict, dict):
                    for zone_name in zone_dict.keys():
                        names.add(zone_name)
    except Exception:
        print("2 did not work")
        pass

    # 3) Try TUI list_zones (text command). Some TUI calls print to console; some return values.
    #    We attempt to call list_zones and parse any returned string/list.
    try:
        tui_call = solver.tui.define.boundary_conditions.modify_zones.list_zones
        out = tui_call()  # may return None, string, list, or print to Fluent console
        if out:
            if isinstance(out, (list, tuple)):
                names.update(out)
            elif isinstance(out, str):
                # crude parse: find words at ends of lines that look like zone names
                for line in out.splitlines():
                    line = line.strip()
                    # lines often contain: id  type  kind  name
                    # capture the token that looks like a name (last token or quoted)
                    m = re.search(r'["\']?([A-Za-z0-9_\-:\. ]{1,200})["\']?$', line)
                    if m:
                        candidate = m.group(1).strip()
                        if candidate:
                            names.add(candidate)
    except Exception:
        print("3 did not work")
        # ignore TUI failure
        pass

    # 4) final: try to query post-processing surface names via field info service (if available)
    try:
        # this asks the field_data service for surface info (works when case/data or mesh loaded)
        f_info = solver.fields.field_info
        surfaces_info = f_info.get_surfaces_info()
        # surfaces_info is commonly a dict where keys are surface names
        if isinstance(surfaces_info, dict):
            names.update(surfaces_info.keys())
    except Exception:
        pass

    return sorted(names)


def get_names_from_casefile(casefile_path):
    """
    If you have an offline case file (.cas.h5), use CaseFile reader to extract surface names (no live solver needed).
    """
    from ansys.fluent.core.filereader.case_file import CaseFile
    reader = CaseFile(case_file_name=casefile_path)
    mesh_reader = reader.get_mesh()
    # get_surface_names() is provided by the CaseFile mesh reader (returns list)
    return mesh_reader.get_surface_names()

def clean_zone_names(raw_names):
    """
    Filters out Fluent internal/non-geometric names from list_zones output.
    """
    # Common internal or config keywords (expand if needed)
    ignore_keywords = [
        "setup", "model", "advanced", "mass_flow", "target_mass_flow",
        "method", "nrbc", "general", "turbo", "parameter", "condition"
    ]

    clean = []
    for name in raw_names:
        lname = name.lower()
        # skip if any ignored word occurs or if it has ":" (e.g. interior:fluid_domain)
        if any(k in lname for k in ignore_keywords):
            continue
        if ":" in name:  # skip linked internal zones
            continue
        # skip empty or single-char strings
        if len(name.strip()) <= 1:
            continue
        clean.append(name)
    return sorted(set(clean))
