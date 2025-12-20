#!/usr/bin/env python
"""Fix missing translations in Spanish locale file."""
import re

# Diccionario de traducciones faltantes
TRANSLATIONS = {
    "Completed": "Completado",
    "Small Team": "Equipo Pequeño",
    "Large Team": "Equipo Grande",
    "User already exists. Please log in.": "El usuario ya existe. Por favor inicie sesión.",
    "You already have a pending invitation. Please register.": "Ya tiene una invitación pendiente. Por favor regístrese.",
    "Optional title for group conversations": "Título opcional para conversaciones grupales",
    "True for group conversations, False for 1-to-1": "Verdadero para conversaciones grupales, Falso para 1 a 1",
    "Cache of last message for quick access": "Caché del último mensaje para acceso rápido",
    "Last message this user has read": "Último mensaje que este usuario ha leído",
    "Is Archived": "Está Archivado",
    "User has archived this conversation": "El usuario ha archivado esta conversación",
    "Is Muted": "Está Silenciado",
    "Delivered": "Entregado",
    "Read": "Leído",
    "Message text content": "Contenido de texto del mensaje",
    "Aggregated delivery status": "Estado de entrega agregado",
    "File": "Archivo",
    "Content Type": "Tipo de Contenido",
    "Size (bytes)": "Tamaño (bytes)",
    "Chat Message Delivery": "Entrega de Mensaje de Chat",
    "Chat Message Deliveries": "Entregas de Mensajes de Chat",
    "Computed field: online if last_activity is recent": "Campo calculado: en línea si last_activity es reciente",
    "User Presence": "Presencia de Usuario",
    "User Presences": "Presencias de Usuario",
    "Category-specific data: vendor, cost_center, destination, etc.": "Datos específicos de categoría: proveedor, centro de costos, destino, etc.",
    "File Size": "Tamaño del Archivo",
    "Accepted": "Aceptada",
    "Token": "Token",
    "Display name for this approval type": "Nombre a mostrar para este tipo de aprobación",
    "Icon": "Ícono",
    "Bootstrap Icons class (e.g., bi-cash, bi-cart)": "Clase de Bootstrap Icons (ej. bi-cash, bi-cart)",
    "Color": "Color",
    "Bootstrap color class (primary, success, warning, danger, info)": "Clase de color Bootstrap (primary, success, warning, danger, info)",
    "Whether this approval type is available for new requests": "Si este tipo de aprobación está disponible para nuevas solicitudes",
    "True if this is a custom type created by the tenant": "Verdadero si este es un tipo personalizado creado por el inquilino",
    "Number of approvers required to approve requests of this type": "Número de aprobadores requeridos para aprobar solicitudes de este tipo",
    "Specific users who can approve this type. Leave empty for any approver.": "Usuarios específicos que pueden aprobar este tipo. Deje vacío para cualquier aprobador.",
    "Cannot delete last active credential. Register another device first.": "No se puede eliminar la última credencial activa. Registre otro dispositivo primero.",
    "Cannot deactivate last active credential.": "No se puede desactivar la última credencial activa.",
    "deactivated": "desactivada",
    'Invalid action. Must be "approve" or "reject".': 'Acción inválida. Debe ser "aprobar" o "rechazar".',
    # Textos de requests
    "Your biometric step-up authentication failed or was cancelled before approving. Please try again.": "Su autenticación biométrica adicional falló o fue cancelada antes de aprobar. Por favor intente de nuevo.",
    "Your biometric step-up authentication failed or was cancelled before rejecting. Please try again.": "Su autenticación biométrica adicional falló o fue cancelada antes de rechazar. Por favor intente de nuevo.",
    # Otros faltantes comunes
    "No active credential found": "No se encontró credencial activa",
    "activated": "activada",
    "Approval Audits": "Auditorías de Aprobación",
    # UI importante
    "Extra Fields": "Campos Adicionales",
    "Sort Order": "Orden de Clasificación",
    "Order in which this type appears in lists": "Orden en que este tipo aparece en las listas",
    "Cannot delete default approval types. You can disable them instead.": "No se pueden eliminar los tipos de aprobación predeterminados. Puede deshabilitarlos en su lugar.",
    "This tenant has no available seats. Please contact the administrator.": "Este inquilino no tiene asientos disponibles. Por favor contacte al administrador.",
    "OK": "Aceptar",
    "Sign in to access your approval workflow dashboard": "Inicie sesión para acceder a su panel de flujo de aprobaciones",
    "WebAuthn is not fully implemented yet. Please use email/password login.": "WebAuthn aún no está completamente implementado. Por favor use inicio de sesión con email/contraseña.",
    "Added": "Añadido",
    "Add a biometric device to enhance your account security": "Añada un dispositivo biométrico para mejorar la seguridad de su cuenta",
    "Pairing link": "Enlace de emparejamiento",
    "This name will be displayed in chats and other interactions.": "Este nombre se mostrará en chats y otras interacciones.",
    "Email address cannot be changed.": "La dirección de email no se puede cambiar.",
    "Please use your fingerprint, Face ID, or security key to sign in": "Por favor use su huella digital, Face ID, o llave de seguridad para iniciar sesión",
    "John Doe": "Juan Pérez",
    "john@company.com": "juan@empresa.com",
    "Your Trial is Ready!": "¡Su Prueba está Lista!",
    "We have created your account and workspace.": "Hemos creado su cuenta y espacio de trabajo.",
    "Please proceed to registration to set up your biometric credentials.": "Por favor proceda al registro para configurar sus credenciales biométricas.",
    "Monitor and analyze usage patterns to improve user experience.": "Monitorear y analizar patrones de uso para mejorar la experiencia del usuario.",
    "To comply with legal obligations or respond to lawful requests.": "Para cumplir con obligaciones legales o responder a solicitudes legales.",
    "Access controls and authentication requirements for our systems.": "Controles de acceso y requisitos de autenticación para nuestros sistemas.",
}

def fix_translations(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    changes_made = 0
    
    for msgid, msgstr in TRANSLATIONS.items():
        # Escapar caracteres especiales para regex
        escaped_msgid = re.escape(msgid)
        
        # Buscar el patrón: msgid "texto"\nmsgstr ""
        pattern = rf'(msgid "{escaped_msgid}"\n)msgstr ""'
        replacement = rf'\1msgstr "{msgstr}"'
        
        new_content, count = re.subn(pattern, replacement, content)
        if count > 0:
            content = new_content
            changes_made += count
            print(f"✓ Translated: {msgid[:50]}...")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n✓ {changes_made} translations added/fixed")

if __name__ == '__main__':
    import sys
    filepath = sys.argv[1] if len(sys.argv) > 1 else 'secureapprove_django/locale/es/LC_MESSAGES/django.po'
    fix_translations(filepath)
