# FIT File Analysis

This program scans a FIT file that includes HRV messages looking for zones with high variability of successive beat to beat interval differences.  

## Description of Operation

A csv file is created containing relevant data.  The data includes:
- timestamp
- latitude (degrees)
- longitude (degrees)
- heart rate (beats per minute) as recorded in the fit file
- RR interval as recorded in the fit file HRV messages (milliseconds)
- RR interval of the previous beat
- instantaneous heart rate calculated from the RR interval (beats per minute)
- estimated standard deviation of the difference in successive RR periods, SDΔRR (milliseconds).  This is similar to the standard metric RMSSD, however SDΔRR is estimated from a subset of the data to make it robust to outliers.
- a flag, warn, indicating zones of high SDΔRR.  An empty field means no data is available, 0 indicates no warning, 1 indicates a warning.

If zone(s) are identified a message "Suspicious events found in ..." is printed and [Poincaré plots](https://en.wikipedia.org/wiki/Poincar%C3%A9_plot) are saved as portable network graphics (.png) files.

The program may not identify zones where evidence of an arrhythmia exists.  The program may erroneously identify zones where no arrhythmia occurred.  Artifacts in the data may make the program unreliable.  The program is not intended to identify all types of arrhythmia.  Interpretations of the validity and significance of the results is left to the user and their doctor.

```
usage: analyze_hrv [-h] [--threshold THRESHOLD] src

FIT file HRV analyzer

positional arguments:
  src                   Input FIT file

options:
  -h, --help            show this help message and exit
  --threshold THRESHOLD, -t THRESHOLD
                        HRV threshold(msec) (default: 50)
```

## Data Collection

It is likely that HRV data is not logged by default.  You may have to enable it on your device.  For example, with a Garmin Edge 840, you can enable logging in the [Data Recording Settings](https://www8.garmin.com/manuals/webhelp/GUID-16B12CFE-F96E-4DE9-9F5F-8C4A5936D3B9/EN-US/GUID-5BF2156B-9740-47F1-A564-FA22D55FDEB1.html#)

If you are using Garmin Connect, instructions for exporting your data can be found [in the Garmin FAQs](https://support.garmin.com/en-US/?faq=W1TvTPW8JZ6LfJSfK512Q8).  Follow the instructions for "Export Original" and "Export a Timed Activity From Garmin Connect" to download your FIT file.

## Required Tools

A recent version of python 3 is required. 

You can download the python .whl file from [github](https://github.com/tsteven4/fit-analysis/releases).  Expand "Assets" and select the .whl file.  The "Continuous build" release on that page is continuously updated as changes are made.  The .whl file from older releases are not archived.  The version number may or may not change when it is updated.

You can install the .whl file with pip3.  Substitute the actual name of the .whl file you downloaded.  For example, from a command prompt (DOS, powershell, bash, etc.) :
```
pip3 install --upgrade fit_analysis-0.0.2-py3-none-any.whl
```

### Windows

On windows python 3 can be downloaded from the [Microsoft Store](https://apps.microsoft.com/store/detail/python-310/9PJPW5LDXLZ5).  You may want to heed the message "WARNING: The script analyze_hrv.exe is installed in ... which is not on PATH.  Consider adding this directory to PATH ...".  Having the script directory in your path will make it easier analyze fit files from the command line.

### macOS

On macOS python 3 can be downloaded from [python.org](https://www.python.org/downloads/macos/), or installed with [Homebrew](https://brew.sh/) or [MacPorts](https://ports.macports.org/).

### Linux

On linux python3 is probably available from your distribution using your standard packaging tools, e.g. apt, dnf, ...
