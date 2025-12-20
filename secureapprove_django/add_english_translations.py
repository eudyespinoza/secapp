#!/usr/bin/env python
"""Add English base translations to ensure all strings exist."""
import polib
import os

# All translation strings for list page (English msgid = msgstr)
ENGLISH_STRINGS = [
    "Requests",
    "Approval Requests",
    "New Request",
    "request in total",
    "requests in total",
    "Filter Requests",
    "Status",
    "Category",
    "Search",
    "All Statuses",
    "All Categories",
    "Search by title or description...",
    "Clear",
    "Clear Filters",
    "Pending",
    "Approved",
    "Rejected",
    "Request",
    "No requests found",
    "Try adjusting your filters or search terms.",
    "Start by creating your first approval request.",
    "Create First Request",
    "Requests pagination",
    "Previous",
    "Next",
    "No requests match your search.",
    "request",
    "requests",
    # Additional from create page that may be needed
    "Critical",
    "High",
    "Medium",
    "Low",
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def add_english_entries():
    """Add English entries to PO file."""
    po_path = os.path.join(BASE_DIR, "locale", "en", "LC_MESSAGES", "django.po")
    
    if not os.path.exists(po_path):
        print(f"PO file not found: {po_path}")
        return 0
    
    po = polib.pofile(po_path)
    added = 0
    
    for msgid in ENGLISH_STRINGS:
        existing = po.find(msgid)
        
        if not existing:
            entry = polib.POEntry(
                msgid=msgid,
                msgstr=msgid,  # In English, msgstr = msgid
            )
            po.append(entry)
            added += 1
            print(f"  [ADDED] {msgid}")
    
    if added > 0:
        po.save()
        print(f"\n  Saved: {added} entries added")
    else:
        print("  All entries already exist")
    
    return added


def compile_po_to_mo():
    """Compile PO to MO."""
    po_path = os.path.join(BASE_DIR, "locale", "en", "LC_MESSAGES", "django.po")
    mo_path = os.path.join(BASE_DIR, "locale", "en", "LC_MESSAGES", "django.mo")
    
    if os.path.exists(po_path):
        po = polib.pofile(po_path)
        po.save_as_mofile(mo_path)
        print("  Compiled en")


def main():
    print("=" * 60)
    print("Adding English base translations")
    print("=" * 60)
    
    print("\n[EN]")
    add_english_entries()
    
    print("\nCompiling MO file...")
    compile_po_to_mo()
    
    print("\nDone!")


if __name__ == "__main__":
    main()
