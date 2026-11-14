from django.test import TestCase

from platforms.models import PlatformIntegration
from platforms.tests.factories import make_institution, make_integration, make_platform


class PlatformModelTests(TestCase):
    def test_platform_institution_integration_relationships(self):
        platform = make_platform()
        institution = make_institution()
        integration = make_integration(platform=platform, institution=institution)
        self.assertEqual(integration.platform, platform)
        self.assertEqual(integration.institution, institution)
        self.assertEqual(platform.integrations.count(), 1)
        self.assertEqual(institution.integrations.count(), 1)
        self.assertNotEqual(integration.api_key_hash, integration.raw_api_key)
        self.assertTrue(integration.api_key_hash)
        self.assertFalse(hasattr(PlatformIntegration, "api_key"))
