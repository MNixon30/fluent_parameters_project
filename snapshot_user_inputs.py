from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from snapshot_functions import (
    ContourPlotSpec,
    SnapshotPreferences,
    SurfaceSpec,
    display_nearest_design_points,
    get_design_points_path,
    list_available_design_points,
    load_project_folder_from_setup_config,
    load_snapshot_preferences,
    normalise_design_points,
    save_snapshot_preferences,
    search_design_points,
    view_design_points,
)

VALID_ORIENTATIONS = {"xy", "yz", "zx"}
VALID_FIELDS = {"velocity-magnitude", "pressure"}
SETUP_CONFIG_NAME = "setup_config.json"


def _load_dimension_from_setup_config(project_folder: Path) -> Optional[int]:
    """Attempt to read `dimension` from setup_config.json.
    
    Searches in:
    1. The project folder
    2. The automation directory (where this script is located)
    
    If setup_config.json is found in the automation directory, verifies that
    its project_folder matches the selected project folder.
    
    Returns:
        Dimension value (2 or 3) if found, None otherwise.
    """
    # Try to find setup_config.json in the project folder first
    config_path = project_folder / SETUP_CONFIG_NAME
    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as fp:
                data = json.load(fp)
            dimension = data.get("dimension")
            if dimension is not None:
                try:
                    dim_int = int(dimension)
                    if dim_int in [2, 3]:
                        return dim_int
                except (TypeError, ValueError):
                    pass
        except (json.JSONDecodeError, OSError):
            pass
    
    # Also try in the automation directory (where this script is located)
    automation_dir = Path(__file__).resolve().parent
    config_path = automation_dir / SETUP_CONFIG_NAME
    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as fp:
                data = json.load(fp)
            # Verify that the project_folder in setup_config.json matches the selected project folder
            config_project_folder = data.get("project_folder")
            if config_project_folder:
                try:
                    config_project_path = Path(config_project_folder).expanduser().resolve()
                    if config_project_path == project_folder.resolve():
                        dimension = data.get("dimension")
                        if dimension is not None:
                            try:
                                dim_int = int(dimension)
                                if dim_int in [2, 3]:
                                    return dim_int
                            except (TypeError, ValueError):
                                pass
                except Exception:
                    pass
        except (json.JSONDecodeError, OSError):
            pass
    
    return None


def _prompt(text: str, default: Optional[str] = None) -> str:
    prompt_text = text
    if default is not None:
        prompt_text += f" [{default}]"
    prompt_text += ": "
    response = input(prompt_text).strip()
    if not response and default is not None:
        return default
    return response


def _prompt_project_folder() -> Path:
    default_path = load_project_folder_from_setup_config()
    if default_path is not None:
        print(f"[INFO] Default project folder detected from setup_config.json: {default_path}")
        use_default = _prompt("Use this project folder? (Y/n)", default="y").lower()
        if use_default in {"", "y", "yes"}:
            return default_path

    while True:
        path_str = _prompt(
            "Enter project folder",
            default=str(default_path) if default_path is not None else str(Path.cwd()),
        )
        project_path = Path(path_str).expanduser().resolve()
        if project_path.exists():
            return project_path
        print(f"[ERROR] Project folder does not exist: {project_path}")


def _display_summary(preferences: SnapshotPreferences, available_dp: List[int]) -> None:
    print("\nCurrent snapshot configuration:")
    print("  Surfaces:")
    if preferences.surfaces:
        for idx, surface in enumerate(preferences.surfaces, start=1):
            print(
                f"    {idx}. {surface.name} | plane={surface.orientation.upper()} | offset={surface.offset}"  # noqa: E501
            )
    else:
        print("    (none)")

    print("  Plots:")
    if preferences.contour_plots:
        for idx, plot in enumerate(preferences.contour_plots, start=1):
            print(
                f"    {idx}. contour | field={plot.field} | surface={plot.surface_name}"
            )
    else:
        print("    (none)")

    print("  Design points:")
    if not available_dp:
        print("    (no DesignPoints.csv detected)")
    elif preferences.design_points is None:
        print("    (not specified)")
    else:
        if set(preferences.design_points) == set(available_dp):
            print("    All available design points")
        else:
            print(f"    Selected indices: {preferences.design_points}")


def _view_configuration(preferences: SnapshotPreferences) -> None:
    available_dp = list_available_design_points(preferences.project_folder)
    _display_summary(preferences, available_dp)


