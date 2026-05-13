import os
os.environ["XDG_SESSION_TYPE"] = "x11"
import open3d as o3d
import cv2


vis = o3d.visualization.Visualizer()
vis.create_window(window_name='Viewer 3D', width=800, height=600)

pcd = o3d.geometry.PointCloud()
vis.add_geometry(pcd)

axes = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.1)
vis.add_geometry(axes)


while True:
    vis.poll_events()
    vis.update_renderer()
    
    if cv2.waitKey(1) == ord('q'):
        break
