# kibana-search-project

## Pre-Reqs
- Docker installed
- Cloud Cluster w/ sufficient ML capacity

## Steps
1. Download the bbc news csv from: https://www.kaggle.com/datasets/gpreda/bbc-news

Unzip the file. The Logstash configuration assumes a particcular data structure, so minor tweaks need to be made to the structure of the file. 

Run the bbc-news.py script, modifying the input / output to reflect the location / name of the saved file.

2. Install the ML model. This tutorial installs using docker, however the guide here presents alternative methods of installation: https://www.elastic.co/blog/introduction-to-custom-machine-learning-models-and-maps
Ensure Docker Desktop is up and running and run the following command:
```
docker run -it --rm docker.elastic.co/eland/eland:latest \
    eland_import_hub_model \
      --cloud-id "{{CLOUD_ID}}" \
      -u {{USERNAME}} -p {{PASSWORD}} \
      --hub-model-id "elastic/distilbert-base-uncased-finetuned-conll03-english" \
      --task-type ner \
      --start
```

This will uplod the custom NER model to your cluster and start it. 

3. Download the latest ELSER model by navigating to: Machine Learning -> Model Management -> Trained Models in your Cloud Cluster. 

4. Add the ingest pipeline using the config in ingest-pipeline.txt. The pipeline uses the following processors to modify the incoming data:
- removes unneccessary fields
- adds inference processors

5. Download Logstash (if not already downloaded) and add the configuration file: bbc-news.conf.
You can either run logstash directly from the command line using the '-f' flag to specify the configuration location, or use the pipelines file to point to the config.

If opting for the latter, add the following lines to your pipelines.yml file:

```
- pipeline.id: bbc-news
  path.config: "path-to-config"
```

6. In Dev Tools, create the new index with mappings, using the index-mappings.txt file. 

7. Run Logstsh and wait for data to ship to cluster. Due to the inclusion of inference procesors in the ingest pipeline, this may take a little time. Ensure the conunt of documents in your csv matches the count in the index, by running GET bbc-news-elser/_count

8. Install Streamlit locally / in your virtual environment. Documentation on running streamlit applications can be found here: https://streamlit.io/

9. Run the following to start the application:

```
streamlit run elasticapp.py 
```

