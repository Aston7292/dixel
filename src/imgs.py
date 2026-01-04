"""Images shared between files."""

from tkinter import messagebox
from pathlib import Path
from io import BytesIO
from typing import Final

import pygame as pg
import numpy as np
from pygame import Surface, surfarray, draw, transform
from numpy import uint8, uint32, bool_
from numpy.typing import NDArray

from src.utils import add_border
from src.file_utils import FileError, handle_file_os_error, try_read_file
from src.lock_utils import LockError, try_lock_file
from src.type_utils import WH
from src.consts import WHITE, FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I


_ERRORS: Final[list[str]] = []
_MISSING_IMG: Final[Surface] = Surface((64, 64))
_MISSING_IMG.fill((255, 0, 0))
draw.rect(_MISSING_IMG, WHITE, _MISSING_IMG.get_rect(), width=4)


def _try_get_img(file_str: str, missing_img_wh: WH) -> Surface:
    """
    Loads an image with retries.

    Args:
        file string, missing image size
    Returns:
        image (if it fails returns MISSING_IMG)
    """

    attempt_i: int
    error_str: str
    should_retry: bool

    file_path: Path = Path("assets", "sprites", file_str)
    img: Surface | None = None
    for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
        try:
            with file_path.open("rb") as f:
                try_lock_file(f, should_be_shared=True)
                img_bytes_io: BytesIO = BytesIO(try_read_file(f))
                img = pg.image.load(img_bytes_io, namehint=file_path.suffix)
            break
        except (FileNotFoundError, PermissionError, LockError, FileError, pg.error) as e:
            error_str = {
                FileNotFoundError: "File missing.",
                PermissionError: "Permission denied.",
                LockError: "File locked.",
                FileError: e.error_str if isinstance(e, FileError) else "",
                pg.error: str(e),
            }[type(e)]

            _ERRORS.append(f"{file_path.name}: {error_str}")
            break
        except OSError as e:
            error_str, should_retry = handle_file_os_error(e)
            if should_retry and _ERRORS == [] and attempt_i != FILE_ATTEMPT_STOP_I:
                pg.time.wait(2 ** attempt_i)
                continue

            _ERRORS.append(f"{file_path.name}: {error_str}")
            break

    if img is None:
        img = transform.scale(_MISSING_IMG, missing_img_wh)
    assert img.get_size() == missing_img_wh, f"{file_str} {img.get_size()}"

    img.set_colorkey((0, 0, 1))
    return img.convert()

def _change_brightness(img: Surface, brightness: float) -> Surface:
    """
    Changes the brightness of an image while preserving the transparent pixels and colorkey

    Args:
        image, brightness
    Returns:
        image
    """

    img = img.convert_alpha()
    pixels: NDArray[uint8] = np.dstack((surfarray.pixels3d(img), surfarray.pixels_alpha(img)))
    colorkey_arr: NDArray[uint8] = np.array((0, 0, 1, 0), uint8)
    colorkey_mask: NDArray[bool_] = pixels.view(uint32)[..., 0] == colorkey_arr.view(uint32)[0]

    transform.hsl(img, lightness=brightness, dest_surface=img)
    surfarray.pixels3d(img)[colorkey_mask] = (0, 0, 1)
    img.set_colorkey((0, 0, 1))
    return img.convert()


ICON_IMG: Final[Surface] = _try_get_img("icon.png", (32, 32))

CHECKBOX_OFF_IMG: Final[Surface] = _try_get_img("checkbox.png", (48, 48))
CHECK_IMG: Final[Surface] = _try_get_img("check.png", (32, 32))
CHECKBOX_ON_IMG: Final[Surface] = CHECKBOX_OFF_IMG.copy()
CHECKBOX_ON_IMG.blit(
    CHECK_IMG,
    (
        CHECKBOX_OFF_IMG.get_rect().centerx - (CHECK_IMG.get_width()  / 2),
        CHECKBOX_OFF_IMG.get_rect().centery - (CHECK_IMG.get_height() / 2),
    )
)

