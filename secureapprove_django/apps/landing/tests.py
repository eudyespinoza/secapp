from django.test import TestCase, override_settings


class AnimatedProofDemoTests(TestCase):
    def test_demo_exposes_accessible_five_step_walkthrough(self):
        response = self.client.get('/en/demo/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Watch a secure approval become verifiable evidence')
        self.assertContains(response, 'data-step="', count=5)
        self.assertContains(response, 'role="progressbar"')
        self.assertContains(response, 'aria-live="polite"')
        self.assertContains(response, 'prefers-reduced-motion: reduce')
        self.assertContains(
            response,
            'This simulation does not create a real approval or request biometric data.',
        )

    def test_demo_is_translated_to_spanish_and_portuguese(self):
        spanish = self.client.get('/es/demo/')
        self.assertContains(
            spanish,
            'Mira cómo una aprobación segura se convierte en evidencia verificable',
        )
        self.assertContains(spanish, 'Esta simulación no crea una aprobación real')

        portuguese = self.client.get('/pt-br/demo/')
        self.assertContains(
            portuguese,
            'Veja uma aprovação segura se transformar em evidência verificável',
        )
        self.assertContains(portuguese, 'Esta simulação não cria uma aprovação real')

    @override_settings(
        SECUREAPPROVE_PROOF_ENABLED=True,
        SECUREAPPROVE_PROOF_MARKETING_ENABLED=True,
    )
    def test_landing_exposes_demo_and_public_verifier(self):
        response = self.client.get('/en/')

        self.assertContains(response, 'href="/en/demo/"')
        self.assertContains(response, 'Watch animated demo')
        self.assertContains(response, 'href="/en/verify/"')
        self.assertContains(response, 'Verify a proof')
