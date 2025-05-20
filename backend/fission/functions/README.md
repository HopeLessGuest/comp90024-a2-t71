###Team 71
###Jiejun Xie 1418316
###Anqi Liao 1578312
###Xinhe Liu 1477404
###Yifu Chen 1609437
###Kexing Ma 1697372

The function folder include part of our fission function include the harvesters and ReST API.

- api folder includes the Part of the ReST API: 
    trafficvolumeapi, trafficaggbyhour, traffic injury, offender, musicapi, victim api, home_transfer api, mastodon keyword sentment API, keywordmastodon API. 
    Detail usage and calling way of these API please refer to the README inside api folder.

- testharvester folder includes:
    VICroads harvester(harvest real time traffic volume data) every 2h
    music harvester(harvest real time music situation) every 2h

- redinit folder includes:
    Reddit harvester in keywords about Australian election  every 10 minutes.

- auselectionapi folder include :
    Definition of ReST API get the data about Reddit post about Australian election

four pkgs in the function folder to be used in the deployment in fission

- pipkg.pkg is the zip file including __init__.py, build.sh, requirements.txt, and all function python files to be used in the deployment.
- testharvester.pkg is the zip file including __init__.py, build.sh, requirements.txt, and all function python files to be used in the deployment.
- redinit.pkg is the zip file including __init__.py, build.sh, requirements.txt, and all function python files to be used in the deployment.
- auselectionapi.pkg is the zip file including __init__.py, build.sh, requirements.txt, and all function python files to be used in the deployment.

