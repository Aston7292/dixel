"""Images shared between files."""

from tkinter import messagebox
from pathlib import Path
from typing import Final, Optional

import pygame as pg

from src.lock_utils import LockException, FileException, try_lock_file
from src.type_utils import WH
from src.consts import BLACK, WHITE, NUM_MAX_FILE_ATTEMPTS, FILE_ATTEMPT_DELAY


ERRORS_LIST: Final[list[str]] = []
MISSING_IMG: Final[pg.Surface] = pg.Surface((64, 64))
MISSING_IMG.fill((255, 0, 0))
pg.draw.rect(MISSING_IMG, WHITE, MISSING_IMG.get_rect(), 4)


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
            ERRORS_LIST.append(f"{file_path.name}: File missing.")
            break
        except PermissionError:
            ERRORS_LIST.append(f"{file_path.name}: Permission denied.")
            break
        except LockException:
            ERRORS_LIST.append(f"{file_path.name}: File locked.")
            break
        except FileException as e:
            ERRORS_LIST.append(f"{file_path.name}: {e.error_str}")
            break
        except pg.error as e:
            ERRORS_LIST.append(f"{file_path.name}: {e}")
            break
        except OSError as e:
            if num_attempts == NUM_MAX_FILE_ATTEMPTS:
                ERRORS_LIST.append(f"{file_path.name}: {e}")
                break

            pg.time.wait(FILE_ATTEMPT_DELAY * num_attempts)

    if img is None:
        img = pg.transform.scale(MISSING_IMG, missing_img_wh)
    img.set_colorkey(BLACK)

    return img.convert()


ICON_IMG: Final[pg.Surface] = _try_get_img("icon.png", (32, 32))
BUTTON_M_OFF_IMG: Final[pg.Surface] = _try_get_img("button_m_off.png", (128, 64))
BUTTON_M_ON_IMG: Final[pg.Surface] = _try_get_img("button_m_on.png", (128, 64))
BUTTON_S_OFF_IMG: Final[pg.Surface] = pg.transform.scale(BUTTON_M_OFF_IMG, (64, 32)).convert()
BUTTON_S_ON_IMG: Final[pg.Surface] = pg.transform.scale(BUTTON_M_ON_IMG, (64, 32)).convert()

ARROW_UP_IMG_OFF: Final[pg.Surface] = _try_get_img("arrow_up_button_off.png", (35, 18))
ARROW_UP_IMG_ON: Final[pg.Surface] = _try_get_img("arrow_up_button_on.png", (35, 18))
ARROW_DOWN_IMG_OFF: Final[pg.Surface] = pg.transform.rotate(ARROW_UP_IMG_OFF, 180).convert()
ARROW_DOWN_IMG_ON: Final[pg.Surface] = pg.transform.rotate(ARROW_UP_IMG_ON, 180).convert()

PENCIL_IMG: Final[pg.Surface] = _try_get_img("pencil_tool.png", (64, 64))
BUCKET_IMG: Final[pg.Surface] = _try_get_img("pencil_tool.png", (64, 64))

CLOSE_BUTTON_OFF_IMG: Final[pg.Surface] = _try_get_img("close_button_off.png", (48, 48))
CLOSE_BUTTON_ON_IMG: Final[pg.Surface] = _try_get_img("close_button_on.png", (48, 48))
CHECKBOX_IMG_OFF: Final[pg.Surface] = _try_get_img("checkbox_off.png", (48, 48))
CHECKBOX_IMG_ON: Final[pg.Surface] = _try_get_img("checkbox_on.png", (48, 48))

if ERRORS_LIST != []:
    error_str: str = "\n".join(ERRORS_LIST)
    messagebox.showerror("Image Load Failed", error_str)
