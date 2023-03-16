
rem powershell equivalent to https://github.com/lutraconsulting/qgis-crayfish-plugin/blob/master/package.bash

%systemroot%\System32\WindowsPowerShell\v1.0\powershell.exe -command "cd ..; rm -r -fo plugin/qgistim.zip; cd plugin/qgistim; git archive --prefix=qgistim/ -o ../qgistim.zip HEAD"

pause