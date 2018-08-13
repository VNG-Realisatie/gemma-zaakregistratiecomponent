import uuid
from datetime import date

from django.contrib.gis.db.models import GeometryField
from django.db import models
from django.utils.crypto import get_random_string

from zds_schema.constants import (
    RolOmschrijving, RolOmschrijvingGeneriek, RolTypes
)
from zds_schema.fields import RSINField
from zds_schema.validators import alphanumeric_excluding_diacritic

from .constants import ZaakobjectTypes


class Zaak(models.Model):
    """
    Modelleer de structuur van een ZAAK.

    Een samenhangende hoeveelheid werk met een welgedefinieerde aanleiding
    en een welgedefinieerd eindresultaat, waarvan kwaliteit en doorlooptijd
    bewaakt moeten worden.
    """
    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4,
        help_text="Unieke resource identifier (UUID4)"
    )
    zaakidentificatie = models.CharField(
        max_length=40, unique=True, blank=True,
        help_text='De unieke identificatie van de ZAAK binnen de organisatie die '
                  'verantwoordelijk is voor de behandeling van de ZAAK.',
        validators=[alphanumeric_excluding_diacritic]
    )
    bronorganisatie = RSINField(help_text='Het RSIN van de Niet-natuurlijk persoon zijnde de '
                                          'organisatie die de zaak heeft gecreeerd.')
    zaaktype = models.URLField(help_text="URL naar het zaaktype in de CATALOGUS waar deze voorkomt")
    registratiedatum = models.DateField(
        help_text='De datum waarop de zaakbehandelende organisatie de ZAAK heeft '
                  'geregistreerd. Indien deze niet opgegeven wordt, wordt de '
                  'datum van vandaag gebruikt.',
        default=date.today
    )

    startdatum = models.DateField(help_text='De datum waarop met de uitvoering van de zaak is gestart')
    einddatum = models.DateField(
        blank=True, null=True,
        help_text='De datum waarop de uitvoering van de zaak afgerond is.',
    )
    einddatum_gepland = models.DateField(
        blank=True, null=True,
        help_text='De datum waarop volgens de planning verwacht wordt dat de zaak afgerond wordt.',
    )

    toelichting = models.TextField(
        max_length=1000, blank=True,
        help_text='Een toelichting op de zaak.'
    )
    zaakgeometrie = GeometryField(
        blank=True, null=True,
        help_text="Punt, lijn of (multi-)vlak geometrie-informatie."
    )

    class Meta:
        verbose_name = 'zaak'
        verbose_name_plural = 'zaken'
        unique_together = ('bronorganisatie', 'zaakidentificatie')

    def __str__(self):
        return self.zaakidentificatie

    def save(self, *args, **kwargs):
        if not self.zaakidentificatie:
            self.zaakidentificatie = str(uuid.uuid4())
        super().save(*args, **kwargs)

    @property
    def current_status_uuid(self):
        status = self.status_set.order_by('-datum_status_gezet').first()
        return status.uuid if status else None


class Status(models.Model):
    """
    Modelleer een status van een ZAAK.

    Een aanduiding van de stand van zaken van een ZAAK op basis van
    betekenisvol behaald resultaat voor de initiator van de ZAAK.
    """
    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4,
        help_text="Unieke resource identifier (UUID4)"
    )
    # relaties
    zaak = models.ForeignKey('Zaak', on_delete=models.CASCADE)
    status_type = models.URLField()

    # extra informatie
    datum_status_gezet = models.DateTimeField(
        help_text='De datum waarop de ZAAK de status heeft verkregen.'
    )
    statustoelichting = models.TextField(
        max_length=1000, blank=True,
        help_text='Een, voor de initiator van de zaak relevante, toelichting '
                  'op de status van een zaak.'
    )

    class Meta:
        verbose_name = 'status'
        verbose_name_plural = 'statussen'

    def __str__(self):
        return "Status op {}".format(self.datum_status_gezet)


