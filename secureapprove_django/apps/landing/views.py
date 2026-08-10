import re

from django.conf import settings
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt

from apps.authentication.approvals_api_serializers import normalize_parent_origin
from apps.authentication.models import SecurityProof
from apps.authentication.proof_service import verification_result_for_jws, verification_result_for_proof

class LandingPageView(TemplateView):
    """Landing page for SecureApprove"""
    template_name = 'landing/index.html'
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('requests:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'app_name': 'SecureApprove',
            # Never advertise proofs while issuance is disabled. This keeps the
            # marketing rollout fail-closed with the product rollout.
            'proof_marketing_enabled': (
                settings.SECUREAPPROVE_PROOF_ENABLED
                and settings.SECUREAPPROVE_PROOF_MARKETING_ENABLED
            ),
            'features': [
                {
                    'icon': 'bi-fingerprint',
                    'title': 'Autenticación Biométrica',
                    'description': 'Seguridad avanzada y autenticación biométrica'
                },
                {
                    'icon': 'bi-lightning',
                    'title': 'Tiempo Real',
                    'description': 'Notificaciones instantáneas y actualizaciones en tiempo real'
                },
                {
                    'icon': 'bi-lock',
                    'title': 'Seguridad Empresarial',
                    'description': 'Cumplimiento de estándares de seguridad'
                },
                {
                    'icon': 'bi-graph-up',
                    'title': 'Auditoría Completa',
                    'description': 'Trazabilidad completa y reportes detallados de actividad'
                },
                {
                    'icon': 'bi-phone',
                    'title': 'Multiplataforma',
                    'description': 'Compatible con PC, Android e iOS'
                },
                {
                    'icon': 'bi-chat-dots',
                    'title': 'Chat Integrado',
                    'description': 'Comunicación en tiempo real entre usuarios'
                }
            ]
        })
        return context


class ProofVerifierView(TemplateView):
    """Human-readable public verifier. Its result contains no private evidence or PII."""

    template_name = 'landing/proof_verify.html'

    def _context_for_id(self, proof_id):
        proof = SecurityProof.objects.select_related('signing_key').filter(pk=proof_id).first()
        if not proof:
            return {'result': {'valid': False, 'status': 'unknown'}}
        return {'result': verification_result_for_proof(proof), 'submitted_jws': proof.jws}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        proof_id = kwargs.get('proof_id')
        if proof_id:
            context.update(self._context_for_id(proof_id))
        return context

    def post(self, request, *args, **kwargs):
        jws = (request.POST.get('jws') or '').strip()
        context = self.get_context_data(**kwargs)
        context['submitted_jws'] = jws
        if not jws:
            context['result'] = {'valid': False, 'status': 'unknown'}
        elif len(jws.encode('utf-8')) > 16384:
            context['result'] = {'valid': False, 'status': 'altered', 'detail': 'Proof exceeds the 16 KB limit.'}
        else:
            context['result'] = verification_result_for_jws(jws)
        return self.render_to_response(context)

class DemoPageView(TemplateView):
    """Demo page showing sample approval request"""
    template_name = 'landing/demo.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Demo de solicitud de aprobación
        demo_request = {
            'title': 'Aprobar Compra de Equipos',
            'amount': '$2,500.00',
            'department': 'IT',
            'requestor': 'Juan Pérez',
            'date': '2024-01-15',
            'priority': 'Media',
            'description': 'Compra de 2 laptops para nuevos desarrolladores del equipo de IT.'
        }
        
        context['demo_request'] = demo_request
        return context

class TermsView(TemplateView):
    """Terms and Conditions page"""
    template_name = 'legal/terms.html'


class PrivacyView(TemplateView):
    """Privacy Policy page"""
    template_name = 'legal/privacy.html'


@method_decorator(xframe_options_exempt, name='dispatch')
class SecureApproveEmbedView(TemplateView):
    """Embeddable iframe endpoint for high-security biometric approval confirmation."""
    template_name = 'embed/secureapprove_iframe.html'

    def get(self, request, *args, **kwargs):
        try:
            parent_origin = normalize_parent_origin(request.GET.get('parent_origin', ''))
        except Exception:
            return HttpResponseBadRequest('Invalid parent_origin')

        nonce = request.GET.get('nonce', '')
        if not re.fullmatch(r'[0-9a-f]{32}', nonce):
            return HttpResponseBadRequest('Invalid nonce')

        response = super().get(request, *args, **kwargs)
        response['Cache-Control'] = 'no-store, max-age=0'
        response['Referrer-Policy'] = 'no-referrer'
        response['Permissions-Policy'] = 'publickey-credentials-get=*'
        response['Content-Security-Policy'] = (
            "default-src 'none'; "
            "script-src 'unsafe-inline'; "
            "style-src 'unsafe-inline'; "
            "connect-src 'self'; "
            "img-src 'self' data:; "
            f'frame-ancestors {parent_origin}'
        )
        return response
