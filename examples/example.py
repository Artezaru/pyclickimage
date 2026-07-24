import cv2
from pyclickimage import run, read_session_csv
import os

img = cv2.imread(os.path.join(os.path.dirname(__file__), "example.png"))
run(images=img)
# Save at example.csv in order the next line work !

clicks = read_session_csv("example.csv")
print(clicks)
