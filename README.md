# Linked events

[![Build status](https://travis-ci.org/City-of-Helsinki/linkedevents.svg)](https://travis-ci.org/City-of-Helsinki/linkedevents)
[![Requirements](https://requires.io/github/City-of-Helsinki/linkedevents/requirements.svg?branch=master)](https://requires.io/github/City-of-Helsinki/linkedevents/requirements/?branch=master)
[![Stories in Ready](https://badge.waffle.io/City-of-Helsinki/linkedevents.svg?label=ready&title=Ready)](http://waffle.io/City-of-Helsinki/linkedevents)

Linked Events provides categorized data on events and places. The project was originally developed for the City of Helsinki.

[The Linked Events API for the Helsinki capital region](http://api.hel.fi/linkedevents/) contains data from the Helsinki City Tourist & Convention Bureau, the City of Helsinki Cultural Office and the Helmet metropolitan area public libraries.


Installation for development
----------------------------
These instructions assume an $INSTALL_BASE, like so:
```bash
INSTALL_BASE=$HOME/linkedevents
```
If you've already cloned this repository, just move repository root into $INSTALL_BASE/linkedevents. Otherwise just clone the repository, like so:
```bash
git clone https://github.com/City-of-Helsinki/linkedevents.git $INSTALL_BASE/linkedevents
```
Prepare Python 3.x virtualenv using your favorite tools and activate it. Plain virtualenv is like so:
```bash
virtualenv -p python3 $INSTALL_BASE/venv
source $INSTALL_BASE/venv/bin/activate
```
Install required Python packages into the virtualenv
```bash
cd $INSTALL_BASE/linkedevents
pip install -r requirements.txt
```
Create the database, like so: (we have only tested on PostgreSQL)
```bash
cd $INSTALL_BASE/linkedevents
sudo -u postgres createuser -R -S linkedevents
# Following is for US locale, we are not certain whether Linkedevents
# behaves differently depending on DB collation & ctype
#sudo -u postgres createdb -Olinkedevents linkedevents
# This is is for Finnish locale
sudo -u postgres createdb -Olinkedevents -Ttemplate0 -lfi_FI.UTF-8 linkedevents
# Create extensions in the database
sudo -u postgres psql linkedevents -c "CREATE EXTENSION postgis;"
sudo -u postgres psql linkedevents -c "CREATE EXTENSION hstore;"
# This fills the database with a basic skeleton
python manage.py migrate
```
You probably want to import some data for testing (these are events around Helsinki), like so:
```bash
cd $INSTALL_BASE/linkedevents
# Import places from Helsinki service registry (used by events from following sources)
python manage.py event_import tprek --places
# Import events from Visit Helsinki
python manage.py event_import matko --events
# Import events from Helsinki metropolitan region libraries
python manage.py event_import helmet --events
```
Furthermore, you may install city-specific HTML page templates for the browsable API by
```bash
cd $INSTALL_BASE/linkedevents
python manage.py install_templates helevents
```
This will install the `helevents/templates/rest_framework/api.html` template,
which contains Helsinki event data summary and license. Customize the template
for your favorite city by creating `your_favorite_city/templates/rest_framework/api.html`.
For further erudition, take a look at the DRF documentation on [customizing the browsable API](http://www.django-rest-framework.org/topics/browsable-api/#customizing)

After this, everything but search endpoint (/search) is working. See [search](#search)

Running tests
------------
Tests must be run using an user who can create (and drop) databases and write the directories
your linkedevents installation resides in.
```bash
py.test events
```

Requirements
------------

Linked Events uses two files for requirements. The workflow is as follows.

`requirements.txt` is not edited manually, but is generated
with `pip-compile`.

`requirements.txt` always contains fully tested, pinned versions
of the requirements. `requirements.in` contains the primary, unpinned
requirements of the project without their dependencies.

In production, deployments should always use `requirements.txt`
and the versions pinned therein. In development, new virtualenvs
and development environments should also be initialised using
`requirements.txt`. `pip-sync` will synchronize the active
virtualenv to match exactly the packages in `requirements.txt`.

In development and testing, to update to the latest versions
of requirements, use the command `pip-compile`. You can
use [requires.io](https://requires.io) to monitor the
pinned versions for updates.

To remove a dependency, remove it from `requirements.in`,
run `pip-compile` and then `pip-sync`. If everything works
as expected, commit the changes.

Search
------
Linkedevents uses Elasticsearch for generating results on the /search-endpoint. If you wish to use that functionality, proceed like so:

1. Install elasticsearch

    We've only tested using the rather ancient 1.7 version. Version 5.x will certainly not work as the `django-haystack`-library does not support it.

2. (For finnish support) Install elasticsearch-analyzer-voikko, libvoikko and needed dictionaries

    `/usr/share/elasticsearch/bin/plugin -i fi.evident.elasticsearch/elasticsearch-analysis-voikko/0.3.0`
    This specific command is for Debian derivatives. The path to `plugin` command might be different on yours.

    Installing libvoikko:
    `apt-get install libvoikko`

    Installing the dictionaries:

    ```bash
    wget -P $INSTALL_BASE http://www.puimula.org/htp/testing/voikko-snapshot/dict-morpho.zip
    unzip $INSTALL_BASE/dict-morpho.zip -d /etc/voikko
    ```

3. Configure the thing

    Add the block below these instructions to $INSTALL_BASE/linkedevents/local_settings.py:
    
4. Rebuild the search indexes

   `python manage.py rebuild_index`
  
   You should now have a working /search endpoint, give or take a few.

```python
CUSTOM_MAPPINGS = {
    'autosuggest': {
        'search_analyzer': 'standard',
        'index_analyzer': 'edgengram_analyzer',
        'analyzer': None
    },
    'text': {
        'analyzer': 'default'
    }
}

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'multilingual_haystack.backends.MultilingualSearchEngine',
    },
    'default-fi': {
        'ENGINE': 'multilingual_haystack.backends.LanguageSearchEngine',
        'BASE_ENGINE': 'events.custom_elasticsearch_search_backend.CustomEsSearchEngine',
        'URL': 'http://localhost:9200/',
        'INDEX_NAME': 'linkedevents-fi',
        'MAPPINGS': CUSTOM_MAPPINGS,
        'SETTINGS': {
            "analysis": {
                "analyzer": {
                    "default": {
                        "tokenizer": "finnish",
                        "filter": ["lowercase", "voikko_filter"]
                    }
                },
                "filter": {
                    "voikko_filter": {
                        "type": "voikko",
                    }
                }
            }
        }
    },
    'default-sv': {
        'ENGINE': 'multilingual_haystack.backends.LanguageSearchEngine',
        'BASE_ENGINE': 'events.custom_elasticsearch_search_backend.CustomEsSearchEngine',
        'URL': 'http://localhost:9200/',
        'INDEX_NAME': 'linkedevents-sv',
        'MAPPINGS': CUSTOM_MAPPINGS
    },
    'default-en': {
        'ENGINE': 'multilingual_haystack.backends.LanguageSearchEngine',
        'BASE_ENGINE': 'events.custom_elasticsearch_search_backend.CustomEsSearchEngine',
        'URL': 'http://localhost:9200/',
        'INDEX_NAME': 'linkedevents-en',
        'MAPPINGS': CUSTOM_MAPPINGS
    },
}
```
