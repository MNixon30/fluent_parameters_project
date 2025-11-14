import json
import os
from datetime import datetime
from typing import List, Optional

import matplotlib.pyplot as plt

from graph_functions import (
    plot_aero_maps,
    plot_cfd_results,
    plot_output_correlation_heatmap,
    plot_parameter_output_scatter,
)
from post_process import parse_results_for_analysis, summarize_fluent_results


def _resolve_project_folder(initial: Optional[str] = None) -> str:
    """
    Resolve the project folder either from the provided value, setup_config.json,
    or by prompting the user.
    """
    if initial and os.path.isdir(initial):
        return os.path.abspath(initial)

    setup_path = os.path.join(os.getcwd(), "setup_config.json")
    if os.path.exists(setup_path):
        try:
            with open(setup_path, "r", encoding="utf-8") as f:
                setup_data = json.load(f)
            project_folder = setup_data.get("project_folder")
            if project_folder and os.path.isdir(project_folder):
                return os.path.abspath(project_folder)
        except Exception as exc:
            print(f"[WARNING] Could not read setup_config.json: {exc}")

    while True:
        user_input = input("Enter project folder path: ").strip('"').strip()
        if user_input and os.path.isdir(user_input):
            return os.path.abspath(user_input)
        print("Invalid project folder. Please try again.")


def _prompt_indices(prompt: str, options: List[str], allow_all: bool = True) -> List[int]:
    """
    Prompt the user to select indices for the provided options list.
    Returns zero-based indices.
    """
    if not options:
        return []

    print(f"\n{prompt}")
    for idx, name in enumerate(options, start=1):
        print(f"  {idx}. {name}")
    if allow_all:
        print("  0. All")

    while True:
        selection = input("Select by number (comma-separated): ").strip()
        if not selection and allow_all:
            return list(range(len(options)))

        parts = [item.strip() for item in selection.split(",") if item.strip()]
        indices: List[int] = []

        try:
            for part in parts:
                num = int(part)
                if num == 0 and allow_all:
                    return list(range(len(options)))
                if num < 1 or num > len(options):
                    raise ValueError
                indices.append(num - 1)
            if indices:
                seen = set()
                unique_indices = []
                for idx in indices:
                    if idx not in seen:
                        unique_indices.append(idx)
                        seen.add(idx)
                return unique_indices
        except ValueError:
            pass

        print("Invalid selection. Please enter valid numbers separated by commas.")


def _prompt_int(prompt: str, default: int, minimum: int, maximum: int) -> int:
    while True:
        value = input(f"{prompt} [{default}]: ").strip()
        if not value:
            return default
        try:
            num = int(value)
            if minimum <= num <= maximum:
                return num
        except ValueError:
            pass
        print(f"Enter an integer between {minimum} and {maximum}.")


def _load_analysis_data(project_folder: str, refresh_summary: bool) -> Optional[dict]:
    if refresh_summary:
        summarize_fluent_results(project_folder)

    data = parse_results_for_analysis(project_folder)
    if not data:
        print("[ERROR] Unable to load analysis data. "
              "Ensure design points and summary outputs are available.")
        return None
    return data


def _ensure_data_available(current_data: Optional[dict], project_folder: str) -> Optional[dict]:
    if current_data is None:
        return _load_analysis_data(project_folder, refresh_summary=True)
    return current_data


def _plot_surfaces(data: dict):
    parameter_names = data["parameter_names"]
    output_names = data["output_names"]
    if not parameter_names or not output_names:
        print("No parameters or outputs available for plotting.")
        return

    selected_inputs = _prompt_indices("Select input parameters for surface plots:", parameter_names)
    if not selected_inputs:
        print("No input parameters selected. Skipping surface plots.")
        return

    selected_outputs = _prompt_indices("Select output parameters for surface plots:", output_names)
    if not selected_outputs:
        print("No output parameters selected. Skipping surface plots.")
        return

    grid_res = _prompt_int("Grid resolution (higher = smoother surfaces)", default=50, minimum=10, maximum=200)

    figures = plot_cfd_results(
        data["data_matrix"],
        data["output_matrix"],
        parameter_names,
        output_names,
        grid_resolution=grid_res,
        selected_inputs=selected_inputs,
        selected_outputs=selected_outputs,
    )
    _prompt_save_figures(figures, data["project_folder"])


def _plot_scatter(data: dict):
    parameter_names = data["parameter_names"]
    output_names = data["output_names"]
    if not parameter_names or not output_names:
        print("No parameters or outputs available for plotting.")
        return

    selected_inputs = _prompt_indices("Select input parameters for scatter plots:", parameter_names)
    selected_outputs = _prompt_indices("Select output parameters for scatter plots:", output_names)

    if not selected_inputs or not selected_outputs:
        print("Input and output selections are required for scatter plots.")
        return

    figures = plot_parameter_output_scatter(
        data["data_matrix"],
        data["output_matrix"],
        parameter_names,
        output_names,
        selected_inputs=selected_inputs,
        selected_outputs=selected_outputs,
    )
    _prompt_save_figures(figures, data["project_folder"])


