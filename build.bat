@echo off
if exist final_hour\ (
    rmdir /s /q final_hour
    )
if not exist final_hour\ (
    md final_hour
    md final_hour\data
    )
echo building...
python -m nuitka --quiet --standalone --python-flag=no_site --user-plugin=CyalPlugin.py --windows-disable-console --windows-force-stderr=%program%final_hour.log --windows-force-stdout=%program%final_hour.log final_hour.py
xcopy /S /Q  dlls_windows\* final_hour\
copy *.mhr final_hour\
copy default_keyconfig.json final_hour\
xcopy /E /I /Q final_hour.dist final_hour
echo build completed...
echo copying required data...
xcopy /E /I /Q data final_hour\data\
xcopy /E /I /Q urlextract final_hour\urlextract\
if exist final_hour.dist\ (
    rmdir /s /q final_hour.dist
    )
if exist final_hour.build\ (
    rmdir /s /q final_hour.build
    )
echo build complete!