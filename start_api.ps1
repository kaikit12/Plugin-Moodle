$apiPath = Join-Path $PSScriptRoot "exercise_suggestion_api"
Set-Location $apiPath
php -S localhost:8080 api_server.php
