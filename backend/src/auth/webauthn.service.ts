import { Injectable, UnauthorizedException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import {
  generateRegistrationOptions,
  verifyRegistrationResponse,
  generateAuthenticationOptions,
  verifyAuthenticationResponse,
} from '@simplewebauthn/server';
import type {
  RegistrationResponseJSON,
  AuthenticationResponseJSON,
} from '@simplewebauthn/types';

@Injectable()
export class WebAuthnService {
  private readonly rpName: string;
  private readonly rpID: string;
  private readonly origin: string;

  // Store challenges temporarily (in production, use Redis)
  private challenges = new Map<string, string>();

  constructor(private configService: ConfigService) {
    this.rpName = this.configService.get('WEBAUTHN_RP_NAME') || 'SecureApprove';
    this.rpID = this.configService.get('WEBAUTHN_RP_ID') || 'localhost';
    this.origin = this.configService.get('WEBAUTHN_ORIGIN') || 'http://localhost:3000';
  }

  async generateRegistrationOptions(user: any) {
    const options = await generateRegistrationOptions({
      rpName: this.rpName,
      rpID: this.rpID,
      userID: user.id,
      userName: user.email,
      userDisplayName: user.name || user.email,
      timeout: 60000,
      attestationType: 'none',
      excludeCredentials: user.credentials?.map((cred: any) => ({
        id: Buffer.from(cred.credentialID, 'base64'),
        type: 'public-key',
        transports: cred.transports,
      })) || [],
      authenticatorSelection: {
        residentKey: 'preferred',
        userVerification: 'preferred',
        authenticatorAttachment: 'platform',
      },
      supportedAlgorithmIDs: [-7, -257],
    });

    // Store challenge temporarily
    this.challenges.set(user.id, options.challenge);

    return options;
  }

  async verifyRegistration(
    userId: string,
    response: RegistrationResponseJSON,
  ) {
    const expectedChallenge = this.challenges.get(userId);
    if (!expectedChallenge) {
      throw new UnauthorizedException('Challenge not found or expired');
    }

    try {
      const verification = await verifyRegistrationResponse({
        response,
        expectedChallenge,
        expectedOrigin: this.origin,
        expectedRPID: this.rpID,
        requireUserVerification: false,
      });

      // Clean up challenge
      this.challenges.delete(userId);

      if (!verification.verified) {
        throw new UnauthorizedException('Registration verification failed');
      }

      return {
        verified: true,
        registrationInfo: verification.registrationInfo,
      };
    } catch (error) {
      this.challenges.delete(userId);
      throw new UnauthorizedException('Registration verification failed: ' + error.message);
    }
  }

  async generateAuthenticationOptions(user: any) {
    const options = await generateAuthenticationOptions({
      timeout: 60000,
      allowCredentials: user.credentials?.map((cred: any) => ({
        id: Buffer.from(cred.credentialID, 'base64'),
        type: 'public-key',
        transports: cred.transports,
      })) || [],
      userVerification: 'preferred',
      rpID: this.rpID,
    });

    // Store challenge
    this.challenges.set(user.id, options.challenge);

    return options;
  }

  async verifyAuthentication(
    userId: string,
    response: AuthenticationResponseJSON,
    credential: any,
  ) {
    const expectedChallenge = this.challenges.get(userId);
    if (!expectedChallenge) {
      throw new UnauthorizedException('Challenge not found or expired');
    }

    try {
      const verification = await verifyAuthenticationResponse({
        response,
        expectedChallenge,
        expectedOrigin: this.origin,
        expectedRPID: this.rpID,
        authenticator: {
          credentialID: Buffer.from(credential.credentialID, 'base64'),
          credentialPublicKey: Buffer.from(credential.credentialPublicKey, 'base64'),
          counter: credential.counter,
          transports: credential.transports,
        },
        requireUserVerification: false,
      });

      // Clean up challenge
      this.challenges.delete(userId);

      if (!verification.verified) {
        throw new UnauthorizedException('Authentication verification failed');
      }

      return {
        verified: true,
        authenticationInfo: verification.authenticationInfo,
      };
    } catch (error) {
      this.challenges.delete(userId);
      throw new UnauthorizedException('Authentication verification failed: ' + error.message);
    }
  }

  clearChallenge(userId: string) {
    this.challenges.delete(userId);
  }
}
