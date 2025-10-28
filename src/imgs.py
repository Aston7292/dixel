"""Images shared between files."""

from tkinter import messagebox
from pathlib import Path
from io import BytesIO
from typing import Final

import pygame as pg

from src.utils import add_border
from src.file_utils import FileError, handle_file_os_error, try_read_file
from src.lock_utils import LockError, try_lock_file
from src.type_utils import WH
from src.consts import WHITE, FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I


_ERRORS: Final[list[str]] = []
_MISSING_IMG: Final[pg.Surface] = pg.Surface((64, 64))
_MISSING_IMG.fill((255, 0, 0))
pg.draw.rect(_MISSING_IMG, WHITE, _MISSING_IMG.get_rect(), 4)


def _try_get_img(file_str: str, missing_img_wh: WH) -> pg.Surface:
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
    img: pg.Surface | None = None
    for attempt_i in range(FILE_ATTEMPT_START_I, FILE_ATTEMPT_STOP_I + 1):
        try:
            with file_path.open("rb") as f:
                try_lock_file(f, is_shared=True)
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
        img = pg.transform.scale(_MISSING_IMG, missing_img_wh)
    assert img.get_size() == missing_img_wh, f"{file_str} {img.get_size()}"

    img.set_colorkey((0, 0, 1))
    return img.convert()


ICON_IMG: Final[pg.Surface] = _try_get_img("icon.png", (32, 32))

CHECKBOX_OFF_IMG: Final[pg.Surface] = _try_get_img("checkbox_off.png", (48, 48))
CHECKBOX_ON_IMG: Final[pg.Surface]  = _try_get_img("checkbox_on.png" , (48, 48))

BUTTON_M_OFF_IMG: Final[pg.Surface] = _try_get_img("button_off.png", (128, 64))
BUTTON_M_ON_IMG: Final[pg.Surface]  = _try_get_img("button_on.png" , (128, 64))
BUTTON_S_OFF_IMG = pg.transform.scale(BUTTON_M_OFF_IMG, (96, 48)).convert()
BUTTON_S_ON_IMG  = pg.transform.scale(BUTTON_M_ON_IMG , (96, 48)).convert()
BUTTON_XS_OFF_IMG: Final[pg.Surface] = pg.transform.scale(BUTTON_M_OFF_IMG, (64, 32)).convert()
BUTTON_XS_ON_IMG: Final[pg.Surface]  = pg.transform.scale(BUTTON_M_ON_IMG , (64, 32)).convert()

X_MIRROR_OFF_IMG: Final[pg.Surface] = _try_get_img("mirror.png", (72, 70))
X_MIRROR_ON_IMG: Final[pg.Surface] = add_border(X_MIRROR_OFF_IMG, WHITE)
Y_MIRROR_OFF_IMG: Final[pg.Surface] = pg.transform.rotate(X_MIRROR_OFF_IMG, -90)
Y_MIRROR_ON_IMG: Final[pg.Surface]  = pg.transform.rotate(X_MIRROR_ON_IMG , -90)

ARROW_UP_OFF_IMG: Final[pg.Surface] = _try_get_img("arrow_off.png", (16, 10))
ARROW_UP_ON_IMG: Final[pg.Surface]  = _try_get_img("arrow_on.png" , (16, 10))
ARROW_DOWN_OFF_IMG: Final[pg.Surface] = pg.transform.rotate(ARROW_UP_OFF_IMG, 180).convert()
ARROW_DOWN_ON_IMG: Final[pg.Surface]  = pg.transform.rotate(ARROW_UP_ON_IMG , 180).convert()

ADD_OFF_IMG: Final[pg.Surface] = _try_get_img("add_off.png", (32, 32))
ADD_ON_IMG: Final[pg.Surface]  = _try_get_img("add_on.png" , (32, 32))

PENCIL_IMG: Final[pg.Surface]      = _try_get_img("pencil.png"     , (64, 64))
BUCKET_IMG: Final[pg.Surface]      = _try_get_img("bucket.png"     , (64, 64))
EYE_DROPPER_IMG: Final[pg.Surface] = _try_get_img("eye_dropper.png", (64, 64))
LINE_IMG: Final[pg.Surface]        = _try_get_img("line.png"       , (64, 64))
RECT_IMG: Final[pg.Surface]        = _try_get_img("rect.png"       , (64, 64))

SETTINGS_OFF_IMG: Final[pg.Surface] = _try_get_img("settings_off.png", (48, 48))
SETTINGS_ON_IMG: Final[pg.Surface]  = _try_get_img("settings_on.png" , (48, 48))

CLOSE_OFF_IMG: Final[pg.Surface] = _try_get_img("close_off.png", (48, 48))
CLOSE_ON_IMG: Final[pg.Surface]  = _try_get_img("close_on.png" , (48, 48))

ROTATE_LEFT_OFF_IMG: Final[pg.Surface] = _try_get_img("rotate_off.png", (38, 44))
ROTATE_LEFT_ON_IMG: Final[pg.Surface]  = _try_get_img("rotate_on.png" , (38, 44))
ROTATE_RIGHT_OFF_IMG: Final[pg.Surface] = pg.transform.flip(
    ROTATE_LEFT_OFF_IMG, True, False
).convert()
ROTATE_RIGHT_ON_IMG: Final[pg.Surface] = pg.transform.flip(
    ROTATE_LEFT_ON_IMG , True, False
).convert()

if _ERRORS != []:
    messagebox.showerror("Images Load Failed", "\n".join(_ERRORS))
del _ERRORS, _MISSING_IMG
