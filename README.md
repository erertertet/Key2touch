# Key2touch

A Windows utility for simulating touch events via custom keyboard mappings.

## Features
- Map keyboard keys to touch input at specified screen coordinates  
- Support single-key and multi-key combinations  
- Target a specific application window for touch injection  
- Command‑line interface with quickstart support  

## Getting started

https://github.com/user-attachments/assets/1549d923-ae3b-4b23-acbb-277e3c6e94bd

1. download `kt_shell.exe` from releases
2. put it into a prefered folder and double click it to start

## Directory Structure
```
Key2touch/
├─ mappings/           # Mapping files (.txt)
├─ utils.py            # Utility functions and Win32 Touch API wrappers
├─ test.py             # Core logic: key hooks and touch injection
├─ kt_shell.py         # Command‑line shell for managing mappings
├─ writer.py           # Helper script for creating new mapping files
├─ quickstart.json     # Quickstart configuration (auto‑generated)
└─ README.md           # Project documentation
```

## Requirements
- Windows 10 or later  
- Python 3.8+  
- Dependencies (see `requirements.txt`):
  - keyboard
  - ordered-set
  - zstandard

## Installation
```bash
git clone https://github.com/yourname/Key2touch.git
cd Key2touch
pip install -r requirements.txt
```

## Usage
### Method 1

Download executable and use as described above

### Method 2
1. Prepare or edit a mapping file in the `mappings/` directory  
2. Launch the shell interface:
   ```bash
   python kt_shell.py
   ```
3. Available commands:
   - `help`  : show help message  
   - `list`  : list mapping files  
   - `load`  : select a mapping file  
   - `create`: create a new mapping file  
   - `start` : start the mapper with chosen mapping and target app  
   - `qs`    : quickstart last used mapping  
   - `exit`  : quit the shell  

## Compilation
The project is compiled using nutika, simply run:
```python -m nuitka --onefile --msvc=latest .\kt_shell.py```
Notice: Compilation in other version of MSVC might end in malware prediction, 
by testing MSVC v143 result in normal form.

## Mapping File Format (example)
```txt
# example.txt
a: (100, 200)       # Single key 'a'
(b,c): (150, 250)   # Combination 'b' + 'c'
```

## Quickstart
Last used mapping and target are saved to `quickstart.json`.  
Use the `qs` command to launch with saved settings.

## Contributing
Contributions are welcome via issues and pull requests.

## License
This project is licensed under the Apache License.
