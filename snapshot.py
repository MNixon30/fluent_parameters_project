import os
from pathlib import Path

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
os.environ.setdefault("MPLBACKEND", "Agg")

import ansys.fluent.core as pyfluent

from ansys.fluent.visualization import config, GraphicsWindow, Contour

CASE_PATH = r"C:\Users\mitch\Ravens_Racing_CFD\z_Project_Test\test_files\cas\design_point_0_case.cas.h5"
DATA_PATH = r"C:\Users\mitch\Ravens_Racing_CFD\z_Project_Test\test_files\cas\design_point_0_data.dat.h5"
OUTPUT_FILENAME = "saved_contour_high_res.png"
HIGH_RESOLUTION_SIZE = (3840, 2160)
OUTPUT_PATH = Path(OUTPUT_FILENAME)


config.interactive = False
config.view = "xy"


def _auto_crop_image(image_path: Path, margin: int = 30) -> None:
    try:
        from PIL import Image
        import numpy as np
    except (ImportError, ModuleNotFoundError):
        print("[INFO] Pillow not installed; skipping automatic cropping.")
        return

    if not image_path.exists():
        print(f"[WARNING] Cannot crop missing image: {image_path}")
        return

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


def main() -> int:
    solver = None
    try:
        solver = pyfluent.launch_fluent(
            ui_mode="no_gui",
            mode="solver",
            precision="single",
            processor_count=2,
            dimension=3,
        )

        solver.settings.file.read_case(file_name=CASE_PATH)
        solver.settings.file.read_data(file_name=DATA_PATH)

        solver.settings.results.surfaces.plane_surface.create("My_Plane")
        plane_surface = solver.settings.results.surfaces.plane_surface["my_plane"]

        allowed_methods = plane_surface.method.allowed_values()
        print(f"[INFO] Allowed methods: {allowed_methods}")

        plane_surface.method = "xy-plane"
        print(f"[INFO] Plane surface call result: {plane_surface()}")

        plane_surface.z = 0

        contour = Contour(solver=solver, field="velocity-magnitude", surfaces=["my_plane"])
        graphics_window = GraphicsWindow()
        graphics_window.add_graphics(contour)

        renderer = graphics_window.renderer
        renderer.view_xy()
        print(f"[DEBUG] Renderer type: {type(renderer)}")

        plotter = getattr(renderer, "plotter", None)
        print(f"[DEBUG] Plotter present: {plotter is not None}")
        if plotter is not None:
            try:
                camera = plotter.camera
                print(f"[DEBUG] Initial parallel scale: {camera.GetParallelScale()}")
                camera.SetParallelScale(camera.GetParallelScale() * 0.45)
                print(f"[DEBUG] Adjusted parallel scale: {camera.GetParallelScale()}")
                plotter.reset_camera_clipping_range()
                plotter.render()
            except Exception as zoom_error:  # pragma: no cover - best effort zoom
                print(f"[WARNING] Unable to tighten camera zoom: {zoom_error}")

        renderer.screenshot(
            str(OUTPUT_PATH),
            window_size=HIGH_RESOLUTION_SIZE,
            transparent_background=False,
        )
        print(f"[INFO] Image saved to {OUTPUT_FILENAME} at resolution {HIGH_RESOLUTION_SIZE}.")

        _auto_crop_image(OUTPUT_PATH)

        return 0
    except Exception as error:
        print(f"[ERROR] Snapshot workflow failed: {error}")
        return 1
    finally:
        if solver is not None:
            try:
                solver.exit()
            except Exception as exit_error:
                print(f"[WARNING] Fluent did not exit cleanly: {exit_error}")


if __name__ == "__main__":
    raise SystemExit(main())
