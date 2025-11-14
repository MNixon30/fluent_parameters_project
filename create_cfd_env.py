from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


PACKAGES: Sequence[Tuple[str, str]] = [
    ("aiohappyeyeballs", "2.6.1"),
    ("aiohttp", "3.12.15"),
    ("aiosignal", "1.4.0"),
    ("ansys-api-fluent", "0.3.36"),
    ("ansys-api-platform-instancemanagement", "1.1.3"),
    ("ansys-api-tools-filetransfer", "0.1.1"),
    ("ansys-fluent-core", "0.34.2"),
    ("ansys-fluent-visualization", "0.21.0"),
    ("ansys-platform-instancemanagement", "1.1.2"),
    ("ansys-tools-filetransfer", "0.1.1"),
    ("ansys-units", "0.7.0"),
    ("anyio", "4.10.0"),
    ("argon2-cffi", "25.1.0"),
    ("argon2-cffi-bindings", "25.1.0"),
    ("arrow", "1.3.0"),
    ("asttokens", "3.0.0"),
    ("async-lru", "2.0.5"),
    ("attrs", "25.3.0"),
    ("babel", "2.17.0"),
    ("beautifulsoup4", "4.13.5"),
    ("bleach", "6.2.0"),
    ("certifi", "2025.8.3"),
    ("cffi", "1.17.1"),
    ("charset-normalizer", "3.4.3"),
    ("click", "8.2.1"),
    ("cmcrameri", "1.9"),
    ("cmocean", "4.0.3"),
    ("colorama", "0.4.6"),
    ("colorcet", "3.1.0"),
    ("comm", "0.2.3"),
    ("contourpy", "1.3.3"),
    ("cycler", "0.12.1"),
    ("debugpy", "1.8.16"),
    ("decorator", "5.2.1"),
    ("defusedxml", "0.7.1"),
    ("Deprecated", "1.2.18"),
    ("docker", "7.1.0"),
    ("executing", "2.2.1"),
    ("fastjsonschema", "2.21.2"),
    ("fonttools", "4.59.2"),
    ("fqdn", "1.5.1"),
    ("frozenlist", "1.7.0"),
    ("googleapis-common-protos", "1.70.0"),
    ("grpcio", "1.74.0"),
    ("grpcio-health-checking", "1.62.3"),
    ("grpcio-status", "1.62.3"),
    ("h11", "0.16.0"),
    ("h5py", "3.14.0"),
    ("httpcore", "1.0.9"),
    ("httpx", "0.28.1"),
    ("idna", "3.10"),
    ("imageio", "2.37.0"),
    ("importlib_metadata", "8.7.0"),
    ("ipykernel", "7.1.0"),
    ("ipython", "9.5.0"),
    ("ipython_pygments_lexers", "1.1.1"),
    ("ipywidgets", "8.1.7"),
    ("isoduration", "20.11.0"),
    ("jedi", "0.19.2"),
    ("Jinja2", "3.1.6"),
    ("joblib", "1.5.2"),
    ("json5", "0.12.1"),
    ("jsonpointer", "3.0.0"),
    ("jsonschema", "4.25.1"),
    ("jsonschema-specifications", "2025.4.1"),
    ("jupyter", "1.1.1"),
    ("jupyter_client", "8.6.3"),
    ("jupyter-console", "6.6.3"),
    ("jupyter_core", "5.8.1"),
    ("jupyter-events", "0.12.0"),
    ("jupyter-lsp", "2.3.0"),
    ("jupyter_server", "2.17.0"),
    ("jupyter_server_proxy", "4.4.0"),
    ("jupyter_server_terminals", "0.5.3"),
    ("jupyterlab", "4.4.7"),
    ("jupyterlab_pygments", "0.3.0"),
    ("jupyterlab_server", "2.27.3"),
    ("jupyterlab_widgets", "3.0.15"),
    ("kiwisolver", "1.4.9"),
    ("lark", "1.2.2"),
    ("lxml", "6.0.1"),
    ("markdown-it-py", "4.0.0"),
    ("MarkupSafe", "3.0.2"),
    ("matplotlib", "3.10.6"),
    ("matplotlib-inline", "0.1.7"),
    ("mdurl", "0.1.2"),
    ("meshio", "5.3.5"),
    ("mistune", "3.1.4"),
    ("more-itertools", "10.8.0"),
    ("msgpack", "1.1.1"),
    ("multidict", "6.6.4"),
    ("nbclient", "0.10.2"),
    ("nbconvert", "7.16.6"),
    ("nbformat", "5.10.4"),
    ("nest-asyncio", "1.6.0"),
    ("nltk", "3.9.1"),
    ("notebook", "7.4.5"),
    ("notebook_shim", "0.2.4"),
    ("numpy", "2.3.2"),
    ("packaging", "25.0"),
    ("pandas", "2.2.3"),
    ("pandocfilters", "1.5.1"),
    ("parso", "0.8.5"),
    ("pillow", "11.3.0"),
    ("pip", "25.3"),
    ("platformdirs", "4.4.0"),
    ("pooch", "1.8.2"),
    ("prometheus_client", "0.22.1"),
    ("prompt_toolkit", "3.0.52"),
    ("propcache", "0.3.2"),
    ("protobuf", "4.25.8"),
    ("psutil", "7.0.0"),
    ("pure_eval", "0.2.3"),
    ("pyaml", "25.7.0"),
    ("pyansys-tools-report", "0.8.2"),
    ("pycparser", "2.22"),
    ("pyDOE2", "1.3.0"),
    ("Pygments", "2.19.2"),
    ("pyparsing", "3.2.3"),
    ("python-dateutil", "2.9.0.post0"),
    ("python-json-logger", "3.3.0"),
    ("pytz", "2025.2"),
    ("pyvista", "0.46.3"),
    ("pyvistaqt", "0.11.3"),
    ("pywin32", "311"),
    ("pywinpty", "3.0.0"),
    ("PyYAML", "6.0.2"),
    ("pyzmq", "27.0.2"),
    ("QtPy", "2.4.3"),
    ("referencing", "0.36.2"),
    ("regex", "2025.9.1"),
    ("requests", "2.32.5"),
    ("rfc3339-validator", "0.1.4"),
    ("rfc3986-validator", "0.1.1"),
    ("rfc3987-syntax", "1.1.0"),
    ("rich", "14.1.0"),
    ("rpds-py", "0.27.1"),
    ("scikit-learn", "1.7.1"),
    ("scikit-optimize", "0.10.2"),
    ("scipy", "1.16.1"),
    ("scooby", "0.10.1"),
    ("seaborn", "0.13.2"),
    ("Send2Trash", "1.8.3"),
    ("setuptools", "80.9.0"),
    ("simpervisor", "1.0.0"),
    ("six", "1.17.0"),
    ("sniffio", "1.3.1"),
    ("soupsieve", "2.8"),
    ("stack-data", "0.6.3"),
    ("terminado", "0.18.1"),
    ("threadpoolctl", "3.6.0"),
    ("tinycss2", "1.4.0"),
    ("tornado", "6.5.2"),
    ("tqdm", "4.67.1"),
    ("traitlets", "5.14.3"),
    ("trame", "3.12.0"),
    ("trame-client", "3.10.1"),
    ("trame-common", "1.0.1"),
    ("trame-server", "3.6.0"),
    ("trame-vtk", "2.9.1"),
    ("trame-vuetify", "3.0.2"),
    ("ttkthemes", "3.2.2"),
    ("types-python-dateutil", "2.9.0.20250822"),
    ("typing_extensions", "4.15.0"),
    ("tzdata", "2025.2"),
    ("uri-template", "1.3.0"),
    ("urllib3", "2.5.0"),
    ("uv", "0.8.15"),
    ("vtk", "9.5.1"),
    ("wcwidth", "0.2.13"),
    ("webcolors", "24.11.1"),
    ("webencodings", "0.5.1"),
    ("websocket-client", "1.8.0"),
    ("widgetsnbextension", "4.0.14"),
    ("wrapt", "1.17.3"),
    ("wslink", "2.4.0"),
    ("xgboost", "3.1.1"),
    ("yarl", "1.20.1"),
    ("zipp", "3.23.0"),
]


