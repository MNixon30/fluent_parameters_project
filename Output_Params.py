#Get output parameters from fluent

file_path = r"C:\Users\mitch\Ravens_Racing_CFD\Project\Test_Files\OutputFiles\dp_1.json"  # actually a text file

output_params = {}

with open(file_path, "r") as f:
    lines = f.readlines()

# Parse the table
for line in lines:
    line = line.strip()
    if line == "" or line.startswith("----") or line.startswith("Output Parameter"):
        continue
    
    parts = line.split()
    if len(parts) >= 2:
        # Name = first part
        name = parts[0]
        # Value = second part
        value = float(parts[1])
        # Unit = last part in brackets
        unit = parts[-1] if parts[-1].startswith("[") and parts[-1].endswith("]") else ""
        output_params[name] = {"value": value, "unit": unit}