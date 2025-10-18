import { Injectable, ConflictException, NotFoundException, ForbiddenException } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { Invite } from './schemas/invite.schema';
import { Tenant } from './schemas/tenant.schema';
import { User } from './schemas/user.schema';
import { randomBytes } from 'crypto';

@Injectable()
export class InvitesService {
  constructor(
    @InjectModel(Invite.name) private inviteModel: Model<Invite>,
    @InjectModel(Tenant.name) private tenantModel: Model<Tenant>,
    @InjectModel(User.name) private userModel: Model<User>,
  ) {}

  async list(tenantId: string) {
    return this.inviteModel.find({ tenantId, status: { $in: ['pending'] } }).sort({ createdAt: -1 }).exec();
  }

  async create({ tenantId, email, role, createdBy }: { tenantId: string; email: string; role: string; createdBy?: string; }) {
    const tenant = await this.tenantModel.findById(tenantId);
    if (!tenant) throw new NotFoundException('Tenant not found');
    if (tenant.status !== 'active' && tenant.status !== 'past_due') {
      throw new ForbiddenException('Tenant subscription is not active');
    }
    // Enforce approver limit including pending invites
    if (role === 'approver') {
      const approverCount = await this.userModel.countDocuments({ tenantId, role: 'approver', isActive: true });
      const pendingApproverInvites = await this.inviteModel.countDocuments({ tenantId, role: 'approver', status: 'pending' });
      const limit = (tenant as any).approverLimit ?? Infinity;
      if (Number.isFinite(limit) && (approverCount + pendingApproverInvites) >= limit) {
        throw new ConflictException('Approver limit reached for this tenant');
      }
    }
    const existingUser = await this.userModel.findOne({ email, tenantId });
    if (existingUser) throw new ConflictException('User already exists in this tenant');

    const token = randomBytes(24).toString('hex');
    const expiresAt = new Date(Date.now() + 1000 * 60 * 60 * 24 * 7); // 7 days

    const invite = new this.inviteModel({ tenantId, email, role, token, expiresAt, status: 'pending', createdBy });
    await invite.save();
    return {
      id: invite._id.toString(),
      email: invite.email,
      role: invite.role,
      token: invite.token,
      expiresAt: invite.expiresAt,
      status: invite.status,
    };
  }

  async revoke(tenantId: string, id: string) {
    const invite = await this.inviteModel.findOne({ _id: id, tenantId });
    if (!invite) throw new NotFoundException('Invite not found');
    invite.status = 'revoked';
    await invite.save();
    return { message: 'Invite revoked', id };
  }

  async getByToken(token: string) {
    const invite = await this.inviteModel.findOne({ token });
    if (!invite) throw new NotFoundException('Invite not found');
    if (invite.status !== 'pending') throw new ForbiddenException('Invite is not valid');
    if (invite.expiresAt.getTime() < Date.now()) {
      invite.status = 'expired';
      await invite.save();
      throw new ForbiddenException('Invite expired');
    }
    return invite;
  }
}
