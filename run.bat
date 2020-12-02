FOR /f %%G IN ('conda env list ^|find "energy_usage"') DO set ENVIRONMENT=%%G
IF NOT "%ENVIRONMENT%" == "energy_usage" call conda env create -f environment.yml
CALL conda activate energy_usage
SET PYTHONPATH=%cd%
CD src
SET PYTHONPATH=%PYTHONPATH%;%cd%
PYTHON usage_analyser.py
CALL conda deactivate
PAUSE