def _add_surface(surfaces: List[SurfaceSpec]) -> None:
    print("\nAdd surface")
    print("  1. Plane surface")
    print("  0. Cancel")
    choice = _prompt("Select surface type", default="1")
    if choice == "0":
        return
    if choice != "1":
        print("[ERROR] Unsupported surface type selected.")
        return

    orientation = _prompt(
        "Plane orientation (xy/yz/zx)",
        default=surfaces[-1].orientation if surfaces else "xy",
    ).lower()
    if orientation not in VALID_ORIENTATIONS:
        print("[ERROR] Orientation must be one of: xy, yz, zx")
        return

    offset_str = _prompt("Plane offset distance", default="0.0")
    try:
        offset = float(offset_str)
    except ValueError:
        print("[ERROR] Offset must be a number.")
        return

    name_default = f"{orientation}_plane_{len(surfaces) + 1}"
    name = _prompt("Surface name", default=name_default)
    surfaces.append(SurfaceSpec(name=name, orientation=orientation, offset=offset))
    print(f"[INFO] Added plane surface '{name}'.")


def _select_surface_index(surfaces: List[SurfaceSpec], action: str) -> Optional[int]:
    if not surfaces:
        print("[INFO] No surfaces available.")
        return None
    for idx, surface in enumerate(surfaces, start=1):
        print(
            f"  {idx}. {surface.name} | plane={surface.orientation.upper()} | offset={surface.offset}"  # noqa: E501
        )
    while True:
        raw = _prompt(f"Select surface to {action} (blank to cancel)", default="")
        if not raw.strip():
            return None
        try:
            value = int(raw)
        except ValueError:
            print("[ERROR] Enter a valid number.")
            continue
        if 1 <= value <= len(surfaces):
            return value - 1
        print("[ERROR] Selection out of range.")


def _update_surface(surfaces: List[SurfaceSpec], idx: int) -> None:
    surface = surfaces[idx]
    orientation = _prompt(
        "New orientation (xy/yz/zx)",
        default=surface.orientation,
    ).lower()
    if orientation not in VALID_ORIENTATIONS:
        print("[ERROR] Orientation must be one of: xy, yz, zx")
        return

    while True:
        offset_str = _prompt("New offset", default=str(surface.offset))
        try:
            offset = float(offset_str)
        except ValueError:
            print("[ERROR] Offset must be a number.")
            continue
        break

    name = _prompt("New surface name", default=surface.name)
    surfaces[idx] = SurfaceSpec(name=name, orientation=orientation, offset=offset)
    print(f"[INFO] Surface '{name}' updated.")


def _surface_actions_menu(surfaces: List[SurfaceSpec]) -> None:
    idx = _select_surface_index(surfaces, action="modify")
    if idx is None:
        return

    while True:
        surface = surfaces[idx]
        print("\nSurface actions:")
        print(
            f"  Selected: {surface.name} | plane={surface.orientation.upper()} | offset={surface.offset}"  # noqa: E501
        )
        print("  1. Modify surface")
        print("  2. Remove surface")
        print("  0. Back")
        choice = _prompt("Select an option", default="1")

        if choice == "1":
            _update_surface(surfaces, idx)
            return
        elif choice == "2":
            removed = surfaces.pop(idx)
            print(f"[INFO] Removed surface '{removed.name}'.")
            return
        elif choice == "0":
            return
        else:
            print("[ERROR] Invalid option.")


def _add_contour_plot(preferences: SnapshotPreferences) -> None:
    if not preferences.surfaces:
        print("[INFO] Define at least one surface before adding plots.")
        return

    print("\nAdd plot")
    print("  1. Contour plot")
    print("  0. Cancel")
    choice = _prompt("Select plot type", default="1")
    if choice == "0":
        return
    if choice != "1":
        print("[ERROR] Unsupported plot type selected.")
        return

    remaining_fields = sorted(VALID_FIELDS)
    print("Available contour fields:")
    for idx, field in enumerate(remaining_fields, start=1):
        print(f"  {idx}. {field}")
    while True:
        raw_field = _prompt("Select field", default="1")
        try:
            field_index = int(raw_field)
        except ValueError:
            print("[ERROR] Enter a valid number.")
            continue
        if 1 <= field_index <= len(remaining_fields):
            field = remaining_fields[field_index - 1]
            break
        print("[ERROR] Selection out of range.")

    print("Available surfaces:")
    for idx, surface in enumerate(preferences.surfaces, start=1):
        print(
            f"  {idx}. {surface.name} | plane={surface.orientation.upper()} | offset={surface.offset}"  # noqa: E501
        )
    while True:
        raw_surface = _prompt("Select surface", default="1")
        try:
            surface_index = int(raw_surface)
        except ValueError:
            print("[ERROR] Enter a valid number.")
            continue
        if 1 <= surface_index <= len(preferences.surfaces):
            surface = preferences.surfaces[surface_index - 1]
            break
        print("[ERROR] Selection out of range.")

    plot_name = _prompt(
        "Plot label", default=f"contour_{surface.name}_{field.replace('-', '_')}"
    )
    preferences.contour_plots.append(
        ContourPlotSpec(surface_name=surface.name, field=field)
    )
    print(f"[INFO] Added contour plot '{plot_name}' for surface '{surface.name}'.")


