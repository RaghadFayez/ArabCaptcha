"""
utils/image_obfuscation.py

Final production version for ArabCaptcha. 
Handles difficulty purely on the server side using OpenCV.
"""
import io
import cv2
import numpy as np

PARAMS = {
    "easy": {
        "amplitude": 6,
        "period": 100,
        "num_lines": 1,      # Subtle line to not look "plain"
        "num_dots": 100,     # Table requirement
        "noise_eps": 3,
        "angle": -2,         # Subtle slant
        "blur": False,
    },
    "medium": {
        "amplitude": 9,
        "period": 80,
        "num_lines": 5,      # Table requirement
        "num_dots": 400,     # Table requirement
        "noise_eps": 6,
        "angle": 3,          # Medium slant
        "blur": False,
    },
    "hard": {
        "amplitude": 13,
        "period": 60,
        "num_lines": 7,      # Table requirement
        "num_dots": 550,     # Table requirement
        "noise_eps": 9,
        "angle": -5,         # Strong slant
        "blur": True,        # Table requirement
    },
}

def _rotate_image(image: np.ndarray, angle: float) -> np.ndarray:
    """Rotate image by a small angle with white background."""
    h, w = image.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(image, M, (w, h), borderValue=(255, 255, 255))

def _wave_distortion(image: np.ndarray, amplitude: int, period: int) -> np.ndarray:
    rows = image.shape[0]
    distorted = np.zeros_like(image)
    for i in range(rows):
        shift = int(amplitude * np.sin(2 * np.pi * i / period))
        distorted[i] = np.roll(image[i], shift, axis=0)
    return distorted

def _add_lines(image: np.ndarray, num_lines: int) -> np.ndarray:
    img = image.copy()
    h, w = img.shape[:2]
    for _ in range(num_lines):
        x1, y1 = np.random.randint(0, w), np.random.randint(0, h)
        x2, y2 = np.random.randint(0, w), np.random.randint(0, h)
        color = tuple(int(c) for c in np.random.randint(80, 180, 3))
        cv2.line(img, (x1, y1), (x2, y2), color, 1)
    return img

def _add_dots(image: np.ndarray, num_dots: int) -> np.ndarray:
    img = image.copy()
    h, w = img.shape[:2]
    for _ in range(num_dots):
        x = np.random.randint(0, w)
        y = np.random.randint(0, h)
        img[y, x] = np.random.randint(100, 220, 3)
    return img

def _adversarial_noise(image: np.ndarray, epsilon: float) -> np.ndarray:
    noise = np.random.randn(*image.shape) * epsilon
    return np.clip(image.astype(np.float32) + noise, 0, 255).astype(np.uint8)

def apply_difficulty_filters(image_bytes: bytes, difficulty: str) -> bytes:
    params = PARAMS.get(difficulty, PARAMS["easy"])
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        return image_bytes

    # High quality upscale to 400x150 for clarity
    image = cv2.resize(image, (400, 150), interpolation=cv2.INTER_CUBIC)

    # Distortion pipeline
    image = _rotate_image(image, params["angle"])
    image = _wave_distortion(image, params["amplitude"], params["period"])
    image = _add_lines(image, params["num_lines"])
    image = _add_dots(image, params["num_dots"])
    image = _adversarial_noise(image, params["noise_eps"])
    if params["blur"]:
        image = cv2.GaussianBlur(image, (3, 3), 0)

    success, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return buffer.tobytes() if success else image_bytes
