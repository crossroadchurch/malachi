@echo off
xcopy .\src\UpdateMalachi.py . /q /y > nul
python UpdateMalachi.py
echo.
echo Installing new Python modules ...
python -m pip install -r requirements.txt
echo.
del UpdateMalachi.py /q
echo Malachi has been updated!
echo.
pause