#!/usr/bin/env python3
"""
Script DEFINITIVO para traducir TODAS las entradas españolas a portugués
"""

import re
from pathlib import Path

# Diccionario completo ES → PT (basado en landing page)
TRANSLATIONS = {
    # Landing hero
    "Ver Demo": "Ver Demonstração",
    "Automatiza tus procesos de aprobación con seguridad de nivel empresarial y autenticación biométrica avanzada.": "Automatize seus processos de aprovação com segurança de nível empresarial e autenticação biométrica avançada.",
    "Comienza Ahora": "Comece Agora",
    "Solicitar Demo": "Solicitar Demonstração",
    
    # Features
    "Características Principales": "Características Principais",
    "Flujos de trabajo inteligentes": "Fluxos de trabalho inteligentes",
    "Crea reglas de aprobación personalizadas con lógica condicional": "Crie regras de aprovação personalizadas com lógica condicional",
    "Autenticación Biométrica": "Autenticação Biométrica",
    "WebAuthn con soporte para Face ID, Touch ID y llaves de seguridad": "WebAuthn com suporte para Face ID, Touch ID e chaves de segurança",
    "Trazabilidad Completa": "Rastreabilidade Completa",
    "Registro inmutable de todas las acciones y decisiones": "Registro imutável de todas as ações e decisões",
    "Tiempo Real": "Tempo Real",
    "Actualizaciones instantáneas vía WebSocket": "Atualizações instantâneas via WebSocket",
    "Integraciones": "Integrações",
    "Conecta con tus herramientas favoritas vía API REST": "Conecte com suas ferramentas favoritas via API REST",
    "Multi-idioma": "Multi-idioma",
    "Soporte para español, inglés y portugués": "Suporte para espanhol, inglês e português",
    
    # Plans
    "Elige el plan que se adapta a tu equipo": "Escolha o plano que se adapta à sua equipe",
    "Gratis": "Grátis",
    "Perfecto para equipos pequeños": "Perfeito para equipes pequenas",
    "Solicitudes ilimitadas": "Solicitações ilimitadas",
    "usuarios": "usuários",
    "aprobadores": "aprovadores",
    "WebAuthn completo": "WebAuthn completo",
    "Auditoría básica": "Auditoria básica",
    "Soporte por email": "Suporte por e-mail",
    "Comienza Gratis": "Comece Grátis",
    
    "Profesional": "Profissional",
    "Para equipos en crecimiento": "Para equipes em crescimento",
    "Todo lo de Gratis, más:": "Tudo do Grátis, mais:",
    "10 usuarios": "10 usuários",
    "3 aprobadores": "3 aprovadores",
    "Flujos personalizados": "Fluxos personalizados",
    "Auditoria avanzada": "Auditoria avançada",
    "Integraciones API": "Integrações API",
    "Actualizar Plan": "Atualizar Plano",
    
    "Empresas": "Empresas",
    "Para organizaciones grandes": "Para organizações grandes",
    "Todo lo de Profesional, más:": "Tudo do Profissional, mais:",
    "Usuarios ilimitados": "Usuários ilimitados",
    "Aprobadores ilimitados": "Aprovadores ilimitados",
    "SSO / SAML": "SSO / SAML",
    "Integraciones premium": "Integrações premium",
    "Soporte prioritario": "Suporte prioritário",
    "Contáctanos": "Entre em Contato",
    
    # CTA Final
    "¿Listo para transformar tus aprobaciones?": "Pronto para transformar suas aprovações?",
    "Únete a empresas que ya optimizaron sus procesos con SecureApprove": "Junte-se a empresas que já otimizaram seus processos com o SecureApprove",
    
    # Auth forms (muy comunes)
    "Email Address": "Endereço de E-mail",
    "Enter your email address": "Digite seu endereço de e-mail",
    "Password": "Senha",
    "Enter your password": "Digite sua senha",
    "Enter your current password": "Digite sua senha atual",
    "Create a strong password": "Crie uma senha forte",
    "Required.": "Obrigatório.",
    "Create Account": "Criar Conta",
    "Sign In": "Entrar",
    "Sign Up": "Cadastrar-se",
    "Forgot Password?": "Esqueceu a Senha?",
    "Remember Me": "Lembrar-me",
    "First Name": "Nome",
    "Last Name": "Sobrenome",
    "Enter your first name": "Digite seu nome",
    "Enter your last name": "Digite seu sobrenome",
    "Phone Number": "Número de Telefone",
    "Enter your phone number": "Digite seu número de telefone",
    "Company Name": "Nome da Empresa",
    "Enter your company name": "Digite o nome da sua empresa",
    "I accept the Terms of Service and Privacy Policy": "Aceito os Termos de Serviço e Política de Privacidade",
    "Terms of Service": "Termos de Serviço",
    "Privacy Policy": "Política de Privacidade",
    
    # Common
    "Dashboard": "Painel",
    "Requests": "Solicitações",
    "Settings": "Configurações",
    "Logout": "Sair",
    "Save": "Salvar",
    "Cancel": "Cancelar",
    "Delete": "Excluir",
    "Edit": "Editar",
    "Create": "Criar",
    "Update": "Atualizar",
    "Close": "Fechar",
    "Search": "Pesquisar",
    "Filter": "Filtrar",
    "Export": "Exportar",
    "Import": "Importar",
    "Download": "Baixar",
    "Upload": "Upload",
    "Next": "Próximo",
    "Previous": "Anterior",
    "Submit": "Enviar",
    "Back": "Voltar",
    "Home": "Início",
    "Profile": "Perfil",
    "Help": "Ajuda",
    "About": "Sobre",
    "Contact": "Contato",
    "Support": "Suporte",
    "Documentation": "Documentação",
    "API": "API",
    "Status": "Status",
    "Date": "Data",
    "Time": "Hora",
    "Name": "Nome",
    "Description": "Descrição",
    "Type": "Tipo",
    "Actions": "Ações",
    "Details": "Detalhes",
    "View": "Ver",
    "Add": "Adicionar",
    "Remove": "Remover",
    "Yes": "Sim",
    "No": "Não",
    "Confirm": "Confirmar",
    "Are you sure?": "Tem certeza?",
    "Success": "Sucesso",
    "Error": "Erro",
    "Warning": "Aviso",
    "Info": "Informação",
    "Loading...": "Carregando...",
    "Please wait": "Por favor, aguarde",
    "No results found": "Nenhum resultado encontrado",
    "Total": "Total",
    "Page": "Página",
    "of": "de",
    "Show": "Mostrar",
    "entries": "entradas",
    "All": "Todos",
    "Active": "Ativo",
    "Inactive": "Inativo",
    "Pending": "Pendente",
    "Approved": "Aprovado",
    "Rejected": "Rejeitado",
    "Draft": "Rascunho",
    "Published": "Publicado",
    "Archived": "Arquivado",
}

