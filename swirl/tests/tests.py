from django.test import TestCase
import pytest
import logging
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from swirl.processors.transform_query_processor import *

logger = logging.getLogger(__name__)

######################################################################
## fixtures

## General and shared

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def test_suser_pw():
    return 'password'

@pytest.fixture
def test_suser(test_suser_pw):
    return User.objects.create_user(
        username='admin',
        password=test_suser_pw,
        is_staff=True,  # Set to True if your view requires a staff user
        is_superuser=True,  # Set to True if your view requires a superuser
    )

## Test data

@pytest.fixture
def qrx_record_1():
    return {
        "name": "xxx",
        "shared": True,
        "qrx_type": "rewrite",
        "config_content": "# This is a test\n# column1, colum2\nmobiles; ombile; mo bile, mobile\ncheapest smartphones, cheap smartphone"
}

@pytest.fixture
def qrx_rewrite():
    return {
        "name": "xxx",
        "shared": True,
        "qrx_type": "rewrite",
        "config_content": "# This is a test\n# column1, colum2\nmobiles; ombile; mo bile, mobile\ncheapest smartphones, cheap smartphone"
}

@pytest.fixture
def qrx_synonym():
    return {
        "name": "xxx",
        "shared": True,
        "qrx_type": "synonym",
        "config_content": "# column1, column2\nnotebook, laptop\nlaptop, personal computer\npc, personal computer\npersonal computer, pc"
}

@pytest.fixture
def qrx_synonym_bag():
    return {
        "name": "xxx",
        "shared": True,
        "qrx_type": "bag",
        "config_content": "# column1....columnN\nnotebook, personal computer, laptop, pc\ncar,automobile, ride"
}
######################################################################
## tests
######################################################################
@pytest.mark.django_db
def test_query_trasnform_viewset_create_and_list(api_client, test_suser, test_suser_pw, qrx_record_1):

    is_logged_in = api_client.login(username=test_suser.username, password=test_suser_pw)

    # Check if the login was successful
    assert is_logged_in, 'Client login failed'
    response = api_client.post(reverse('querytransforms/create'),data=qrx_record_1, format='json')

    assert response.status_code == 201, 'Expected HTTP status code 201'
    # Call the viewset
    response = api_client.get(reverse('querytransforms/list'))

    # Check if the response is successful
    assert response.status_code == 200, 'Expected HTTP status code 200'

    # Check if the number of users in the response is correct
    assert len(response.json()) == 1, 'Expected 1 transform'

    # Check if the data is correct
    content = response.json()[0]
    assert content.get('name','') == qrx_record_1.get('name')
    assert content.get('shared','') == qrx_record_1.get('shared')
    assert content.get('qrx_type','') == qrx_record_1.get('qrx_type')
    assert content.get('config_content','') == qrx_record_1.get('config_content')

@pytest.mark.django_db
def test_query_transform_allocation(qrx_rewrite, qrx_synonym, qrx_synonym_bag):
    ret = TransformQueryProcessorFactory.alloc_query_transform(qrx_rewrite.get('qrx_type'),
                                        qrx_rewrite.get('name'),
                                        qrx_rewrite.get('config_content'))
    assert str(ret) == 'RewriteQueryProcessor'

    ret = TransformQueryProcessorFactory.alloc_query_transform(qrx_synonym.get('qrx_type'),
                                        qrx_rewrite.get('name'),
                                        qrx_rewrite.get('config_content'))
    assert str(ret) == 'SynonymQueryProcessor'

    ret = TransformQueryProcessorFactory.alloc_query_transform(qrx_synonym_bag.get('qrx_type'),
                                        qrx_rewrite.get('name'),
                                        qrx_rewrite.get('config_content'))
    assert str(ret) == 'SynonymBagQueryProcessor'

@pytest.mark.django_db
def test_query_transform_rewwrite_parse(qrx_rewrite):
    rw_qxr = TransformQueryProcessorFactory.alloc_query_transform(qrx_rewrite.get('qrx_type'),
                                        qrx_rewrite.get('name'),
                                        qrx_rewrite.get('config_content'))
    assert str(rw_qxr) == 'RewriteQueryProcessor'
    rw_qxr.parse_config()
    rps = rw_qxr.get_replace_patterns()
    assert len(rps) == 4
    assert str(rps[0]) == "<<mobiles>> -> <<['mobile']>>"
    assert str(rps[1]) == "<<ombile>> -> <<['mobile']>>"
    assert str(rps[2]) == "<<mo bile>> -> <<['mobile']>>"
    assert str(rps[3]) == "<<cheapest smartphones>> -> <<['cheap smartphone']>>"

@pytest.mark.django_db
def test_query_transform_synonym_parse(qrx_synonym):
    sy_qxr = TransformQueryProcessorFactory.alloc_query_transform(qrx_synonym.get('qrx_type'),
                                        qrx_synonym.get('name'),
                                        qrx_synonym.get('config_content'))
    assert str(sy_qxr) == 'SynonymQueryProcessor'
    sy_qxr.parse_config()
    rps = sy_qxr.get_replace_patterns()
    assert len(rps) == 4
    assert str(rps[0]) == "<<notebook>> -> <<['laptop']>>"
    assert str(rps[1]) == "<<laptop>> -> <<['personal computer']>>"
    assert str(rps[2]) == "<<pc>> -> <<['personal computer']>>"
    assert str(rps[3]) == "<<personal computer>> -> <<['pc']>>"

@pytest.mark.django_db
def test_query_transform_synonym_bag_parse(qrx_synonym_bag):
    sy_qxr = TransformQueryProcessorFactory.alloc_query_transform(qrx_synonym_bag.get('qrx_type'),
                                        qrx_synonym_bag.get('name'),
                                        qrx_synonym_bag.get('config_content'))
    assert str(sy_qxr) == 'SynonymBagQueryProcessor'
    sy_qxr.parse_config()
    rps = sy_qxr.get_replace_patterns()
    assert str(rps[0]) == "<<notebook>> -> <<['notebook', 'personal computer', 'laptop', 'pc']>>"
    assert str(rps[1]) == "<<personal computer>> -> <<['notebook', 'personal computer', 'laptop', 'pc']>>"
    assert str(rps[2]) == "<<laptop>> -> <<['notebook', 'personal computer', 'laptop', 'pc']>>"
    assert str(rps[3]) == "<<pc>> -> <<['notebook', 'personal computer', 'laptop', 'pc']>>"
    assert str(rps[4]) == "<<car>> -> <<['car', 'automobile', 'ride']>>"
    assert str(rps[5]) == "<<automobile>> -> <<['car', 'automobile', 'ride']>>"
    assert str(rps[6]) == "<<ride>> -> <<['car', 'automobile', 'ride']>>"
