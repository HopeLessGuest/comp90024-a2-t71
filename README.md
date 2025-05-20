# COMP90024-A2-T71

## Team 71 Jiejun Xie 1418316 Anqi Liao 1578312 Xinhe Liu 1477404 Yifu Chen 1609437 Kexing Ma 1697372

## Prerequisite

```
Installed kubernetes cluster, fission, elasticsearch, redis
have .config file of the cluster
```

## Backend deployment

```
Follow the instructions in /backend/fisson/README.md to deploy our fission environment, packages, functions, httptrigger, timer
```

## Frontend

```
We use Jupyter Notebook as our frontend, to run it locally, you need to do port-forward first
    """
    kubectl port-forward service/router -n fission 9090:80
    """

    """
    kubectl port-forward service/elasticsearch-master -n elastic 9200:9200
    """

Then under /frontend directory
run
"""
    pip install -r requirements.txt
"""

The you can run the jupyer notebooks.

We have several jupyter notebooks include traffic_dashboard.ipynb, Youtube_Election.ipynb, Youtube_Life_Display.ipynb, mastodon_144g_sentiment_crime_house.ipynb, Inflation_and_House.ipynb, Hot_Word_Analysis.ipynb.
```

## Unit test

```
Make sure you have do port forward in the terminal.
    """
    kubectl port-forward service/router -n fission 9090:80
    """

    """
    kubectl port-forward service/elasticsearch-master -n elastic 9200:9200
    """

Make sure you are under /test directory
Then run
“”“
    pip install -r requirements.txt
    python test_route_api.py
”“”
```

## database

```
We use  a jupyter notebook to see the mapping of our indices in our Elasticsearch

run
"""
    pip install -r requirements.txt
"""

Then you can open the indices_mapping_dashboard.ipynb to see the indices mapping in our Elasticsearch.
```