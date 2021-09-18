@echo off
xcopy .\src\UpdateMalachi.py . /q /y > nul
python UpdateMalachi.py
del UpdateMalachi.py /q
pause