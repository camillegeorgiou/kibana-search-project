import streamlit as st
from elasticsearch import Elasticsearch
import os
from datetime import datetime

cloud_id = os.getenv("CLOUD_ID")
username = os.getenv("USER")
password = os.getenv("PASSWORD")

es = Elasticsearch(
    cloud_id=cloud_id,
    basic_auth=(username, password),
)

def main():
    st.title("Elasticsearch News App")

    selected_index = st.sidebar.selectbox("Elasticsearch Index", ["bbc-news-elser"], key="selected_index")

    if 'selected_tags' not in st.session_state:
        st.session_state['selected_tags'] = {"LOC": set(), "PER": set(), "MISC": set()}

    if 'search_results' not in st.session_state:
        st.session_state['search_results'] = fetch_recent_data(selected_index, size=20)

    semantic_query = st.text_input("Semantic Query:", key="semantic_query")
    regular_query = st.text_input("Standard Query:", key="regular_query")
    
    min_date, max_date = get_date_range(selected_index)
    start_date = st.date_input("Start Date", min_date, key="start_date")
    end_date = st.date_input("End Date", max_date, key="end_date")

    if st.button("Search"):
        st.session_state['search_results'] = fetch_data(selected_index, semantic_query, regular_query, start_date, end_date)
        st.session_state['selected_tags'] = {tag_type: set() for tag_type in ["LOC", "PER", "MISC"]}  # Reset filters on new search

    for tag_type in ["LOC", "PER", "MISC"]:
        current_tags = get_unique_tags(tag_type, st.session_state['search_results'])
        st.session_state['selected_tags'][tag_type] = st.sidebar.multiselect(f"Filter by {tag_type}", current_tags, key=f"filter_{tag_type}")

    filtered_results = filter_results_by_tags(st.session_state['search_results'], st.session_state['selected_tags'])
    update_results(filtered_results)

def fetch_recent_data(index_name, size=100):
    try:
        query_body = {
            "size": size,
            "sort": [
                {"pubDate": {"order": "desc"}},  # Primary sort by date
            ]
        }
        response = es.search(index=index_name, body=query_body)
        return [hit['_source'] for hit in response['hits']['hits']]
    except Exception as e:
        st.error(f"Error fetching recent data from Elasticsearch: {e}")
        return []

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
def update_results(results):
    try:
        for result_item in results:
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

                        st.markdown(
                            f"<span style='background-color: {tag_color}; color: white; padding: 5px; margin: 2px; border-radius: 5px;'>{tag_type}: {tag_value}</span>",
                            unsafe_allow_html=True)

            st.write("---")

    except Exception as e:
        st.error(f"Error performing search in Elasticsearch: {e}")

# Fetch data from ES based on index + queries. Specify size - can be modified.
def fetch_data(index_name, semantic_query, regular_query, start_date=None, end_date=None, size=100):
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
                {"bool": {
                    "should": {
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
                        }
                    }
                }}
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
        data = [{'_id': hit['_id'], 'title': hit['_source'].get('title', ''),
                 'description': hit['_source'].get('description', ''),
                 'tags': hit['_source'].get('tags', {}), 'pubDate': hit['_source'].get('pubDate', ''),
                 'url': hit['_source'].get('url', '')} for hit in hits]
        return data
    except Exception as e:
        st.error(f"Error fetching data from Elasticsearch: {e}")
        return []

# Function to get unique tags of a specific type
def get_unique_tags(tag_type, results):
    unique_tags = set()
    for result_item in results:
        tags = result_item.get('tags', {}).get(tag_type, [])
        unique_tags.update(tags)
    return sorted(unique_tags)

# Function to filter results based on selected tags
def filter_results_by_tags(results, selected_tags):
    filtered_results = []
    for result_item in results:
        tags = result_item.get('tags', {})
        add_result = True
        for tag_type, selected_values in selected_tags.items():
            if selected_values:
                result_values = tags.get(tag_type, [])
                if not any(value in selected_values for value in result_values):
                    add_result = False
                    break
        if add_result:
            filtered_results.append(result_item)
    return filtered_results

if __name__ == "__main__":
    main()
