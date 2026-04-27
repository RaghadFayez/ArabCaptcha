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
        "amplitude": 5,
        "period": 140,
        "num_lines": 2,      
        "num_dots": 100,     
        "noise_eps": 2,
        "angle": -3,         
        "blur": False,
    },
    "medium": {
        "amplitude": 8,
        "period": 110,
        "num_lines": 4,      
        "num_dots": 250,     
        "noise_eps": 5,
        "angle": 4,          
        "blur": False,
    },
    "hard": {
        "amplitude": 12,
        "period": 85,
        "num_lines": 6,      
        "num_dots": 400,     
        "noise_eps": 8,
        "angle": -5,         
        "blur": True,        
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

def stitch_and_obfuscate(ref_bytes: bytes, low_conf_bytes: bytes, difficulty: str) -> bytes:
    """Stitch reference and low_confidence images horizontally, then apply obfuscation."""
    params = PARAMS.get(difficulty, PARAMS["easy"])
    
    nparr_ref = np.frombuffer(ref_bytes, np.uint8)
    nparr_low = np.frombuffer(low_conf_bytes, np.uint8)
    
    img_ref = cv2.imdecode(nparr_ref, cv2.IMREAD_COLOR)
    img_low = cv2.imdecode(nparr_low, cv2.IMREAD_COLOR)
    
    if img_ref is None or img_low is None:
        return ref_bytes # Fallback
        
    # Resize both to fixed height, maintain or force width
    # 200 width x 150 height each => 400x150 total
    img_ref = cv2.resize(img_ref, (200, 150), interpolation=cv2.INTER_CUBIC)
    img_low = cv2.resize(img_low, (200, 150), interpolation=cv2.INTER_CUBIC)
    
    # Generate random noisy gap between words (50px wide)
    gap = np.ones((150, 50, 3), dtype=np.uint8) * 255
    # Arabic is RTL: Reference word on right, low confidence on left
    composite = np.hstack([img_low, gap, img_ref])

    # Distortion pipeline over the ENTIRE composite image
    # This blurs the boundary between the two words
    composite = _rotate_image(composite, params["angle"])
    composite = _wave_distortion(composite, params["amplitude"], params["period"])
    composite = _add_lines(composite, params["num_lines"])
    composite = _add_dots(composite, params["num_dots"])
    composite = _adversarial_noise(composite, params["noise_eps"])
    if params["blur"]:
        composite = cv2.GaussianBlur(composite, (3, 3), 0)

    success, buffer = cv2.imencode(".jpg", composite, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return buffer.tobytes() if success else ref_bytes
