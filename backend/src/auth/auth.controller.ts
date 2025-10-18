import { Controller, Get, Post, Body, UseGuards, Req, UnauthorizedException, NotFoundException, ForbiddenException, ConflictException } from '@nestjs/common';
import { AuthService } from './auth.service';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { User } from '../users/schemas/user.schema';
import { Invite } from '../users/schemas/invite.schema';
import { Tenant } from '../users/schemas/tenant.schema';

@Controller('auth')
export class AuthController {
  constructor(
    private readonly authService: AuthService,
    @InjectModel(User.name) private userModel: Model<User>,
    @InjectModel(Invite.name) private inviteModel: Model<Invite>,
    @InjectModel(Tenant.name) private tenantModel: Model<Tenant>,
  ) {}

  @Post('register')
  async register(@Body() registerDto: { name: string; email: string; role?: string }) {
    return this.authService.register(registerDto);
  }

  @Post('register/options')
  async getRegistrationOptions(@Body() body: { userId: string }) {
    return this.authService.getRegistrationOptions(body.userId);
  }

  @Post('register/verify')
  async verifyRegistration(@Body() body: { userId: string; response: any }) {
    return this.authService.verifyRegistration(body.userId, body.response);
  }

  @Post('login/options')
  async getAuthenticationOptions(@Body() body: { email: string }) {
    return this.authService.getAuthenticationOptions(body.email);
  }

  @Post('login/verify')
  async verifyAuthentication(@Body() body: { userId: string; response: any }) {
    return this.authService.verifyAuthentication(body.userId, body.response);
  }

  @Post('refresh')
  async refreshToken(@Body() body: { refreshToken: string }) {
    if (!body.refreshToken) {
      throw new UnauthorizedException('Refresh token is required');
    }
    return this.authService.refreshToken(body.refreshToken);
  }

  @Post('logout')
  async logout(@Body() body: { userId: string }) {
    return this.authService.logout(body.userId);
  }

  // Accept invite and create user
  @Post('invite/accept')
  async acceptInvite(@Body() body: { token: string; name: string }) {
    const invite = await this.inviteModel.findOne({ token: body.token });
    if (!invite) throw new NotFoundException('Invite not found');
    if (invite.status !== 'pending') throw new ForbiddenException('Invite is not valid');
    if (invite.expiresAt.getTime() < Date.now()) {
      invite.status = 'expired';
      await invite.save();
      throw new ForbiddenException('Invite expired');
    }

    const tenant = await this.tenantModel.findById(invite.tenantId);
    if (!tenant) throw new NotFoundException('Tenant not found');

    // Check if user already exists in this tenant
    const existing = await this.userModel.findOne({ email: invite.email, tenantId: invite.tenantId });
    if (existing) throw new ConflictException('User already exists');

    const user = new this.userModel({
      email: invite.email,
      name: body.name,
      role: invite.role,
      tenantId: invite.tenantId,
      isActive: true,
      credentials: [],
    });
    await user.save();

    invite.status = 'accepted';
    invite.acceptedAt = new Date();
    await invite.save();

    // Issue tokens so the user can continue onboarding
    const tokens = await this.authService['generateTokens'](user as any);
    return {
      message: 'Invite accepted',
      user: { id: user._id.toString(), email: user.email, role: user.role, tenantId: user.tenantId },
      ...tokens,
    };
  }

  @Get('me')
  async getProfile(@Req() req: any) {
    // TODO: Implement JWT guard to extract user from token
    return { message: 'Get current user profile - requires JWT guard' };
  }

  // DEV ONLY: Delete user by email for testing
  @Post('dev/delete-user')
  async deleteUserByEmail(@Body() body: { email: string }) {
    if (process.env.NODE_ENV !== 'development') {
      throw new UnauthorizedException('This endpoint is only available in development');
    }
    return this.authService.deleteUserByEmail(body.email);
  }

  // DEV ONLY: Seed a superadmin if not exists
  @Post('dev/seed-superadmin')
  async seedSuperAdmin(@Body() body: { email: string; name?: string }) {
    if (process.env.NODE_ENV !== 'development') {
      throw new UnauthorizedException('This endpoint is only available in development');
    }
    const email = body.email || 'superadmin@example.com';
    let user = await this.userModel.findOne({ email });
    if (!user) {
      user = new this.userModel({ email, name: body.name || 'Super Admin', role: 'superadmin', isActive: true });
      await user.save();
    } else {
      user.role = 'superadmin';
      user.isActive = true;
      await user.save();
    }
    return { id: user._id.toString(), email: user.email, role: user.role };
  }

  // DEV ONLY: Normalize legacy role 'user' -> 'requester'
  @Post('dev/normalize-roles')
  async normalizeRoles() {
    if (process.env.NODE_ENV !== 'development') {
      throw new UnauthorizedException('This endpoint is only available in development');
    }
    const outdated = await this.userModel.find({ role: 'user' }).select('email role');
    if (outdated.length === 0) {
      return { message: 'No users with legacy role found', updated: 0 };
    }
    const emails = outdated.map(u => u.email);
    await this.userModel.updateMany({ role: 'user' }, { $set: { role: 'requester' } });
    return { message: 'Normalized legacy roles', updated: outdated.length, emails };
  }
}
