from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Iterable, List, Optional

CONFIG_DIR_NAME = "test_files/plots"
CONFIG_FILENAME = "snapshot_config.json"
SETUP_CONFIG_NAME = "setup_config.json"


@dataclass
class SurfaceSpec:
    """Definition for a simple Fluent plane surface."""

    name: str
    orientation: str  # One of "xy", "yz", "zx"
    offset: float = 0.0

    def to_dict(self) -> dict:
        data = asdict(self)
        data["orientation"] = self.orientation.lower()
        return data


@dataclass
class ContourPlotSpec:
    """Configuration for a contour plot on a given surface."""

    surface_name: str
    field: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SnapshotPreferences:
    project_folder: Path
    surfaces: List[SurfaceSpec] = field(default_factory=list)
    contour_plots: List[ContourPlotSpec] = field(default_factory=list)
    design_points: Optional[List[int]] = None

    def to_dict(self) -> dict:
        return {
            "project_folder": str(self.project_folder),
            "surfaces": [surface.to_dict() for surface in self.surfaces],
            "contour_plots": [plot.to_dict() for plot in self.contour_plots],
            "design_points": self.design_points,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SnapshotPreferences":
        project_folder = Path(data["project_folder"]) if "project_folder" in data else Path()
        surfaces = [SurfaceSpec(**s) for s in data.get("surfaces", [])]
        contour_plots = [ContourPlotSpec(**p) for p in data.get("contour_plots", [])]
        design_points = data.get("design_points")
        return cls(
            project_folder=project_folder,
            surfaces=surfaces,
            contour_plots=contour_plots,
            design_points=design_points,
        )


def resolve_config_path(project_folder: Path) -> Path:
    plots_dir = project_folder / CONFIG_DIR_NAME
    plots_dir.mkdir(parents=True, exist_ok=True)
    return plots_dir / CONFIG_FILENAME


def save_snapshot_preferences(preferences: SnapshotPreferences) -> Path:
    config_path = resolve_config_path(preferences.project_folder)
    with config_path.open("w", encoding="utf-8") as fp:
        json.dump(preferences.to_dict(), fp, indent=2)
    return config_path


def load_snapshot_preferences(project_folder: Path) -> SnapshotPreferences:
    config_path = resolve_config_path(project_folder)
    if not config_path.exists():
        raise FileNotFoundError(f"Snapshot configuration not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    return SnapshotPreferences.from_dict(data)


def load_project_folder_from_setup_config(project_folder: Optional[Path] = None) -> Optional[Path]:
    """Attempt to read `project_folder` from setup_config.json."""

    if project_folder is None:
        search_paths = [Path.cwd(), Path(__file__).resolve().parent]
    else:
        search_paths = [project_folder]

    for base in search_paths:
        config_path = base / SETUP_CONFIG_NAME
        if not config_path.exists():
            continue
        try:
            with config_path.open("r", encoding="utf-8") as fp:
                data = json.load(fp)
            value = data.get("project_folder")
            if value:
                candidate = Path(value).expanduser().resolve()
                if candidate.exists():
                    return candidate
        except (json.JSONDecodeError, OSError):
            continue
    return None


def list_available_design_points(project_folder: Path) -> List[int]:
    """Return available design point indices based on DesignPoints.csv."""

    dps_csv = project_folder / "test_files" / "dps" / "DesignPoints.csv"
    if not dps_csv.exists():
        return []

    import csv

    indices: List[int] = []
    try:
        with dps_csv.open("r", encoding="utf-8-sig") as fp:
            reader = csv.reader(fp)
            next(reader, None)  # header
            for idx, row in enumerate(reader):
                if row:
                    indices.append(idx)
    except Exception:
        return []
    return indices


def normalise_design_points(entries: Iterable[int | str]) -> List[int]:
    normalised: List[int] = []
    for entry in entries:
        if isinstance(entry, int):
            normalised.append(entry)
            continue
        try:
            normalised.append(int(str(entry).strip()))
        except (TypeError, ValueError):
            raise ValueError(f"Invalid design point identifier: {entry}")
    return normalised


def get_design_points_path(project_folder: Path) -> Path:
    """Return the path to DesignPoints.csv."""
    return project_folder / "test_files" / "dps" / "DesignPoints.csv"


def view_design_points(project_folder: Path) -> None:
    """
    Display information about the design points from DesignPoints.csv.
    
    Args:
        project_folder: Path to the project folder
    """
    print("\n" + "=" * 50)
    print("DESIGN POINTS")
    print("=" * 50)

    design_points_path = get_design_points_path(project_folder)
    if not design_points_path.exists():
        print("No DesignPoints.csv found.")
        print(f"Expected location: {design_points_path}")
        return

    try:
        import pandas as pd
        df = pd.read_csv(design_points_path)

        print(f"Number of design points: {len(df)}")
        print(f"Design points file: {design_points_path}")
        print(f"Parameters: {', '.join(df.columns.tolist())}")

        print(f"\nDesign points preview (first 10 rows):")
        print("-" * 50)
        # Display with row index (0-based design point index)
        for idx, row in df.head(10).iterrows():
            values_str = ", ".join([f"{val:.6f}" for val in row.values])
            print(f"  Index {idx}: [{values_str}]")

        if len(df) > 10:
            print(f"\n... and {len(df) - 10} more design points")

    except ImportError:
        print("\n[ERROR] pandas is required to view design points.")
        print("Install it with: pip install pandas")
    except Exception as e:
        print(f"\n[ERROR] Could not read design points file: {e}")

    print("=" * 50)


@dataclass
class NearestDesignPoint:
    """Result of a design point search."""

    index: int
    distance: float
    values: List[float]


def search_design_points(
    project_folder: Path, search_point: List[float], top_k: int = 3
) -> List[NearestDesignPoint]:
    """
    Find the top K nearest design points to a search point using Euclidean distance.
    
    Args:
        project_folder: Path to the project folder
        search_point: List of parameter values to search for
        top_k: Number of nearest neighbors to return (default: 3)
    
    Returns:
        List of NearestDesignPoint objects sorted by distance (nearest first)
    """
    design_points_path = get_design_points_path(project_folder)
    if not design_points_path.exists():
        raise FileNotFoundError(f"DesignPoints.csv not found: {design_points_path}")

    try:
        import pandas as pd
        import numpy as np

        df = pd.read_csv(design_points_path)

        if len(search_point) != len(df.columns):
            raise ValueError(
                f"Search point has {len(search_point)} values, but design points have {len(df.columns)} parameters"
            )

        # Convert search point to numpy array
        search_array = np.array(search_point)

        # Calculate Euclidean distance to each design point
        distances = []
        for idx, row in df.iterrows():
            design_point_values = row.values
            distance = np.linalg.norm(design_point_values - search_array)
            distances.append((idx, distance, design_point_values.tolist()))

        # Sort by distance and take top K
        distances.sort(key=lambda x: x[1])
        top_results = distances[:top_k]

        # Convert to NearestDesignPoint objects
        results = [
            NearestDesignPoint(index=idx, distance=dist, values=vals)
            for idx, dist, vals in top_results
        ]

        return results

    except ImportError:
        raise ImportError("pandas and numpy are required for design point search. Install with: pip install pandas numpy")
    except Exception as e:
        raise RuntimeError(f"Error searching design points: {e}")


def display_nearest_design_points(results: List[NearestDesignPoint], parameter_names: List[str]) -> None:
    """
    Display the results of a design point search.
    
    Args:
        results: List of NearestDesignPoint objects from search_design_points
        parameter_names: List of parameter names (from CSV header)
    """
    print("\n" + "=" * 50)
    print("NEAREST DESIGN POINTS")
    print("=" * 50)

    if not results:
        print("No results found.")
        return

    for rank, result in enumerate(results, start=1):
        print(f"\nRank {rank}:")
        print(f"  Design Point Index: {result.index}")
        print(f"  Distance: {result.distance:.6f}")
        print(f"  Values:")
        for param_name, value in zip(parameter_names, result.values):
            print(f"    {param_name}: {value:.6f}")

    print("=" * 50)


def generate_snapshots_from_config(
    solver,
    preferences: SnapshotPreferences,
    design_point_index: int,
    output_dir: Optional[Path] = None,
) -> List[Path]:
    """
    Generate snapshot images for a design point based on snapshot configuration.
    
    This function creates surfaces and plots from the snapshot config, then saves
    high-resolution PNG images. The solver should already be running with case/data loaded.
    
    Args:
        solver: PyFluent solver session (already running with case/data loaded)
        preferences: SnapshotPreferences object with surfaces and plots configuration
        design_point_index: 0-based design point index
        output_dir: Directory to save snapshots (default: project_folder/test_files/plots)
    
    Returns:
        List of Path objects for saved snapshot images
    """
    import os

    # Set environment variables for off-screen rendering
    os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
    os.environ.setdefault("MPLBACKEND", "Agg")

    from ansys.fluent.visualization import config as viz_config, GraphicsWindow, Contour

    # Set visualization config (matching snapshot.py)
    viz_config.interactive = False
    # Note: viz_config.view is set per-surface below via renderer.view_xy() etc.

    if output_dir is None:
        output_dir = preferences.project_folder / "test_files" / "plots"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    saved_images: List[Path] = []

    print(f"[DEBUG] generate_snapshots_from_config called for design point {design_point_index}")
    print(f"[DEBUG] Output directory: {output_dir}")
    print(f"[DEBUG] Surfaces configured: {len(preferences.surfaces)}")
    print(f"[DEBUG] Plots configured: {len(preferences.contour_plots)}")

    try:
        # Create all surfaces from config
        surface_names = []
        for surface_spec in preferences.surfaces:
            try:
                # Create surface with specified name
                solver.settings.results.surfaces.plane_surface.create(surface_spec.name)
                plane_surface = solver.settings.results.surfaces.plane_surface[
                    surface_spec.name.lower()
                ]

                # Set plane orientation
                orientation_map = {
                    "xy": "xy-plane",
                    "yz": "yz-plane",
                    "zx": "zx-plane",
                }
                method = orientation_map.get(surface_spec.orientation.lower())
                if method is None:
                    print(
                        f"[WARNING] Unknown orientation '{surface_spec.orientation}', skipping surface '{surface_spec.name}'"
                    )
                    continue

                plane_surface.method = method

                # Set offset based on orientation
                if surface_spec.orientation.lower() == "xy":
                    plane_surface.z = surface_spec.offset
                elif surface_spec.orientation.lower() == "yz":
                    plane_surface.x = surface_spec.offset
                elif surface_spec.orientation.lower() == "zx":
                    plane_surface.y = surface_spec.offset

                # Execute surface creation (matching snapshot.py pattern)
                surface_result = plane_surface()
                print(f"[INFO] Plane surface '{surface_spec.name}' call result: {surface_result}")
                surface_names.append(surface_spec.name.lower())
                print(
                    f"[INFO] Created surface '{surface_spec.name}' ({surface_spec.orientation}, offset={surface_spec.offset})"
                )

            except Exception as e:
                print(
                    f"[WARNING] Failed to create surface '{surface_spec.name}': {e}"
                )
                continue

        if not surface_names:
            print("[WARNING] No surfaces created, cannot generate plots")
            return saved_images

        # Generate snapshots for each plot
        for plot_idx, plot_spec in enumerate(preferences.contour_plots):
            try:
                # Check if surface exists
                if plot_spec.surface_name.lower() not in surface_names:
                    print(
                        f"[WARNING] Surface '{plot_spec.surface_name}' not found, skipping plot"
                    )
                    continue

                # Create contour plot
                contour = Contour(
                    solver=solver,
                    field=plot_spec.field,
                    surfaces=[plot_spec.surface_name.lower()],
                )

                # Create graphics window (matching snapshot.py pattern)
                graphics_window = GraphicsWindow()
                graphics_window.add_graphics(contour)

                renderer = graphics_window.renderer
                print(f"[DEBUG] Renderer type: {type(renderer)}")

                # Set view based on surface orientation
                surface_orient = None
                for surf in preferences.surfaces:
                    if surf.name.lower() == plot_spec.surface_name.lower():
                        surface_orient = surf.orientation.lower()
                        break

                if surface_orient == "xy":
                    renderer.view_xy()
                elif surface_orient == "yz":
                    renderer.view_yz()
                elif surface_orient == "zx":
                    renderer.view_zx()
                else:
                    renderer.view_xy()  # Default

                # Zoom in for better view (matching snapshot.py pattern)
                plotter = getattr(renderer, "plotter", None)
                print(f"[DEBUG] Plotter present: {plotter is not None}")
                if plotter is not None:
                    try:
                        camera = plotter.camera
                        initial_scale = camera.GetParallelScale()
                        print(f"[DEBUG] Initial parallel scale: {initial_scale}")
                        camera.SetParallelScale(initial_scale * 0.45)
                        adjusted_scale = camera.GetParallelScale()
                        print(f"[DEBUG] Adjusted parallel scale: {adjusted_scale}")
                        plotter.reset_camera_clipping_range()
                        plotter.render()
                    except Exception as zoom_error:
                        print(
                            f"[WARNING] Unable to tighten camera zoom: {zoom_error}"
                        )

                # Generate output filename
                field_safe = plot_spec.field.replace("-", "_")
                surface_safe = plot_spec.surface_name.replace(" ", "_")
                output_filename = (
                    f"design_point_{design_point_index}_{surface_safe}_{field_safe}.png"
                )
                output_path = output_dir / output_filename

                # Ensure renderer is ready (matching snapshot.py pattern)
                # The plotter.render() call above should have handled this, but ensure it's done
                if plotter is not None:
                    try:
                        plotter.render()
                    except Exception:
                        pass  # Best effort render

                # Save screenshot (matching snapshot.py pattern)
                HIGH_RESOLUTION_SIZE = (3840, 2160)
                print(f"[DEBUG] Taking screenshot: {output_path}")
                renderer.screenshot(
                    str(output_path),
                    window_size=HIGH_RESOLUTION_SIZE,
                    transparent_background=False,
                )
                print(
                    f"[INFO] Image saved to {output_filename} at resolution {HIGH_RESOLUTION_SIZE}."
                )
                
                # Verify file was created
                if output_path.exists():
                    file_size = output_path.stat().st_size
                    print(f"[DEBUG] Snapshot file created: {output_path} ({file_size} bytes)")
                else:
                    print(f"[ERROR] Snapshot file was not created: {output_path}")

                # Auto-crop image
                _auto_crop_image(output_path)

                saved_images.append(output_path)

                # Clean up graphics window for next plot (if method exists)
                try:
                    if hasattr(graphics_window, 'close'):
                        graphics_window.close()
                except Exception:
                    pass  # Graphics window cleanup is optional

            except Exception as e:
                print(f"[WARNING] Failed to generate plot for '{plot_spec.field}': {e}")
                import traceback

                traceback.print_exc()
                continue

    except Exception as e:
        print(f"[ERROR] Snapshot generation failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"[DEBUG] generate_snapshots_from_config completed. Generated {len(saved_images)} snapshot(s)")

    return saved_images


def _auto_crop_image(image_path: Path, margin: int = 30) -> None:
    """Auto-crop whitespace from image using Pillow."""
    try:
        from PIL import Image
        import numpy as np
    except (ImportError, ModuleNotFoundError):
        print("[INFO] Pillow not installed; skipping automatic cropping.")
        return

    if not image_path.exists():
        print(f"[WARNING] Cannot crop missing image: {image_path}")
        return

    try:
        with Image.open(image_path) as img:
            data = np.array(img)

        if data.ndim == 3:
            non_white_mask = np.any(data < 250, axis=2)
        else:
            non_white_mask = data < 250

        if not non_white_mask.any():
            print("[INFO] Cropping skipped; image appears blank or fully white.")
            return

        rows = np.any(non_white_mask, axis=1)
        cols = np.any(non_white_mask, axis=0)
        top, bottom = rows.argmax(), len(rows) - rows[::-1].argmax()
        left, right = cols.argmax(), len(cols) - cols[::-1].argmax()

        top = max(top - margin, 0)
        left = max(left - margin, 0)
        bottom = min(bottom + margin, data.shape[0])
        right = min(right + margin, data.shape[1])

        if top >= bottom or left >= right:
            print("[INFO] Cropping skipped; computed bounds invalid.")
            return

        with Image.open(image_path) as img:
            cropped = img.crop((left, top, right, bottom))
            cropped.save(image_path)
            print(f"[INFO] Cropped image saved: {cropped.size}")

    except Exception as e:
        print(f"[WARNING] Auto-crop failed: {e}")
