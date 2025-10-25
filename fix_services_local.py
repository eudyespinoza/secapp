#!/usr/bin/env python3
"""
Quick script to fix billing_service references in views.py (local version)
"""

import re

def fix_billing_services():
    """Fix all billing_service references to use lazy initialization"""
    
    file_path = r'd:\OtherProyects\SecApp\secureapprove_django\apps\billing\views.py'
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace direct usage with function calls
    content = re.sub(r'(\s+)billing_service\.', r'\1get_billing_service().', content)
    content = re.sub(r'(\s+)mp_service\.', r'\1get_mp_service().', content)
    
    # Also replace assignments
    content = re.sub(r'= billing_service\.', r'= get_billing_service().', content)
    content = re.sub(r'= mp_service\.', r'= get_mp_service().', content)
    
    # Replace standalone usage
    content = re.sub(r'\bbilling_service\.', r'get_billing_service().', content)
    content = re.sub(r'\bmp_service\.', r'get_mp_service().', content)
    
    # Save the fixed content
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("✅ Fixed all billing_service and mp_service references")

if __name__ == "__main__":
    fix_billing_services()