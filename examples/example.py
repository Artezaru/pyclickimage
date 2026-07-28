import cv2
from pyclickimage import run, read_session
import os

img = os.path.join(os.path.dirname(__file__), "example.png")
run(images=img)
# Save at example.csv in order the next line work !

clicks = read_session(os.path.join(os.path.dirname(__file__), "example.csv"))
print(clicks)
