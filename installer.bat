@echo off
cd C:\Users\kelleyk\repos\cv_gx

rmdir /s dist

echo building binary
pyinstaller --onefile --icon=cam.bmp --splash=cam.png cam.py --add-data "config.txt;."

echo Zipping the folder...

:: Use tar to compress the folder to a zip file
tar -a -c -f cam.zip dist

echo Folder zipped successfully

:: Copy the zip file to the new location
echo Copying the zip file
copy cam.zip R:\PE\CAMERA\

echo  File copied successfully

:: Pause to wait for user input before closing the script
pause