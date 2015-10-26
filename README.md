# Procurement charts
This script generates a set of JSON files that powers the [procurement dashboards](https://github.com/procurement-analytics/procurement-analytics). It is developed to work with the OCDS record packages that the Compranet to OCDS](https://github.com/procurement-analytics/compranet-data/) script generates. These record packages are not fully compliant with the standard, which is why this script may not work on all OCDS record packages. It does serve as a reference for other implementations.

## How to use this script
The `procurement-charts.py` script reads all JSON files in a folder and outputs JSON files with aggregate stats.

`$ python procurement-charts.py [path to folder]`