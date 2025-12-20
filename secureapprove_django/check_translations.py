#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Check translations for request creation form
"""
import re
import polib

# All texts that need translation from create.html
TEXTS_TO_TRANSLATE = [
    "New Request",
    "Submit a new approval request for review",
    "Back to Requests",
    "Category",
    "Details",
    "Review",
    "Select Request Category",
    "Choose the type of request you want to submit",
    "Expense",
    "Reimbursements",
    "Purchase",
    "Equipment & supplies",
    "Travel",
    "Trips & logistics",
    "Contract",
    "Agreements",
    "Document",
    "Approvals",
    "Other",
    "General",
    "Request Details",
    "Title",
    "Enter a descriptive title for your request",
    "Description",
    "Provide detailed information about your request",
    "Priority",
    "Low",
    "Medium",
    "High",
    "Amount",
    "Expense Category",
    "Meals, Transportation, etc.",
    "Receipt Reference",
    "Receipt number",
    "Vendor",
    "Vendor name",
    "Cost Center",
    "Cost center code",
    "Destination",
    "Travel destination",
    "Start Date",
    "End Date",
    "Reason",
    "Explain the reason for this request",
    "Document ID",
    "Document ID or reference",
    "Attachments",
    "Drag and drop files here or click to browse",
    "PDF, Word, Excel, Images (Max 25MB per file)",
    "Cancel",
    "Submit Request",
    "Request Preview",
    "Fill in the form to see a preview",
    "Confirm Your Identity",
    "Biometric Verification Required",
    "Please authenticate using your fingerprint, face recognition, or security key to submit this request.",
    "Loading...",
    "Waiting for authentication...",
    "Please complete the biometric prompt on your device.",
    "Authentication Successful",
    "Submitting your request...",
    "Authentication Failed",
    "Please try again.",
    "Authenticate",
    "Try Again",
    "Close",
    "File is too large",
    "file(s)",
    "No biometric credentials registered. Please register a device from your profile first.",
    "Failed to get authentication options",
    "WebAuthn authentication was cancelled",
    "Authentication verification failed",
    "Verification failed",
    "Biometric authentication was cancelled or denied. Please try again.",
    "No matching credential found on this device.",
    "This device does not support the required authentication method.",
    "Please fill in all required fields.",
    "WebAuthn is not supported on this device/browser.",
]

def check_translations(po_file_path, lang_name):
    """Check which translations are missing or empty"""
    try:
        po = polib.pofile(po_file_path)
    except Exception as e:
        print(f"Error loading {po_file_path}: {e}")
        return []
    
    # Build a dict of existing translations
    existing = {}
    for entry in po:
        existing[entry.msgid] = entry.msgstr
    
    missing = []
    empty = []
    
    for text in TEXTS_TO_TRANSLATE:
        if text not in existing:
            missing.append(text)
        elif not existing[text] or existing[text] == text:
            # Empty or same as source (not translated)
            if lang_name != 'en':  # English doesn't need translation
                empty.append(text)
    
    return missing, empty

def main():
    languages = [
        ('locale/es/LC_MESSAGES/django.po', 'Spanish (es)'),
        ('locale/pt_BR/LC_MESSAGES/django.po', 'Portuguese (pt_BR)'),
        ('locale/en/LC_MESSAGES/django.po', 'English (en)'),
    ]
    
    print("=" * 60)
    print("TRANSLATION CHECK FOR REQUEST CREATION FORM")
    print("=" * 60)
    print(f"Total texts to verify: {len(TEXTS_TO_TRANSLATE)}")
    print()
    
    for po_path, lang_name in languages:
        print(f"\n{'='*60}")
        print(f"Language: {lang_name}")
        print(f"{'='*60}")
        
        missing, empty = check_translations(po_path, lang_name)
        
        if missing:
            print(f"\n⚠️  MISSING ({len(missing)} texts):")
            for text in missing:
                print(f"   - \"{text}\"")
        
        if empty:
            print(f"\n⚠️  EMPTY/NOT TRANSLATED ({len(empty)} texts):")
            for text in empty:
                print(f"   - \"{text}\"")
        
        if not missing and not empty:
            print("✅ All translations present!")

if __name__ == '__main__':
    main()
