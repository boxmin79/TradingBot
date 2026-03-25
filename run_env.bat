@echo off
echo [*] .swingbot 가상환경을 활성화하는 중...
set PATH=%CD%\.swingbot\Scripts;%PATH%
cmd /k ".swingbot\Scripts\activate.bat"