"""
Provides support for searching posts with ElasticSearch
"""

from flask import current_app


def add_to_index(index, model):
    """
    Adds entries to a full-text index
    ---------------------------------
    Parameters:
    index - an index in ElasticSearch
    model - SQLAlchamy model
    """
    if not current_app.elasticsearch:
        return
    payload = {}
    for field in model.__searchable__:
        payload[field] = getattr(model, field)
    current_app.elasticsearch.index(index=index, id=model.id, body=payload)


def remove_from_index(index, model):
    """
    Removes entries from the index
    ------------------------------
    Parameters:
    index - an index in ElasticSearch
    model - SQLAlchamy model
    """
    if not current_app.elasticsearch:
        return
    current_app.elasticsearch.delete(index=index, id=model.id)


def query_index(index, query, page, per_page):
    """
    Search the index for a given string.
    ------------------------------------
    Parameters:
    index - an index in ElasticSearch
    query - the text string to search for
    page - the current page
    per_page - the number of results to include per page
    ------------------------------------
    Returns:
    The search results within the pagination limits, this is
    a tuple (list of ids, number of search hits).
    """
    if not current_app.elasticsearch:
        return [], 0
    search = current_app.elasticsearch.search(
        index=index,
        body={'query':{'multi_match':{'query': query, 'fields':['*']}},
              'from': (page - 1) * per_page, 'size': per_page})
    ids = [int(hit['_id']) for hit in search['hits']['hits']]
    return ids, search['hits']['total']['value']