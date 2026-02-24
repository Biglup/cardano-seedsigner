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

## Display Options

The emulator supports multiple display sizes:

```bash
# Default 240x240 (original SeedSigner display)
python scripts/emulate.py

# Larger 320x240 display
python scripts/emulate.py --display st7789_320x240

# ILI9341 320x240 (beta)
python scripts/emulate.py --display ili9341_320x240
```

Available configurations:
| Option | Resolution | Notes |
|--------|------------|-------|
| `st7789_240x240` | 240x240 | Default, original Waveshare 1.3" |
| `st7789_320x240` | 320x240 | Larger ST7789 display |
| `ili9341_320x240` | 320x240 | ILI9341 driver (beta) |

This will:
1. Create a `build/emulation` folder with the patched source
2. Launch the emulator in a Tkinter window

## Controls

- **Arrow Keys**: Navigation (Up/Down/Left/Right)
- **Enter**: Press/Select
- **1, 2, 3** (or numpad): Side buttons
