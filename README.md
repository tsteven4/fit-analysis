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

If zone(s) are identified a message "Suspicious events found in ..." is printed and Poincaré plots are saved as portable network graphics (png) files.

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

If you are using Garmin Connect, instructions for exporting your data can be found [here](https://support.garmin.com/en-US/?faq=W1TvTPW8JZ6LfJSfK512Q8).  Follow the instructions for "Export Original" and "Export a Timed Activity From Garmin Connect" to download your FIT file.
