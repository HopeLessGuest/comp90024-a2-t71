# Fission

## Pre-requirements

- OpenStack RC file and API password obtained and sourced in current shell (see [here](../installation/README.md#client-configuration))
- A Kubernetes cluster created on NeCTAR (see [here](../installation/README.md#elasticsearch))
- Connect to [Campus network](https://studentit.unimelb.edu.au/wifi-vpn#uniwireless) if on-campus or [UniMelb Student VPN](https://studentit.unimelb.edu.au/wifi-vpn#vpn) if off-campus
- Kubernetes cluster is accessible (see [here](../installation/README.md#accessing-the-kubernetes-cluster))
- ElasticSearch is installed (see [here](../installation/README.md#elasticsearch))
- Fission CLI is installed on the client (see [here](../installation/README.md#fission-client)). Do not download the fission client in this directory, use a different one to avoid clashes with the already-existing `fission` directory.
- Fission is installed on the cluster (see [here](../installation/README.md#fission))
- Docker >= 24.x installed on your laptop (optional, only if you want to build a custom Fission environment
- [DockerHub account](https://hub.docker.com/)  (optional, only if you want to build a custom Fission environment

> Note: the code used here is for didactic purposes only. It has no error handling, no testing, and is not production-ready.

## Basic Fission

### Create a Fission Function and Expose it as a Service

First, let's create the Python environment on the cluster with the Python builder (it allows to extend the base Python image),
and the Node.js environment and builder:

```shell
fission env create --name python --image fission/python-env --builder fission/python-builder
fission env create --name nodejs --image fission/node-env --builder fission/node-builder
```

Find the Kubernetes ElasticSearch service:

```shell
kubectl get svc -n elastic
```

The name of the service is `elasticsearch-master` and the port is `9200`; to this we have to add the
namespace and the suffix that the Kubernetes DNS uses to route services within the cluster.
`elasticsearch-master` becomes `elasticsearch-master.elastic.svc.cluster.local`.

The `health.py` source code checks the state of the ElasticSearch cluster and returns it:

Test the function:
```shell
fission function create --name health --env python --code ./fission/functions/health.py
fission function test --name health | jq '.'
```

Create a route so that the function can be accessed from outside the cluster:
```shell
fission route create --url /health --function health --name health --createingress
```
>Note: Fission ingresses are created under the `fission` namespace (`kubectl get ingress -n fission`)) 

Start a port forward from the Fission router in different shell:
```shell
kubectl port-forward service/router -n fission 9090:80
```

In a new terminal, invoke the function from port `9090` of your laptop:
```shell
curl "http://127.0.0.1:9090/health" | jq '.'
```
(You can have a look at the function log with `fission function log -f --name health`.)

### Create a Fission Function that harvests Data from the Bureau of Meteorology

```shell
fission function create --name wharvestersimple --env python --code ./fission/functions/wharvestersimple.py
fission function test --name wharvestersimple | jq '.'
```


### Call the function at interval using a timer trigger

```shell
fission timer create --name wharvester --function wharvestersimple --cron "@every 20s"
fission function log -f --name wharvestersimple
```
(Every 20 seconds a new log line should appear.)

Delete the timer:
```shell
fission timer delete --name wharvester
```

## Fission with advanced functions

### Create a function that uses additional Python libraries

#### Build an index to hold weather observations

In a new terminal, start a port forward from ElasticSearch:
```shell
kubectl port-forward service/elasticsearch-master -n elastic 9200:9200
```

Create the index:
```shell
curl -XPUT -k 'https://127.0.0.1:9200/observations' \
   --user 'elastic:elastic' \
   --header 'Content-Type: application/json' \
   --data '{
    "settings": {
        "index": {
            "number_of_shards": 3,
            "number_of_replicas": 1
        }
    },
    "mappings": {
        "properties": {
            "stationid": {
                "type": "keyword"
            },
            "timestamp": {
                "type": "date"
            },
            "geo": {
                "type": "geo_point"
            },
            "name": {
                "type": "text"
            },
            "air_temp": {
                "type": "float"
            },
            "rel_hum": {
                "type": "float"
            },
            "pm10": {
                "type": "float"
            },
            "pm2p5": {
                "type": "float"
            },
            "ozone": {
                "type": "float"
            }
        }
    }
}'  | jq '.'
```

#### Create a function that stores data in ElasticSearch

The function used so far are very simple and do not require any additional Python libraries: let's
see how we can pack libraries (such as the ElasticSearch Python client) together with a function source code.

In order to do so, a `requirements.txt` file must be created in the same directory as the function, then
a `build.sh` command must be created to install the libraries and finally the function must be packaged in a ZIP file.

```shell
(
  cd fission/functions/addobservations
  zip -r addobservations.zip .
  mv addobservations.zip ../
)
```
>Note: the ZIP file must be relative to the directory the function is in; otherwise the package build will fail. 
> To avoid this. always build the ZIP file from within the directory the function is in and then move it somewhere else  
> to avoid a recursive ZIP file (see the shell commands above).

Creation of a function with dependencies (this function depends on the ElasticSearch client package to add data to ElasticSearch):
```shell
fission package create --sourcearchive ./fission/functions/addobservations.zip\
  --env python\
  --name addobservations\
  --buildcmd './build.sh'
```
>Note: use `package update` to update a package that already exists.

Check that the package has been created:
```shell
fission package list
```

>Note: to check for errors during package creation, the `info` command can be used `fission package info --name <package name>`.

Function creation:
```shell
fission fn create --name addobservations\
  --pkg addobservations\
  --env python\
  --entrypoint "addobservations.main" # Function name and entrypoint
```

>Note: use `function update` to update a function that already exists.

## Use of YAML specifications to deploy functions

### Re-creation of functions with YAML specifications

Let's start by deleting functions, packages, triggers, and even the environments we have created so far:

```shell
fission httptrigger delete --name health
fission function delete --name addobservations
fission function delete --name health
fission function delete --name wharvestersimple
fission package delete --name addobservations
fission environment delete --name python
fission environment delete --name nodejs
```

Creation of a directory to hold our specifications (by default it is named `specs`):
```shell
(
  cd fission
  fission specs init
)  
```

From now on our actions will add YAML files under the `specs` directory (not the `spec` argument),
and the YAML files will then be applied to the cluster with the `kubectl apply` command.

Let's start by creating the specs for the Python and Node.js environments:
```shell
(
  cd fission
  fission env create --spec --name python --image fission/python-env --builder fission/python-builder
  fission env create --spec --name nodejs --image fission/node-env --builder fission/node-builder
)  
```

>Note: by default Fission uses Python 3.7, but if you plan to use Pandas 2.2.x you have to use Python 3.9, using the following command instead:
```shell
(
  cd fission
  fission env create --name python39 --builder fission/python-builder-3.9 --image fission/python-env-3.9
)  
```

Let's create the specification file for a function:
```shell
(
  cd fission
  fission function create --spec --name health --env python --code ./functions/health.py
)
```

A file named `function-health.yaml` will be created under the `specs` directory, but so far no actions
has been taken on the cluster.

Let's create the spec for a route to this function:
```shell
(
  cd fission
  fission route create --spec --url /health --function health --name health --createingress
)
```

Let's check everything is fine with our specs:
```shell
(
  cd fission
  fission spec validate
)
```

Provided no errors are reported, we can now apply the specs to the cluster:
```shell
fission spec apply --specdir fission/specs --wait
```

Let's test the `health` function and related route:
```shell
curl "http://127.0.0.1:9090/health" | jq '.'
```

### Passing of parameters to functions with config maps

Parameters (such as username and passwords) can be passed to functions through the environment
rather than be hard-coded in the source code (which has to be avoided, especially for sensitive information).

A common to share parameters in Kubernetes is through `configmaps`, which are key-value pairs that can be
accessed by all pods within a namespace.
Fission functions can read configmaps as files, so we can create a configmap with the ElasticSearch username and password.

Let's start by creating a configmap as `shared-data.yaml` file under `specs`:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  namespace: default
  name: shared-data
data:
  ES_USERNAME: elastic
  ES_PASSWORD: elastic
```

Since config maps are not directly managed by Fission, we have to apply it to the cluster with `kubectl`:
```shell
kubectl apply -f ./fission/specs/shared-data.yaml
```

>Note: To avoid warning messages when managing specs, add a line with `shared-data.yaml` to a new file called `fission/specs/.specignore`.

To use the values om the config map we have to change the function to make it use the ConfigMap, hence we create a `healthcm.py` file 
to read the config map.
In addition, we have to create the function definition so that the config map is mounted as volume `/configs/default/shared-data`.
(we have to create a route to the `healthcm` function as well):
```shell
(
  cd fission
  fission httptrigger delete --name health
  fission function create --spec --name healthcm --env python --code ./functions/healthcm.py --configmap shared-data
  fission route create --spec --url /healthcm --function healthcm --name healthcm --createingress
)
```

To apply the changes we have to run the following command:
```shell
fission spec apply --specdir fission/specs --wait
```

We can now test the function (after waiting for all the pods to have been updated) to see if the environment variables
have been passed correctly:

Let's open a log window in another shell:
```shell
fission fn log -f --name healthcm
```

And try out the changed function
```shell
curl "http://127.0.0.1:9090/healthcm"  | jq '.'
```

When ConfigMaps are changed, the specs have to be re-applied.

Fission can read secrets as well, which are better suited to hold sensitive information (such as passwords).

### Creation of a RestFUL API with YAML specifications

Fission HTTPTrigger can be used to create a ReSTful API that allows a further decoupling between the function and the
way it is invoked.

For instance, let's suppose we want to query ElasticSearch for the average temperature on a given day for one station or
for all stations.

A ReSTful API may look like:
```
/temperature/{date}
/temperature/{date}/{station}
```

#### Function creation

Let's create the function (`avgtemp.py`) and related package specs:
```shell
(
  cd fission
  
  fission package create --spec --name avgtemp \
    --source ./functions/avgtemp/__init__.py \
    --source ./functions/avgtemp/avgtemp.py \
    --source ./functions/avgtemp/requirements.txt \
    --source ./functions/avgtemp/build.sh \
    --env python \
    --buildcmd './build.sh'
    
  fission fn create --spec --name avgtemp \
    --pkg avgtemp \
    --env python \
    --entrypoint "avgtemp.main"
)
```
>Note: avoiding the use of `*.zip` files in packages makes it easier to update functions, but it may not be always possible
>Note: from the point of view of the function, the path parameters `date` and `station` are headers prefixed by `X-Fission-Params`.)

#### Route creation

We start by using the fission commands to create the YAML files defining the routes/HTTPTriggers:
```shell
(
  cd fission
  fission route create --spec --name avgtempday --function avgtemp \
    --method GET \
    --url '/temperature/days/{date:[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]}'
  fission route create --spec --name avgtempdaystation --function avgtemp \
    --method GET \
    --url '/temperature/days/{date:[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]}/stations/{station:[a-zA-Z0-9]+}'
)
```

Let's apply the specs to the cluster:
```shell
fission spec apply --specdir fission/specs --wait
```


## Customisation of a Fission environment

A Fission env can be customised to avoid building packages with the same dependencies over and over again.
The way of doing it is by creating a custom Docker image from the base Fission image and add the dependencies that
are needed.


### Use af a custom Fission environment

On DockerHub there is already an image named `lmorandini/python39x` that has the ElasticSearch Python client, SciPy, and NumPy
in it, which should satisfy most of the requirements needed for Assignment 2. This image can be used as it is 
by following these steps.

Create a Fission env from the custom image:
```shell
fission env create --name python39x --image lmorandini/python39x:1.0.0 --builder fission/python-builder-3.9
```

Create a Fission function that prints the version of ElasticSearch, NumPy, and Scipy:
```shell
fission function create --name python39x --env python39x --code ./fission/functions/python39x.py
```

Test it:
```shell
fission function test --name python39x
```


### Building af a custom Fission environment

If something more specific is needed, a custom Fission environment as to be built.
First a Dockerfile that extends the base Fission image has to be created, for this Docker must be installed 
on your laptop and you need a DockerHub account (see requirements at the beginning of this README).

The files for the `lmorandini/python49x` Fission env image can be found in the `fission/python39x` directory.

After changing the files to suit your needs, build the docker image. 
USER has to be the name of your account on DockerHub, and VERSION has to be changed every time the image is updated and pushed on DockerHub,
you can also change the image name:
```shell
(
  cd fission/python39x
  USER='lmorandini'
  VERSION='1.0.0'
  docker build --network host --tag ${USER}/python39x:${VERSION} --build-arg PY_BASE_IMG=3.9-alpine .
  docker push ${USER}/python39x:${VERSION}
)
``` 
>Note: To push the image once the build is successful (you have to be logged in to DockerHub)

Once the image is created on DockerHub, the environment can be created as specified in the paragraph above.


## Development of an Event-driven architecture with Fission

>Note:: This is not needed for Assignment 2, it is provided for didactic purposes only.

### Installation of Keda

Keda is a workload autoscaler for Kubernetes (it creates/removes pods depending on events). 
```shell
export KEDA_VERSION='2.9'
helm repo add kedacore https://kedacore.github.io/charts
helm repo add ot-helm https://ot-container-kit.github.io/helm-charts/
helm repo update
helm upgrade keda kedacore/keda --install --namespace keda --create-namespace --version ${KEDA_VERSION}
```

### Installation of Redis

Redis is a key-value store used to store messages for Fission.
```shell
export REDIS_VERSION='0.19.1'
helm repo add ot-helm https://ot-container-kit.github.io/helm-charts/
helm upgrade redis-operator ot-helm/redis-operator \
    --install --namespace redis --create-namespace --version ${REDIS_VERSION}
    
kubectl create secret generic redis-secret --from-literal=password=password -n redis
helm upgrade redis ot-helm/redis --install --namespace redis   
```

>Note: the password is 'password' for both Redis, which is bad practice and used here only for didactic purposes.
 
Wait for all pods to have started:

```shell
kubectl get pods -n keda --watch
```
```shell
kubectl get pods -n redis --watch
```

### Redis-insight installation and setup

Redis-insight is a GUI for Redis. Redis-insight must be installed with a deployment since it ha no associated Helm chart.
```shell
kubectl apply -f ./fission/redisinsight.yaml --namespace redis
```

Wait for all pods to have started:
```shell
kubectl get pods -n redis --watch
```

To interact with the Redis-insight UI:
* start a port-forward: `kubectl port-forward service/redis-insight --namespace redis 5540:5540`
* Open a browser and go to: `http://localhost:5540/`
* Check the "I have read and understood the Terms" and click on "Submit"
* Click on "Add a redis database" and use this URL as connection string: `redis://redis-headless.redis.svc.cluster.local:6379` 
* Click on the database name
* Set auto-refresh

### Application development

Functions can be composed for added flexibility and reuse (message queues are used to bind them together).

Let's create a mini-application that:
- harvests meteorological data from the Bureau of Meteorology;
- harvests pollution from the NSW Air Quality API; 
- stores the data in ElasticSearch.

Since AQ and BoM data have different structures, we need to have an intermediate function that filters and splits the data
into a standardized structure that can be added to ElasticSearch.

#### Functions

We would reuse the `addobservations` functions we introduced earlier, but have also to add:
- an `aharvester` function to get data from the Air Quality project;
- a `wharvester` function to get data from the BoM;
- a `Wprocessor` function to filter, convert, and split the BoM data into a simpler structure;
- an `aprocessor` function to filter, convert, and split the AIRQ data into a simpler structure;
- an `enqueue` function to add data to a queue (Redis list).

```shell
(
  cd fission
  fission function create --name aharvester --spec --env python --code ./functions/aharvester.py
  fission function create --name wharvester --spec --env python --code ./functions/wharvester.py
  fission function create --name wprocessor --spec --env nodejs --code ./functions/wprocessor.js
  fission function create --name aprocessor --spec --env nodejs --code ./functions/aprocessor.js
)  

(
  cd fission
  
  fission package create --spec --name enqueue \
    --source ./functions/enqueue/__init__.py \
    --source ./functions/enqueue/enqueue.py \
    --source ./functions/enqueue/requirements.txt \
    --source ./functions/enqueue/build.sh \
    --env python \
    --buildcmd './build.sh'

  fission function create --spec --name enqueue \
    --pkg enqueue \
    --env python \
    --entrypoint "enqueue.main"
)
  
(
  cd fission/functions/addobservations
  zip -r addobservations.zip .
  mv addobservations.zip ../
)

(
  cd fission
  fission package create --sourcearchive ./functions/addobservations.zip\
    --spec\
    --env python\
    --name addobservations\
    --buildcmd './build.sh'
    
  fission fn create --name addobservations\
    --spec\
    --pkg addobservations\
    --env python\
    --entrypoint "addobservations.main" # Function name and entrypoint  
)
```

Apply the specification to the cluster:
```shell
fission spec apply --specdir fission/specs --wait
```

>Note: these functions communicate amongst them by storing and reading messages in queues. In Redis queues are implemented as lists.

#### Triggers

To bind all these functions and queues together, we have now to create triggers:
- a `weather-ingest` timer trigger to capture BoM data;
- an `airquality-ingest` timer trigger to capture pollution data;
- an `enqueue` HTTP trigger to add data to a message queue;
- a `weather-processing` queue trigger to process meteorological data from a message queue;
- an `airquality-processing` queue trigger to process pollution data from a message queue;
- an `add-observations` queue trigger to add observations to ElasticSearch.

```shell
(
  cd fission
  fission timer create --spec --name weather-ingest --function wharvester --cron "@every 20s"
  fission timer create --spec --name airquality-ingest --function aharvester --cron "@every 20s"

  fission httptrigger create --spec --name enqueue --url "/enqueue/{topic}" --method POST --function enqueue

  fission mqtrigger create --name weather-processing \
    --spec\
    --function wprocessor \
    --mqtype redis\
    --mqtkind keda\
    --topic weather \
    --resptopic observations \
    --errortopic errors \
    --maxretries 3 \
    --metadata address=redis-headless.redis.svc.cluster.local:6379\
    --metadata listLength=100\
    --metadata listName=weather

  fission mqtrigger create --name airquality-processing \
    --spec\
    --function aprocessor \
    --mqtype redis \
    --mqtkind keda \
    --topic airquality \
    --resptopic observations \
    --errortopic errors \
    --maxretries 3 \
    --metadata address=redis-headless.redis.svc.cluster.local:6379\
    --metadata listLength=100\
    --metadata listName=airquality

  fission mqtrigger create --name add-observations \
    --spec\
    --function addobservations \
    --mqtype redis \
    --mqtkind keda \
    --topic observations \
    --errortopic errors \
    --maxretries 3 \
    --metadata address=redis-headless.redis.svc.cluster.local:6379\
    --metadata listLength=100\
    --metadata listName=observations
)   
```
>Note: list name is the same as the topic name.

Apply the specs:
```shell
fission spec apply --specdir fission/specs --wait
```

>Note: for `spec apply` to pick up changes to function that use packages the zipfile has to be updated first.

From the logs you should now be able to see the data flowing from the harvesters to the processors and finally to ElasticSearch

After a while enough data would be harvested to be able to query ElasticSearch.

>Note: depending on how we define the document ID in the `addobservations` function, the same document may be added multiple times 
> (if we were to omit the document Id a new one will be generated automatically by ElasticSearch).

#### Create a data view from Kibana

In a different shell, start a port forward from Kibana:
```shell
kubectl port-forward service/kibana-kibana -n elastic 5601:5601
```

Open Kibana in your browser, create a data view named "observations" with pattern "observation*" and timestamp field "timestamp", and check that the documents have been
added to the index by going to "Analysis / Discover".

Now Kibana can be used to test search queries or to have a look at the data.

#### ReSTful API test

These requests return the same results because there is only one station in the data:
```shell
DAY=$(date -d '-1 day' +"%Y-%m-%d")
curl "http://localhost:9090/temperature/days/${DAY}" | jq '.'
curl "http://localhost:9090/temperature/days/${DAY}/stations/95936" | jq '.'
```
>Note: the port forwarding from the Fission router must be running.


## Harvesting requests

### Harvest Data from the Bureau of Meteorology

List of stations:
http://reg.bom.gov.au/vic/observations/melbourne.shtml

Single station observations:
http://reg.bom.gov.au/fwo/IDV60901/IDV60901.95936.json


### Harvest Data from the NSW EPA

NSW Air Quality API:
https://data.airquality.nsw.gov.au/docs/index.html


### Mastodon harvester

This is just a basic example of a Mastodon harvester. It is not meant to be used in production.

The function takes the last status from the Mastodon server, wait for a few seconds, then harvests the
statuses that have been posted in the meantime.

A possible design for a Mastodon harvester could use a timer trigger to call the function at regular intervals and store the
statuses in ElasticSearch, with the `lastid` variable value taken from an ElasticSearch query looking for the latest status.

Even better, the Mastodon harvester could use a WebSocket to communicate with Mastodon in streaming mode and have the function
executed whenever there are new posts.

Create the archive, the package, and the function:
```shell
(
  cd fission

  fission package create --spec --name mharvester \
    --source ./functions/mharvester/__init__.py \
    --source ./functions/mharvester/mharvester.py \
    --source ./functions/mharvester/requirements.txt \
    --source ./functions/mharvester/build.sh \
    --env python \
    --buildcmd './build.sh'

  fission fn create --name mharvester \
    --spec\
    --pkg mharvester \
    --env python \
    --entrypoint "mharvester.main"
)

fission spec apply --specdir fission/specs --wait
```

Test the harvester:
```shell
(
  cd fission;
  fission timer create --spec --name mastodon-ingest --function mharvester --cron "@every 20s"
)
  
fission spec apply --specdir fission/specs --wait
fission fn logs -f --name mharvester 
```

To look at the harvested posts (they are returned by the function upon invocation):
```shell
fission fn test --name mharvester | jq '.'
```

## Uninstallation of the event-driven infrastructure (if previously installed)

### Application uninstallation

Delete the resources defined in the specs directory
```shell
fission spec destroy --specdir fission/specs
```

Delete environments (some may be)
```shell
fission  fn delete --name python39x
fission environment delete --name python39
fission environment delete --name python39x
```

Remove the specs deployment file and all the other files from the specs directory except `.specignore` and the ConfigMap (if you want to keep the ConfigMap, obviously):
```shell
rm fission/specs/README
rm fission/specs/fission-deployment-config.yaml
rm fission/specs/env*.yaml
rm fission/specs/function*.yaml
rm fission/specs/mqtrigger*.yaml
rm fission/specs/package*.yaml
rm fission/specs/route*.yaml
rm fission/specs/timetrigger*.yaml
```

### Redis uninstallation

```shell
kubectl delete deployment redis-insight --namespace redis
helm uninstall redis --namespace redis
helm uninstall redis-operator --namespace redis
```

### Keda uninstallation

```shell
helm uninstall keda --namespace keda
```

### Delete the ElasticSearch index

```shell
curl -XDELETE -k 'https://127.0.0.1:9200/observations' \
   --user 'elastic:elastic' 
```

