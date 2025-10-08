# signals2dve

**signals2dve** is a Python helper script that automates adding signals in batch to an existing **Synopsys DVE** `.tcl` session file.  
It reads a YAML configuration file that defines groups, dividers, signals, and hierarchical relationships, then generates DVE-compatible TCL commands to create and organize waveform groups automatically.

---

## Overview

- Parses a **YAML** configuration describing signal hierarchies and group structures.
- Expands environment variables and iterators (e.g., `${core}`, `${w}`) to handle multiple instances of same components dynamically.
- Generates TCL code for:
  - Creating DVE signal groups and subgroups.
  - Adding signals with the correct radix.
  - Collapsing/expanding groups.
  - Adding named dividers.
- Inserts the generated code into an existing DVE `.tcl` session file.

This eliminates the need to manually browse and add hundreds of signals repeteadly for multiple instances (e.g. entries alternating banks of the ROB in BOOM).

---

## Usage

```bash
./signals2dve.py -c boom-medium-spt.yaml -s input_blank.tcl -o output.tcl
```

* `-c` / `--config` : YAML configuration file defining signals and groups.
* `-s` / `--source` : Input TCL file (e.g., a DVE session template).
* `-o` / `--output` : Output TCL file with the new groups inserted.

If `-o` is omitted, the output defaults to `patched_<source>.tcl`.

Example configs (`boom-medium-spt.yaml`, `sample.yaml`) are included for guidance.

---

## Example Workflow

1. Use one of the template provides, or edit your own YAML file to add your desired the signals.
2. Run the script as above.
3. Open the generated `output.tcl` in DVE:

   ```bash
   dve -session output.tcl
   ```
4. Verify the new groups and signals appear in your Waveform view (`Wave.1` by default).

*Note: Missing signals will show up as errors on  DVE's console after loading the script.*

---

## Requirements

Python 3 and PyYAML

```bash
pip install -r requirements.txt
```

---

## Audience

Initially designed for students working on BOOM (https://boom-core.org/) at the Chair of Electronic Design Automation in RPTU (https://github.com/RPTU-EIS), but it can be useful to any RTL engineers using **Synopsys VCS/DVE** for waveform visualization and debugging.

---


