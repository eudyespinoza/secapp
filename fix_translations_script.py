
import os

po_file = r"d:\OtherProyects\SecApp\secureapprove_django\locale\es\LC_MESSAGES\django.po"

with open(po_file, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Fix encoding issues
replacements = {
    "Informacin": "Información",
    "Configuracin": "Configuración",
    "categoras": "categorías",
    "permitirn": "permitirán",
    "personalizacin": "personalización",
    'msgstr "Role"': 'msgstr "Rol"',
}

for old, new in replacements.items():
    content = content.replace(old, new)

# Add missing translations
missing_translations = """

msgid "Approvers"
msgstr "Aprobadores"

msgid "Invite User"
msgstr "Invitar Usuario"

msgid "Invite"
msgstr "Invitar"

msgid "seats available"
msgstr "asientos disponibles"

msgid "Active Users"
msgstr "Usuarios Activos"

msgid "Pending Invitations"
msgstr "Invitaciones Pendientes"

msgid "Expires"
msgstr "Expira"

msgid "Cancel Invitation"
msgstr "Cancelar Invitación"

msgid "No users found."
msgstr "No se encontraron usuarios."

msgid "Invalid role selected."
msgstr "Rol seleccionado inválido."

msgid "User updated successfully."
msgstr "Usuario actualizado exitosamente."

msgid "Email is required to invite a user."
msgstr "El correo es obligatorio para invitar a un usuario."

msgid "You have reached the maximum number of users for your current seats. Please upgrade your subscription to add more users."
msgstr "Has alcanzado el número máximo de usuarios para tus asientos actuales. Por favor actualiza tu suscripción para agregar más usuarios."

msgid "Your current subscription does not allow adding more users this month."
msgstr "Tu suscripción actual no permite agregar más usuarios este mes."

msgid "Invitation created successfully for %(email)s."
msgstr "Invitación creada exitosamente para %(email)s."

msgid "Invitation updated for %(email)s."
msgstr "Invitación actualizada para %(email)s."

msgid "Invitation for %(email)s has been cancelled."
msgstr "La invitación para %(email)s ha sido cancelada."
"""

if 'msgid "Approvers"' not in content:
    content += missing_translations

with open(po_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Translations fixed and appended.")