def translate_po_file(po_file_path):
    """Traduce todas las entradas vacías del archivo .po"""
    
    print(f"\n{'='*60}")
    print(f"TRADUCIENDO: {po_file_path}")
    print(f"{'='*60}\n")
    
    with open(po_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Contar traducciones antes
    empty_before = content.count('msgstr ""')
    
    # Para cada traducción en el diccionario
    translated_count = 0
    for spanish, portuguese in TRANSLATIONS.items():
        # Escapar caracteres especiales para regex
        escaped_spanish = re.escape(spanish)
        
        # Buscar msgid con msgstr vacío
        pattern = rf'(msgid "{escaped_spanish}"\n)msgstr ""'
        
        if re.search(pattern, content):
            # Reemplazar msgstr vacío con la traducción
            replacement = rf'\1msgstr "{portuguese}"'
            content = re.sub(pattern, replacement, content)
            translated_count += 1
            print(f"✓ {spanish[:50]}")
    
    # Guardar archivo modificado
    with open(po_file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Contar traducciones después
    empty_after = content.count('msgstr ""')
    
    print(f"\n{'='*60}")
    print(f"RESUMEN:")
    print(f"  - Traducciones agregadas: {translated_count}")
    print(f"  - msgstr vacíos antes: {empty_before}")
    print(f"  - msgstr vacíos después: {empty_after}")
    print(f"  - msgstr vacíos eliminados: {empty_before - empty_after}")
    print(f"{'='*60}\n")

def main():
    locale_dir = Path(__file__).parent / 'locale'
    po_pt = locale_dir / 'pt_BR' / 'LC_MESSAGES' / 'django.po'
    
    if po_pt.exists():
        translate_po_file(po_pt)
        print("✓ Archivo traducido correctamente")
        print("  Ahora ejecuta: python manage.py compilemessages")
    else:
        print(f"✗ No se encontró: {po_pt}")

if __name__ == '__main__':
    main()
