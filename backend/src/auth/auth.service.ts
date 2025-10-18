import { Injectable, UnauthorizedException, ConflictException, BadRequestException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { ConfigService } from '@nestjs/config';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { User } from '../users/schemas/user.schema';
import { WebAuthnService } from './webauthn.service';
import * as crypto from 'crypto';

@Injectable()
export class AuthService {
  constructor(
    @InjectModel(User.name) private userModel: Model<User>,
    private jwtService: JwtService,
    private webAuthnService: WebAuthnService,
    private configService: ConfigService,
  ) {}

  async register(registerDto: { name: string; email: string; role?: string }) {
    // Check if user exists
    const existingUser = await this.userModel.findOne({ email: registerDto.email });
    if (existingUser) {
      // If user exists but has no credentials, allow to continue registration
      if (existingUser.credentials && existingUser.credentials.length === 0) {
        return {
          id: existingUser._id.toString(),
          name: existingUser.name,
          email: existingUser.email,
          role: existingUser.role,
          message: 'User exists but needs to complete WebAuthn registration',
        };
      }
      throw new ConflictException('Email already registered');
    }

    // Create new user
    const user = new this.userModel({
      name: registerDto.name,
      email: registerDto.email,
      role: registerDto.role || 'requester',
      credentials: [],
      isActive: true,
    });

    await user.save();

    return {
      id: user._id.toString(),
      name: user.name,
      email: user.email,
      role: user.role,
    };
  }

  async getRegistrationOptions(userId: string) {
    const user = await this.userModel.findById(userId);
    if (!user) {
      throw new UnauthorizedException('User not found');
    }

    const options = await this.webAuthnService.generateRegistrationOptions({
      id: user._id.toString(),
      email: user.email,
      name: user.name,
      credentials: user.credentials,
    });

    return options;
  }

  async verifyRegistration(userId: string, response: any) {
    console.log('=== VERIFY REGISTRATION START ===');
    console.log('userId:', userId);
    console.log('response:', JSON.stringify(response, null, 2));

    const user = await this.userModel.findById(userId);
    if (!user) {
      console.log('ERROR: User not found');
      throw new UnauthorizedException('User not found');
    }

    console.log('User found:', user.email);
    console.log('Current credentials count:', user.credentials.length);

    const verification = await this.webAuthnService.verifyRegistration(userId, response);
    console.log('Verification result:', verification.verified);

    if (verification.verified && verification.registrationInfo) {
      const { credentialPublicKey, credentialID, counter } = verification.registrationInfo;

      console.log('Saving credential to user...');
      // Save credential to user
      // Normalize legacy role value to match enum
      if (user.role === 'user') {
        user.role = 'requester';
      }
      user.credentials.push({
        credentialID: Buffer.from(credentialID).toString('base64'),
        credentialPublicKey: Buffer.from(credentialPublicKey).toString('base64'),
        counter,
        transports: response.response.transports || [],
      });

      console.log('Credentials after push:', user.credentials.length);
      await user.save();
      console.log('User saved successfully');

      // Verify it was saved
      const savedUser = await this.userModel.findById(userId);
      console.log('Verified credentials in DB:', savedUser.credentials.length);

      // Generate tokens
      const tokens = await this.generateTokens(user);

      console.log('=== VERIFY REGISTRATION SUCCESS ===');
      return {
        message: 'Registration successful',
        user: {
          id: user._id.toString(),
          name: user.name,
          email: user.email,
          role: user.role,
        },
        ...tokens,
      };
    }

    console.log('ERROR: Registration verification failed');
    throw new UnauthorizedException('Registration verification failed');
  }

  async getAuthenticationOptions(email: string) {
    console.log('=== GET AUTHENTICATION OPTIONS ===');
    console.log('email:', email);

    const user = await this.userModel.findOne({ email });
    if (!user) {
      console.log('ERROR: User not found');
      throw new UnauthorizedException('User not found');
    }

    console.log('User found:', user.email);
    console.log('User credentials count:', user.credentials.length);
    console.log('User credentials:', JSON.stringify(user.credentials, null, 2));

    if (user.credentials.length === 0) {
      console.log('ERROR: No credentials registered for this user');
      throw new BadRequestException('No credentials registered for this user');
    }

    const options = await this.webAuthnService.generateAuthenticationOptions({
      id: user._id.toString(),
      email: user.email,
      credentials: user.credentials,
    });

    console.log('=== AUTHENTICATION OPTIONS GENERATED ===');
    return {
      options,
      userId: user._id.toString(),
    };
  }

  async verifyAuthentication(userId: string, response: any) {
    console.log('=== VERIFY AUTHENTICATION START ===');
    console.log('userId:', userId);
    console.log('response.id:', response.id);

    const user = await this.userModel.findById(userId);
    if (!user) {
      console.log('ERROR: User not found');
      throw new UnauthorizedException('User not found');
    }

    console.log('User found:', user.email);
    console.log('User credentials count:', user.credentials.length);

    if (!user.isActive) {
      console.log('ERROR: User account is disabled');
      throw new UnauthorizedException('User account is disabled');
    }

    // Find the credential used
    // Convert Base64URL to Base64 for comparison
    const credentialID = response.id;
    const credentialIDBase64 = credentialID
      .replace(/-/g, '+')
      .replace(/_/g, '/');
    
    console.log('Looking for credential with ID:', credentialID);
    console.log('Converted to Base64:', credentialIDBase64);
    
    const credential = user.credentials.find(
      (cred) => {
        const storedID = cred.credentialID.replace(/=+$/, ''); // Remove padding
        const searchID = credentialIDBase64.replace(/=+$/, ''); // Remove padding
        return storedID === searchID;
      }
    );

    if (!credential) {
      console.log('ERROR: Credential not found');
      console.log('Available credentials:', user.credentials.map(c => c.credentialID));
      throw new UnauthorizedException('Credential not found');
    }

    console.log('Credential found, verifying...');
    const verification = await this.webAuthnService.verifyAuthentication(
      userId,
      response,
      credential,
    );

    console.log('Verification result:', verification.verified);

    if (verification.verified) {
      // Update counter
      credential.counter = verification.authenticationInfo.newCounter;
      user.lastLoginAt = new Date();
      // Normalize legacy role value before saving (enum enforcement)
      if (user.role === 'user') {
        user.role = 'requester';
      }
      await user.save();
      console.log('Counter updated, generating tokens...');

      // Generate tokens
      const tokens = await this.generateTokens(user);

      return {
        message: 'Authentication successful',
        user: {
          id: user._id.toString(),
          name: user.name,
          email: user.email,
          role: user.role,
        },
        ...tokens,
      };
    }

    throw new UnauthorizedException('Authentication verification failed');
  }

  async refreshToken(refreshToken: string) {
    try {
      const payload = this.jwtService.verify(refreshToken, {
        secret: this.configService.get('JWT_REFRESH_SECRET'),
      });

      const user = await this.userModel.findById(payload.sub);
      if (!user || !user.isActive) {
        throw new UnauthorizedException('Invalid token');
      }

      const tokens = await this.generateTokens(user);
      return tokens;
    } catch (error) {
      throw new UnauthorizedException('Invalid refresh token');
    }
  }

  async logout(userId: string) {
    // In production, invalidate tokens in Redis
    return { message: 'Logout successful' };
  }

  async validateUser(userId: string) {
    const user = await this.userModel.findById(userId);
    if (!user || !user.isActive) {
      return null;
    }
    return user;
  }

  private async generateTokens(user: any) {
    const payload = {
      sub: user._id.toString(),
      email: user.email,
      role: user.role,
      tenantId: user.tenantId || null,
    };

    const [accessToken, refreshToken] = await Promise.all([
      this.jwtService.signAsync(payload, {
        secret: this.configService.get('JWT_ACCESS_SECRET'),
        expiresIn: this.configService.get('JWT_ACCESS_EXPIRATION') || '15m',
      }),
      this.jwtService.signAsync(payload, {
        secret: this.configService.get('JWT_REFRESH_SECRET'),
        expiresIn: this.configService.get('JWT_REFRESH_EXPIRATION') || '7d',
      }),
    ]);

    return { accessToken, refreshToken };
  }

  // DEV ONLY: Delete user by email
  async deleteUserByEmail(email: string) {
    const user = await this.userModel.findOne({ email });
    if (!user) {
      return { message: 'User not found', deleted: false };
    }
    await this.userModel.deleteOne({ email });
    return { message: 'User deleted successfully', deleted: true, email };
  }
}
