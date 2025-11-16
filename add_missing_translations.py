#!/usr/bin/env python3
"""
Script para agregar TODAS las traducciones faltantes
"""

# INGLÉS
translations_en = {
    "Características Principales": "Key Features",
    "Tecnología avanzada para procesos de aprobación seguros y eficientes": "Advanced technology for secure and efficient approval processes",
    "Seguridad avanzada con WebAuthn y autenticación biométrica": "Advanced security with WebAuthn and biometric authentication",
    "Tiempo Real": "Real Time",
    "Notificaciones instantáneas y actualizaciones en tiempo real": "Instant notifications and real-time updates",
    "Seguridad Empresarial": "Enterprise Security",
    "Cifrado de 256-bit y cumplimiento de estándares de seguridad": "256-bit encryption and security standards compliance",
    "Trazabilidad completa y reportes detallados de actividad": "Complete traceability and detailed activity reports",
    "Disponibilidad": "Availability",
    "Tiempo de Respuesta": "Response Time",
    "Solicitudes Procesadas": "Requests Processed",
    "Cifrado": "Encryption",
    "Planes de Suscripción": "Subscription Plans",
    "Elige el plan que se adapta a tu equipo": "Choose the plan that fits your team",
    "Hasta 2 aprobadores": "Up to 2 approvers",
    "2 aprobadores": "2 approvers",
    "Solicitudes ilimitadas": "Unlimited requests",
    "Soporte básico": "Basic support",
    "Suscribirme": "Subscribe",
    "Popular": "Popular",
    "Hasta 6 aprobadores": "Up to 6 approvers",
    "6 aprobadores": "6 approvers",
    "Auditoría avanzada": "Advanced auditing",
    "Integraciones API": "API integrations",
    "Aprobadores ilimitados": "Unlimited approvers",
    "Integraciones premium": "Premium integrations",
    "¿Listo para transformar tus aprobaciones?": "Ready to transform your approvals?",
    "Únete a empresas que ya optimizaron sus procesos con SecureApprove": "Join companies that have already optimized their processes with SecureApprove",
    "Ver Planes": "View Plans",
    "Construido con ❤️ para la Seguridad Empresarial": "Built with ❤️ for Enterprise Security",
    "Todos los derechos reservados.": "All rights reserved.",
}

# PORTUGUÉS
translations_pt = {
    "Características Principales": "Características Principais",
    "Tecnología avanzada para procesos de aprobación seguros y eficientes": "Tecnologia avançada para processos de aprovação seguros e eficientes",
    "Seguridad avanzada con WebAuthn y autenticación biométrica": "Segurança avançada com WebAuthn e autenticação biométrica",
    "Tiempo Real": "Tempo Real",
    "Notificaciones instantáneas y actualizaciones en tiempo real": "Notificações instantâneas e atualizações em tempo real",
    "Seguridad Empresarial": "Segurança Empresarial",
    "Cifrado de 256-bit y cumplimiento de estándares de seguridad": "Criptografia de 256 bits e conformidade com padrões de segurança",
    "Trazabilidad completa y reportes detallados de actividad": "Rastreabilidade completa e relatórios detalhados de atividade",
    "Disponibilidad": "Disponibilidade",
    "Tiempo de Respuesta": "Tempo de Resposta",
    "Solicitudes Procesadas": "Solicitações Processadas",
    "Cifrado": "Criptografia",
    "Planes de Suscripción": "Planos de Assinatura",
    "Elige el plan que se adapta a tu equipo": "Escolha o plano que se adapta à sua equipe",
    "Hasta 2 aprobadores": "Até 2 aprovadores",
    "2 aprobadores": "2 aprovadores",
    "Solicitudes ilimitadas": "Solicitações ilimitadas",
    "Soporte básico": "Suporte básico",
    "Suscribirme": "Assinar",
    "Popular": "Popular",
    "Hasta 6 aprobadores": "Até 6 aprovadores",
    "6 aprobadores": "6 aprovadores",
    "Auditoría avanzada": "Auditoria avançada",
    "Integraciones API": "Integrações API",
    "Aprobadores ilimitados": "Aprovadores ilimitados",
    "Integraciones premium": "Integrações premium",
    "¿Listo para transformar tus aprobaciones?": "Pronto para transformar suas aprovações?",
    "Únete a empresas que ya optimizaron sus procesos con SecureApprove": "Junte-se a empresas que já otimizaram seus processos com o SecureApprove",
    "Ver Planes": "Ver Planos",
    "Construido con ❤️ para la Seguridad Empresarial": "Construído com ❤️ para Segurança Empresarial",
    "Todos los derechos reservados.": "Todos os direitos reservados.",
}

def add_missing_translations(filepath, translations):
    """Agrega traducciones faltantes al final del archivo .po"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Encontrar qué traducciones faltan
    missing = []
    for msgid, msgstr in translations.items():
        if f'msgid "{msgid}"' not in content:
            missing.append((msgid, msgstr))
    
    if not missing:
        print(f"✓ No hay traducciones faltantes en {filepath}")
        return
    
    # Agregar al final del archivo
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write('\n# === TRADUCCIONES ADICIONALES ===\n')
        for msgid, msgstr in missing:
            f.write(f'\nmsgid "{msgid}"\n')
            f.write(f'msgstr "{msgstr}"\n')
    
    print(f"✓ Agregadas {len(missing)} traducciones a {filepath}")

if __name__ == '__main__':
    import sys
    lang = sys.argv[1] if len(sys.argv) > 1 else 'all'
    
    if lang in ['en', 'all']:
        add_missing_translations('secureapprove_django/locale/en/LC_MESSAGES/django.po', translations_en)
    
    if lang in ['pt', 'all']:
        add_missing_translations('secureapprove_django/locale/pt_BR/LC_MESSAGES/django.po', translations_pt)
