from unittest import skip
from unittest.mock import patch

from django.test import override_settings

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import JWTAuthMixin, get_validation_errors, reverse
from vng_api_common.validators import (
    IsImmutableValidator, ResourceValidator, URLValidator
)
from zds_client.tests.mocks import mock_client

from zrc.datamodel.constants import AardZaakRelatie, BetalingsIndicatie
from zrc.datamodel.models import ZaakInformatieObject
from zrc.datamodel.tests.factories import (
    ResultaatFactory, StatusFactory, ZaakFactory
)
from zrc.tests.utils import ZAAK_WRITE_KWARGS, isodatetime

from ..scopes import (
    SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN, SCOPE_ZAKEN_CREATE
)

ZAAKTYPE = 'https://example.com/foo/bar'
STATUSTYPE = f'{ZAAKTYPE}/statustypen/5b348dbf-9301-410b-be9e-83723e288785'

RESPONSES = {
    ZAAKTYPE: {
        'url': ZAAKTYPE,
        'productenOfDiensten': [
            'https://example.com/product/123',
        ]
    },
    STATUSTYPE: {
        'url': STATUSTYPE,
        'zaaktype': ZAAKTYPE,
        'volgnummer': 1,
        'isEindstatus': False
    },
}


class ZaakValidationTests(JWTAuthMixin, APITestCase):

    scopes = [SCOPE_ZAKEN_CREATE, SCOPE_ZAKEN_ALLES_LEZEN]
    zaaktype = ZAAKTYPE

    # Needed to pass Django's URLValidator, since the default APIClient domain
    # is not considered a valid URL by Django
    valid_testserver_url = 'testserver.nl'

    @override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_404')
    def test_validate_zaaktype_invalid(self):
        url = reverse('zaak-list')

        response = self.client.post(url, {
            'zaaktype': 'https://example.com/foo/bar',
            'bronorganisatie': '517439943',
            'verantwoordelijkeOrganisatie': '517439943',
            'registratiedatum': '2018-06-11',
            'startdatum': '2018-06-11',
        }, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, 'zaaktype')
        self.assertEqual(validation_error['code'], URLValidator.code)
        self.assertEqual(validation_error['name'], 'zaaktype')

    @override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_200')
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_validate_zaaktype_valid(self, *mocks):
        url = reverse('zaak-list')

        response = self.client.post(url, {
            'zaaktype': ZAAKTYPE,
            'vertrouwelijkheidaanduiding': VertrouwelijkheidsAanduiding.openbaar,
            'bronorganisatie': '517439943',
            'verantwoordelijkeOrganisatie': '517439943',
            'registratiedatum': '2018-06-11',
            'startdatum': '2018-06-11',
        }, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_200')
    def test_create_zaak_validate_incorrect_zaaktype_resource(self, *mocks):
        responses = {
            ZAAKTYPE: {
                'some': 'incorrect property'
            }
        }
        with mock_client(responses):
            response = self.client.post(reverse('zaak-list'), {
                'zaaktype': ZAAKTYPE,
                'bronorganisatie': '517439943',
                'verantwoordelijkeOrganisatie': '517439943',
                'registratiedatum': '2018-12-24',
                'startdatum': '2018-12-24',
                'vertrouwelijkheidaanduiding': VertrouwelijkheidsAanduiding.openbaar,
            }, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, 'zaaktype')
        self.assertEqual(error['code'], 'invalid-resource')

    def test_validation_camelcase(self):
        url = reverse('zaak-list')

        response = self.client.post(url, {}, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        bad_casing = get_validation_errors(response, 'verantwoordelijke_organisatie')
        self.assertIsNone(bad_casing)

        good_casing = get_validation_errors(response, 'verantwoordelijkeOrganisatie')
        self.assertIsNotNone(good_casing)

    @patch('vng_api_common.validators.fetcher')
    @patch('vng_api_common.validators.obj_has_shape', return_value=False)
    @override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_200')
    def test_validate_communicatiekanaal_invalid_resource(self, mock_has_shape, mock_fetcher):
        url = reverse('zaak-list')
        body = {'communicatiekanaal': 'https://ref.tst.vng.cloud/referentielijsten/api/v1/'}

        response = self.client.post(url, body, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, 'communicatiekanaal')
        self.assertEqual(error['code'], ResourceValidator._ResourceValidator__code)

    @patch('vng_api_common.validators.fetcher')
    @override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_404')
    def test_validate_communicatiekanaal_bad_url(self, mock_fetcher):
        url = reverse('zaak-list')
        body = {'communicatiekanaal': 'https://someurlthatdoesntexist.com'}

        response = self.client.post(url, body, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, 'communicatiekanaal')
        self.assertEqual(error['code'], URLValidator.code)

    @patch('vng_api_common.validators.fetcher')
    def test_validate_communicatiekanaal_valid(self, mock_fetcher):
        url = reverse('zaak-list')
        body = {'communicatiekanaal': 'https://example.com/dummy'}

        with override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_200'):
            with patch('vng_api_common.validators.obj_has_shape', return_value=True):
                response = self.client.post(url, body, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, 'communicatiekanaal')
        self.assertIsNone(error)

    @override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_404')
    def test_relevante_andere_zaken(self):
        url = reverse('zaak-list')

        response = self.client.post(url, {
            'zaaktype': 'https://example.com/foo/bar',
            'bronorganisatie': '517439943',
            'verantwoordelijkeOrganisatie': '517439943',
            'registratiedatum': '2018-06-11',
            'startdatum': '2018-06-11',
            'relevanteAndereZaken': [{
                'url': 'https://example.com/andereZaak',
                'aardRelatie': AardZaakRelatie.vervolg
            }]
        }, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, 'relevanteAndereZaken.0.url')
        self.assertEqual(validation_error['code'], URLValidator.code)

    @patch('vng_api_common.validators.obj_has_shape', return_value=True)
    @override_settings(
        LINK_FETCHER='vng_api_common.mocks.link_fetcher_200',
        ALLOWED_HOSTS=[valid_testserver_url]
    )
    def test_relevante_andere_zaken_valid_zaak_url(self, *mocks):
        url = reverse('zaak-list')

        zaak_body = {
            'zaaktype': ZAAKTYPE,
            'bronorganisatie': '517439943',
            'verantwoordelijkeOrganisatie': '517439943',
            'registratiedatum': '2018-06-11',
            'startdatum': '2018-06-11',
            'vertrouwelijkheidaanduiding': VertrouwelijkheidsAanduiding.openbaar,
        }

        with mock_client(RESPONSES):
            response = self.client.post(
                url,
                zaak_body,
                HTTP_HOST=self.valid_testserver_url,
                **ZAAK_WRITE_KWARGS
            )

        andere_zaak_url = response.data['url']

        zaak_body.update({'relevanteAndereZaken': [{
            'url': andere_zaak_url,
            'aardRelatie': AardZaakRelatie.vervolg
        }]})

        with mock_client(RESPONSES):
            response = self.client.post(
                url,
                zaak_body,
                HTTP_HOST=self.valid_testserver_url,
                **ZAAK_WRITE_KWARGS
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_200')
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_laatste_betaaldatum_betaalindicatie_nvt(self, *mocks):
        """
        Assert that the field laatsteBetaaldatum may not be set for the NVT
        indication.
        """
        url = reverse('zaak-list')

        # all valid values
        for value in BetalingsIndicatie.values:
            if value == BetalingsIndicatie.nvt:
                continue
            with self.subTest(betalingsindicatie=value):
                response = self.client.post(url, {
                    'zaaktype': 'https://example.com/foo/bar',
                    'vertrouwelijkheidaanduiding': VertrouwelijkheidsAanduiding.openbaar,
                    'bronorganisatie': '517439943',
                    'verantwoordelijkeOrganisatie': '517439943',
                    'registratiedatum': '2018-06-11',
                    'startdatum': '2018-06-11',
                    'betalingsindicatie': value,
                    'laatsteBetaaldatum': '2019-01-01T14:03:00Z',
                }, **ZAAK_WRITE_KWARGS)

                self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # invalid value
        with self.subTest(betalingsindicatie=BetalingsIndicatie.nvt):
            response = self.client.post(url, {
                'zaaktype': 'https://example.com/foo/bar',
                'vertrouwelijkheidaanduiding': VertrouwelijkheidsAanduiding.openbaar,
                'bronorganisatie': '517439943',
                'verantwoordelijkeOrganisatie': '517439943',
                'registratiedatum': '2018-06-11',
                'startdatum': '2018-06-11',
                'betalingsindicatie': BetalingsIndicatie.nvt,
                'laatsteBetaaldatum': '2019-01-01T14:03:00Z',
            }, **ZAAK_WRITE_KWARGS)

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            validation_error = get_validation_errors(response, 'laatsteBetaaldatum')
            self.assertEqual(validation_error['code'], 'betaling-nvt')

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    @override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_200')
    def test_invalide_product_of_dienst(self, *mocks):
        url = reverse('zaak-list')

        with mock_client(RESPONSES):
            response = self.client.post(url, {
                'zaaktype': 'https://example.com/foo/bar',
                'vertrouwelijkheidaanduiding': VertrouwelijkheidsAanduiding.openbaar,
                'bronorganisatie': '517439943',
                'verantwoordelijkeOrganisatie': '517439943',
                'registratiedatum': '2018-12-24',
                'startdatum': '2018-12-24',
                'productenOfDiensten': ['https://example.com/product/999'],
            }, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        validation_error = get_validation_errors(response, 'productenOfDiensten')
        self.assertEqual(validation_error['code'], 'invalid-products-services')


class ZaakUpdateValidation(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_validate_verlenging(self):
        """
        Regression test for https://github.com/VNG-Realisatie/gemma-zaken/issues/920
        """
        zaak = ZaakFactory.create(zaaktype='https://example.com/foo/bar')
        zaak_url = reverse(zaak)

        response = self.client.patch(zaak_url, {
            'verlenging': {
                'reden': 'We hebben nog tijd genoeg',
                'duur': 'P0Y1M0D'
            }
        }, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_validate_opschorting_indicatie_false(self):
        zaak = ZaakFactory.create(zaaktype='https://example.com/foo/bar')
        zaak_url = reverse(zaak)

        response = self.client.patch(zaak_url, {
            'opschorting': {
                'indicatie': False,
                'reden': ''
            }
        }, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_validate_opschorting_required_fields_partial_update(self):
        zaak = ZaakFactory.create(zaaktype='https://example.com/foo/bar')
        zaak_url = reverse(zaak)

        response = self.client.patch(zaak_url, {
            'opschorting': {
                'wrongfield': 'bla'
            }
        }, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        for field in ['opschorting.indicatie', 'opschorting.reden']:
            with self.subTest(field=field):
                error = get_validation_errors(response, field)
                self.assertEqual(error['code'], 'required')

    def test_validate_verlenging_required_fields_partial_update(self):
        zaak = ZaakFactory.create(zaaktype='https://example.com/foo/bar')
        zaak_url = reverse(zaak)

        response = self.client.patch(zaak_url, {
            'verlenging': {
                'wrongfield': 'bla'
            }
        }, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        for field in ['verlenging.reden', 'verlenging.duur']:
            with self.subTest(field=field):
                error = get_validation_errors(response, field)
                self.assertEqual(error['code'], 'required')

    @override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_200')
    def test_not_allowed_to_change_zaaktype(self):
        zaak = ZaakFactory.create()
        url = reverse(zaak)

        response = self.client.patch(url, {
            "zaaktype": "https://ander.zaaktype.nl/foo/bar",
        }, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        validation_error = get_validation_errors(response, 'zaaktype')
        self.assertEqual(validation_error['code'], IsImmutableValidator.code)

    @override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_200')
    def test_not_allowed_to_change_identificatie(self):
        zaak = ZaakFactory.create(identificatie='gibberish')
        url = reverse(zaak)

        response = self.client.patch(url, {
            "identificatie": "new value",
        }, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        validation_error = get_validation_errors(response, 'identificatie')
        self.assertEqual(validation_error['code'], IsImmutableValidator.code)


@override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_200')
class DeelZaakValidationTests(JWTAuthMixin, APITestCase):
    scopes = [
        SCOPE_ZAKEN_BIJWERKEN,
        SCOPE_ZAKEN_CREATE
    ]
    zaaktype = 'https://example.com/foo/bar'

    def test_cannot_use_self_as_hoofdzaak(self):
        """
        Hoofdzaak moet een andere zaak zijn dan de deelzaak zelf.
        """
        zaak = ZaakFactory.create(zaaktype='https://example.com/foo/bar')
        detail_url = reverse(zaak)

        response = self.client.patch(
            detail_url,
            {'hoofdzaak': detail_url},
            **ZAAK_WRITE_KWARGS
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, 'hoofdzaak')
        self.assertEqual(error['code'], 'self-forbidden')

    def test_cannot_have_multiple_levels(self):
        """
        Deelzaak kan enkel deelzaak zijn van hoofdzaak en niet andere deelzaken.
        """
        url = reverse('zaak-list')
        hoofdzaak = ZaakFactory.create(zaaktype='https://example.com/foo/bar')
        deelzaak = ZaakFactory.create(hoofdzaak=hoofdzaak, zaaktype='https://example.com/foo/bar')
        deelzaak_url = reverse(deelzaak)

        response = self.client.post(
            url,
            {'hoofdzaak': deelzaak_url},
            **ZAAK_WRITE_KWARGS
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, 'hoofdzaak')
        self.assertEqual(error['code'], 'deelzaak-als-hoofdzaak')


class ZaakInformatieObjectValidationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @override_settings(
        LINK_FETCHER='vng_api_common.mocks.link_fetcher_404',
        ZDS_CLIENT_CLASS='vng_api_common.mocks.ObjectInformatieObjectClient'
    )
    def test_informatieobject_invalid(self):
        zaak = ZaakFactory.create(zaaktype='https://example.com/foo/bar')
        zaak_url = reverse(zaak)

        url = reverse(ZaakInformatieObject)

        response = self.client.post(url, {
            'zaak': zaak_url,
            'informatieobject': 'https://drc.nl/api/v1'
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, 'informatieobject')
        self.assertEqual(validation_error['code'], URLValidator.code)
        self.assertEqual(validation_error['name'], 'informatieobject')


class FilterValidationTests(JWTAuthMixin, APITestCase):
    """
    Test that incorrect filter usage results in HTTP 400.
    """

    heeft_alle_autorisaties = True

    def test_zaak_invalid_filters(self):
        url = reverse('zaak-list')

        invalid_filters = {
            'zaaktype': '123',
            'bronorganisatie': '123',
            'foo': 'bar',
        }

        for key, value in invalid_filters.items():
            with self.subTest(query_param=key, value=value):
                response = self.client.get(url, {key: value}, **ZAAK_WRITE_KWARGS)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @skip('LIST action for /rollen is not supported')
    def test_rol_invalid_filters(self):
        url = reverse('rol-list')

        invalid_filters = {
            'zaak': '123',  # must be a url
            'betrokkene': '123',  # must be a url
            'betrokkeneType': 'not-a-valid-choice',  # must be a pre-defined choice
            'rolomschrijving': 'not-a-valid-choice',  # must be a pre-defined choice
            'foo': 'bar',
        }

        for key, value in invalid_filters.items():
            with self.subTest(query_param=key, value=value):
                response = self.client.get(url, {key: value})
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_status_invalid_filters(self):
        url = reverse('status-list')

        invalid_filters = {
            'zaak': '123',  # must be a url
            'statustype': '123',  # must be a url
            'foo': 'bar',
        }

        for key, value in invalid_filters.items():
            with self.subTest(query_param=key, value=value):
                response = self.client.get(url, {key: value})
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class StatusValidationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_200')
    def test_not_allowed_to_change_statustype(self):
        _status = StatusFactory.create()
        url = reverse(_status)

        response = self.client.patch(url, {
            "statustype": "https://ander.statustype.nl/foo/bar",
        })

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # validation_error = get_validation_errors(response, 'statustype')
        # self.assertEqual(validation_error['code'], IsImmutableValidator.code)

    @override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_200')
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_statustype_valid_resource(self, *mocks):
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak_url = reverse('zaak-detail', kwargs={'uuid': zaak.uuid})

        list_url = reverse('status-list')

        with mock_client(RESPONSES):
            response = self.client.post(list_url, {
                'zaak': zaak_url,
                'statustype': STATUSTYPE,
                'datumStatusGezet': isodatetime(2018, 10, 1, 10, 00, 00),
            })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_200')
    def test_statustype_invalid_resource(self, *mocks):
        responses = {
            STATUSTYPE: {
                'some': 'incorrect property'
            }
        }

        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak_url = reverse('zaak-detail', kwargs={'uuid': zaak.uuid})

        list_url = reverse('status-list')

        with mock_client(responses):
            response = self.client.post(list_url, {
                'zaak': zaak_url,
                'statustype': STATUSTYPE,
                'datumStatusGezet': isodatetime(2018, 10, 1, 10, 00, 00),
            })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, 'statustype')
        self.assertEqual(error['code'], 'invalid-resource')

    @override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_200')
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_statustype_zaaktype_mismatch(self, *mocks):
        responses = {
            STATUSTYPE: {
                'url': STATUSTYPE,
                'zaaktype': 'http://example.com/zaaktypen/1234',
                'volgnummer': 1,
                'isEindstatus': False
            }
        }

        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak_url = reverse('zaak-detail', kwargs={'uuid': zaak.uuid})

        list_url = reverse('status-list')

        with mock_client(responses):
            response = self.client.post(list_url, {
                'zaak': zaak_url,
                'statustype': STATUSTYPE,
                'datumStatusGezet': isodatetime(2018, 10, 1, 10, 00, 00),
            })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, 'nonFieldErrors')
        self.assertEqual(error['code'], 'zaaktype-mismatch')


class ResultaatValidationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_200')
    def test_not_allowed_to_change_resultaattype(self):
        resultaat = ResultaatFactory.create()
        url = reverse(resultaat)

        response = self.client.patch(url, {
            "resultaattype": "https://ander.resultaattype.nl/foo/bar",
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        validation_error = get_validation_errors(response, 'resultaattype')
        self.assertEqual(validation_error['code'], IsImmutableValidator.code)