BUTTON_M_OFF_IMG: Final[Surface] = _try_get_img("button.png", (128, 64))
BUTTON_M_ON_IMG: Final[Surface] = _change_brightness(BUTTON_M_OFF_IMG, 0.5)
BUTTON_S_OFF_IMG = transform.scale(BUTTON_M_OFF_IMG, (96, 48)).convert()
BUTTON_S_ON_IMG  = transform.scale(BUTTON_M_ON_IMG , (96, 48)).convert()
BUTTON_XS_OFF_IMG: Final[Surface] = transform.scale(BUTTON_M_OFF_IMG, (64, 32)).convert()
BUTTON_XS_ON_IMG: Final[Surface]  = transform.scale(BUTTON_M_ON_IMG , (64, 32)).convert()

X_MIRROR_OFF_IMG: Final[Surface] = _try_get_img("mirror.png", (72, 70))
X_MIRROR_ON_IMG: Final[Surface] = add_border(X_MIRROR_OFF_IMG, WHITE)
Y_MIRROR_OFF_IMG: Final[Surface] = transform.rotate(X_MIRROR_OFF_IMG, -90).convert()
Y_MIRROR_ON_IMG: Final[Surface]  = transform.rotate(X_MIRROR_ON_IMG , -90).convert()

ARROW_UP_OFF_IMG: Final[Surface] = _try_get_img("arrow.png", (16, 10))
ARROW_UP_ON_IMG: Final[Surface] = _change_brightness(ARROW_UP_OFF_IMG, -0.5)
ARROW_DOWN_OFF_IMG: Final[Surface] = transform.rotate(ARROW_UP_OFF_IMG, 180).convert()
ARROW_DOWN_ON_IMG: Final[Surface]  = transform.rotate(ARROW_UP_ON_IMG , 180).convert()

ADD_OFF_IMG: Final[Surface] = _try_get_img("add.png", (32, 32))
ADD_ON_IMG: Final[Surface] = _change_brightness(ADD_OFF_IMG, 0.5)
INFO_OFF_IMG: Final[pg.Surface] = _try_get_img("info.png", (11, 3))
INFO_ON_IMG: Final[pg.Surface] = _change_brightness(INFO_OFF_IMG, 0.5)

PENCIL_IMG: Final[Surface]      = _try_get_img("pencil.png"     , (64, 64))
ERASER_IMG: Final[Surface]      = _try_get_img("eraser.png"     , (64, 64))
BUCKET_IMG: Final[Surface]      = _try_get_img("bucket.png"     , (64, 64))
EYE_DROPPER_IMG: Final[Surface] = _try_get_img("eye_dropper.png", (64, 64))
LINE_IMG: Final[Surface]        = _try_get_img("line.png"       , (64, 64))
RECT_IMG: Final[Surface]        = _try_get_img("rect.png"       , (64, 64))

SETTINGS_OFF_IMG: Final[Surface] = _try_get_img("settings.png", (48, 48))
SETTINGS_ON_IMG: Final[Surface] = _change_brightness(SETTINGS_OFF_IMG, 0.5)

CLOSE_OFF_IMG: Final[Surface] = _try_get_img("close.png", (48, 48))
CLOSE_ON_IMG: Final[Surface] = _change_brightness(CLOSE_OFF_IMG, -0.5)

ROTATE_LEFT_OFF_IMG: Final[Surface] = _try_get_img("rotate.png", (38, 44))
ROTATE_LEFT_ON_IMG: Final[Surface] = _change_brightness(ROTATE_LEFT_OFF_IMG, -0.5)
ROTATE_RIGHT_OFF_IMG: Final[Surface] = transform.flip(ROTATE_LEFT_OFF_IMG, True, False).convert()
ROTATE_RIGHT_ON_IMG: Final[Surface]  = transform.flip(ROTATE_LEFT_ON_IMG , True, False).convert()

if _ERRORS != []:
    messagebox.showerror("Images Load Failed", "\n".join(_ERRORS))
del _ERRORS, _MISSING_IMG
