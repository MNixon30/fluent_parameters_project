#Iterate over folders

from pathlib import Path

folder_path = Path("C:/Users/mitch/Ravens_Racing_CFD/Front_Wing_Study/geoms_files/dp0/Geom-2/DM")

for file in folder_path.rglob("*.*"):
    converted_path = file.as_posix()  # matches all files
    print(file)