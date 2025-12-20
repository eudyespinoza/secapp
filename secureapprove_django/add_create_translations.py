#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Add missing translations for request creation form to all languages
"""
import polib

# All translations for request creation form
TRANSLATIONS = {
    # Key: English text
    # Value: (Spanish, Portuguese)
    
    # Page header
    "New Request": ("Nueva Solicitud", "Nova Solicitação"),
    "Submit a new approval request for review": ("Envía una nueva solicitud de aprobación para revisión", "Envie uma nova solicitação de aprovação para revisão"),
    "Back to Requests": ("Volver a Solicitudes", "Voltar para Solicitações"),
    
    # Step indicators
    "Category": ("Categoría", "Categoria"),
    "Details": ("Detalles", "Detalhes"),
    "Review": ("Revisar", "Revisar"),
    
    # Category selection
    "Select Request Category": ("Selecciona la Categoría de Solicitud", "Selecione a Categoria da Solicitação"),
    "Choose the type of request you want to submit": ("Elige el tipo de solicitud que deseas enviar", "Escolha o tipo de solicitação que deseja enviar"),
    
    # Categories
    "Expense": ("Gasto", "Despesa"),
    "Reimbursements": ("Reembolsos", "Reembolsos"),
    "Purchase": ("Compra", "Compra"),
    "Equipment & supplies": ("Equipos y suministros", "Equipamentos e suprimentos"),
    "Travel": ("Viaje", "Viagem"),
    "Trips & logistics": ("Viajes y logística", "Viagens e logística"),
    "Contract": ("Contrato", "Contrato"),
    "Agreements": ("Acuerdos", "Acordos"),
    "Document": ("Documento", "Documento"),
    "Approvals": ("Aprobaciones", "Aprovações"),
    "Other": ("Otro", "Outro"),
    "General": ("General", "Geral"),
    
    # Request details
    "Request Details": ("Detalles de la Solicitud", "Detalhes da Solicitação"),
    "Title": ("Título", "Título"),
    "Enter a descriptive title for your request": ("Ingresa un título descriptivo para tu solicitud", "Digite um título descritivo para sua solicitação"),
    "Description": ("Descripción", "Descrição"),
    "Provide detailed information about your request": ("Proporciona información detallada sobre tu solicitud", "Forneça informações detalhadas sobre sua solicitação"),
    "Priority": ("Prioridad", "Prioridade"),
    "Low": ("Baja", "Baixa"),
    "Medium": ("Media", "Média"),
    "High": ("Alta", "Alta"),
    "Amount": ("Monto", "Valor"),
    
    # Expense fields
    "Expense Category": ("Categoría de Gasto", "Categoria de Despesa"),
    "Meals, Transportation, etc.": ("Comidas, Transporte, etc.", "Refeições, Transporte, etc."),
    "Receipt Reference": ("Referencia de Recibo", "Referência do Recibo"),
    "Receipt number": ("Número de recibo", "Número do recibo"),
    
    # Purchase fields
    "Vendor": ("Proveedor", "Fornecedor"),
    "Vendor name": ("Nombre del proveedor", "Nome do fornecedor"),
    "Cost Center": ("Centro de Costos", "Centro de Custos"),
    "Cost center code": ("Código del centro de costos", "Código do centro de custos"),
    
    # Travel fields
    "Destination": ("Destino", "Destino"),
    "Travel destination": ("Destino del viaje", "Destino da viagem"),
    "Start Date": ("Fecha de Inicio", "Data de Início"),
    "End Date": ("Fecha de Fin", "Data de Término"),
    
    # Contract/Document fields
    "Reason": ("Razón", "Motivo"),
    "Explain the reason for this request": ("Explica la razón de esta solicitud", "Explique o motivo desta solicitação"),
    "Document ID": ("ID del Documento", "ID do Documento"),
    "Document ID or reference": ("ID o referencia del documento", "ID ou referência do documento"),
    
    # Attachments
    "Attachments": ("Adjuntos", "Anexos"),
    "Drag and drop files here or click to browse": ("Arrastra y suelta archivos aquí o haz clic para explorar", "Arraste e solte arquivos aqui ou clique para navegar"),
    "PDF, Word, Excel, Images (Max 25MB per file)": ("PDF, Word, Excel, Imágenes (Máx 25MB por archivo)", "PDF, Word, Excel, Imagens (Máx 25MB por arquivo)"),
    
    # Actions
    "Cancel": ("Cancelar", "Cancelar"),
    "Submit Request": ("Enviar Solicitud", "Enviar Solicitação"),
    
    # Preview
    "Request Preview": ("Vista Previa de Solicitud", "Prévia da Solicitação"),
    "Fill in the form to see a preview": ("Completa el formulario para ver una vista previa", "Preencha o formulário para ver uma prévia"),
    
    # WebAuthn Modal
    "Confirm Your Identity": ("Confirma Tu Identidad", "Confirme Sua Identidade"),
    "Biometric Verification Required": ("Verificación Biométrica Requerida", "Verificação Biométrica Necessária"),
    "Please authenticate using your fingerprint, face recognition, or security key to submit this request.": (
        "Por favor, autentícate usando tu huella digital, reconocimiento facial o llave de seguridad para enviar esta solicitud.",
        "Por favor, autentique-se usando sua impressão digital, reconhecimento facial ou chave de segurança para enviar esta solicitação."
    ),
    "Loading...": ("Cargando...", "Carregando..."),
    "Waiting for authentication...": ("Esperando autenticación...", "Aguardando autenticação..."),
    "Please complete the biometric prompt on your device.": (
        "Por favor, completa el aviso biométrico en tu dispositivo.",
        "Por favor, complete o prompt biométrico no seu dispositivo."
    ),
    "Authentication Successful": ("Autenticación Exitosa", "Autenticação Bem-sucedida"),
    "Submitting your request...": ("Enviando tu solicitud...", "Enviando sua solicitação..."),
    "Authentication Failed": ("Autenticación Fallida", "Autenticação Falhou"),
    "Please try again.": ("Por favor, intenta de nuevo.", "Por favor, tente novamente."),
    "Authenticate": ("Autenticar", "Autenticar"),
    "Try Again": ("Intentar de Nuevo", "Tentar Novamente"),
    "Close": ("Cerrar", "Fechar"),
    
    # Error messages
    "File is too large": ("El archivo es muy grande", "O arquivo é muito grande"),
    "file(s)": ("archivo(s)", "arquivo(s)"),
    "No biometric credentials registered. Please register a device from your profile first.": (
        "No hay credenciales biométricas registradas. Por favor, registra un dispositivo desde tu perfil primero.",
        "Nenhuma credencial biométrica registrada. Por favor, registre um dispositivo no seu perfil primeiro."
    ),
    "Failed to get authentication options": ("Error al obtener opciones de autenticación", "Falha ao obter opções de autenticação"),
    "WebAuthn authentication was cancelled": ("La autenticación WebAuthn fue cancelada", "A autenticação WebAuthn foi cancelada"),
    "Authentication verification failed": ("La verificación de autenticación falló", "A verificação de autenticação falhou"),
    "Verification failed": ("La verificación falló", "A verificação falhou"),
    "Biometric authentication was cancelled or denied. Please try again.": (
        "La autenticación biométrica fue cancelada o denegada. Por favor, intenta nuevamente.",
        "A autenticação biométrica foi cancelada ou negada. Por favor, tente novamente."
    ),
    "No matching credential found on this device.": (
        "No se encontró credencial coincidente en este dispositivo.",
        "Nenhuma credencial correspondente encontrada neste dispositivo."
    ),
    "This device does not support the required authentication method.": (
        "Este dispositivo no admite el método de autenticación requerido.",
        "Este dispositivo não suporta o método de autenticação necessário."
    ),
    "Please fill in all required fields.": (
        "Por favor completa todos los campos obligatorios.",
        "Por favor, preencha todos os campos obrigatórios."
    ),
    "WebAuthn is not supported on this device/browser.": (
        "WebAuthn no es compatible con este dispositivo/navegador.",
        "WebAuthn não é suportado neste dispositivo/navegador."
    ),
}


def add_translations(po_path, lang_index, lang_name):
    """Add missing translations to a PO file"""
    try:
        po = polib.pofile(po_path)
    except Exception as e:
        print(f"Error loading {po_path}: {e}")
        return
    
    existing_msgids = {entry.msgid for entry in po}
    added = 0
    updated = 0
    
    for english, translations in TRANSLATIONS.items():
        if lang_index == 2:  # English
            translation = english  # Keep same as source
        else:
            translation = translations[lang_index]
        
        if english not in existing_msgids:
            # Add new entry
            entry = polib.POEntry(
                msgid=english,
                msgstr=translation
            )
            po.append(entry)
            added += 1
        else:
            # Update if empty
            for entry in po:
                if entry.msgid == english:
                    if not entry.msgstr or (entry.msgstr == english and lang_index != 2):
                        entry.msgstr = translation
                        updated += 1
                    break
    
    po.save()
    print(f"{lang_name}: Added {added} new, updated {updated} empty translations")
    
    # Compile to .mo
    mo_path = po_path.replace('.po', '.mo')
    po.save_as_mofile(mo_path)
    print(f"{lang_name}: Compiled to {mo_path}")


def main():
    print("=" * 60)
    print("ADDING TRANSLATIONS FOR REQUEST CREATION FORM")
    print("=" * 60)
    print(f"Total texts: {len(TRANSLATIONS)}")
    print()
    
    # Spanish (index 0)
    add_translations('locale/es/LC_MESSAGES/django.po', 0, 'Spanish')
    
    # Portuguese (index 1)
    add_translations('locale/pt_BR/LC_MESSAGES/django.po', 1, 'Portuguese')
    
    # English (index 2 - just add msgid=msgstr)
    add_translations('locale/en/LC_MESSAGES/django.po', 2, 'English')
    
    print()
    print("✅ All translations added successfully!")


if __name__ == '__main__':
    main()