def _select_plot_index(preferences: SnapshotPreferences, action: str) -> Optional[int]:
    plots = preferences.contour_plots
    if not plots:
        print("[INFO] No plots configured.")
        return None
    for idx, plot in enumerate(plots, start=1):
        print(f"  {idx}. contour | field={plot.field} | surface={plot.surface_name}")
    while True:
        raw = _prompt(f"Select plot to {action} (blank to cancel)", default="")
        if not raw.strip():
            return None
        try:
            value = int(raw)
        except ValueError:
            print("[ERROR] Enter a valid number.")
            continue
        if 1 <= value <= len(plots):
            return value - 1
        print("[ERROR] Selection out of range.")


def _update_contour_plot(preferences: SnapshotPreferences, idx: int) -> None:
    plot = preferences.contour_plots[idx]

    fields = sorted(VALID_FIELDS)
    print("Available contour fields:")
    for opt_idx, field in enumerate(fields, start=1):
        default_marker = " (current)" if field == plot.field else ""
        print(f"  {opt_idx}. {field}{default_marker}")
    while True:
        raw_field = _prompt(
            "Select new field", default=str(fields.index(plot.field) + 1)
        )
        try:
            field_index = int(raw_field)
        except ValueError:
            print("[ERROR] Enter a valid number.")
            continue
        if 1 <= field_index <= len(fields):
            new_field = fields[field_index - 1]
            break
        print("[ERROR] Selection out of range.")

    print("Available surfaces:")
    for opt_idx, surface in enumerate(preferences.surfaces, start=1):
        default_marker = " (current)" if surface.name == plot.surface_name else ""
        print(
            f"  {opt_idx}. {surface.name} | plane={surface.orientation.upper()} | offset={surface.offset}{default_marker}"  # noqa: E501
        )
    while True:
        raw_surface = _prompt(
            "Select new surface",
            default=str(
                next(
                    (i + 1 for i, s in enumerate(preferences.surfaces) if s.name == plot.surface_name),
                    1,
                )
            ),
        )
        try:
            surface_index = int(raw_surface)
        except ValueError:
            print("[ERROR] Enter a valid number.")
            continue
        if 1 <= surface_index <= len(preferences.surfaces):
            new_surface = preferences.surfaces[surface_index - 1]
            break
        print("[ERROR] Selection out of range.")

    preferences.contour_plots[idx] = ContourPlotSpec(
        surface_name=new_surface.name,
        field=new_field,
    )
    print(
        f"[INFO] Plot updated to contour field '{new_field}' on surface '{new_surface.name}'."
    )


def _plot_actions_menu(preferences: SnapshotPreferences) -> None:
    idx = _select_plot_index(preferences, action="modify")
    if idx is None:
        return

    while True:
        plot = preferences.contour_plots[idx]
        print("\nPlot actions:")
        print(f"  Selected: contour | field={plot.field} | surface={plot.surface_name}")
        print("  1. Modify plot")
        print("  2. Remove plot")
        print("  0. Back")
        choice = _prompt("Select an option", default="1")

        if choice == "1":
            if not preferences.surfaces:
                print("[INFO] No surfaces defined; cannot modify plot.")
                return
            _update_contour_plot(preferences, idx)
            return
        elif choice == "2":
            removed = preferences.contour_plots.pop(idx)
            print(
                f"[INFO] Removed contour plot (field={removed.field}, surface={removed.surface_name})."
            )
            return
        elif choice == "0":
            return
        else:
            print("[ERROR] Invalid option.")


def _view_design_points_menu(project_folder: Path) -> None:
    """Display design points from DesignPoints.csv."""
    view_design_points(project_folder)


def _search_design_points_menu(project_folder: Path) -> None:
    """Search for the top 3 nearest design points to a search point."""
    design_points_path = get_design_points_path(project_folder)
    if not design_points_path.exists():
        print("[ERROR] DesignPoints.csv not found.")
        print(f"Expected location: {design_points_path}")
        return

    try:
        import pandas as pd

        df = pd.read_csv(design_points_path)
        parameter_names = df.columns.tolist()

        print(f"\nSearch Design Points")
        print(f"Parameters: {', '.join(parameter_names)}")
        print(f"Enter values for each parameter (space-separated):")
        print(f"Example: {' '.join(['0.0'] * len(parameter_names))}")

        while True:
            raw_input = _prompt("Enter search point values", default="")
            if not raw_input.strip():
                print("[INFO] Search cancelled.")
                return

            try:
                values = [float(x.strip()) for x in raw_input.split()]
                if len(values) != len(parameter_names):
                    print(
                        f"[ERROR] Expected {len(parameter_names)} values, got {len(values)}."
                    )
                    continue

                # Perform search
                results = search_design_points(project_folder, values, top_k=3)
                display_nearest_design_points(results, parameter_names)
                return

            except ValueError:
                print("[ERROR] Invalid input. Enter space-separated numbers.")
            except Exception as exc:
                print(f"[ERROR] {exc}")
                return

    except ImportError:
        print("[ERROR] pandas is required for design point search.")
        print("Install it with: pip install pandas numpy")
    except Exception as exc:
        print(f"[ERROR] Could not search design points: {exc}")


