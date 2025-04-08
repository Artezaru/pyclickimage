import cv2
from pyclickimage import launch_app, ClickManager

img = cv2.imread("example.png")
launch_app(img, "output.csv")

clicks = ClickManager.load_from_csv("output.csv")
default_clicks = clicks.extract_group("default")
print(default_clicks)