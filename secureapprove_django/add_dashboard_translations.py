#!/usr/bin/env python
"""Add missing translations for the dashboard page."""
import polib
import os

# Translations for the dashboard
TRANSLATIONS = {
    # Dashboard header
    "Dashboard": {"es": "Panel de Control", "pt_BR": "Painel de Controle"},
    "Welcome back": {"es": "Bienvenido de nuevo", "pt_BR": "Bem-vindo de volta"},
    "Here's what's happening with your requests.": {"es": "Esto es lo que está pasando con tus solicitudes.", "pt_BR": "Veja o que está acontecendo com suas solicitações."},
    
    # Quick actions
    "New Request": {"es": "Nueva Solicitud", "pt_BR": "Nova Solicitação"},
    "Review Pending": {"es": "Revisar Pendientes", "pt_BR": "Revisar Pendentes"},
    "View Approved": {"es": "Ver Aprobadas", "pt_BR": "Ver Aprovadas"},
    "All Requests": {"es": "Todas las Solicitudes", "pt_BR": "Todas as Solicitações"},
    
    # Stats
    "Total": {"es": "Total", "pt_BR": "Total"},
    "Pending": {"es": "Pendiente", "pt_BR": "Pendente"},
    "Approved": {"es": "Aprobado", "pt_BR": "Aprovado"},
    "Cancelled": {"es": "Cancelado", "pt_BR": "Cancelado"},
    "My Requests": {"es": "Mis Solicitudes", "pt_BR": "Minhas Solicitações"},
    
    # Charts
    "Requests by Category": {"es": "Solicitudes por Categoría", "pt_BR": "Solicitações por Categoria"},
    "Last 30 days": {"es": "Últimos 30 días", "pt_BR": "Últimos 30 dias"},
    "Activity Timeline": {"es": "Línea de Tiempo de Actividad", "pt_BR": "Linha do Tempo de Atividade"},
    
    # Sidebar
    "Pending Approvals": {"es": "Aprobaciones Pendientes", "pt_BR": "Aprovações Pendentes"},
    "View All Pending": {"es": "Ver Todas las Pendientes", "pt_BR": "Ver Todas as Pendentes"},
    "Recent Requests": {"es": "Solicitudes Recientes", "pt_BR": "Solicitações Recentes"},
    "No requests yet": {"es": "Sin solicitudes aún", "pt_BR": "Ainda sem solicitações"},
    "ago": {"es": "atrás", "pt_BR": "atrás"},
    
    # JS translations
    "Just now": {"es": "Justo ahora", "pt_BR": "Agora mesmo"},
    "General": {"es": "General", "pt_BR": "Geral"},
    "Other": {"es": "Otro", "pt_BR": "Outro"},
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def add_translations_to_po(lang_code, translations):
    """Add translations to a PO file."""
    if lang_code == "en":
        return 0
    
    po_path = os.path.join(BASE_DIR, "locale", lang_code, "LC_MESSAGES", "django.po")
    
    if not os.path.exists(po_path):
        print(f"PO file not found: {po_path}")
        return 0
    
    po = polib.pofile(po_path)
    added = 0
    updated = 0
    
    for msgid, trans_dict in translations.items():
        trans = trans_dict.get(lang_code, "")
        if not trans:
            continue
        
        existing = po.find(msgid)
        
        if existing:
            if not existing.msgstr or existing.msgstr == msgid:
                existing.msgstr = trans
                if 'fuzzy' in existing.flags:
                    existing.flags.remove('fuzzy')
                updated += 1
                print(f"  [UPDATED] {msgid[:40]}...")
        else:
            entry = polib.POEntry(
                msgid=msgid,
                msgstr=trans,
            )
            po.append(entry)
            added += 1
            print(f"  [ADDED] {msgid[:40]}...")
    
    if added > 0 or updated > 0:
        po.save()
        print(f"  Saved: {added} added, {updated} updated")
    
    return added + updated


def add_english_entries(strings):
    """Add English entries."""
    po_path = os.path.join(BASE_DIR, "locale", "en", "LC_MESSAGES", "django.po")
    
    if not os.path.exists(po_path):
        return 0
    
    po = polib.pofile(po_path)
    added = 0
    
    for msgid in strings:
        existing = po.find(msgid)
        
        if not existing:
            entry = polib.POEntry(
                msgid=msgid,
                msgstr=msgid,
            )
            po.append(entry)
            added += 1
            print(f"  [ADDED] {msgid}")
    
    if added > 0:
        po.save()
        print(f"\n  Saved: {added} entries added")
    
    return added


def compile_po_to_mo(lang_code):
    """Compile PO to MO."""
    po_path = os.path.join(BASE_DIR, "locale", lang_code, "LC_MESSAGES", "django.po")
    mo_path = os.path.join(BASE_DIR, "locale", lang_code, "LC_MESSAGES", "django.mo")
    
    if os.path.exists(po_path):
        po = polib.pofile(po_path)
        po.save_as_mofile(mo_path)
        print(f"  Compiled {lang_code}")


def main():
    print("=" * 60)
    print("Adding dashboard translations")
    print("=" * 60)
    
    total = 0
    
    for lang in ["es", "pt_BR"]:
        print(f"\n[{lang.upper()}]")
        count = add_translations_to_po(lang, TRANSLATIONS)
        total += count
    
    print(f"\n[EN]")
    add_english_entries(list(TRANSLATIONS.keys()))
    
    print(f"\nTotal translations processed: {total}")
    
    print("\nCompiling MO files...")
    for lang in ["es", "pt_BR", "en"]:
        compile_po_to_mo(lang)
    
    print("\nDone!")


if __name__ == "__main__":
    main()
