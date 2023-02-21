set plugin_dir=%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins

robocopy %~dp0\..\plugin\qgistim %plugin_dir%\qgistim /E
