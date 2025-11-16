# Task 2 - CGMES EQ Profile Analyzer

## What is this?
A Python script that analyzes a CGMES (Common Grid Model Exchange Standard) XML file containing Dutch electrical network data. It answers 6 specific power system questions and identifies model errors.

## Files
- `task2.py` - Main analyzer script (English version)
- `20210325T1530Z_1D_NL_EQ_001.xml` - Input data file (CGMES model)
- `output_english.txt` - Analysis results

## How to run?
```bash
python task2.py
```

## What does it do?

### Question 1: Generator Capacity
Shows total production capacity and power factors of all generators.
**Answer:** 1,500 MW total (0.90 power factor)

### Question 2: NL-G1 Voltage Control
Identifies the regulation mode for generator NL-G1.
**Answer:** Voltage control regulation

### Question 3: Transformer Specifications
Displays winding voltages and specifications for transformer NL_TR2_2.
**Answer:** 220/15.75 kV (ratio 13.97:1)

### Question 4: Line Limits
Shows PATL and TATL current limits for line NL-Line_5.
**Answer:** PATL=1876A, TATL=500A (illogical - TATL should be higher)

### Question 5: Slack Bus
Identifies which generator should be the slack bus.
**Answer:** Gen-12923 (largest, 1000 MW)

### Question 6: Model Errors
Lists all errors and inconsistencies found in the model.
**Answer:** 25 critical errors found (duplicate mRIDs, illogical limits, incomplete data)

## Key Findings
- ✓ Total capacity: 1,500 MW
- ⚠ All generators set to 'offAGC' - needs slack designation
- ⚠ 12 line segments have TATL < PATL (backwards)
- ⚠ Duplicate mRID in 3 transformer windings
- ⚠ 5 equipment items have zero impedance

## Requirements
- Python 3.x
- xml.etree.ElementTree (built-in)

## How to Create Output File?

The output file is already created! It's at: **`output_english.txt`** in your task2 folder.

But if you want to create it again, run this command:

```powershell
python task2.py | Out-File -Encoding UTF8 output_english.txt
```

Or save it with a different name:

```powershell
python task2.py | Out-File -Encoding UTF8 my_results.txt
```

The output file contains all the analysis results from running `task2.py` in a text file you can open and read.

## Output Format
- Console output (when running script)
- Saved to `output.txt` (complete results)
