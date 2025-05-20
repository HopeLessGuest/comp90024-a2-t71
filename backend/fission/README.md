## Team 71 Jiejun Xie 1418316 Anqi Liao 1578312 Xinhe Liu 1477404 Yifu Chen 1609437 Kexing Ma 1697372

## Fission apply all the environments, packages, functions httptriggers and timers

Due to our groups have multiple fission function and they are deployed in different way. So make sure in the following procedure.

### From a clean cluster(which means there are no python39 environment inside yet):

  Run the following commands in order:
  1. Under fission directory, run 
      ```
      fission spec apply --wait
      ```
     to set all packages, function of traffic and Australian election

  2. Run 
      ```
      cd youtube
      ```
  3. Run  
      ```
      fission spec apply --wait
      ```
     under this directory to set all youtube relatd service active.
  4. Run 
      ```
      cd ..
      ```

  5. Run
      ```
      cd inflation 
      ```
  6. Run
      ```
      cd inflation_api
      ```

  7. Run
      ```
      fission spec apply --wait
      ``` 
     under this route to get all inflation ReST API.

  8. Run
      ```
      cd ..
      ```

  9. Run
        ```
        cd inflation_harvester
        ```
    
  10. Run
      ```
      fission spec apply --wait
      ```
     under this route to get all inflation harvesters


### If the cluster is not clean(which means there are already python39 environment inside)
  Run the following  commands in order:
  1. Under fission directory, run  
        ```
        fission spec apply --wait --force
        ```
  
     to set all environment, packages, function of traffic and Australian election(Cuz now there is already an python39 environment exist, but in our deployment file, we have the env deploment)

  2. Run 
        ```
        cd youtube
        ```

  3. Run 
        ```
        fission spec apply --wait
        ```
     under this directory to set all youtube related service active.

  4. Run 
        ```
        cd ..
        ```

  5. Run
      ```
      cd inflation 
      ```
  6. Run
      ```
      cd inflation_api
      ```

  7. Run
      ```
      fission spec apply --wait
      ``` 
     under this route to get all inflation ReST API.

  8. Run
      ```
      cd ..
      ```
  9. Run
        ```
        cd inflation_harvester
        ```
    
  10. Run
      ```
      fission spec apply --wait
      ```
     under this route to get all inflation harvesters