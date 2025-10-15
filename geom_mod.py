#IronPython Geom Mod

# Python Script, API Version = V252

import csv

def read_design_points(file_path):
    points = []
    with open(file_path, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            points.append([float(x) for x in row])
            
    return points

#Relativize the points
def successive_differences(points):
    if not points:
        return []

    out = [points[0]]  

    for i in range(1, len(points)):
        prev = points[i-1]
        cur  = points[i]

        if len(prev) != len(cur):
            raise ValueError("All points must have the same number of dimensions")

        diff = [cur[j] - prev[j] for j in range(len(cur))]
        out.append(diff)

    return out

Design_Points = read_design_points(r"C:\Users\mitch\Ravens_Racing_CFD\Project\Test_Files\DesignPoints\DesignPoints.csv")
print(Design_Points)

DPs = successive_differences(Design_Points)
print(DPs)

def main():
    counter = 0

    # Insert Parameteric Variations (Subject to change depending on parameters)
    for i in DPs:
        selection = FaceSelection.Create(Face2, Face3)
        axis = Move.GetAxis(selection)
        options = MoveOptions()
        result = Move.Rotate(selection, axis, DEG(i[0]), options, Info1)
        
        save_path = r"C:\Users\mitch\Ravens_Racing_CFD\Project\Test_Files\Geometry\Geom-1_dp{}.dsco".format(counter)
        File.SaveAs(save_path)
        counter += 1

# EndBlock
