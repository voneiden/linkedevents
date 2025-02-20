# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

import pytest
import pytz
from dateutil import parser
from django.conf import settings
from django.contrib.gis.gdal import CoordTransform, SpatialReference
from django.contrib.gis.geos import Point
from freezegun import freeze_time

from events.models import Event, Language, PublicationStatus
from events.tests.conftest import APIClient
from events.tests.utils import assert_fields_exist, datetime_zone_aware, get
from events.tests.utils import versioned_reverse as reverse

api_client = APIClient()


# === util methods ===
def get_list(api_client, version="v1", data=None, query_string=None):
    url = reverse("event-list", version=version)
    if query_string:
        url = "%s?%s" % (url, query_string)
    return get(api_client, url, data=data)


def get_list_no_code_assert(api_client, version="v1", data=None, query_string=None):
    url = reverse("event-list", version=version)
    if query_string:
        url = "%s?%s" % (url, query_string)
    return api_client.get(url, data=data, format="json")


def get_detail(api_client, detail_pk, version="v1", data=None):
    detail_url = reverse("event-detail", version=version, kwargs={"pk": detail_pk})
    return get(api_client, detail_url, data=data)


def assert_event_fields_exist(data, version="v1"):
    # TODO: incorporate version parameter into version aware
    # parts of test code
    fields = (
        "@context",
        "@id",
        "@type",
        "audience",
        "created_time",
        "custom_data",
        "data_source",
        "date_published",
        "description",
        "end_time",
        "event_status",
        "external_links",
        "id",
        "images",
        "in_language",
        "info_url",
        "keywords",
        "last_modified_time",
        "location",
        "location_extra_info",
        "name",
        "offers",
        "provider",
        "provider_contact_info",
        "publisher",
        "short_description",
        "audience_min_age",
        "audience_max_age",
        "start_time",
        "sub_events",
        "super_event",
        "super_event_type",
        "videos",
        "replaced_by",
        "deleted",
        "local",
        "search_vector_sv",
        "search_vector_fi",
        "search_vector_en",
        "type_id",
        "enrolment_start_time",
        "maximum_attendee_capacity",
        "minimum_attendee_capacity",
        "enrolment_end_time",
        "registration",
    )
    if version == "v0.1":
        fields += (
            "origin_id",
            "headline",
            "secondary_headline",
        )
    assert_fields_exist(data, fields)


def assert_events_in_response(events, response, query=""):
    response_event_ids = {event["id"] for event in response.data["data"]}
    expected_event_ids = {event.id for event in events}
    if query:
        assert response_event_ids == expected_event_ids, f"\nquery: {query}"
    else:
        assert response_event_ids == expected_event_ids


def get_list_and_assert_events(
    query: str, events: list, api_client: APIClient = api_client
):
    response = get_list(api_client, query_string=query)
    assert_events_in_response(events, response, query)


def get_detail_and_assert_events(
    query: str, events: list, api_client: APIClient = api_client
):
    response = get(api_client, query_string=query)
    assert_events_in_response(events, response, query)


# === tests ===
@pytest.mark.django_db
def test_get_event_list_html_renders(api_client, event):
    url = reverse("event-list", version="v1")
    response = api_client.get(url, data=None, HTTP_ACCEPT="text/html")
    assert response.status_code == 200, str(response.content)


@pytest.mark.django_db
def test_get_event_list_check_fields_exist(api_client, event):
    """
    Tests that event list endpoint returns the correct fields.
    """
    response = get_list(api_client)
    assert_event_fields_exist(response.data["data"][0])


@pytest.mark.django_db
def test_get_event_detail_check_fields_exist(api_client, event):
    """
    Tests that event detail endpoint returns the correct fields.
    """
    response = get_detail(api_client, event.pk)
    assert_event_fields_exist(response.data)


