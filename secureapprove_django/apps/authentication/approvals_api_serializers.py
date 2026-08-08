import re
from urllib.parse import urlsplit

from rest_framework import serializers


SHA256_RE = re.compile(r'^[0-9a-f]{64}$')


def normalize_parent_origin(value: str) -> str:
    """Return a canonical web origin and reject paths, credentials, and unsafe schemes."""
    raw_value = (value or '').strip()
    if any(character.isspace() for character in raw_value) or '\\' in raw_value:
        raise serializers.ValidationError('parent_origin contains invalid characters.')
    parsed = urlsplit(raw_value)

    if not parsed.scheme or not parsed.hostname or parsed.username or parsed.password:
        raise serializers.ValidationError('A valid parent web origin is required.')

    if parsed.path not in ('', '/') or parsed.query or parsed.fragment:
        raise serializers.ValidationError('parent_origin must contain only scheme, host, and optional port.')

    hostname = parsed.hostname.lower()
    is_local = hostname in {'localhost', '127.0.0.1', '::1'}
    if parsed.scheme != 'https' and not (parsed.scheme == 'http' and is_local):
        raise serializers.ValidationError('parent_origin must use HTTPS outside local development.')

    host = f'[{hostname}]' if ':' in hostname and not hostname.startswith('[') else hostname
    try:
        port = parsed.port
    except ValueError as exc:
        raise serializers.ValidationError('parent_origin contains an invalid port.') from exc
    is_default_port = (parsed.scheme == 'https' and port == 443) or (parsed.scheme == 'http' and port == 80)
    if port and not is_default_port:
        host = f'{host}:{port}'
    return f'{parsed.scheme.lower()}://{host}'


class TermsTokenRequestSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    purpose = serializers.CharField(max_length=64, required=False, default='terms_acceptance')

    decision = serializers.ChoiceField(choices=('approve', 'reject'), default='approve')
    parent_origin = serializers.CharField(max_length=255)

    document_type = serializers.CharField(max_length=32, required=False, default='terms')
    document_version = serializers.CharField(max_length=64, allow_blank=False)
    document_hash = serializers.CharField(max_length=64, allow_blank=False)

    context = serializers.DictField(required=False, default=dict)

    def validate_parent_origin(self, value):
        return normalize_parent_origin(value)

    def validate_document_hash(self, value):
        normalized = value.strip().lower()
        if not SHA256_RE.fullmatch(normalized):
            raise serializers.ValidationError('document_hash must be a 64-character SHA-256 hex digest.')
        return normalized


class TermsConfirmRequestSerializer(serializers.Serializer):
    approval_token = serializers.CharField()
    webauthn_response = serializers.DictField(required=True)