class Rol(models.Model):
    """
    Modelleer de rol van een BETROKKENE bij een ZAAK.

    Een of meerdere BETROKKENEn hebben een of meerdere ROL(len) in een ZAAK.
    """
    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4,
        help_text="Unieke resource identifier (UUID4)"
    )
    zaak = models.ForeignKey('Zaak', on_delete=models.CASCADE)
    betrokkene = models.URLField(help_text="Een betrokkene gerelateerd aan een zaak")
    betrokkene_type = models.CharField(max_length=100, choices=RolTypes.choices)

    rolomschrijving = models.CharField(
        max_length=80, choices=RolOmschrijving.choices,
        help_text='Algemeen gehanteerde benaming van de aard van de ROL'
    )
    rolomschrijving_generiek = models.CharField(
        max_length=40, choices=RolOmschrijvingGeneriek.choices,
        help_text='Algemeen gehanteerde benaming van de aard van de ROL'
    )
    roltoelichting = models.TextField(max_length=1000)

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Rollen"


class ZaakObject(models.Model):
    """
    Modelleer een object behorende bij een ZAAK.

    Het OBJECT in kwestie kan in verschillende andere componenten leven,
    zoals het RSGB.
    """
    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4,
        help_text="Unieke resource identifier (UUID4)"
    )
    zaak = models.ForeignKey('Zaak', on_delete=models.CASCADE)
    object = models.URLField(help_text='URL naar de resource die het OBJECT beschrijft.')
    relatieomschrijving = models.CharField(
        max_length=80, blank=True,
        help_text='Omschrijving van de betrekking tussen de ZAAK en het OBJECT.'
    )
    object_type = models.CharField(
        max_length=100,
        choices=ZaakobjectTypes.choices,
        help_text="Beschrijft het type object gerelateerd aan de zaak"
    )

    class Meta:
        verbose_name = 'zaakobject'
        verbose_name_plural = 'zaakobjecten'


class ZaakEigenschap(models.Model):
    """
    Een relevant inhoudelijk gegeven waarvan waarden bij
    ZAAKen van eenzelfde ZAAKTYPE geregistreerd moeten
    kunnen worden en dat geen standaard kenmerk is van een
    ZAAK.

    Het RGBZ biedt generieke kenmerken van zaken. Bij zaken van een bepaald zaaktype kan de
    behoefte bestaan om waarden uit te wisselen van gegevens die specifiek zijn voor die zaken. Met
    dit groepattribuutsoort simuleren we de aanwezigheid van dergelijke eigenschappen. Aangezien
    deze eigenschappen specifiek zijn per zaaktype, modelleren we deze eigenschappen hier niet
    specifiek. De eigenschappen worden per zaaktype in een desbetreffende zaaktypecatalogus
    gespecificeerd.
    """
    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4,
        help_text="Unieke resource identifier (UUID4)"
    )
    zaak = models.ForeignKey('Zaak', on_delete=models.CASCADE)
    eigenschap = models.URLField(help_text="URL naar de eigenschap in het ZTC")
    # TODO - validatie _zou kunnen_ de configuratie van ZTC uitlezen om input
    # te valideren, en per eigenschap een specifiek datatype terug te geven.
    # In eerste instantie laten we het aan de client over om validatie en
    # type-conversie te doen.
    waarde = models.TextField()

    class Meta:
        verbose_name = 'zaakeigenschap'
        verbose_name_plural = 'zaakeigenschappen'


class KlantContact(models.Model):
    """
    Modelleer het contact tussen een medewerker en een klant.

    Een uniek en persoonlijk contact van een burger of bedrijfsmedewerker met
    een MEDEWERKER van de zaakbehandelende organisatie over een onderhanden of
    afgesloten ZAAK.
    """
    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4,
        help_text="Unieke resource identifier (UUID4)"
    )
    zaak = models.ForeignKey('Zaak', on_delete=models.CASCADE)
    identificatie = models.CharField(
        max_length=14, unique=True,
        help_text='De unieke aanduiding van een KLANTCONTACT'
    )
    datumtijd = models.DateTimeField(
        help_text='De datum en het tijdstip waarop het KLANTCONTACT begint'
    )
    kanaal = models.CharField(
        blank=True, max_length=20,
        help_text='Het communicatiekanaal waarlangs het KLANTCONTACT gevoerd wordt'
    )

    class Meta:
        verbose_name = "klantcontact"
        verbose_name_plural = "klantcontacten"

    def __str__(self):
        return self.identificatie

    def save(self, *args, **kwargs):
        if not self.identificatie:
            gen_id = True
            while gen_id:
                identificatie = get_random_string(length=12)
                gen_id = self.__class__.objects.filter(identificatie=identificatie).exists()
            self.identificatie = identificatie
        super().save(*args, **kwargs)
