set PYTHONPATH=%cd%
cd src
set PYTHONPATH=%PYTHONPATH%;%cd%
python usage_analyser.py
pause