#!/usr/bin/env python3
"""
Script para traducir automáticamente las cadenas vacías en django.po
"""

translations = {
    # Títulos y páginas
    "SecureApprove - Sistema de Aprobaciones Seguras": "SecureApprove - Secure Approval System",
    "Sistema de aprobaciones seguras con autenticación biométrica": "Secure approval system with biometric authentication",
    "Sistema de Aprobaciones Seguras con Autenticación Biométrica": "Secure Approval System with Biometric Authentication",
    "Automatiza tus procesos de aprobación con seguridad de nivel empresarial y autenticación biométrica avanzada.": "Automate your approval processes with enterprise-level security and advanced biometric authentication.",
    
    # Botones y acciones
    "Comenzar Ahora": "Get Started Now",
    "Ver Demo": "View Demo",
    "Comenzar Gratis": "Start Free",
    "Suscribirme Ahora": "Subscribe Now",
    "Suscribirse": "Subscribe",
    "Volver": "Back",
    "Aprobar Solicitud": "Approve Request",
    "Rechazar": "Reject",
    "Solicitar Info": "Request Info",
    
    # Navegación
    "Características": "Features",
    "Precios": "Pricing",
    "Contacto": "Contact",
    "Entrar": "Sign In",
    "Iniciar Sesión": "Sign In",
    "Registrarse": "Sign Up",
    
    # Características
    "Autenticación Biométrica": "Biometric Authentication",
    "Seguridad de nivel empresarial con autenticación por huella dactilar, reconocimiento facial y llaves de seguridad.": "Enterprise-level security with fingerprint authentication, facial recognition, and security keys.",
    
    "Flujos Personalizables": "Customizable Workflows",
    "Crea flujos de aprobación adaptados a tus necesidades empresariales específicas.": "Create approval workflows tailored to your specific business needs.",
    
    "Auditoría Completa": "Complete Audit Trail",
    "Registro detallado de todas las acciones y decisiones para cumplimiento normativo.": "Detailed logging of all actions and decisions for regulatory compliance.",
    
    "Notificaciones en Tiempo Real": "Real-Time Notifications",
    "Mantén a tu equipo informado con notificaciones instantáneas de solicitudes pendientes.": "Keep your team informed with instant notifications of pending requests.",
    
    "Integración API": "API Integration",
    "Conecta SecureApprove con tus sistemas existentes a través de nuestra API REST.": "Connect SecureApprove with your existing systems through our REST API.",
    
    "Multi-tenancy": "Multi-tenancy",
    "Gestiona múltiples organizaciones desde una sola instalación de forma segura.": "Manage multiple organizations from a single installation securely.",
    
    # Planes
    "Planes y Precios": "Plans and Pricing",
    "Elige el plan perfecto para tu empresa": "Choose the perfect plan for your business",
    
    "Básico": "Basic",
    "Ideal para pequeños equipos": "Ideal for small teams",
    "Por usuario/mes": "Per user/month",
    "Usuarios": "Users",
    "Solicitudes/mes": "Requests/month",
    "Autenticación biométrica": "Biometric authentication",
    "Soporte por email": "Email support",
    
    "Profesional": "Professional",
    "Para empresas en crecimiento": "For growing businesses",
    "Ilimitado": "Unlimited",
    "Flujos personalizados": "Custom workflows",
    "API REST": "REST API",
    "Soporte prioritario": "Priority support",
    "Más Popular": "Most Popular",
    
    "Empresarial": "Enterprise",
    "Para grandes organizaciones": "For large organizations",
    "Soporte 24/7": "24/7 support",
    "Gerente de cuenta dedicado": "Dedicated account manager",
    "SLA garantizado": "Guaranteed SLA",
    
    # Testimonios
    "Lo que dicen nuestros clientes": "What our customers say",
    
    # Footer
    "Producto": "Product",
    "Recursos": "Resources",
    "Legal": "Legal",
    "Documentación": "Documentation",
    "Blog": "Blog",
    "Privacidad": "Privacy",
    "Términos": "Terms",
    "Todos los derechos reservados": "All rights reserved",
    
    # Demo
    "Demo - SecureApprove": "Demo - SecureApprove",
    "Demostración Interactiva": "Interactive Demo",
    "Esta es una demo de cómo funciona el proceso de aprobación en SecureApprove. Los botones son interactivos para simular la experiencia real.": "This is a demo of how the approval process works in SecureApprove. The buttons are interactive to simulate the real experience.",
    
    "Compra de Equipos de Oficina": "Office Equipment Purchase",
    "Pendiente": "Pending",
    "Prioridad": "Priority",
    "Media": "Medium",
    "SOLICITANTE": "REQUESTER",
    "Ana García": "Ana García",
    "DEPARTAMENTO": "DEPARTMENT",
    "Recursos Humanos": "Human Resources",
    "DESCRIPCIÓN": "DESCRIPTION",
    "Solicitud para la compra de 3 sillas ergonómicas y 2 escritorios ajustables para el nuevo equipo de trabajo remoto. Los equipos actuales no cumplen con los estándares ergonómicos necesarios para el trabajo prolongado.": "Request for the purchase of 3 ergonomic chairs and 2 adjustable desks for the new remote work team. Current equipment does not meet the necessary ergonomic standards for prolonged work.",
    
    "DOCUMENTOS ADJUNTOS": "ATTACHED DOCUMENTS",
    
    "¿Te gusta lo que ves?": "Do you like what you see?",
    "Comienza a gestionar tus aprobaciones de manera profesional": "Start managing your approvals professionally",
    
    # Mensajes de resultado
    "¡Solicitud Aprobada!": "Request Approved!",
    "La solicitud ha sido aprobada exitosamente. Se ha enviado notificación al solicitante y se procederá con la compra.": "The request has been successfully approved. Notification has been sent to the requester and the purchase will proceed.",
    
    "Solicitud Rechazada": "Request Rejected",
    "La solicitud ha sido rechazada. Se ha enviado notificación al solicitante con los motivos del rechazo.": "The request has been rejected. Notification has been sent to the requester with the reasons for rejection.",
    
    "Información Solicitada": "Information Requested",
    "Se ha enviado una solicitud de información adicional al solicitante. La aprobación quedará pendiente hasta recibir los datos necesarios.": "A request for additional information has been sent to the requester. Approval will remain pending until the necessary data is received.",
    
    # Temas
    "Claro": "Light",
    "Oscuro": "Dark",
    "Sistema": "System",
    
    # Common
    "SecureApprove": "SecureApprove",
    "Dashboard": "Dashboard",
    "Panel de Control": "Dashboard",
    "Solicitudes": "Requests",
    "Requests": "Requests",
    "Nueva Solicitud": "New Request",
    "Todas las Solicitudes": "All Requests",
    "Mis Solicitudes": "My Requests",
    "Bienvenido de vuelta": "Welcome back",
    "Aprobado": "Approved",
    "Rechazado": "Rejected",
    "Perfil": "Profile",
    "Cerrar Sesión": "Sign Out",
    "Sistema de aprobaciones seguras para empresas modernas.": "Secure approval system for modern businesses.",
}

def fix_po_file(filepath):
    """Rellena los msgstr vacíos con las traducciones"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    output = []
    i = 0
    changes = 0
    
    while i < len(lines):
        line = lines[i]
        output.append(line)
        
        # Buscar msgid
        if line.startswith('msgid "') and not line.startswith('msgid ""'):
            # Extraer el texto del msgid (puede ser multilínea)
            msgid_text = line[7:-2]  # Quitar 'msgid "' y '"\n'
            
            # Manejar msgid multilínea
            j = i + 1
            while j < len(lines) and lines[j].startswith('"'):
                msgid_text += lines[j][1:-2]
                output.append(lines[j])
                j += 1
            
            # Verificar si el siguiente es msgstr vacío
            if j < len(lines) and lines[j].startswith('msgstr ""'):
                if msgid_text in translations:
                    # Reemplazar con la traducción
                    output.append(f'msgstr "{translations[msgid_text]}"\n')
                    changes += 1
                    i = j + 1
                    continue
        
        i += 1
    
    # Escribir el archivo
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(output)
    
    print(f"✓ Archivo procesado: {filepath}")
    print(f"  {changes} traducciones agregadas")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        fix_po_file(sys.argv[1])
    else:
        print("Uso: python fix_translations.py <archivo.po>")
