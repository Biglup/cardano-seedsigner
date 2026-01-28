# SeedSigner Emulator Components

This folder contains emulator components adapted from the [SeedSigner Emulator](https://github.com/enteropositivo/seedsigner-emulator).

## How It Works

The emulator replaces hardware-specific drivers with desktop equivalents:
- `desktopDisplay.py` - Tkinter-based display replacing ST7789
- `virtualGPIO.py` - GPIO emulation for button inputs
- `webcamvideostream.py` - Webcam integration replacing Pi camera

## Usage

From the project root, run:
```bash
python scripts/emulate.py
```

Or with clean rebuild:
```bash
python scripts/emulate.py --clean
```

This will:
1. Create a `build/emulation` folder with the patched source
2. Launch the emulator in a Tkinter window

## Controls

- **Arrow Keys**: Navigation (Up/Down/Left/Right)
- **Enter**: Press/Select
- **1, 2, 3** (or numpad): Side buttons
