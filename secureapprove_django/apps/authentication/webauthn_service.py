# ==================================================
# SecureApprove Django - WebAuthn Service
# ==================================================

import json
import base64
from typing import Optional, Dict, List, Any
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from webauthn import generate_registration_options, verify_registration_response
from webauthn import generate_authentication_options, verify_authentication_response
from webauthn.helpers.structs import (
    PublicKeyCredentialCreationOptions,
    RegistrationCredential,
    PublicKeyCredentialRequestOptions,
    AuthenticationCredential,
    UserVerificationRequirement,
    AuthenticatorSelectionCriteria,
    AuthenticatorAttachment,
    ResidentKeyRequirement,
    AttestationConveyancePreference,
)
from webauthn.helpers.cose import COSEAlgorithmIdentifier

User = get_user_model()


class WebAuthnService:
    """
    WebAuthn service for handling passwordless authentication
    Replicates the functionality from the NestJS WebAuthnService
    """
    
    def __init__(self):
        # Configuration from Django settings or defaults
        self.rp_name = getattr(settings, 'WEBAUTHN_RP_NAME', 'SecureApprove')
        self.rp_id = getattr(settings, 'WEBAUTHN_RP_ID', 'localhost')
        self.origin = getattr(settings, 'WEBAUTHN_ORIGIN', 'http://localhost:8000')
        self.challenge_timeout = getattr(settings, 'WEBAUTHN_CHALLENGE_TIMEOUT', 300)  # 5 minutes
    
    def generate_registration_options(self, user: User) -> Dict[str, Any]:
        """
        Generate WebAuthn registration options for a user
        Equivalent to generateRegistrationOptions in NestJS
        """
        # Get existing credentials to exclude them
        exclude_credentials = []
        for cred in user.webauthn_credentials:
            if 'credential_id' in cred:
                exclude_credentials.append({
                    'id': base64.b64decode(cred['credential_id']),
                    'type': 'public-key',
                    'transports': cred.get('transports', [])
                })
        
        # Generate registration options
        options = generate_registration_options(
            rp_id=self.rp_id,
            rp_name=self.rp_name,
            user_id=str(user.id),
            user_name=user.email,
            user_display_name=user.get_full_name(),
            exclude_credentials=exclude_credentials,
            authenticator_selection=AuthenticatorSelectionCriteria(
                authenticator_attachment=None,  # Allow both platform and cross-platform authenticators
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.DISCOURAGED,  # Don't require biometrics
            ),
            supported_pub_key_algs=[
                COSEAlgorithmIdentifier.ECDSA_SHA_256,
                COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
            ],
            attestation=AttestationConveyancePreference.NONE,
            timeout=60000,
        )
        
        # Store challenge in cache
        challenge_key = f"webauthn_challenge_reg_{user.id}"
        cache.set(challenge_key, options.challenge, timeout=self.challenge_timeout)
        
        return {
            'challenge': base64.b64encode(options.challenge).decode('utf-8') if isinstance(options.challenge, bytes) else base64.b64encode(options.challenge.encode('utf-8')).decode('utf-8'),
            'rp': {
                'name': options.rp.name,
                'id': options.rp.id,
            },
            'user': {
                'id': base64.b64encode(options.user.id).decode('utf-8') if isinstance(options.user.id, bytes) else base64.b64encode(str(options.user.id).encode('utf-8')).decode('utf-8'),
                'name': options.user.name,
                'displayName': options.user.display_name,
            },
            'pubKeyCredParams': [
                {'type': 'public-key', 'alg': alg.alg}
                for alg in options.pub_key_cred_params
            ],
            'timeout': options.timeout,
            'excludeCredentials': [
                {
                    'id': base64.b64encode(cred.id).decode('utf-8') if isinstance(cred.id, bytes) else base64.b64encode(cred.id.encode()).decode('utf-8'),
                    'type': cred.type,
                    'transports': cred.transports,
                }
                for cred in options.exclude_credentials
            ],
            'authenticatorSelection': {
                'authenticatorAttachment': options.authenticator_selection.authenticator_attachment.value if options.authenticator_selection.authenticator_attachment else None,
                'requireResidentKey': options.authenticator_selection.resident_key == ResidentKeyRequirement.REQUIRED,
                'residentKey': options.authenticator_selection.resident_key.value,
                'userVerification': options.authenticator_selection.user_verification.value,
            },
            'attestation': options.attestation.value,
        }
    
    def verify_registration_response(self, user: User, credential_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify WebAuthn registration response
        Equivalent to verifyRegistration in NestJS
        """
        challenge_key = f"webauthn_challenge_reg_{user.id}"
        expected_challenge = cache.get(challenge_key)
        
        if not expected_challenge:
            raise ValueError(_('Challenge not found or expired'))
        
        try:
            # Convert the credential data to the expected format
            registration_credential = RegistrationCredential.parse_raw(json.dumps({
                'id': credential_data['id'],
                'raw_id': credential_data['rawId'],
                'response': {
                    'client_data_json': credential_data['response']['clientDataJSON'],
                    'attestation_object': credential_data['response']['attestationObject'],
                },
                'type': credential_data['type'],
            }))
            
            # Verify the registration
            verification = verify_registration_response(
                credential=registration_credential,
                expected_challenge=expected_challenge,
                expected_origin=self.origin,
                expected_rp_id=self.rp_id,
                require_user_verification=False,
            )
            
            # Clean up challenge
            cache.delete(challenge_key)
            
            # The VerifiedRegistration object doesn't have a 'verified' attribute
            # Instead, if the verification was successful, the object is returned
            # If it fails, an exception is raised
            
            # Create credential data to store
            credential = {
                'credential_id': base64.b64encode(verification.credential_id).decode('utf-8') if isinstance(verification.credential_id, bytes) else base64.b64encode(verification.credential_id.encode('utf-8')).decode('utf-8'),
                'credential_public_key': base64.b64encode(verification.credential_public_key).decode('utf-8') if isinstance(verification.credential_public_key, bytes) else base64.b64encode(verification.credential_public_key.encode('utf-8')).decode('utf-8'),
                'sign_count': verification.sign_count,
                'transports': credential_data.get('response', {}).get('transports', []),
                'created_at': user.date_joined.isoformat() if hasattr(user, 'date_joined') else None,
            }
            
            # Add credential to user
            user.webauthn_credentials.append(credential)
            user.save(update_fields=['webauthn_credentials'])
            
            return {
                'verified': True,
                'credential_id': credential['credential_id'],
                'registration_info': {
                    'credential_public_key': verification.credential_public_key,
                    'credential_id': verification.credential_id,
                    'sign_count': verification.sign_count,
                }
            }
            
        except Exception as e:
            cache.delete(challenge_key)
            raise ValueError(f'{_("Registration verification failed")}: {str(e)}')
    
    def generate_authentication_options(self, user: User) -> Dict[str, Any]:
        """
        Generate WebAuthn authentication options for a user
        Equivalent to generateAuthenticationOptions in NestJS
        """
        if not user.webauthn_credentials:
            raise ValueError(_('No credentials registered for this user'))
        
        # Prepare allowed credentials
        allow_credentials = []
        for cred in user.webauthn_credentials:
            if 'credential_id' in cred:
                allow_credentials.append({
                    'id': base64.b64decode(cred['credential_id']),
                    'type': 'public-key',
                    'transports': cred.get('transports', [])
                })
        
        # Generate authentication options
        options = generate_authentication_options(
            rp_id=self.rp_id,
            allow_credentials=allow_credentials,
            user_verification=UserVerificationRequirement.PREFERRED,
            timeout=60000,
        )
        
        # Store challenge in cache
        challenge_key = f"webauthn_challenge_auth_{user.id}"
        cache.set(challenge_key, options.challenge, timeout=self.challenge_timeout)
        
        return {
            'challenge': base64.b64encode(options.challenge).decode('utf-8') if isinstance(options.challenge, bytes) else base64.b64encode(options.challenge.encode('utf-8')).decode('utf-8'),
            'timeout': options.timeout,
            'rpId': options.rp_id,
            'allowCredentials': [
                {
                    'id': base64.b64encode(cred.id).decode('utf-8') if isinstance(cred.id, bytes) else base64.b64encode(cred.id.encode('utf-8')).decode('utf-8'),
                    'type': cred.type,
                    'transports': cred.transports,
                }
                for cred in options.allow_credentials
            ],
            'userVerification': options.user_verification.value,
        }
    
    def verify_authentication_response(self, user: User, credential_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify WebAuthn authentication response
        Equivalent to verifyAuthentication in NestJS
        """
        challenge_key = f"webauthn_challenge_auth_{user.id}"
        expected_challenge = cache.get(challenge_key)
        
        if not expected_challenge:
            raise ValueError(_('Challenge not found or expired'))
        
        try:
            # Find the credential
            credential_id = credential_data.get('id', '')
            
            # Normalize base64 padding for comparison
            def normalize_base64(b64_str):
                # Add padding if missing
                missing_padding = len(b64_str) % 4
                if missing_padding:
                    b64_str += '=' * (4 - missing_padding)
                return b64_str
            
            normalized_credential_id = normalize_base64(credential_id)
            
            user_credential = None
            
            for cred in user.webauthn_credentials:
                stored_id = cred.get('credential_id', '')
                normalized_stored_id = normalize_base64(stored_id)
                if normalized_stored_id == normalized_credential_id:
                    user_credential = cred
                    break
            
            if not user_credential:
                raise ValueError(_('Credential not found'))
            
            # Convert the credential data to the expected format
            authentication_credential = AuthenticationCredential.parse_raw(json.dumps({
                'id': credential_data['id'],
                'raw_id': credential_data['rawId'],
                'response': {
                    'client_data_json': credential_data['response']['clientDataJSON'],
                    'authenticator_data': credential_data['response']['authenticatorData'],
                    'signature': credential_data['response']['signature'],
                    'user_handle': credential_data['response'].get('userHandle'),
                },
                'type': credential_data['type'],
            }))
            
            # Verify the authentication
            verification = verify_authentication_response(
                credential=authentication_credential,
                expected_challenge=expected_challenge,
                expected_origin=self.origin,
                expected_rp_id=self.rp_id,
                credential_public_key=base64.b64decode(user_credential['credential_public_key']),
                credential_current_sign_count=user_credential.get('sign_count', 0),
                require_user_verification=False,
            )
            
            # Clean up challenge
            cache.delete(challenge_key)
            
            # The VerifiedAuthentication object doesn't have a 'verified' attribute
            # Instead, if the verification was successful, the object is returned
            # If it fails, an exception is raised
            
            # Update sign count
            user_credential['sign_count'] = verification.new_sign_count
            user.save(update_fields=['webauthn_credentials'])
            
            return {
                'verified': True,
                'new_sign_count': verification.new_sign_count,
            }
            
        except Exception as e:
            cache.delete(challenge_key)
            raise ValueError(f'{_("Authentication verification failed")}: {str(e)}')
    
    def clear_challenge(self, user_id: str, challenge_type: str = 'both'):
        """
        Clear stored challenges for a user
        """
        if challenge_type in ['reg', 'both']:
            cache.delete(f"webauthn_challenge_reg_{user_id}")
        if challenge_type in ['auth', 'both']:
            cache.delete(f"webauthn_challenge_auth_{user_id}")


# Global instance
webauthn_service = WebAuthnService()