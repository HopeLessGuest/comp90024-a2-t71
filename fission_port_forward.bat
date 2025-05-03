set KUBECONFIG=C:\ALAN\Python\CCC\comp90024-a2-t71\.kube\config

kubectl get nodes

kubectl port-forward svc/router 9090:80 -n fission

cmd /k