
import re
import warnings
from itertools import combinations
from typing import Iterable, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy.interpolate import griddata
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (needed for 3D projections)


def _prepare_numeric_arrays(
    data_matrix: np.ndarray,
    output_matrix: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Convert incoming matrices to float arrays and drop rows with NaNs.
    Returns cleaned input matrix, output matrix, and a boolean mask of kept rows.
    """
    try:
        input_array = np.asarray(data_matrix, dtype=float)
    except Exception:
        input_array = np.array(data_matrix, dtype=float, copy=False)

    try:
        output_array = np.asarray(output_matrix, dtype=float)
    except Exception:
        output_array = np.array(output_matrix, dtype=float, copy=False)

    if input_array.ndim != 2:
        raise ValueError("data_matrix must be convertible to a 2D array.")
    if output_array.ndim == 1:
        output_array = output_array.reshape(-1, 1)
    if output_array.ndim != 2:
        raise ValueError("output_matrix must be convertible to a 2D array.")
    if input_array.shape[0] != output_array.shape[0]:
        raise ValueError("data_matrix and output_matrix must have the same number of rows.")

    combined = np.concatenate((input_array, output_array), axis=1)
    valid_rows = ~np.isnan(combined).any(axis=1)

    if not np.any(valid_rows):
        raise ValueError("No valid rows remain after removing NaN values.")

    return input_array[valid_rows], output_array[valid_rows], valid_rows


def _apply_selection(
    matrix: np.ndarray,
    names: Sequence[str],
    selected_indices: Optional[Iterable[int]],
) -> tuple[np.ndarray, list[str]]:
    if selected_indices is None:
        return matrix, list(names)

    selected_indices = list(dict.fromkeys(int(idx) for idx in selected_indices))
    if not selected_indices:
        return matrix, list(names)

    for idx in selected_indices:
        if idx < 0 or idx >= matrix.shape[1]:
            raise IndexError(f"Selected index {idx} is out of bounds for matrix with {matrix.shape[1]} columns.")

    return matrix[:, selected_indices], [names[i] for i in selected_indices]


def plot_cfd_results(
    data_matrix,
    output_matrix,
    parameter_names,
    output_names,
    grid_resolution: int = 50,
    selected_inputs: Optional[Iterable[int]] = None,
    selected_outputs: Optional[Iterable[int]] = None,
) -> List[Tuple[Figure, str]]:
    """
    Plot CFD results using surface plots (for >=2 inputs) or line plots (for 1 input).

    Args:
        data_matrix: 2D array-like of shape (samples, input_parameters)
        output_matrix: 2D array-like of shape (samples, output_parameters)
        parameter_names: List of input parameter names
        output_names: List of output parameter names
        grid_resolution: Resolution used for surface interpolation
        selected_inputs: Optional iterable of column indices to include from inputs
        selected_outputs: Optional iterable of column indices to include from outputs
    """
    if len(parameter_names) != np.asarray(data_matrix).shape[1]:
        raise ValueError("parameter_names length must match number of input columns.")
    if len(output_names) != np.asarray(output_matrix).shape[1]:
        raise ValueError("output_names length must match number of output columns.")

    inputs, outputs, _ = _prepare_numeric_arrays(data_matrix, output_matrix)
    inputs, parameter_names = _apply_selection(inputs, parameter_names, selected_inputs)
    outputs, output_names = _apply_selection(outputs, output_names, selected_outputs)

    n_samples, n_inputs = inputs.shape
    _, n_outputs = outputs.shape

    if n_inputs == 0:
        raise ValueError("At least one input parameter must be selected for plotting.")
    if n_outputs == 0:
        raise ValueError("At least one output parameter must be selected for plotting.")

    figures: List[Tuple[Figure, str]] = []

    # Case 1: only one input variable
    if n_inputs == 1:
        x = inputs[:, 0]
        for out_i, output_name in enumerate(output_names):
            fig = plt.figure(figsize=(6, 5))
            ax = fig.add_subplot(111)
            y = outputs[:, out_i]
            scatter = ax.scatter(
                x,
                y,
                c=y,
                cmap='viridis',
                edgecolor='black',
                linewidth=0.5,
                alpha=0.85,
                s=60,
            )
            ax.set_xlabel(parameter_names[0])
            ax.set_ylabel(output_name)
            ax.set_title(f"{output_name} vs {parameter_names[0]}")
            ax.grid(True, linestyle='--', alpha=0.3)
            cbar = fig.colorbar(scatter, ax=ax, pad=0.02)
            cbar.set_label(output_name)
            fig.tight_layout()
            fig.canvas.manager.set_window_title(f"{output_name} vs {parameter_names[0]}")
            figures.append((fig, _sanitize_filename(f"{output_name}_vs_{parameter_names[0]}")))

        if figures:
            plt.show()
        return figures

    # Case 2: normal case (2 or more inputs)
    input_pairs = list(combinations(range(n_inputs), 2))

    for out_i, output_name in enumerate(output_names):
        fig = plt.figure(figsize=(6 * len(input_pairs), 6))
        fig.suptitle(f"Output: {output_name}", fontsize=14, y=0.94)

        for subplot_i, (i, j) in enumerate(input_pairs):
            ax = fig.add_subplot(1, len(input_pairs), subplot_i + 1, projection='3d')

            x, y = inputs[:, i], inputs[:, j]
            z = outputs[:, out_i]

            xi = np.linspace(x.min(), x.max(), grid_resolution)
            yi = np.linspace(y.min(), y.max(), grid_resolution)
            Xi, Yi = np.meshgrid(xi, yi)

            try:
                Zi = griddata((x, y), z, (Xi, Yi), method='cubic')
            except Exception as exc:
                warnings.warn(
                    f"Grid interpolation failed for parameters {parameter_names[i]} / {parameter_names[j]} "
                    f"with output {output_name}: {exc}. Falling back to scatter plot.",
                    RuntimeWarning,
                )
                Zi = None

            if Zi is not None and not np.isnan(Zi).all():
                surf = ax.plot_surface(Xi, Yi, Zi, cmap='viridis', edgecolor='none', alpha=0.9)
                mappable = plt.cm.ScalarMappable(cmap='viridis')
                mappable.set_array(z)
                cbar = fig.colorbar(mappable, ax=ax, shrink=0.6, pad=0.1)
                cbar.set_label(output_name)
            else:
                ax.scatter(x, y, z, c=z, cmap='viridis', s=40)

            ax.set_xlabel(parameter_names[i])
            ax.set_ylabel(parameter_names[j])
            ax.set_zlabel(output_name)
            ax.set_title(f"{parameter_names[i]} vs {parameter_names[j]}")
            ax.view_init(elev=25, azim=135)

        plt.tight_layout(rect=[0, 0, 1, 0.92])
        figures.append((fig, _sanitize_filename(f"{output_name}_surface")))

    if figures:
        plt.show()

    return figures


def plot_aero_maps(
    data_matrix,
    output_matrix,
    parameter_names,
    output_names,
    grid_resolution: int = 60,
    selected_inputs: Optional[Iterable[int]] = None,
    selected_outputs: Optional[Iterable[int]] = None,
) -> List[Tuple[Figure, str]]:
    """
    Plot 2D heat maps (aero maps) for selected input parameter pairs against outputs.
    """
    if len(parameter_names) != np.asarray(data_matrix).shape[1]:
        raise ValueError("parameter_names length must match number of input columns.")
    if len(output_names) != np.asarray(output_matrix).shape[1]:
        raise ValueError("output_names length must match number of output columns.")

    inputs, outputs, _ = _prepare_numeric_arrays(data_matrix, output_matrix)
    inputs, parameter_names = _apply_selection(inputs, parameter_names, selected_inputs)
    outputs, output_names = _apply_selection(outputs, output_names, selected_outputs)

    n_inputs = inputs.shape[1]
    n_outputs = outputs.shape[1]

    if n_inputs < 2:
        raise ValueError("Aero maps require at least two input parameters.")
    if n_outputs == 0:
        raise ValueError("At least one output parameter must be selected for plotting.")

    figures: List[Tuple[Figure, str]] = []
    input_pairs = list(combinations(range(n_inputs), 2))

    for out_idx, output_name in enumerate(output_names):
        fig, axes = plt.subplots(
            1,
            len(input_pairs),
            figsize=(6 * len(input_pairs), 5),
            squeeze=False,
        )
        fig.suptitle(f"Aero Map: {output_name}", fontsize=14, y=0.94)

        for pair_idx, (i, j) in enumerate(input_pairs):
            ax = axes[0][pair_idx]
            x = inputs[:, i]
            y = inputs[:, j]
            z = outputs[:, out_idx]

            xi = np.linspace(x.min(), x.max(), grid_resolution)
            yi = np.linspace(y.min(), y.max(), grid_resolution)
            Xi, Yi = np.meshgrid(xi, yi)

            try:
                Zi = griddata((x, y), z, (Xi, Yi), method='cubic')
            except Exception as exc:
                warnings.warn(
                    f"Grid interpolation failed for parameters {parameter_names[i]} / {parameter_names[j]} "
                    f"with output {output_name}: {exc}. Falling back to scatter plot.",
                    RuntimeWarning,
                )
                Zi = None

            if Zi is not None and not np.isnan(Zi).all():
                hm = ax.imshow(
                    Zi,
                    extent=(xi.min(), xi.max(), yi.min(), yi.max()),
                    origin='lower',
                    aspect='auto',
                    cmap='viridis',
                )
                contour_levels = 10
                try:
                    ax.contour(Xi, Yi, Zi, contour_levels, colors='k', linewidths=0.5, alpha=0.6)
                except Exception:
                    pass
                cbar = fig.colorbar(hm, ax=ax, shrink=0.8, pad=0.02)
                cbar.set_label(output_name)
            else:
                hm = ax.scatter(x, y, c=z, cmap='viridis', edgecolor='black', linewidth=0.4)
                cbar = fig.colorbar(hm, ax=ax, shrink=0.8, pad=0.02)
                cbar.set_label(output_name)

            ax.set_xlabel(parameter_names[i])
            ax.set_ylabel(parameter_names[j])
            ax.set_title(f"{parameter_names[i]} vs {parameter_names[j]}")
            ax.grid(True, linestyle='--', alpha=0.2)

        fig.tight_layout(rect=[0, 0, 1, 0.92])
        fig.canvas.manager.set_window_title(f"Aero Map: {output_name}")
        figures.append((fig, _sanitize_filename(f"{output_name}_aero_map")))

    if figures:
        plt.show()

    return figures


def plot_parameter_output_scatter(
    data_matrix,
    output_matrix,
    parameter_names,
    output_names,
    selected_inputs: Optional[Iterable[int]] = None,
    selected_outputs: Optional[Iterable[int]] = None,
) -> List[Tuple[Figure, str]]:
    """
    Create 2D scatter plots for selected input/output combinations.
    """
    inputs, outputs, _ = _prepare_numeric_arrays(data_matrix, output_matrix)
    inputs, parameter_names = _apply_selection(inputs, parameter_names, selected_inputs)
    outputs, output_names = _apply_selection(outputs, output_names, selected_outputs)

    n_inputs = inputs.shape[1]
    n_outputs = outputs.shape[1]

    fig, axes = plt.subplots(
        n_outputs,
        n_inputs,
        figsize=(5 * n_inputs, 4 * n_outputs),
        squeeze=False,
    )

    for out_idx, output_name in enumerate(output_names):
        for in_idx, param_name in enumerate(parameter_names):
            ax = axes[out_idx][in_idx]
            ax.scatter(inputs[:, in_idx], outputs[:, out_idx], color='tab:blue', alpha=0.7, edgecolors='none')
            ax.set_xlabel(param_name)
            ax.set_ylabel(output_name)
            ax.grid(True, linestyle='--', alpha=0.3)
            ax.set_title(f"{output_name} vs {param_name}")

    fig.tight_layout()
    fig.canvas.manager.set_window_title("Parameter vs Output Scatter")
    plt.show()

    return [(fig, _sanitize_filename("parameter_vs_output_scatter"))]


def plot_output_correlation_heatmap(
    output_matrix,
    output_names,
    selected_outputs: Optional[Iterable[int]] = None,
) -> List[Tuple[Figure, str]]:
    """
    Plot a correlation heatmap for selected output parameters.
    """
    outputs, output_names = _prepare_for_heatmap(output_matrix, output_names, selected_outputs)

    corr_matrix = np.corrcoef(outputs, rowvar=False)

    fig, ax = plt.subplots(figsize=(1.5 * len(output_names), 1.2 * len(output_names)))
    cax = ax.imshow(corr_matrix, cmap='coolwarm', vmin=-1, vmax=1)

    ax.set_xticks(range(len(output_names)))
    ax.set_yticks(range(len(output_names)))
    ax.set_xticklabels(output_names, rotation=45, ha='right')
    ax.set_yticklabels(output_names)
    ax.set_title("Output Parameter Correlation")

    fig.colorbar(cax, ax=ax, fraction=0.046, pad=0.04, label="Correlation")
    fig.tight_layout()
    fig.canvas.manager.set_window_title("Output Correlation Heatmap")
    plt.show()

    return [(fig, _sanitize_filename("output_correlation_heatmap"))]


def _prepare_for_heatmap(
    output_matrix,
    output_names: Sequence[str],
    selected_outputs: Optional[Iterable[int]],
) -> tuple[np.ndarray, list[str]]:
    try:
        outputs = np.asarray(output_matrix, dtype=float)
    except Exception:
        outputs = np.array(output_matrix, dtype=float, copy=False)

    if outputs.ndim == 1:
        outputs = outputs.reshape(-1, 1)

    if outputs.ndim != 2:
        raise ValueError("output_matrix must be convertible to a 2D array.")

    outputs, output_names = _apply_selection(outputs, output_names, selected_outputs)

    valid_rows = ~np.isnan(outputs).any(axis=1)
    outputs = outputs[valid_rows]

    if outputs.shape[0] < 2:
        raise ValueError("At least two valid rows are required to compute correlations.")

    return outputs, output_names


def _sanitize_filename(name: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_-]+", "_", name).strip("_")
    return sanitized or "plot"