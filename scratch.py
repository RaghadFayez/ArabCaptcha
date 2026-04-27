from app.utils.image_obfuscation import stitch_and_obfuscate
import cv2
import numpy as np
ref_bytes = open("assets/words/word_1.jpg", "rb").read()
low_bytes = open("assets/words/word_2.jpg", "rb").read()
out = stitch_and_obfuscate(ref_bytes, low_bytes, "easy")
open("out.jpg", "wb").write(out)
print("Done")