def _manage_design_points(preferences: SnapshotPreferences) -> None:
    available = list_available_design_points(preferences.project_folder)
    if not available:
        print("[INFO] No DesignPoints.csv found or file has no entries.")
        preferences.design_points = None
        return

    while True:
        print("\nDesign point menu:")
        print("  1. View design points")
        print("  2. Search design points")
        print("  3. Use all available design points")
        print("  4. Choose specific design points")
        print("  5. Clear selection")
        print("  6. Refresh available list")
        print("  0. Back")
        choice = _prompt("Select an option", default="0")

        if choice == "1":
            _view_design_points_menu(preferences.project_folder)
        elif choice == "2":
            _search_design_points_menu(preferences.project_folder)
        elif choice == "3":
            preferences.design_points = available
            print(f"[INFO] Using all {len(available)} design points.")
        elif choice == "4":
            print(f"Available design point indices: {available}")
            raw = _prompt("Enter indices (comma separated)")
            entries = [entry for entry in raw.split(",") if entry.strip()]
            try:
                chosen = normalise_design_points(entries)
            except ValueError as exc:
                print(f"[ERROR] {exc}")
                continue
            missing = [idx for idx in chosen if idx not in available]
            if missing:
                print(f"[ERROR] Indices not available: {missing}")
                continue
            preferences.design_points = chosen
            print(f"[INFO] Selected design points: {chosen}")
        elif choice == "5":
            preferences.design_points = None
            print("[INFO] Cleared design point selection.")
        elif choice == "6":
            available = list_available_design_points(preferences.project_folder)
            print("[INFO] Design point list refreshed.")
            if not available:
                print("[INFO] No design points available after refresh.")
                preferences.design_points = None
                return
        elif choice == "0":
            return
        else:
            print("[ERROR] Invalid option.")


def main() -> int:
    print("CFD Snapshot User Input Menu")
    project_folder = _prompt_project_folder()

    # Check dimension from setup_config.json - snapshots only work for 3D simulations
    dimension = _load_dimension_from_setup_config(project_folder)
    if dimension is None:
        print("\n[ERROR] Could not read dimension from setup_config.json.")
        print("[ERROR] Please ensure setup_config.json exists and contains a 'dimension' field.")
        print("[ERROR] Snapshot setup requires a valid setup configuration.")
        return 1
    
    if dimension != 3:
        print(f"\n[ERROR] Snapshot/contour setup is only available for 3D simulations.")
        print(f"[ERROR] Current simulation dimension: {dimension}D")
        print("[ERROR] Please configure a 3D simulation in Setup Wizard before using this feature.")
        return 1
    
    print(f"[INFO] Simulation dimension verified: {dimension}D (required for snapshots)")

    try:
        preferences = load_snapshot_preferences(project_folder)
        preferences.project_folder = project_folder
        print("[INFO] Loaded existing snapshot configuration.")
    except FileNotFoundError:
        preferences = SnapshotPreferences(project_folder=project_folder)
        print("[INFO] Starting with a new snapshot configuration.")

    _view_configuration(preferences)

    while True:
        print("\nMain menu:")
        print("  1. View configuration")
        print("  2. Add surface")
        print("  3. Edit surface")
        print("  4. Add plot")
        print("  5. Edit plot")
        print("  6. Select design points")
        print("  7. Save and exit")
        print("  0. Exit without saving")

        choice = _prompt("Select an option", default="7")

        if choice == "1":
            _view_configuration(preferences)
        elif choice == "2":
            _add_surface(preferences.surfaces)
        elif choice == "3":
            _surface_actions_menu(preferences.surfaces)
        elif choice == "4":
            _add_contour_plot(preferences)
        elif choice == "5":
            _plot_actions_menu(preferences)
        elif choice == "6":
            _manage_design_points(preferences)
        elif choice == "7":
            config_path = save_snapshot_preferences(preferences)
            print(f"\n[SUCCESS] Snapshot configuration saved to {config_path}")
            return 0
        elif choice == "0":
            print("[INFO] Exiting without saving changes.")
            return 0
        else:
            print("[ERROR] Invalid option.")


if __name__ == "__main__":
    raise SystemExit(main())
