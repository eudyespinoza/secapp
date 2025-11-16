#!/usr/bin/env python3
"""
Script para corregir TODAS las traducciones en los archivos .po
"""

# DICCIONARIO COMPLETO DE TRADUCCIONES INGLÉS
all_translations_en = {
    # Ya existentes
    "Dashboard": "Dashboard",
    "Welcome back": "Welcome back",
    "Requests": "Requests",
    "New Request": "New Request",
    "Pending": "Pending",
    "Approved": "Approved",
    "Rejected": "Rejected",
    "SecureApprove - Sistema de Aprobaciones Seguras": "SecureApprove - Secure Approval System",
    "Sistema de aprobaciones seguras con autenticación biométrica": "Secure approval system with biometric authentication",
    "Sistema de Aprobaciones Seguras con Autenticación Biométrica": "Secure Approval System with Biometric Authentication",
    "Automatiza tus procesos de aprobación con seguridad de nivel empresarial y autenticación biométrica avanzada.": "Automate your approval processes with enterprise-level security and advanced biometric authentication.",
    "Comenzar Ahora": "Get Started Now",
    "Ver Demo": "View Demo",
    "Autenticación Biométrica": "Biometric Authentication",
    
    # Nuevas - Landing page
    "Características Principales": "Key Features",
    "Tecnología avanzada para procesos de aprobación seguros y eficientes": "Advanced technology for secure and efficient approval processes",
    "Seguridad avanzada con WebAuthn y autenticación biométrica": "Advanced security with WebAuthn and biometric authentication",
    "Tiempo Real": "Real Time",
    "Notificaciones instantáneas y actualizaciones en tiempo real": "Instant notifications and real-time updates",
    "Seguridad Empresarial": "Enterprise Security",
    "Cifrado de 256-bit y cumplimiento de estándares de seguridad": "256-bit encryption and security standards compliance",
    "Auditoría Completa": "Complete Audit Trail",
    "Trazabilidad completa y reportes detallados de actividad": "Complete traceability and detailed activity reports",
    "Disponibilidad": "Availability",
    "Tiempo de Respuesta": "Response Time",
    "Solicitudes Procesadas": "Requests Processed",
    "Cifrado": "Encryption",
    
    # Planes
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
    "Soporte prioritario": "Priority support",
    
    # CTA
    "¿Listo para transformar tus aprobaciones?": "Ready to transform your approvals?",
    "Únete a empresas que ya optimizaron sus procesos con SecureApprove": "Join companies that have already optimized their processes with SecureApprove",
    "Ver Planes": "View Plans",
    "Sistema de aprobaciones seguras para empresas modernas.": "Secure approval system for modern businesses.",
    "Construido con ❤️ para la Seguridad Empresarial": "Built with ❤️ for Enterprise Security",
    "Todos los derechos reservados.": "All rights reserved.",
}

# PORTUGUÉS
all_translations_pt = {
    "Dashboard": "Painel",
    "Welcome back": "Bem-vindo de volta",
    "Requests": "Solicitações",
    "New Request": "Nova Solicitação",
    "Pending": "Pendente",
    "Approved": "Aprovado",
    "Rejected": "Rejeitado",
    "SecureApprove - Sistema de Aprobaciones Seguras": "SecureApprove - Sistema de Aprovações Seguras",
    "Sistema de aprobaciones seguras con autenticación biométrica": "Sistema de aprovações seguras com autenticação biométrica",
    "Sistema de Aprobaciones Seguras con Autenticación Biométrica": "Sistema de Aprovações Seguras com Autenticação Biométrica",
    "Automatiza tus procesos de aprobación con seguridad de nivel empresarial y autenticación biométrica avanzada.": "Automatize seus processos de aprovação com segurança de nível empresarial e autenticação biométrica avançada.",
    "Comenzar Ahora": "Começar Agora",
    "Ver Demo": "Ver Demo",
    "Autenticación Biométrica": "Autenticação Biométrica",
    
    # Landing page
    "Características Principales": "Características Principais",
    "Tecnología avanzada para procesos de aprobación seguros y eficientes": "Tecnologia avançada para processos de aprovação seguros e eficientes",
    "Seguridad avanzada con WebAuthn y autenticación biométrica": "Segurança avançada com WebAuthn e autenticação biométrica",
    "Tiempo Real": "Tempo Real",
    "Notificaciones instantáneas y actualizaciones en tiempo real": "Notificações instantâneas e atualizações em tempo real",
    "Seguridad Empresarial": "Segurança Empresarial",
    "Cifrado de 256-bit y cumplimiento de estándares de seguridad": "Criptografia de 256 bits e conformidade com padrões de segurança",
    "Auditoría Completa": "Auditoria Completa",
    "Trazabilidad completa y reportes detallados de actividad": "Rastreabilidade completa e relatórios detalhados de atividade",
    "Disponibilidad": "Disponibilidade",
    "Tiempo de Respuesta": "Tempo de Resposta",
    "Solicitudes Procesadas": "Solicitações Processadas",
    "Cifrado": "Criptografia",
    
    # Planes
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
    "Soporte prioritario": "Suporte prioritário",
    
    # CTA
    "¿Listo para transformar tus aprobaciones?": "Pronto para transformar suas aprovações?",
    "Únete a empresas que ya optimizaron sus procesos con SecureApprove": "Junte-se a empresas que já otimizaram seus processos com o SecureApprove",
    "Ver Planes": "Ver Planos",
    "Sistema de aprobaciones seguras para empresas modernas.": "Sistema de aprovações seguras para empresas modernas.",
    "Construido con ❤️ para la Seguridad Empresarial": "Construído com ❤️ para Segurança Empresarial",
    "Todos los derechos reservados.": "Todos os direitos reservados.",
}

def fix_all_translations(filepath, translations):
    """Corrige TODAS las traducciones en el archivo .po"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    output = []
    i = 0
    fixed = 0
    
    while i < len(lines):
        line = lines[i]
        output.append(line)
        
        # Buscar msgid
        if line.startswith('msgid "') and not line.startswith('msgid ""'):
            # Extraer el texto del msgid
            msgid_text = line[7:-2]  # Quitar 'msgid "' y '"\n'
            
            # Manejar msgid multilínea
            j = i + 1
            while j < len(lines) and lines[j].startswith('"'):
                msgid_text += lines[j][1:-2]
                output.append(lines[j])
                j += 1
            
            # Verificar el msgstr siguiente
            if j < len(lines) and lines[j].startswith('msgstr'):
                if msgid_text in translations:
                    # Reemplazar con la traducción correcta
                    output.append(f'msgstr "{translations[msgid_text]}"\n')
                    fixed += 1
                    i = j + 1
                    continue
                else:
                    # Mantener el msgstr existente
                    output.append(lines[j])
                    i = j + 1
                    continue
        
        i += 1
    
    # Escribir el archivo
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(output)
    
    print(f"✓ Archivo corregido: {filepath}")
    print(f"  {fixed} traducciones corregidas/actualizadas")

if __name__ == '__main__':
    print("Corrigiendo traducciones de inglés...")
    fix_all_translations('secureapprove_django/locale/en/LC_MESSAGES/django.po', all_translations_en)
    
    print("\nCorrigiendo traducciones de portugués...")
    fix_all_translations('secureapprove_django/locale/pt_BR/LC_MESSAGES/django.po', all_translations_pt)
    
    print("\n✅ HECHO! Ahora copia los archivos al contenedor y compila.")
