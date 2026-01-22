from rest_framework import serializers


class TermsTokenRequestSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    purpose = serializers.CharField(max_length=64, required=False, default='terms_acceptance')

    document_type = serializers.CharField(max_length=32, required=False, default='terms')
    document_version = serializers.CharField(max_length=64, required=False, allow_blank=True, default='')
    document_hash = serializers.CharField(max_length=128, required=False, allow_blank=True, default='')

    context = serializers.DictField(required=False, default=dict)


class TermsConfirmRequestSerializer(serializers.Serializer):
    approval_token = serializers.CharField()
    approved = serializers.BooleanField(required=True)
    webauthn_response = serializers.DictField(required=True)
