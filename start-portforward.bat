@echo off
echo Starting port-forwarding for Elasticsearch, Kibana, and Fission...

REM Kibana 5601
start "Kibana5601" cmd /k "echo Forwarding Kibana to http://localhost:5601 && kubectl port-forward svc/kibana-kibana -n elastic 5601:5601"

REM Elasticsearch 9200
start "Elasticsearch9200" cmd /k "echo Forwarding Elasticsearch to https://localhost:9200 && kubectl port-forward svc/elasticsearch-master -n elastic 9200:9200"

REM Fission Router 9090
start "Fission9090" cmd /k "echo Forwarding Fission Router to http://localhost:9090 && kubectl port-forward svc/router -n fission 9090:80"

