#!/usr/bin/env python3
"""
Quick script to fix billing_service references in views.py
"""

import re

def fix_billing_services():
    """Fix all billing_service references to use lazy initialization"""
    
    with open('/app/apps/billing/views.py', 'r') as f:
        content = f.read()
    
    # Pattern to find function definitions
    function_pattern = r'(def\s+\w+\([^)]*\):.*?)(\n\s+.*?)(billing_service\.|mp_service\.)'
    
    # Find all functions that use billing_service or mp_service
    functions_using_services = set()
    
    # Find all uses of billing_service and mp_service
    billing_uses = re.findall(r'(\w+)\s*=\s*billing_service\.', content)
    mp_uses = re.findall(r'(\w+)\s*=\s*mp_service\.', content)
    
    # Replace direct usage with function calls
    content = re.sub(r'(\s+)billing_service\.', r'\1get_billing_service().', content)
    content = re.sub(r'(\s+)mp_service\.', r'\1get_mp_service().', content)
    
    # Also replace assignments
    content = re.sub(r'= billing_service\.', r'= get_billing_service().', content)
    content = re.sub(r'= mp_service\.', r'= get_mp_service().', content)
    
    # Save the fixed content
    with open('/app/apps/billing/views.py', 'w') as f:
        f.write(content)
    
    print("✅ Fixed all billing_service and mp_service references")

if __name__ == "__main__":
    fix_billing_services()