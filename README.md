# Dixel

Drawing program for pixel art
Requires pygame-ce, numpy and portalocker (multi-platform way to detect locked files)

## Features

- **Load Images**: Import pngs into a pixel grid.
- **View Navigation**: Move the view for large images.
- **Edit Pixels**: Color and erase pixels.
- **Brush Size**: Select the brush size using checkboxes.
- **Palette Options**: Edit or delete a color from the palette with a drop-down menu
- **Zooming**: Zoom in/out towards the mouse
- **Minimap**: See the current position on the grid with a minimap
- **Color Picker**: Select colors with a colorful and intuitive UI.
- **Resizable Grid**: Change the grid size and have a preview of how it will look.
- **Auto Save**: If you're editing an existing image it will be saved
- when the program or the file is closed if the program crashes the image will always be saved.

### Tools

- **Pencil**: Change individual pixels (x/y mirror)

## Keyboard Shortcuts

- **CTRL A**: Go to add color UI
- **CTRL M**: Go to modify grid UI
- **CTRL S**: Save file with name
- **CTRL O**: Open file
- **CTRL Q**: Close file
- **CTRL Backspace**: Exit in UI
- **CTRL Enter**: Confirm in UI

- **ALT arrows**: move selected pixel by brush size
- **SHIFT arrows**: move selected pixel by visible area
- **CTRL arrows**: move selected pixel to the limit of the grid
- **CTRL -/+**: zoom in/out
- **CTRL SHIFT -/+**: zoom in/out until limit
- **CTRL R**: reset grid offset and visible area

- **CTRL 1-5**: Change brush size
- **CTRL E**: Edit selected color
- **CTRL Del**: delete selected color

- **CTRL left/right**: go to end of text in input box
- **CTRL ALT left/right**: switch between scrollbar and input box in color picking UI
- **CTRL K**: toggle keep ratio in grid UI

## Screenshots

### Main Interface

![Main Interface](screenshots/main_interface.png)

### Color Picker

![Choosing Color](screenshots/color_ui.png)

### Grid UI

![Resizing Grid](screenshots/grid_ui.png)
