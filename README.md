## Installation & Setup
### Set up a python virtual environment
```py
py -m venv pvenv
```
### Activate the python virual environment
```bash
pvenv\Scripts\Activate
```
or
```bash
cmd
(cmd) pvenv\Scripts\Activate
```
### Use pip to install packages
```py
pip install -r requirements.txt
```
### Setting up
1. Place PDFs in the ***./input_files/pdfs*** folder
2. Place excel data in the ***./input_files/excel*** folder
    - make sure the excel file name matches the path in ***config.json/paths/excel_source***
    - i'd reccomend keeping the name as '**placeholder_excelname.xlsx**' or something discrete/general
3. Ensure that the path to the **.gguf** is correctly set in ***config.json/paths/gguf_path*** don't include any PII in the path
