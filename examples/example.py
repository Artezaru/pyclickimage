import cv2
from pyclickimage import ClickManager, run

img = cv2.imread("example.png")
run(image=img, output="clicks.csv")

clicks = ClickManager.load_from_csv("clicks.csv")
default_clicks = clicks.extract_group("default")
print(default_clicks)