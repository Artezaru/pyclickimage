import cv2
from pyclickimage import ClickManager, run
import os

img = cv2.imread(os.path.join(os.path.dirname(__file__), "example.png"))
file = os.path.join(os.path.dirname(__file__), "clicks.csv")
run(image=img, output=file)

clicks = ClickManager.load_from_csv(file)
default_clicks = clicks.extract_group("default")
print(default_clicks)