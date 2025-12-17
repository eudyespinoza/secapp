# ==================================================
# SecureApprove Django - WebAuthn Service
# ==================================================

import json
import base64
import logging
from typing import Optional, Dict, List, Any
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from django.utils import timezone

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
logger = logging.getLogger(__name__)


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
        
        # Build list of allowed origins (www and non-www variants)
        self.allowed_origins = self._build_allowed_origins()
    
    def _build_allowed_origins(self) -> list:
        """Build list of allowed origins including www and non-www variants"""
        origins = [self.origin]
        
        # If origin contains a domain, also allow the www variant (or non-www if www)
        if '://' in self.origin:
            scheme, rest = self.origin.split('://', 1)
            domain = rest.split('/')[0]  # Get domain without path
            
            if domain.startswith('www.'):
                # Add non-www variant
                non_www_domain = domain[4:]  # Remove 'www.'
                origins.append(f"{scheme}://{non_www_domain}")
            else:
                # Add www variant
                origins.append(f"{scheme}://www.{domain}")
        
        return origins
    
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
                user_verification=UserVerificationRequirement.REQUIRED,  # REQUIRE biometrics/PIN
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
        
        result = {
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
                {'type': 'public-key', 'alg': param.alg.value if hasattr(param.alg, 'value') else int(param.alg)}
                for param in options.pub_key_cred_params
            ],
            'timeout': options.timeout,
            'excludeCredentials': [
                {
                    'id': base64.b64encode(cred.id).decode('utf-8') if isinstance(cred.id, bytes) else base64.b64encode(cred.id.encode()).decode('utf-8'),
                    'type': cred.type,
                    'transports': list(cred.transports) if cred.transports else [],
                }
                for cred in options.exclude_credentials
            ],
            'authenticatorSelection': {
                'residentKey': options.authenticator_selection.resident_key.value,
                'userVerification': options.authenticator_selection.user_verification.value,
            },
            'attestation': options.attestation.value,
        }
        
        # Log the pubKeyCredParams for debugging
        logger.info(f"WebAuthn registration options pubKeyCredParams: {result['pubKeyCredParams']}")
        
        return result
    
    def verify_registration_response(self, user: User, credential_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify WebAuthn registration response
        Equivalent to verifyRegistration in NestJS
        """
        challenge_key = f"webauthn_challenge_reg_{user.id}"
        expected_challenge = cache.get(challenge_key)
        
        logger.info(f"WebAuthn verify_registration_response for user {user.id} ({user.email})")
        logger.info(f"Challenge key: {challenge_key}, Challenge exists: {expected_challenge is not None}")
        logger.info(f"Allowed origins: {self.allowed_origins}")
        logger.info(f"RP ID: {self.rp_id}")
        
        if not expected_challenge:
            logger.error(f"Challenge not found or expired for user {user.id}")
            raise ValueError(_('Challenge not found or expired. Please try again.'))
        
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
            
            logger.info(f"Attempting WebAuthn verification with origins: {self.allowed_origins}")
            
            # Verify the registration (accept both www and non-www origins)
            verification = verify_registration_response(
                credential=registration_credential,
                expected_challenge=expected_challenge,
                expected_origin=self.allowed_origins,
                expected_rp_id=self.rp_id,
                require_user_verification=True,  # Require user verification
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
            # Only include active credentials
            if 'credential_id' in cred and cred.get('is_active', True):
                allow_credentials.append({
                    'id': base64.b64decode(cred['credential_id']),
                    'type': 'public-key',
                    'transports': cred.get('transports', [])
                })
        
        if not allow_credentials:
            raise ValueError(_('No active credentials available for authentication'))
        
        # Generate authentication options
        options = generate_authentication_options(
            rp_id=self.rp_id,
            allow_credentials=allow_credentials,
            user_verification=UserVerificationRequirement.REQUIRED,  # REQUIRE user verification
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
            
            # Debug logging
            logger.info(f"Verifying authentication for user {user.email}")
            logger.info(f"Credential ID from response (full): {credential_id}")
            logger.info(f"User has {len(user.webauthn_credentials)} stored credentials")
            
            # Log all stored credentials
            for idx, cred in enumerate(user.webauthn_credentials):
                logger.info(f"  Stored credential #{idx+1}: {cred.get('credential_id', 'N/A')}")
                logger.info(f"    is_active: {cred.get('is_active', 'NOT SET')}")
                logger.info(f"    display_name: {cred.get('display_name', 'N/A')}")
            
            # Normalize base64 padding and convert base64url to base64
            def normalize_base64(b64_str):
                # Convert base64url to base64 (- to +, _ to /)
                b64_str = b64_str.replace('-', '+').replace('_', '/')
                # Add padding if missing
                missing_padding = len(b64_str) % 4
                if missing_padding:
                    b64_str += '=' * (4 - missing_padding)
                return b64_str
            
            normalized_credential_id = normalize_base64(credential_id)
            logger.info(f"Normalized credential ID from response: {normalized_credential_id}")
            
            user_credential = None
            
            for idx, cred in enumerate(user.webauthn_credentials):
                # Skip inactive credentials
                if not cred.get('is_active', True):
                    logger.warning(f"Skipping inactive credential #{idx+1}")
                    continue
                    
                stored_id = cred.get('credential_id', '')
                normalized_stored_id = normalize_base64(stored_id)
                logger.info(f"Comparing normalized stored #{idx+1}: {normalized_stored_id}")
                logger.info(f"  Match: {normalized_stored_id == normalized_credential_id}")
                
                if normalized_stored_id == normalized_credential_id:
                    user_credential = cred
                    logger.info(f"✓ Found matching credential #{idx+1}!")
                    break
            
            if not user_credential:
                logger.error(f"❌ No matching credential found!")
                logger.error(f"Response ID (normalized): {normalized_credential_id}")
                logger.error(f"Available active credentials: {sum(1 for c in user.webauthn_credentials if c.get('is_active', True))}")
                raise ValueError(_('Credential not found or inactive'))
            
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
            
            # Verify the authentication (accept both www and non-www origins)
            verification = verify_authentication_response(
                credential=authentication_credential,
                expected_challenge=expected_challenge,
                expected_origin=self.allowed_origins,
                expected_rp_id=self.rp_id,
                credential_public_key=base64.b64decode(user_credential['credential_public_key']),
                credential_current_sign_count=user_credential.get('sign_count', 0),
                require_user_verification=True,  # Require user verification
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
    
    def generate_approval_challenge(self, user: User, approval_id: str, context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate WebAuthn challenge specifically for an approval action (step-up authentication).
        
        Args:
            user: User performing the approval
            approval_id: ID of the approval request
            context_data: Additional context (amount, type, etc.) for cryptographic binding
        
        Returns:
            Dictionary with challenge options
        """
        import secrets
        import hashlib
        
        if not user.webauthn_credentials:
            raise ValueError(_('No credentials registered for this user'))
        
        # Only include active credentials
        active_credentials = [
            cred for cred in user.webauthn_credentials 
            if cred.get('is_active', True)
        ]
        
        if not active_credentials:
            raise ValueError(_('No active credentials found'))
        
        # Prepare allowed credentials
        allow_credentials = []
        for cred in active_credentials:
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
            user_verification=UserVerificationRequirement.REQUIRED,
            timeout=60000,
        )
        
        # Generate unique challenge ID for this approval
        challenge_id = secrets.token_urlsafe(32)
        
        # Create context hash for cryptographic binding (optional but recommended)
        context_hash = None
        if context_data:
            context_str = json.dumps(context_data, sort_keys=True)
            context_hash = hashlib.sha256(context_str.encode()).hexdigest()
        
        # Store challenge with approval context
        challenge_key = f"webauthn_challenge_approval_{user.id}_{approval_id}"
        challenge_data = {
            'challenge': options.challenge,
            'challenge_id': challenge_id,
            'approval_id': approval_id,
            'context_hash': context_hash,
            'created_at': timezone.now().isoformat(),
        }
        cache.set(challenge_key, challenge_data, timeout=self.challenge_timeout)
        
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
            'challengeId': challenge_id,
        }
    
    def verify_approval_response(self, user: User, approval_id: str, credential_data: Dict[str, Any], context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Verify WebAuthn response for approval step-up authentication.
        
        Args:
            user: User performing the approval
            approval_id: ID of the approval request
            credential_data: WebAuthn response from client
            context_data: Context data to verify against stored hash
        
        Returns:
            Dictionary with verification result
        """
        import hashlib
        
        challenge_key = f"webauthn_challenge_approval_{user.id}_{approval_id}"
        challenge_data = cache.get(challenge_key)
        
        if not challenge_data:
            raise ValueError(_('Challenge not found or expired. Please try again.'))
        
        expected_challenge = challenge_data['challenge']
        stored_challenge_id = challenge_data['challenge_id']
        stored_approval_id = challenge_data['approval_id']
        stored_context_hash = challenge_data.get('context_hash')
        
        # Verify approval_id matches
        if stored_approval_id != approval_id:
            cache.delete(challenge_key)
            raise ValueError(_('Challenge does not match the approval request'))
        
        # Verify context hash if provided
        if stored_context_hash and context_data:
            context_str = json.dumps(context_data, sort_keys=True)
            context_hash = hashlib.sha256(context_str.encode()).hexdigest()
            if context_hash != stored_context_hash:
                cache.delete(challenge_key)
                raise ValueError(_('Approval context has changed. Please try again.'))
        
        try:
            # Find the credential
            credential_id = credential_data.get('id', '')
            
            # Debug logging
            logger.info(f"Verifying approval for user {user.email}")
            logger.info(f"Credential ID from response: {credential_id}")
            
            # Normalize base64 padding and convert base64url to base64
            def normalize_base64(b64_str):
                # Convert base64url to base64 (- to +, _ to /)
                b64_str = b64_str.replace('-', '+').replace('_', '/')
                # Add padding if missing
                missing_padding = len(b64_str) % 4
                if missing_padding:
                    b64_str += '=' * (4 - missing_padding)
                return b64_str
            
            normalized_credential_id = normalize_base64(credential_id)
            logger.info(f"Normalized credential ID: {normalized_credential_id}")
            
            user_credential = None
            for cred in user.webauthn_credentials:
                stored_id = cred.get('credential_id', '')
                normalized_stored_id = normalize_base64(stored_id)
                
                if normalized_stored_id == normalized_credential_id:
                    user_credential = cred
                    logger.info(f"✓ Found matching credential!")
                    break
            
            if not user_credential:
                logger.error(f"❌ No matching credential found for approval!")
                logger.error(f"Available credentials: {[c.get('credential_id') for c in user.webauthn_credentials]}")
                raise ValueError(_('Credential not found'))
            
            # Check if credential is active
            if not user_credential.get('is_active', True):
                raise ValueError(_('This credential has been deactivated'))
            
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
            
            # Verify the authentication (accept both www and non-www origins)
            verification = verify_authentication_response(
                credential=authentication_credential,
                expected_challenge=expected_challenge,
                expected_origin=self.allowed_origins,
                expected_rp_id=self.rp_id,
                credential_public_key=base64.b64decode(user_credential['credential_public_key']),
                credential_current_sign_count=user_credential.get('sign_count', 0),
                require_user_verification=True,
            )
            
            # Clean up challenge (one-time use)
            cache.delete(challenge_key)
            
            # Update sign count and last_used_at
            user_credential['sign_count'] = verification.new_sign_count
            user_credential['last_used_at'] = timezone.now().isoformat()
            user.save(update_fields=['webauthn_credentials'])
            
            return {
                'verified': True,
                'credential_id': credential_id,
                'challenge_id': stored_challenge_id,
                'new_sign_count': verification.new_sign_count,
                'user_verified': True,
            }
            
        except Exception as e:
            cache.delete(challenge_key)
            raise ValueError(f'{_("Approval verification failed")}: {str(e)}')


# Global instance
webauthn_service = WebAuthnService()