"""
utils/image_obfuscation.py

Applies visual distortion filters to CAPTCHA word images
based on the challenge's difficulty level (easy / medium / hard).

The same three filters are applied to all levels;
only the intensity parameters vary — creating a smooth,
progressive difficulty curve that is imperceptible to humans
at low levels but devastating to OCR models at high levels.
"""
import io
import cv2
import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# Filter parameters per difficulty level
# ─────────────────────────────────────────────────────────────────────────────

PARAMS = {
    "easy": {
        "amplitude": 7,
        "period": 100,
        "num_lines": 2,      # أضفنا خطين عشان ما تطلع "سادة"
        "num_dots": 150,
        "noise_eps": 4,
        "angle": -3,         # ميلان خفيف
        "blur": False,
    },
    "medium": {
        "amplitude": 10,
        "period": 80,
        "num_lines": 5,
        "num_dots": 400,
        "noise_eps": 8,
        "angle": 4,          # ميلان متوسط
        "blur": False,
    },
    "hard": {
        "amplitude": 14,
        "period": 60,
        "num_lines": 8,
        "num_dots": 600,
        "noise_eps": 10,
        "angle": -6,         # ميلان قوي
        "blur": True,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Individual filters
# ─────────────────────────────────────────────────────────────────────────────

def _wave_distortion(image: np.ndarray, amplitude: int, period: int) -> np.ndarray:
    """Shift each row horizontally by a sinusoidal amount."""
    rows = image.shape[0]
    distorted = np.zeros_like(image)
    for i in range(rows):
        shift = int(amplitude * np.sin(2 * np.pi * i / period))
        distorted[i] = np.roll(image[i], shift, axis=0)
    return distorted


def _add_lines(image: np.ndarray, num_lines: int) -> np.ndarray:
    """Draw random diagonal lines across the image."""
    img = image.copy()
    h, w = img.shape[:2]
    for _ in range(num_lines):
        x1, y1 = np.random.randint(0, w), np.random.randint(0, h)
        x2, y2 = np.random.randint(0, w), np.random.randint(0, h)
        color = tuple(int(c) for c in np.random.randint(80, 180, 3))
        cv2.line(img, (x1, y1), (x2, y2), color, 1)
    return img


def _add_dots(image: np.ndarray, num_dots: int) -> np.ndarray:
    """Scatter random colored pixels across the image."""
    img = image.copy()
    h, w = img.shape[:2]
    for _ in range(num_dots):
        x = np.random.randint(0, w)
        y = np.random.randint(0, h)
        img[y, x] = np.random.randint(100, 220, 3)
    return img


def _rotate_image(image: np.ndarray, angle: float) -> np.ndarray:
    """Rotate image by a small angle with white background."""
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(image, M, (w, h), borderValue=(255, 255, 255))


def _adversarial_noise(image: np.ndarray, epsilon: float) -> np.ndarray:
    """Add Gaussian noise to subtly perturb pixel values."""
    noise = np.random.randn(*image.shape) * epsilon
    return np.clip(image.astype(np.float32) + noise, 0, 255).astype(np.uint8)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def apply_difficulty_filters(image_bytes: bytes, difficulty: str) -> bytes:
    """
    Load raw image bytes, apply the appropriate distortion pipeline
    for the given difficulty level, and return the processed image as JPEG bytes.

    Args:
        image_bytes: Raw bytes of the original word image.
        difficulty:  One of "easy" | "medium" | "hard".

    Returns:
        JPEG-encoded bytes of the distorted image.
    """
    params = PARAMS.get(difficulty, PARAMS["easy"])

    # Decode image from bytes
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        # If decoding fails, return original bytes unchanged
        return image_bytes

    # Resize for consistency (same as test.py)
    image = cv2.resize(image, (400, 150))

    # Apply pipeline
    image = _rotate_image(image, params["angle"])
    image = _wave_distortion(image, params["amplitude"], params["period"])
    image = _add_lines(image, params["num_lines"])
    image = _add_dots(image, params["num_dots"])
    image = _adversarial_noise(image, params["noise_eps"])
    if params["blur"]:
        image = cv2.GaussianBlur(image, (3, 3), 0)

    # Encode back to JPEG bytes
    success, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not success:
        return image_bytes

    return buffer.tobytes()
