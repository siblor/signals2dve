# signals2dve

**signals2dve** is a Python helper script that automates adding signals in batch to an existing **Synopsys DVE** `.tcl` session file.
It reads a YAML configuration file that defines groups, dividers, signals, and hierarchical relationships, then generates DVE-compatible TCL commands to create and organize waveform groups automatically.

---

## Overview

* Parses a **YAML** configuration describing signal hierarchies and group structures.
* Generates TCL code for:

  * Creating DVE signal groups and subgroups.
  * Adding signals with the correct radix.
  * Collapsing/expanding groups.
  * Adding named dividers.
* Inserts the generated code into an existing DVE `.tcl` session file.
* Expands environment variables and iterators (e.g., `${core}`, `${w}`) to handle multiple instances dynamically.

This eliminates the need to manually browse and add hundreds of signals repeatedly (e.g., alternating ROB banks in BOOM).

---

## Installation

Clone the repository and install the required dependencies:

```bash
git clone https://github.com/siblor/signals2dve.git
cd signals2dve
pip install -r requirements.txt
```

Requires **Python 3** and **PyYAML**.

---

## Usage

You can run `signals2dve.py` directly on an existing `.tcl` DVE session, or create a clean blank session first.

### Direct usage (if you already have a blank session file)

```bash
./signals2dve.py -c configurations/boom-medium-spt.yaml -s empty_wave_session.tcl -o patched_session.tcl
```

* `-c` / `--config` : YAML configuration defining signals and groups
* `-s` / `--source` : Input TCL file (template or empty session)
* `-o` / `--output` : Output TCL file with inserted signal groups

If `-o` is omitted, the output defaults to `patched_<source>.tcl`.

Then open the patched session in DVE:

```bash
dve -full64 -vpd simulationfile.vpd -session patched_session.tcl
```

---

### How to generate a blank session

1. **Copy** `gen_empty_session.tcl` to your VCS simulation directory.
2. **Run** it on DVE with your desired .vpd file:

   ```bash
   dve -full64 -vpd simulationfile.vpd -script gen_empty_session.tcl
   ```

   DVE will launch and immediately ask to close — click **Yes** to exit.
3. A new file `empty_wave_session.tcl` will be created. That is your template.
   **Copy it** to the repository folder next to `signals2dve.py`.


---

## Notes

* Missing signals will appear as console warnings in DVE upon loading.
* Example configurations (`boom-medium-spt.yaml`, `sample.yaml`) are included for reference.

---

## Audience

Originally developed for students working on **BOOM (Berkeley Out-of-Order Machine)** at the
**Chair of Electronic Design Automation (RPTU)** — [https://github.com/RPTU-EIS](https://github.com/RPTU-EIS).
It can be useful to anyone working with **Synopsys VCS/DVE** for RTL waveform analysis and debugging.

---