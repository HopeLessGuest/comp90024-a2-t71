:: This batch script deletes and recreates the 'testyoutube' Fission function and its route.

:: Delete the existing function named 'testyoutube' if it exists
fission fn delete --name=testyoutube

:: Delete the existing route named 'testyoutube' if it exists
fission route delete --name=testyoutube-route

:: Create a new function 'testyoutube' using the source code in Youtube_API/
:: and attaches the secret 'youtube-api-key' --secret youtube-api-key
fission fn create --name testyoutube --env python39 --src ./Youtube_API --entrypoint youtube_harv.main

:: Create a new HTTP route 'testyoutube-route' to expose the function
:: The function will be accessible at '/api/testyoutube' with the GET method
fission route create --name testyoutube-route --function testyoutube --url /api/testyoutube --method GET

pause