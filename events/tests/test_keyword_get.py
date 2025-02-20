# -*- coding: utf-8 -*-
import pytest

from events.models import Keyword

from .utils import get
from .utils import versioned_reverse as reverse


def get_list(api_client, version="v1", data=None):
    list_url = reverse("keyword-list", version=version)
    return get(api_client, list_url, data=data)


def get_detail(api_client, detail_pk, version="v1", data=None):
    detail_url = reverse("keyword-detail", version=version, kwargs={"pk": detail_pk})
    return get(api_client, detail_url, data=data)


@pytest.mark.django_db
def test_get_keyword_detail(api_client, keyword):
    response = get_detail(api_client, keyword.pk)
    assert response.data["id"] == keyword.id


@pytest.mark.django_db
def test_get_keyword_detail_check_redirect(api_client, keyword, keyword2):
    keyword.replaced_by = keyword2
    keyword.deprecated = True
    keyword.save()
    url = reverse("keyword-detail", version="v1", kwargs={"pk": keyword.pk})
    response = api_client.get(url, data=None, format="json")
    assert response.status_code == 301
    response2 = api_client.get(response.url, data=None, format="json")
    assert response2.data["id"] == keyword2.id


@pytest.mark.django_db
def test_get_keyword_detail_check_redirect_to_end_of_replace_chain(
    api_client, keyword, keyword2, keyword3
):
    keyword.replaced_by = keyword2
    keyword.deprecated = True
    keyword.save()
    keyword2.replaced_by = keyword3
    keyword2.deprecated = True
    keyword2.save()
    url = reverse("keyword-detail", version="v1", kwargs={"pk": keyword.pk})
    response = api_client.get(url, data=None, format="json")
    assert response.status_code == 301
    response2 = api_client.get(response.url, data=None, format="json")
    assert response2.data["id"] == keyword3.id


@pytest.mark.django_db
def test_get_unknown_keyword_detail_check_404(api_client):
    response = api_client.get(reverse("keyword-detail", kwargs={"pk": "möö"}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_get_keyword_list_verify_text_filter(api_client, keyword, keyword2, keyword3):
    response = api_client.get(
        reverse("keyword-list"), data={"text": "avainsana", "show_all_keywords": True}
    )
    assert keyword.id in [entry["id"] for entry in response.data["data"]]
    assert keyword2.id not in [entry["id"] for entry in response.data["data"]]
    assert keyword3.id not in [entry["id"] for entry in response.data["data"]]


@pytest.mark.django_db
def test_get_keyword_list_verify_alt_labels_filter(
    api_client, keyword, keyword2, keyword3, keywordlabel
):
    keyword2.alt_labels.add(keywordlabel)
    response = api_client.get(
        reverse("keyword-list"), data={"text": "avainsana", "show_all_keywords": True}
    )
    assert keyword.id in [entry["id"] for entry in response.data["data"]]
    assert keyword2.id in [entry["id"] for entry in response.data["data"]]
    assert keyword3.id not in [entry["id"] for entry in response.data["data"]]


@pytest.mark.django_db
def test_get_keyword_list_verify_show_deprecated_param(api_client, keyword, keyword2):
    keyword.deprecated = True
    keyword.save()

    response = get_list(api_client, data={"show_all_keywords": True})
    ids = [entry["id"] for entry in response.data["data"]]
    assert keyword.id not in ids
    assert keyword2.id in ids

    response = get_list(
        api_client, data={"show_all_keywords": True, "show_deprecated": True}
    )
    ids = [entry["id"] for entry in response.data["data"]]
    assert keyword.id in ids
    assert keyword2.id in ids


@pytest.mark.django_db
def test_get_keyword_with_upcoming_events(
    api_client, keyword, keyword2, event, past_event
):
    event.keywords.add(keyword)
    event.save()
    past_event.keywords.add(keyword)
    past_event.keywords.add(keyword2)
    past_event.save()
    keyword.n_events = 1
    keyword2.n_events = 1
    keyword.save()
    keyword2.save()

    response = get_list(api_client, data={"has_upcoming_events": True})
    assert response.data["meta"]["count"] == 0

    Keyword.objects.has_upcoming_events_update()

    response = get_list(api_client, data={"has_upcoming_events": True})
    ids = [entry["id"] for entry in response.data["data"]]
    assert keyword.id in ids
    assert keyword2.id not in ids

    response = get_list(api_client, data={"has_upcoming_events": False})
    ids = [entry["id"] for entry in response.data["data"]]
    assert keyword.id in ids
    assert keyword2.id in ids


@pytest.mark.django_db
def test_get_keyword_free_search(api_client, keyword, keyword2, keyword3):
    keyword.name_fi = "cheese"
    keyword2.name_en = "blue cheese"
    keyword3.name_sv = "chess"
    keyword.save()
    keyword2.save()
    keyword3.save()

    response = get_list(api_client, data={"free_text": "cheeese"})
    ids = [entry["id"] for entry in response.data["data"]]
    assert ids == [keyword.id, keyword2.id, keyword3.id]
