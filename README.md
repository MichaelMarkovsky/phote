# phote - Photo Digitization Editor
> A smart photo editor focused on digitizing, organizing, and restoring physical photos.
<img width="1513" height="851" alt="thumbnail" src="https://github.com/user-attachments/assets/64db408e-987a-4b26-96e5-296efd43ec1f" />
Demo video: https://github.com/user-attachments/assets/2c9bb5de-4e0b-4b88-a9c3-3bf5a41cce53

---

## Features
- **Automatic Perspective Correction** - Detects photo borders and straightens them
- **Automatic Color Enhancement** - White balance + exposure adjustments
- **Manual Controls** - Simple sliders for fine-tuning
- **Smart Export System** - Organizes photos into folders (front/back, numbered)
- **Edit Persistence** - Saves all edits (JSON-based workflow)

---

### Export Structure:
```
└── Edited/
    └── Black and White/
        ├── 001 
        └── 002 (Photo)/
            ├── `002 - front.png`
            └── `002 - back.png`
```
### JSON Structure:
Each image has a corresponding JSON file that stores all edits and classification data.

Example:
The file we edit: `IMG_9093.CR3`
The json file created: `IMG_9093.CR3.json`
```json
{
    "rotation": 5,
    "perspective": true,
    "color_enabled": true,
    "color_settings": {
        "color_fix": 0.5,
        "warmth": 0,
        "tint": 0,
        "contrast": 0.61,
        "exposure": 0.1
    },
    "classification": {
        "photo_id": 1,
        "side": "front",
        "needs_manual": false
    }
}
```

## Requirements

- Python 3.10+
- `exiftool` installed on system

### Python Dependencies

- `numpy` - numerical operations
- `opencv-python` - image processing
- `PySide6` - GUI framework
- `rawpy` - RAW image loading

Notes: 
- The UI was built using Qt Designer (`phote.ui`).
- For understanding the features, checkout `phote.ipynb`.

---

## Installation
```bash
git clone https://github.com/MichaelMarkovsky/phote.git
cd phote

python -m venv venv
source venv/bin/activate  # Linux

pip install -r requirements.txt
```

---

## Usage
Start the program via `python main.py`.

1. Open a folder that contains `CR3` RAW files.
2. Edit via either the shortcuts or the sliders.
3. Classify the photo as either `front` or `back`.
4. Enter the number of the physical photo.
5. Continue to the next image!


### Key Shortcuts:
- `Q` - Quit
- `Enter` - Auto Perspective
- `C` - Color on/off
- `R` - Rotate
- `E` - Export a single photo
- `Shift+E` - Export all
- `Ctrl+O` - Open Folder