def _plot_aero_maps(data: dict):
    parameter_names = data["parameter_names"]
    output_names = data["output_names"]
    if len(parameter_names) < 2 or not output_names:
        print("Aero maps require at least two input parameters and one output parameter.")
        return

    selected_inputs = _prompt_indices("Select input parameters for aero maps:", parameter_names)
    if len(selected_inputs) < 2:
        print("Select at least two input parameters to generate aero maps.")
        return

    selected_outputs = _prompt_indices("Select output parameters for aero maps:", output_names)
    if not selected_outputs:
        print("At least one output parameter must be selected for aero maps.")
        return

    grid_res = _prompt_int("Grid resolution (higher = smoother heatmap)", default=60, minimum=10, maximum=250)

    figures = plot_aero_maps(
        data["data_matrix"],
        data["output_matrix"],
        parameter_names,
        output_names,
        grid_resolution=grid_res,
        selected_inputs=selected_inputs,
        selected_outputs=selected_outputs,
    )
    _prompt_save_figures(figures, data["project_folder"])


def _plot_correlation(data: dict):
    output_names = data["output_names"]
    if len(output_names) < 2:
        print("At least two outputs are required to compute correlations.")
        return

    selected_outputs = _prompt_indices("Select output parameters for correlation heatmap:", output_names)
    if len(selected_outputs) < 2:
        print("Select at least two outputs to compute correlations.")
        return

    figures = plot_output_correlation_heatmap(
        data["output_matrix"],
        output_names,
        selected_outputs=selected_outputs,
    )
    _prompt_save_figures(figures, data["project_folder"])


def _print_summary(data: dict):
    print("\nAvailable Input Parameters:")
    for idx, name in enumerate(data["parameter_names"], start=1):
        print(f"  {idx}. {name}")

    print("\nAvailable Output Parameters:")
    for idx, name in enumerate(data["output_names"], start=1):
        print(f"  {idx}. {name}")

    data_matrix = data.get("data_matrix")
    output_matrix = data.get("output_matrix")
    if data_matrix is not None and output_matrix is not None:
        shape_inputs = getattr(data_matrix, "shape", None)
        shape_outputs = getattr(output_matrix, "shape", None)
        print(f"\nData matrix shape: {shape_inputs}")
        print(f"Output matrix shape: {shape_outputs}")


def _prompt_save_figures(figures, project_folder: str):
    if not figures:
        return

    choice = input("\nSave these plots as PNG files? [y/N]: ").strip().lower()
    if choice not in {"y", "yes"}:
        for fig, _ in figures:
            plt.close(fig)
        return

    save_dir = os.path.join(project_folder, "test_files", "out_final", "graphs")
    os.makedirs(save_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    saved_any = False
    for idx, (fig, name) in enumerate(figures, start=1):
        filename = f"{timestamp}_{name}_{idx}.png"
        filepath = os.path.join(save_dir, filename)
        try:
            fig.savefig(filepath, dpi=300, bbox_inches="tight")
            print(f"Saved: {filepath}")
            saved_any = True
        except Exception as exc:
            print(f"[WARNING] Failed to save {filename}: {exc}")
        finally:
            plt.close(fig)

    if saved_any:
        print(f"Plots saved to: {save_dir}")


def run_graph_menu(project_folder: Optional[str] = None):
    project_folder = _resolve_project_folder(project_folder)
    print(f"\nProject folder: {project_folder}")
    data_cache: Optional[dict] = None

    while True:
        print("\nGraphing Menu")
        print("  1. Refresh data from Fluent outputs")
        print("  2. Plot 3D/2D surfaces")
        print("  3. Plot Aero Maps (2D heat maps)")
        print("  4. Plot parameter vs output scatter")
        print("  5. Plot output correlation heatmap")
        print("  6. Show available parameters and outputs")
        print("  7. Change project folder")
        print("  0. Exit")

        choice = input("Select an option: ").strip()

        if choice == "1":
            data_cache = _load_analysis_data(project_folder, refresh_summary=True)
        elif choice == "2":
            data_cache = _ensure_data_available(data_cache, project_folder)
            if data_cache:
                enriched = dict(data_cache)
                enriched["project_folder"] = project_folder
                _plot_surfaces(enriched)
        elif choice == "3":
            data_cache = _ensure_data_available(data_cache, project_folder)
            if data_cache:
                enriched = dict(data_cache)
                enriched["project_folder"] = project_folder
                _plot_aero_maps(enriched)
        elif choice == "4":
            data_cache = _ensure_data_available(data_cache, project_folder)
            if data_cache:
                enriched = dict(data_cache)
                enriched["project_folder"] = project_folder
                _plot_scatter(enriched)
        elif choice == "5":
            data_cache = _ensure_data_available(data_cache, project_folder)
            if data_cache:
                try:
                    enriched = dict(data_cache)
                    enriched["project_folder"] = project_folder
                    _plot_correlation(enriched)
                except ValueError as exc:
                    print(f"[WARNING] {exc}")
        elif choice == "6":
            data_cache = _ensure_data_available(data_cache, project_folder)
            if data_cache:
                _print_summary(data_cache)
        elif choice == "7":
            project_folder = _resolve_project_folder()
            data_cache = None
            print(f"\nProject folder updated to: {project_folder}")
        elif choice == "0":
            print("Exiting graphing menu.")
            break
        else:
            print("Invalid selection. Please choose a valid option.")


if __name__ == "__main__":
    run_graph_menu()