def prompt_env_path() -> Path:
    default_path = Path.cwd() / "CFD_PYANSYS_env"
    print("Virtual environment setup")
    print("-------------------------")
    user_input = input(f"Enter venv path [{default_path}]: ").strip()
    if not user_input:
        return default_path.resolve()
    return Path(user_input).expanduser().resolve()


def run_command(command: Iterable[str], env: dict | None = None) -> None:
    command_list: List[str] = list(command)
    print(f"\n[RUN] {' '.join(command_list)}")
    subprocess.run(command_list, check=True, env=env)


def create_virtualenv(venv_path: Path) -> Path:
    if venv_path.exists():
        print(f"[INFO] Virtual environment folder already exists: {venv_path}")
    else:
        print(f"[INFO] Creating virtual environment at {venv_path}")
        run_command([sys.executable, "-m", "venv", str(venv_path)])

    scripts_dir = venv_path / ("Scripts" if os.name == "nt" else "bin")
    python_executable = scripts_dir / ("python.exe" if os.name == "nt" else "python")
    if not python_executable.exists():
        raise FileNotFoundError(f"Could not find python executable in {scripts_dir}")
    print(f"[INFO] Virtual environment python: {python_executable}")
    return python_executable


def install_packages(python_executable: Path) -> None:
    run_command([str(python_executable), "-m", "pip", "install", "--upgrade", "pip"])
    run_command([str(python_executable), "-m", "pip", "install", "--upgrade", "setuptools", "wheel"])

    for chunk in chunked_packages(PACKAGES, chunk_size=25):
        specs = [f"{name}=={version}" for name, version in chunk]
        run_command([str(python_executable), "-m", "pip", "install", *specs])


def chunked_packages(packages: Sequence[Tuple[str, str]], chunk_size: int) -> Iterable[Sequence[Tuple[str, str]]]:
    for i in range(0, len(packages), chunk_size):
        yield packages[i : i + chunk_size]


def main() -> None:
    venv_path = prompt_env_path()
    python_exe = create_virtualenv(venv_path)
    install_packages(python_exe)
    print("\n[INFO] Environment setup complete!")
    print(f"[INFO] Activate it with: {venv_path / ('Scripts/activate' if os.name == 'nt' else 'bin/activate')}")


if __name__ == "__main__":
    main()