@pytest.mark.django_db
def test_get_unknown_event_detail_check_404(api_client):
    response = api_client.get(reverse("event-detail", kwargs={"pk": "möö"}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_get_event_list_verify_text_filter(api_client, event, event2):
    # Search with event name
    get_list_and_assert_events(f"text={event.name}", [event])
    # Search with place name
    get_list_and_assert_events(f"text={event.location.name}", [event])


@pytest.mark.django_db
def test_get_event_list_verify_data_source_filter(
    api_client, data_source, event, event2
):
    get_list_and_assert_events(f"data_source={data_source.id}", [event])


@pytest.mark.django_db
def test_get_event_list_verify_data_source_negative_filter(
    api_client, data_source, event, event2
):
    get_list_and_assert_events(f"data_source!={data_source.id}", [event2])


@pytest.mark.django_db
def test_get_event_list_verify_location_filter(api_client, place, event, event2):
    get_list_and_assert_events(f"location={place.id}", [event])


@pytest.mark.django_db
def test_get_event_list_verify_bbox_filter(api_client, event, event2):
    # API parameters must be provided in EPSG:4326 instead of the database SRS
    left_bottom = Point(25, 25)
    right_top = Point(75, 75)
    ct = CoordTransform(
        SpatialReference(settings.PROJECTION_SRID), SpatialReference(4326)
    )
    left_bottom.transform(ct)
    right_top.transform(ct)
    get_list_and_assert_events(
        f"bbox={left_bottom.x},{left_bottom.y},{right_top.x},{right_top.y}", [event]
    )


@pytest.mark.django_db
def test_get_event_list_verify_audience_max_age_lt_filter(api_client, keyword, event):
    event.audience_max_age = 16
    event.save()
    get_list_and_assert_events(f"audience_max_age_lt={event.audience_max_age}", [event])
    get_list_and_assert_events(f"audience_max_age_lt={event.audience_max_age - 1}", [])
    get_list_and_assert_events(
        f"audience_max_age_lt={event.audience_max_age + 1}", [event]
    )


@pytest.mark.django_db
def test_get_event_list_verify_audience_max_age_gt_filter(api_client, keyword, event):
    #  'audience_max_age' parameter is identical to audience_max_age_gt and is kept for compatibility's sake
    event.audience_max_age = 16
    event.save()
    get_list_and_assert_events(f"audience_max_age_gt={event.audience_max_age}", [event])
    get_list_and_assert_events(
        f"audience_max_age_gt={event.audience_max_age - 1}", [event]
    )
    get_list_and_assert_events(f"audience_max_age_gt={event.audience_max_age + 1}", [])
    get_list_and_assert_events(f"audience_max_age={event.audience_max_age}", [event])
    get_list_and_assert_events(
        f"audience_max_age={event.audience_max_age - 1}", [event]
    )
    get_list_and_assert_events(f"audience_max_age={event.audience_max_age + 1}", [])


@pytest.mark.django_db
def test_get_event_list_verify_audience_min_age_lt_filter(api_client, keyword, event):
    #  'audience_max_age' parameter is identical to audience_max_age_gt and is kept for compatibility's sake
    event.audience_min_age = 14
    event.save()
    get_list_and_assert_events(f"audience_min_age_lt={event.audience_min_age}", [event])
    get_list_and_assert_events(f"audience_min_age_lt={event.audience_min_age - 1}", [])
    get_list_and_assert_events(
        f"audience_min_age_lt={event.audience_min_age + 1}", [event]
    )

    #  'audience_max_age' parameter is identical to audience_max_age_lt and is kept for compatibility's sake
    get_list_and_assert_events(f"audience_min_age={event.audience_min_age}", [event])
    get_list_and_assert_events(f"audience_min_age={event.audience_min_age - 1}", [])
    get_list_and_assert_events(
        f"audience_min_age={event.audience_min_age + 1}", [event]
    )


@pytest.mark.django_db
def test_get_event_list_verify_audience_min_age_gt_filter(api_client, keyword, event):
    #  'audience_max_age' parameter is identical to audience_max_age_gt and is kept for compatibility's sake
    event.audience_min_age = 14
    event.save()
    get_list_and_assert_events(f"audience_min_age_gt={event.audience_min_age}", [event])
    get_list_and_assert_events(
        f"audience_min_age_gt={event.audience_min_age - 1}", [event]
    )
    get_list_and_assert_events(f"audience_min_age_gt={event.audience_min_age + 1}", [])


@pytest.mark.django_db
def test_get_event_list_start_hour_filter(api_client, keyword, event):
    event.start_time = datetime_zone_aware(2020, 1, 1, 16, 30)
    event.save()
    get_list_and_assert_events("starts_after=16", [event])
    get_list_and_assert_events("starts_after=16:", [event])
    get_list_and_assert_events("starts_after=15:59", [event])
    get_list_and_assert_events("starts_after=16:30", [event])
    get_list_and_assert_events("starts_after=17:30", [])

    response = get_list_no_code_assert(api_client, data={"starts_after": "27:30"})
    assert response.status_code == 400
    response = get_list_no_code_assert(api_client, data={"starts_after": "18:70"})
    assert response.status_code == 400
    response = get_list_no_code_assert(api_client, data={"starts_after": ":70"})
    assert response.status_code == 400
    response = get_list_no_code_assert(api_client, data={"starts_after": "18:70:"})
    assert response.status_code == 400

    get_list_and_assert_events("starts_before=16:30", [event])
    get_list_and_assert_events("starts_before=17:30", [event])
    get_list_and_assert_events("starts_before=16:29", [])


@pytest.mark.django_db
def test_get_event_list_end_hour_filter(api_client, keyword, event):
    event.start_time = datetime_zone_aware(2020, 1, 1, 13, 30)
    event.end_time = datetime_zone_aware(2020, 1, 1, 16, 30)
    event.save()
    get_list_and_assert_events("ends_after=16:30", [event])
    get_list_and_assert_events("ends_after=17:30", [])
    get_list_and_assert_events("ends_after=16:29", [event])

    get_list_and_assert_events("ends_before=16:30", [event])
    get_list_and_assert_events("ends_before=17:30", [event])
    get_list_and_assert_events("ends_before=16:29", [])


@pytest.mark.django_db
def test_get_event_list_verify_keyword_filter(api_client, keyword, event, event2):
    event.keywords.add(keyword)
    get_list_and_assert_events(f"keyword={keyword.id}", [event])


@pytest.mark.django_db
def test_get_event_list_verify_keyword_or_filter(api_client, keyword, event, event2):
    # "keyword_OR" filter should be the same as "keyword" filter
    event.keywords.add(keyword)
    get_list_and_assert_events(f"keyword_OR={keyword.id}", [event])


@pytest.mark.django_db
def test_get_event_list_verify_combine_keyword_and_keyword_or(
    api_client, keyword, keyword2, event, event2
):
    # If "keyword" and "keyword_OR" are both present "AND" them together
    event.keywords.add(keyword, keyword2)
    event2.keywords.add(keyword2)
    get_list_and_assert_events(
        f"keyword={keyword.id}&keyword_OR={keyword2.id}", [event]
    )


@pytest.mark.django_db
def test_get_event_list_verify_keyword_and(
    api_client, keyword, keyword2, event, event2
):
    event.keywords.add(keyword)
    event2.keywords.add(keyword, keyword2)
    get_list_and_assert_events(f"keyword_AND={keyword.id},{keyword2.id}", [event2])

    event2.keywords.remove(keyword2)
    event2.audience.add(keyword2)
    get_list_and_assert_events(f"keyword_AND={keyword.id},{keyword2.id}", [event2])


@pytest.mark.django_db
def test_get_event_list_verify_keyword_negative_filter(
    api_client, keyword, keyword2, event, event2
):
    event.keywords.set([keyword])
    event2.keywords.set([keyword2])
    get_list_and_assert_events(f"keyword!={keyword.id}", [event2])
    get_list_and_assert_events(f"keyword!={keyword.id},{keyword2.id}", [])

    event.keywords.set([])
    event.audience.set([keyword])
    get_list_and_assert_events(f"keyword!={keyword.id}", [event2])


@pytest.mark.django_db
def test_get_event_list_verify_replaced_keyword_filter(
    api_client, keyword, keyword2, event
):
    event.keywords.add(keyword2)
    keyword.replaced_by = keyword2
    keyword.deleted = True
    keyword.save()
    get_list_and_assert_events(f"keyword={keyword.id}", [event])
    get_list_and_assert_events("keyword=unknown_keyword", [])


@pytest.mark.django_db
def test_get_event_list_verify_division_filter(
    api_client, event, event2, event3, administrative_division, administrative_division2
):
    event.location.divisions.set([administrative_division])
    event2.location.divisions.set([administrative_division2])

    get_list_and_assert_events(f"division={administrative_division.ocd_id}", [event])
    get_list_and_assert_events(
        f"division={administrative_division.ocd_id},{administrative_division2.ocd_id}",
        [event, event2],
    )  # noqa E501


@pytest.mark.django_db
def test_get_event_list_super_event_filters(api_client, event, event2):
    event.super_event_type = Event.SuperEventType.RECURRING
    event.save()
    event2.super_event = event
    event2.save()

    get_list_and_assert_events("super_event=none", [event])
    get_list_and_assert_events(f"super_event={event.id}", [event2])


@pytest.mark.django_db
def test_get_event_list_recurring_filters(api_client, event, event2):
    event.super_event_type = Event.SuperEventType.RECURRING
    event.save()
    event2.super_event = event
    event2.save()

    get_list_and_assert_events("recurring=super", [event])
    get_list_and_assert_events("recurring=sub", [event2])


@pytest.mark.django_db
def test_super_event_type_filter(api_client, event, event2):
    event.super_event_type = Event.SuperEventType.RECURRING
    event.save()
    event2.super_event = event
    event2.save()

    # "none" and "null" should return only the non super event
    for value in ("none", "null"):
        get_list_and_assert_events(f"super_event_type={value}", [event2])

    # "recurring" should return only the recurring super event
    get_list_and_assert_events("super_event_type=recurring", [event])

    # "recurring,none" should return both
    get_list_and_assert_events("super_event_type=recurring,none", [event, event2])
    get_list_and_assert_events("super_event_type=fwfiuwhfiuwhiw", [])


@pytest.mark.django_db
def test_get_event_disallow_simultaneous_include_super_and_sub(
    api_client, event, event2
):
    event.super_event_type = Event.SuperEventType.RECURRING
    event.save()
    event2.super_event = event
    event2.save()

    # fetch event with super event
    detail_url = reverse("event-detail", version="v1", kwargs={"pk": event2.pk})

    # If not specifically handled, the following combination of
    # include parameters causes an infinite recursion, because the
    # super events of sub events of super events ... are expanded ad
    # infinitum. This test is here to check that execution finishes.
    detail_url += "?include=super_event,sub_events"
    response = get(api_client, detail_url)
    assert_event_fields_exist(response.data)
    assert type(response.data["super_event"] == "dict")


@pytest.mark.django_db
def test_language_filter(api_client, event, event2, event3):
    event.name_sv = "namn"
    event.save()
    event2.in_language.add(Language.objects.get_or_create(id="en")[0])
    event2.in_language.add(Language.objects.get_or_create(id="sv")[0])
    event2.save()
    event3.name_ru = "название"
    event3.in_language.add(Language.objects.get_or_create(id="et")[0])
    event3.save()

    # Finnish should be the default language
    get_list_and_assert_events("language=fi", [event, event2, event3])

    # Swedish should have two events (matches in_language and name_sv)
    get_list_and_assert_events("language=sv", [event, event2])

    # English should have one event (matches in_language)
    get_list_and_assert_events("language=en", [event2])

    # Russian should have one event (matches name_ru)
    get_list_and_assert_events("language=ru", [event3])

    # Chinese should have no events
    get_list_and_assert_events("language=zh_hans", [])

    # Estonian should have one event (matches in_language), even without translations available
    get_list_and_assert_events("language=et", [event3])


@pytest.mark.django_db
def test_event_list_filters(api_client, event, event2):
    filters = (
        ([event.publisher.id, event2.publisher.id], "publisher"),
        ([event.data_source.id, event2.data_source.id], "data_source"),
    )

    for filter_values, filter_name in filters:
        q = ",".join(filter_values)
        get_list_and_assert_events(f"{filter_name}={q}", [event, event2])


@pytest.mark.django_db
def test_event_list_publisher_ancestor_filter(
    api_client, event, event2, organization, organization2, organization3
):
    organization2.parent = organization
    organization2.save()
    event.publisher = organization2
    event.save()
    event2.publisher = organization3
    event2.save()
    get_list_and_assert_events(f"publisher_ancestor={organization.id}", [event])


@pytest.mark.django_db
def test_publication_status_filter(
    api_client, event, event2, user, organization, data_source
):
    event.publication_status = PublicationStatus.PUBLIC
    event.save()

    event2.publication_status = PublicationStatus.DRAFT
    event2.save()

    api_client.force_authenticate(user=user)
    get_list_and_assert_events(
        "show_all=true&publication_status=public", [event], api_client
    )

    # cannot see drafts from other organizations
    get_list_and_assert_events("show_all=true&publication_status=draft", [], api_client)

    event2.publisher = organization
    event2.data_source = data_source
    event2.save()
    get_list_and_assert_events(
        "show_all=true&publication_status=draft", [event2], api_client
    )


@pytest.mark.django_db
def test_event_status_filter(
    api_client, event, event2, event3, event4, user, organization, data_source
):
    event.event_status = Event.Status.SCHEDULED
    event.save()
    event2.event_status = Event.Status.RESCHEDULED
    event2.save()
    event3.event_status = Event.Status.CANCELLED
    event3.save()
    event4.event_status = Event.Status.POSTPONED
    event4.save()
    get_list_and_assert_events("event_status=eventscheduled", [event])
    get_list_and_assert_events("event_status=eventrescheduled", [event2])
    get_list_and_assert_events("event_status=eventcancelled", [event3])
    get_list_and_assert_events("event_status=eventpostponed", [event4])


@pytest.mark.django_db
def test_admin_user_filter(api_client, event, event2, user):
    api_client.force_authenticate(user=user)
    get_list_and_assert_events("admin_user=true", [event], api_client)


@pytest.mark.django_db
def test_redirect_if_replaced(api_client, event, event2, user):
    api_client.force_authenticate(user=user)

    event.replaced_by = event2
    event.save()

    url = reverse("event-detail", version="v1", kwargs={"pk": event.pk})
    response = api_client.get(url, format="json")
    assert response.status_code == 301

    response2 = api_client.get(response.url, format="json")
    assert response2.status_code == 200
    assert response2.data["id"] == event2.pk


@pytest.mark.django_db
def test_redirect_to_end_of_replace_chain(api_client, event, event2, event3, user):
    api_client.force_authenticate(user=user)

    event.replaced_by = event2
    event.save()
    event2.replaced_by = event3
    event2.save()

    url = reverse("event-detail", version="v1", kwargs={"pk": event.pk})
    response = api_client.get(url, format="json")
    assert response.status_code == 301

    response2 = api_client.get(response.url, format="json")
    assert response2.status_code == 200
    assert response2.data["id"] == event3.pk


@pytest.mark.django_db
def test_get_event_list_sub_events(api_client, event, event2):
    event.super_event_type = Event.SuperEventType.RECURRING
    event.save()
    event2.super_event = event
    event2.save()

    # fetch event with sub event
    detail_url = reverse("event-detail", version="v1", kwargs={"pk": event.pk})
    response = get(api_client, detail_url)
    assert_event_fields_exist(response.data)
    assert response.data["sub_events"]


@pytest.mark.django_db
def test_get_event_list_deleted_sub_events(api_client, event, event2):
    event.super_event_type = Event.SuperEventType.RECURRING
    event.save()
    event2.super_event = event
    event2.deleted = True
    event2.save()

    # fetch event with sub event deleted
    detail_url = reverse("event-detail", version="v1", kwargs={"pk": event.pk})
    response = get(api_client, detail_url)
    assert_event_fields_exist(response.data)
    assert not response.data["sub_events"]


@pytest.mark.django_db
def test_event_list_show_deleted_param(api_client, event, event2, user):
    api_client.force_authenticate(user=user)

    event.soft_delete()

    response = get_list(api_client, query_string="show_deleted=true")
    assert response.status_code == 200
    assert event.id in {e["id"] for e in response.data["data"]}
    assert event2.id in {e["id"] for e in response.data["data"]}

    expected_keys = ["id", "name", "last_modified_time", "deleted", "replaced_by"]
    event_data = next((e for e in response.data["data"] if e["id"] == event.id))
    assert len(event_data) == len(expected_keys)
    for key in event_data:
        assert key in expected_keys
    assert event_data["name"]["fi"] == "POISTETTU"
    assert event_data["name"]["sv"] == "RADERAD"
    assert event_data["name"]["en"] == "DELETED"
    get_list_and_assert_events("", [event2], api_client)


@pytest.mark.django_db
def test_event_list_deleted_param(api_client, event, event2, user):
    api_client.force_authenticate(user=user)

    event.soft_delete()

    response = get_list(api_client, query_string="deleted=true")
    assert response.status_code == 200
    assert event.id in {e["id"] for e in response.data["data"]}
    assert event2.id not in {e["id"] for e in response.data["data"]}

    expected_keys = ["id", "name", "last_modified_time", "deleted", "replaced_by"]
    event_data = next((e for e in response.data["data"] if e["id"] == event.id))
    assert len(event_data) == len(expected_keys)
    for key in event_data:
        assert key in expected_keys
    assert event_data["name"]["fi"] == "POISTETTU"
    assert event_data["name"]["sv"] == "RADERAD"
    assert event_data["name"]["en"] == "DELETED"
    get_list_and_assert_events("", [event2], api_client)


@pytest.mark.django_db
def test_event_list_is_free_filter(api_client, event, event2, event3, offer):
    get_list_and_assert_events("is_free=true", [event2])
    get_list_and_assert_events("is_free=false", [event, event3])


@pytest.mark.django_db
def test_start_end_iso_date(api_client, make_event):
    event1 = make_event(
        "1",
        parser.parse("2020-02-19 23:00:00+02"),
        parser.parse("2020-02-19 23:30:00+02"),
    )
    event2 = make_event(
        "2",
        parser.parse("2020-02-19 23:30:00+02"),
        parser.parse("2020-02-20 00:00:00+02"),
    )
    event3 = make_event(
        "3",
        parser.parse("2020-02-19 23:30:00+02"),
        parser.parse("2020-02-20 00:30:00+02"),
    )
    event4 = make_event(
        "4",
        parser.parse("2020-02-20 00:00:00+02"),
        parser.parse("2020-02-20 00:30:00+02"),
    )
    event5 = make_event(
        "5",
        parser.parse("2020-02-20 12:00:00+02"),
        parser.parse("2020-02-20 13:00:00+02"),
    )
    event6 = make_event(
        "6",
        parser.parse("2020-02-21 12:00:00+02"),
        parser.parse("2020-02-21 13:00:00+02"),
    )
    event7 = make_event("7")  # postponed event

    # Start parameter
    get_list_and_assert_events(
        "start=2020-02-19", [event1, event2, event3, event4, event5, event6, event7]
    )

    response = get_list(api_client, query_string="start=2020-02-20")
    expected_events = [event3, event4, event5, event6, event7]
    assert_events_in_response(expected_events, response)
    get_list_and_assert_events(
        "start=2020-02-20", [event3, event4, event5, event6, event7]
    )

    # End parameter
    get_list_and_assert_events("end=2020-02-19", [event1, event2, event3, event4])
    get_list_and_assert_events(
        "end=2020-02-20", [event1, event2, event3, event4, event5]
    )

    # Start and end parameters
    get_list_and_assert_events(
        "start=2020-02-20&end=2020-02-20", [event3, event4, event5]
    )
    get_list_and_assert_events(
        "start=2020-02-19&end=2020-02-21",
        [event1, event2, event3, event4, event5, event6],
    )


@pytest.mark.django_db
def test_start_end_iso_date_time(api_client, make_event):
    event1 = make_event(
        "1",
        parser.parse("2020-02-19 10:00:00+02"),
        parser.parse("2020-02-19 11:22:33+02"),
    )
    event2 = make_event(
        "2",
        parser.parse("2020-02-19 11:22:33+02"),
        parser.parse("2020-02-19 22:33:44+02"),
    )
    event3 = make_event(
        "3",
        parser.parse("2020-02-20 11:22:33+02"),
        parser.parse("2020-02-20 22:33:44+02"),
    )
    event4 = make_event("4")  # postponed event

    # Start parameter
    get_list_and_assert_events(
        "start=2020-02-19T11:22:32", [event1, event2, event3, event4]
    )
    get_list_and_assert_events("start=2020-02-19T11:22:33", [event2, event3, event4])

    # End parameter
    get_list_and_assert_events("end=2020-02-19T11:22:32", [event1])
    get_list_and_assert_events("end=2020-02-19T11:22:33", [event1, event2])

    # Start and end parameters
    get_list_and_assert_events(
        "start=2020-02-19T11:22:33&end=2020-02-19T11:22:33", [event2]
    )


@pytest.mark.django_db
def test_start_end_today(api_client, make_event):
    event1 = make_event(
        "1",
        parser.parse("2020-02-19 23:00:00+02"),
        parser.parse("2020-02-19 23:30:00+02"),
    )
    event2 = make_event(
        "2",
        parser.parse("2020-02-19 23:30:00+02"),
        parser.parse("2020-02-20 00:00:00+02"),
    )
    event3 = make_event(
        "3",
        parser.parse("2020-02-19 23:30:00+02"),
        parser.parse("2020-02-20 00:30:00+02"),
    )
    event4 = make_event(
        "4",
        parser.parse("2020-02-20 00:00:00+02"),
        parser.parse("2020-02-20 00:30:00+02"),
    )
    event5 = make_event(
        "5",
        parser.parse("2020-02-20 12:00:00+02"),
        parser.parse("2020-02-20 13:00:00+02"),
    )
    event6 = make_event(
        "6",
        parser.parse("2020-02-21 00:00:00+02"),
        parser.parse("2020-02-21 01:00:00+02"),
    )
    event7 = make_event(
        "7",
        parser.parse("2020-02-21 12:00:00+02"),
        parser.parse("2020-02-21 13:00:00+02"),
    )
    event8 = make_event("8")  # postponed event

    def times():
        yield "2020-02-20 00:00:00+02"
        yield "2020-02-20 12:00:00+02"
        yield "2020-02-20 23:59:59+02"

    # Start parameter
    with freeze_time(times):
        get_list_and_assert_events(
            "start=today", [event3, event4, event5, event6, event7, event8]
        )

    # End parameter
    with freeze_time(times):
        get_list_and_assert_events(
            "end=today", [event1, event2, event3, event4, event5, event6]
        )

    # Start and end parameters
    with freeze_time(times):
        get_list_and_assert_events(
            "start=today&end=today", [event3, event4, event5, event6]
        )


@pytest.mark.django_db
def test_start_end_now(api_client, make_event):
    event1 = make_event(
        "1",
        parser.parse("2020-02-19 23:00:00+02"),
        parser.parse("2020-02-19 23:30:00+02"),
    )
    event2 = make_event(
        "2",
        parser.parse("2020-02-19 23:30:00+02"),
        parser.parse("2020-02-20 00:00:00+02"),
    )
    event3 = make_event(
        "3",
        parser.parse("2020-02-19 23:30:00+02"),
        parser.parse("2020-02-20 00:30:00+02"),
    )
    event4 = make_event(
        "4",
        parser.parse("2020-02-20 00:00:00+02"),
        parser.parse("2020-02-20 00:30:00+02"),
    )
    event5 = make_event(
        "5",
        parser.parse("2020-02-20 12:00:00+02"),
        parser.parse("2020-02-20 13:00:00+02"),
    )
    event6 = make_event(
        "6",
        parser.parse("2020-02-21 00:00:00+02"),
        parser.parse("2020-02-21 01:00:00+02"),
    )
    event7 = make_event(
        "7",
        parser.parse("2020-02-21 12:00:00+02"),
        parser.parse("2020-02-21 13:00:00+02"),
    )
    event8 = make_event("8")  # postponed event

    # Start parameter
    with freeze_time("2020-02-20 00:30:00+02"):
        get_list_and_assert_events("start=now", [event5, event6, event7, event8])

    # End parameter
    with freeze_time("2020-02-20 12:00:00+02"):
        get_list_and_assert_events("end=now", [event1, event2, event3, event4, event5])

    # Start and end parameters
    with freeze_time("2020-02-20 12:00:00+02"):
        get_list_and_assert_events("start=now&end=now", [event5])


@pytest.mark.django_db
def test_start_end_events_without_endtime(api_client, make_event):
    event1 = make_event("1", parser.parse("2020-02-19 23:00:00+02"))
    event2 = make_event("2", parser.parse("2020-02-20 12:00:00+02"))
    event3 = make_event("3", parser.parse("2020-02-21 12:34:56+02"))
    event4 = make_event("4")  # postponed event

    # Start parameter
    get_list_and_assert_events(
        "start=2020-02-19T23:00:00", [event1, event2, event3, event4]
    )
    get_list_and_assert_events("start=2020-02-20T01:00:00", [event2, event3, event4])

    # End parameter
    get_list_and_assert_events("end=2020-02-20T12:00:00", [event1, event2])
    get_list_and_assert_events("end=2020-02-21T23:00:00", [event1, event2, event3])

    # Start and end parameters
    get_list_and_assert_events(
        "start=2020-02-19T23:00:00&end=2020-02-21T12:34:56", [event1, event2, event3]
    )  # noqa E501
    get_list_and_assert_events(
        "start=2020-02-19T23:00:01&end=2020-02-21T12:34:55", [event2]
    )

    # Kulke special case: multiple day event but no specific start or end times, only dates
    event1.start_time = parser.parse("2020-02-19 00:00:00+02")
    event1.end_time = parser.parse("2020-02-21 00:00:00+02")
    event1.has_start_time = False
    event1.has_end_time = False
    event1.save()
    # Kulke special case: single day event, specific start but no end time
    event2.start_time = parser.parse("2020-02-20 18:00:00+02")
    event2.end_time = parser.parse("2020-02-21 00:00:00+02")
    event2.has_start_time = True
    event2.has_end_time = False
    event2.save()

    # Start parameter for Kulke special case
    # long event (no exact start) that already started should be included
    get_list_and_assert_events(
        "start=2020-02-20T12:00:00", [event1, event2, event3, event4]
    )

    # short event (exact start) that already started should not be included
    get_list_and_assert_events("start=2020-02-20T21:00:00", [event1, event3, event4])


@pytest.mark.django_db
def test_keyword_and_text(api_client, event, event2, keyword):
    keyword.name_fi = "lappset"
    keyword.save()
    event.keywords.add(keyword)
    event.save()
    event2.description_fi = "lapset"
    event2.save()
    get_list_and_assert_events("combined_text=lapset", [event, event2])

    event.description_fi = "lapset ja aikuiset"
    event.save()
    get_list_and_assert_events("combined_text=lapset,aikuiset", [event])


@pytest.mark.django_db
def test_keywordset_search(
    api_client,
    event,
    event2,
    event3,
    keyword,
    keyword2,
    keyword3,
    keyword_set,
    keyword_set2,
):
    event.keywords.add(keyword, keyword3)
    event.save()
    event2.keywords.add(keyword2, keyword3)
    event2.save()
    event3.keywords.add(keyword, keyword2)
    event3.save()
    get_list_and_assert_events("keyword_set_AND=set:1,set:2", [event, event2])
    get_list_and_assert_events("keyword_set_OR=set:1,set:2", [event, event2, event3])

    event3.keywords.remove(keyword, keyword2)
    event3.save()
    get_list_and_assert_events("keyword_set_AND=set:1,set:2", [event, event2])


@pytest.mark.django_db
def test_keyword_OR_set_search(
    api_client,
    event,
    event2,
    event3,
    keyword,
    keyword2,
    keyword3,
    keyword_set,
    keyword_set2,
):
    event.keywords.add(keyword, keyword3)
    event.save()
    event2.keywords.add(keyword2, keyword3)
    event2.save()
    event3.keywords.add(keyword, keyword2)
    event3.save()
    load = f"keyword_OR_set1={keyword.id},{keyword2.id}&keyword_OR_set2={keyword3.id}"
    get_list_and_assert_events(load, [event, event2])


@pytest.mark.django_db
def test_event_get_by_type(api_client, event, event2, event3):
    #  default type is General, only general events should be present in the default search
    event2.type_id = Event.Type_Id.COURSE
    event2.save()
    event3.type_id = Event.Type_Id.VOLUNTEERING
    event3.save()
    get_list_and_assert_events("", [event])
    get_list_and_assert_events("event_type=general", [event])
    get_list_and_assert_events("event_type=general,course", [event, event2])
    get_list_and_assert_events("event_type=course,volunteering", [event2, event3])
    response = get_list_no_code_assert(
        api_client, query_string="event_type=sometypohere"
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_event_get_by_id(api_client, event, event2, event3):
    get_list_and_assert_events(f"ids={event.id},{event2.id}", [event, event2])


@pytest.mark.django_db
def test_suitable_for_certain_age(
    api_client, make_event, event, event2, event3, event4
):
    age_upper = 12
    age_lower = 11
    # suitable
    event.audience_min_age = 11
    event.audience_max_age = 13

    # not suitable, min age too high
    event2.audience_min_age = 13

    # not suitable, max age too low
    event3.audience_max_age = 11

    # suitable
    event4.audience_min_age = None
    event4.audience_max_age = 20

    # not suitable, neither of age limits defined
    event5 = make_event(
        "5",
        datetime.now().astimezone(pytz.timezone("UTC")),
        datetime.now().astimezone(pytz.timezone("UTC")) + timedelta(hours=1),
    )
    event5.audience_min_age = None
    event5.audience_max_age = None

    # suitable
    event6 = make_event(
        "6",
        datetime.now().astimezone(pytz.timezone("UTC")),
        datetime.now().astimezone(pytz.timezone("UTC")) + timedelta(hours=1),
    )
    event6.audience_min_age = 11
    event6.audience_max_age = None

    events = [event, event2, event3, event4, event5, event6]
    Event.objects.bulk_update(events, ["audience_min_age", "audience_max_age"])
    get_list_and_assert_events(f"suitable_for={age_upper}", [event, event4, event6])
    get_list_and_assert_events(
        f"suitable_for={age_upper}, {age_lower}", [event, event4, event6]
    )
    get_list_and_assert_events(
        f"suitable_for={age_lower}, {age_upper}", [event, event4, event6]
    )

    response = get_list_no_code_assert(api_client, query_string="suitable_for=error")
    assert (
        str(response.data["detail"])
        == 'suitable_for must be an integer, you passed "error"'
    )

    response = get_list_no_code_assert(api_client, query_string="suitable_for=12,13,14")
    assert (
        str(response.data["detail"])
        == "suitable_for takes at maximum two values, you provided 3"
    )


@pytest.mark.django_db
def test_private_datasource_events(
    api_client, event, event2, event3, other_data_source
):
    get_list_and_assert_events("", [event, event2, event3])
    other_data_source.private = True
    other_data_source.save()
    get_list_and_assert_events("", [event, event3])
    get_list_and_assert_events(f"data_source={other_data_source.id}", [event2])
