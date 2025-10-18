import { Module } from '@nestjs/common';
import { JwtModule } from '@nestjs/jwt';
import { PassportModule } from '@nestjs/passport';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { MongooseModule } from '@nestjs/mongoose';
import { AuthController } from './auth.controller';
import { AuthService } from './auth.service';
import { WebAuthnService } from './webauthn.service';
import { JwtStrategy } from './strategies/jwt.strategy';
import { JwtAuthGuard } from './guards/jwt-auth.guard';
import { User, UserSchema } from '../users/schemas/user.schema';
import { Invite, InviteSchema } from '../users/schemas/invite.schema';
import { Tenant, TenantSchema } from '../users/schemas/tenant.schema';
import { Credential, CredentialSchema } from './schemas/credential.schema';

@Module({
  imports: [
      PassportModule,
      JwtModule.register({}),
      MongooseModule.forFeature([
        { name: User.name, schema: UserSchema },
        { name: Invite.name, schema: InviteSchema },
        { name: Tenant.name, schema: TenantSchema },
      ]),
  ],
  controllers: [AuthController],
  providers: [AuthService, WebAuthnService, JwtStrategy, JwtAuthGuard],
  exports: [AuthService, WebAuthnService, JwtModule, JwtAuthGuard],
})
export class AuthModule {}
