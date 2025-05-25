"""Images shared between files."""

from tkinter import messagebox
from pathlib import Path
from typing import Final, Optional

import pygame as pg

from src.lock_utils import LockException, FileException, try_lock_file
from src.type_utils import WH
from src.consts import BLACK, WHITE, NUM_MAX_FILE_ATTEMPTS, FILE_ATTEMPT_DELAY


_ERRORS_LIST: Final[list[str]] = []
_MISSING_IMG: Final[pg.Surface] = pg.Surface((64, 64))
_MISSING_IMG.fill((255, 0, 0))
pg.draw.rect(_MISSING_IMG, WHITE, _MISSING_IMG.get_rect(), 4)


def _try_get_img(file_str: str, missing_img_wh: WH) -> pg.Surface:
    """
    Loads an image.

    Args:
        file string, missing image size
    Returns:
        image (if it fails returns MISSING_IMG)
    """

    num_attempts: int

    file_path: Path = Path("assets", "sprites", file_str)
    img: Optional[pg.Surface] = None
    for num_attempts in range(1, NUM_MAX_FILE_ATTEMPTS + 1):
        try:
            with file_path.open("rb") as f:
                try_lock_file(f, True)
                img = pg.image.load(f, file_path.name)
            break
        except FileNotFoundError:
            _ERRORS_LIST.append(f"{file_path.name}: File missing.")
            break
        except PermissionError:
            _ERRORS_LIST.append(f"{file_path.name}: Permission denied.")
            break
        except LockException:
            _ERRORS_LIST.append(f"{file_path.name}: File locked.")
            break
        except FileException as e:
            _ERRORS_LIST.append(f"{file_path.name}: {e.error_str}")
            break
        except pg.error as e:
            _ERRORS_LIST.append(f"{file_path.name}: {e}")
            break
        except OSError as e:
            if num_attempts == NUM_MAX_FILE_ATTEMPTS:
                _ERRORS_LIST.append(f"{file_path.name}: {e}")
                break

            pg.time.wait(FILE_ATTEMPT_DELAY * num_attempts)

    if img is None:
        img = pg.transform.scale(_MISSING_IMG, missing_img_wh)
    img.set_colorkey(BLACK)

    return img.convert()


ICON_IMG: Final[pg.Surface] = _try_get_img("icon.png", (32, 32))

CHECKBOX_OFF_IMG: Final[pg.Surface] = _try_get_img("checkbox_off.png", (48, 48))
CHECKBOX_ON_IMG: Final[pg.Surface] = _try_get_img("checkbox_on.png", (48, 48))

BUTTON_M_OFF_IMG: Final[pg.Surface] = _try_get_img("button_off.png", (128, 64))
BUTTON_M_ON_IMG: Final[pg.Surface] = _try_get_img("button_on.png", (128, 64))

BUTTON_S_OFF_IMG = pg.transform.scale(BUTTON_M_OFF_IMG, (96, 48)).convert()
BUTTON_S_ON_IMG = pg.transform.scale(BUTTON_M_ON_IMG, (96, 48)).convert()
BUTTON_XS_OFF_IMG: Final[pg.Surface] = pg.transform.scale(BUTTON_M_OFF_IMG, (64, 32)).convert()
BUTTON_XS_ON_IMG: Final[pg.Surface] = pg.transform.scale(BUTTON_M_ON_IMG, (64, 32)).convert()

ARROW_UP_OFF_IMG: Final[pg.Surface] = _try_get_img("arrow.png", (35, 18))
ARROW_UP_ON_IMG: Final[pg.Surface] = pg.transform.hsl(ARROW_UP_OFF_IMG, lightness=-0.5).convert()
ARROW_DOWN_OFF_IMG: Final[pg.Surface] = pg.transform.rotate(ARROW_UP_OFF_IMG, 180).convert()
ARROW_DOWN_ON_IMG: Final[pg.Surface] = pg.transform.rotate(ARROW_UP_ON_IMG, 180).convert()

CLOSE_BUTTON_OFF_IMG: Final[pg.Surface] = _try_get_img("close_button.png", (48, 48))
CLOSE_BUTTON_ON_IMG: Final[pg.Surface] = pg.transform.hsl(
    CLOSE_BUTTON_OFF_IMG, lightness=-0.5
).convert()

BRUSH_IMG: Final[pg.Surface] = _try_get_img("brush_tool.png", (64, 64))
BUCKET_IMG: Final[pg.Surface] = _try_get_img("bucket_tool.png", (64, 64))
EYE_DROPPER_IMG: Final[pg.Surface] = _try_get_img("eye_dropper_tool.png", (64, 64))

if _ERRORS_LIST != []:
    error_str: str = "\n".join(_ERRORS_LIST)
    messagebox.showerror("Image Load Failed", error_str)
