Set-Location -Path (Split-Path -Parent $MyInvocation.MyCommand.Path)
waitress-serve --listen=127.0.0.1:8000 --threads=4 --channel-timeout=300 core.wsgi:application
Start-Process "python" -ArgumentList "manage.py","run_huey" -NoNewWindow