#!/usr/bin/env python
"""Add missing translations for the requests list page."""
import polib
import os

# Translations for the list page
TRANSLATIONS = {
    # Header and title
    "Requests": {"es": "Solicitudes", "pt_BR": "Solicitações"},
    "Approval Requests": {"es": "Solicitudes de Aprobación", "pt_BR": "Solicitações de Aprovação"},
    "New Request": {"es": "Nueva Solicitud", "pt_BR": "Nova Solicitação"},
    "request in total": {"es": "solicitud en total", "pt_BR": "solicitação no total"},
    "requests in total": {"es": "solicitudes en total", "pt_BR": "solicitações no total"},
    
    # Filters
    "Filter Requests": {"es": "Filtrar Solicitudes", "pt_BR": "Filtrar Solicitações"},
    "Status": {"es": "Estado", "pt_BR": "Status"},
    "Category": {"es": "Categoría", "pt_BR": "Categoria"},
    "Search": {"es": "Buscar", "pt_BR": "Pesquisar"},
    "All Statuses": {"es": "Todos los Estados", "pt_BR": "Todos os Status"},
    "All Categories": {"es": "Todas las Categorías", "pt_BR": "Todas as Categorias"},
    "Search by title or description...": {"es": "Buscar por título o descripción...", "pt_BR": "Pesquisar por título ou descrição..."},
    "Clear": {"es": "Limpiar", "pt_BR": "Limpar"},
    "Clear Filters": {"es": "Limpiar Filtros", "pt_BR": "Limpar Filtros"},
    
    # Status badges
    "Pending": {"es": "Pendiente", "pt_BR": "Pendente"},
    "Approved": {"es": "Aprobado", "pt_BR": "Aprovado"},
    "Rejected": {"es": "Rechazado", "pt_BR": "Rejeitado"},
    "Request": {"es": "Solicitud", "pt_BR": "Solicitação"},
    
    # Empty state
    "No requests found": {"es": "No se encontraron solicitudes", "pt_BR": "Nenhuma solicitação encontrada"},
    "Try adjusting your filters or search terms.": {"es": "Intenta ajustar tus filtros o términos de búsqueda.", "pt_BR": "Tente ajustar seus filtros ou termos de pesquisa."},
    "Start by creating your first approval request.": {"es": "Comienza creando tu primera solicitud de aprobación.", "pt_BR": "Comece criando sua primeira solicitação de aprovação."},
    "Create First Request": {"es": "Crear Primera Solicitud", "pt_BR": "Criar Primeira Solicitação"},
    
    # Pagination
    "Requests pagination": {"es": "Paginación de solicitudes", "pt_BR": "Paginação de solicitações"},
    "Previous": {"es": "Anterior", "pt_BR": "Anterior"},
    "Next": {"es": "Siguiente", "pt_BR": "Próximo"},
    
    # Search results
    "No requests match your search.": {"es": "Ninguna solicitud coincide con tu búsqueda.", "pt_BR": "Nenhuma solicitação corresponde à sua pesquisa."},
    "request": {"es": "solicitud", "pt_BR": "solicitação"},
    "requests": {"es": "solicitudes", "pt_BR": "solicitações"},
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def add_translations_to_po(lang_code, translations):
    """Add translations to a PO file."""
    if lang_code == "en":
        return 0  # English doesn't need translations
    
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
        
        # Check if entry exists
        existing = po.find(msgid)
        
        if existing:
            if not existing.msgstr or existing.msgstr == msgid:
                existing.msgstr = trans
                if 'fuzzy' in existing.flags:
                    existing.flags.remove('fuzzy')
                updated += 1
                print(f"  [UPDATED] {msgid[:40]}...")
        else:
            # Add new entry
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
    print("Adding list page translations")
    print("=" * 60)
    
    total = 0
    
    for lang in ["es", "pt_BR"]:
        print(f"\n[{lang.upper()}]")
        count = add_translations_to_po(lang, TRANSLATIONS)
        total += count
    
    print(f"\n\nTotal translations processed: {total}")
    
    # Compile all
    print("\nCompiling MO files...")
    for lang in ["es", "pt_BR", "en"]:
        compile_po_to_mo(lang)
    
    print("\nDone!")


if __name__ == "__main__":
    main()
