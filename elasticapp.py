import streamlit as st
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

cloud_id = os.getenv("CLOUD_ID")
username = os.getenv("USER")
password = os.getenv("PASSWORD")

es = Elasticsearch(
    cloud_id=cloud_id,
    http_auth=(username, password),
)

def main():
    st.title("Elasticsearch News App")

    # Adds search functionality for semantic search + a standard text search
    semantic_query = st.text_input("Semantic Query:")
    regular_query = st.text_input("Standard Query:")

    # Specifies indices
    selected_index = st.sidebar.selectbox("Elasticsearch Index", ["bbc-news-elser"])

    # Calculate the earliest and latest dates
    min_date, max_date = get_date_range(selected_index)

    # Specifies date range with default values
    start_date = st.date_input("Start Date", min_date)
    end_date = st.date_input("End Date", max_date)

    # Generates search button
    if st.button("Search"):
        update_results(selected_index, semantic_query, regular_query, start_date, end_date)

# Helper function to calculate the earliest and latest dates in the index
def get_date_range(index_name):
    max_date_aggregation = {
        "max_date": {
            "max": {
                "field": "pubDate"
            }
        }
    }

    min_date_aggregation = {
        "min_date": {
            "min": {
                "field": "pubDate"
            }
        }
    }

    max_date_result = es.search(index=index_name, body={"aggs": max_date_aggregation})
    min_date_result = es.search(index=index_name, body={"aggs": min_date_aggregation})

    max_date_bucket = max_date_result['aggregations']['max_date']
    min_date_bucket = min_date_result['aggregations']['min_date']

    max_date = max_date_bucket['value_as_string']
    min_date = min_date_bucket['value_as_string']

    if max_date:
        max_date = datetime.strptime(max_date, "%a, %d %b %Y %H:%M:%S GMT")
    else:
        max_date = datetime.today().date()

    if min_date:
        min_date = datetime.strptime(min_date, "%a, %d %b %Y %H:%M:%S GMT")
    else:
        min_date = datetime.today().date()

    return min_date, max_date

# Updates results based on search
def update_results(index, semantic_query, regular_query, start_date, end_date):
    try:
        # Retrieves data from specified index based on queries
        result = fetch_data(index, semantic_query, regular_query, start_date, end_date)

        # Present search results as snippets
        for result_item in result:
            # Display document titles as links
            title_with_link = f"[{result_item['title']}]({result_item['url']})"
            st.markdown(f"### {title_with_link}")

            st.write(result_item['description'])

            # Display timestamp with results
            timestamp = result_item.get('pubDate', '')
            if timestamp:
                st.write(f"Published: {timestamp}")

            # Adds tags for entities
            tags = result_item.get('tags', {})
            if tags:
                for tag_type, tag_values in tags.items():
                    for tag_value in tag_values:
                        # Define colors for extracted entity tags
                        tag_color = {
                            "LOC": "#3498db",  
                            "PER": "#2ecc71",  
                            "MISC": "#e74c3c"  
                        }.get(tag_type, "#555555")

                        st.markdown(f"<span style='background-color: {tag_color}; color: white; padding: 5px; margin: 2px; border-radius: 5px;'>{tag_type}: {tag_value}</span>", unsafe_allow_html=True)

            st.write("---")

    except Exception as e:
        st.error(f"Error performing search in Elasticsearch: {e}")

# Fetch data from ES based on index + queries. Specify size - can be modified.
def fetch_data(index_name, semantic_query, regular_query, start_date=None, end_date=None, size=10):
    try:
        query_body = {
            "size": size,
            "query": {
                "bool": {
                    "should": []
                }
            }
        }

        # Add semantic query if provided by the user
        if semantic_query:
            query_body["query"]["bool"]["should"].append(
                {"bool" : {
                    "should" : {
                    "text_expansion": {
                        "ml-elser-title.tokens": {
                            "model_text": semantic_query,
                            "model_id": ".elser_model_2",
                            "boost": 9
                        }
                    },
                
                   "text_expansion": {
                        "ml-elser-description.tokens": {
                            "model_text": semantic_query,
                            "model_id": ".elser_model_2",
                            "boost": 9
                        }
                    }}}}
        )

        # Add regular query if provided by the user
        if regular_query:
            query_body["query"]["bool"]["should"].append({
                "query_string": {
                    "query": regular_query,
                    "boost": 8
                }
            })

        # Add date range if provided
        if start_date or end_date:
            date_range_query = {
                "range": {
                    "pubDate": {}
                }
            }

            if start_date:
                date_range_query["range"]["pubDate"]["gte"] = start_date.strftime("%a, %d %b %Y %H:%M:%S GMT")

            if end_date:
                date_range_query["range"]["pubDate"]["lte"] = end_date.strftime("%a, %d %b %Y %H:%M:%S GMT")

            query_body["query"]["bool"]["must"] = date_range_query

        result = es.search(
            index=index_name,
            body=query_body
        )

        hits = result['hits']['hits']
        data = [{'_id': hit['_id'], 'title': hit['_source'].get('title', ''), 'description': hit['_source'].get('description', ''),
                 'tags': hit['_source'].get('tags', {}), 'pubDate': hit['_source'].get('pubDate', ''), 'url': hit['_source'].get('url', '')} for hit in hits]
        return data
    except Exception as e:
        st.error(f"Error fetching data from Elasticsearch: {e}")
        return []

if __name__ == "__main__":
    main()
