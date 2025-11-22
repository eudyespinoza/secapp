from django.shortcuts import render, redirect
from django.views.generic import TemplateView

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
            'features': [
                {
                    'icon': 'bi-fingerprint',
                    'title': 'Autenticación Biométrica',
                    'description': 'Seguridad avanzada con WebAuthn y autenticación biométrica'
                },
                {
                    'icon': 'bi-lightning',
                    'title': 'Tiempo Real',
                    'description': 'Notificaciones instantáneas y actualizaciones en tiempo real'
                },
                {
                    'icon': 'bi-lock',
                    'title': 'Seguridad Empresarial',
                    'description': 'Cifrado de 256-bit y cumplimiento de estándares de seguridad'
                },
                {
                    'icon': 'bi-graph-up',
                    'title': 'Auditoría Completa',
                    'description': 'Trazabilidad completa y reportes detallados de actividad'
                }
            ]
        })
        return context

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