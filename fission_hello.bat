:: This batch script deletes and recreates the 'testhello' Fission function and its route.

:: Delete the existing function named 'testhello' if it exists
fission fn delete --name=testhellopkg

:: Delete the existing route named 'testhello' if it exists
fission route delete --name=testhellopkg-route

:: Create a new function 'testhello' using the source code in fission/

fission fn create --name testhellopkg --env python39 --src fission/ --entrypoint testhello.main

:: Create a new HTTP route 'testhellopkg-route' to expose the function
:: The function will be accessible at '/api/testhello' with the GET method
fission route create --name testhellopkg-route --function testhellopkg --url /api/testhello --method GET

pause