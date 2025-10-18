import { Injectable, NotFoundException, ConflictException, ForbiddenException } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { User } from './schemas/user.schema';
import { Tenant } from './schemas/tenant.schema';

@Injectable()
export class UsersService {
  constructor(
    @InjectModel(User.name) private userModel: Model<User>,
    @InjectModel(Tenant.name) private tenantModel: Model<Tenant>,
  ) {}

  async findAll(filters?: { role?: string; isActive?: boolean; search?: string; tenantId?: string }) {
    const query: any = {};

    if (filters?.tenantId) {
      query.tenantId = filters.tenantId;
    }

    if (filters?.role) {
      query.role = filters.role;
    }

    if (filters?.isActive !== undefined) {
      query.isActive = filters.isActive;
    }

    if (filters?.search) {
      query.$or = [
        { email: { $regex: filters.search, $options: 'i' } },
        { name: { $regex: filters.search, $options: 'i' } },
        { firstName: { $regex: filters.search, $options: 'i' } },
        { lastName: { $regex: filters.search, $options: 'i' } },
      ];
    }

    const users = await this.userModel
      .find(query)
      .select('-credentials -totpSecret')
      .sort({ createdAt: -1 })
      .exec();

    return users.map(user => ({
      id: user._id.toString(),
      email: user.email,
      name: user.name || `${user.firstName || ''} ${user.lastName || ''}`.trim(),
      firstName: user.firstName,
      lastName: user.lastName,
      phone: user.phone,
      role: user.role,
      isActive: user.isActive,
      emailVerified: user.emailVerified,
      lastLogin: user.lastLogin,
      createdAt: user.createdAt,
    }));
  }

  async findOne(id: string) {
    const user = await this.userModel
      .findById(id)
      .select('-credentials -totpSecret')
      .exec();

    if (!user) {
      throw new NotFoundException('User not found');
    }

    return {
      id: user._id.toString(),
      email: user.email,
      name: user.name || `${user.firstName || ''} ${user.lastName || ''}`.trim(),
      firstName: user.firstName,
      lastName: user.lastName,
      phone: user.phone,
      role: user.role,
      isActive: user.isActive,
      emailVerified: user.emailVerified,
      lastLogin: user.lastLogin,
      createdAt: user.createdAt,
      updatedAt: user.updatedAt,
    };
  }

  async findByEmail(email: string) {
    return this.userModel.findOne({ email }).exec();
  }

  async create(userData: {
    email: string;
    name?: string;
    firstName?: string;
    lastName?: string;
    phone?: string;
    role?: string;
    tenantId?: string;
  }) {
    // Tenant seats enforcement
    if (userData.tenantId) {
      const tenant = await this.tenantModel.findById(userData.tenantId);
      if (!tenant) throw new NotFoundException('Tenant not found');
      if (tenant.status !== 'active' && tenant.status !== 'past_due') {
        throw new ForbiddenException('Tenant subscription is not active');
      }
      const activeCount = await this.userModel.countDocuments({ tenantId: userData.tenantId, isActive: true });
      if (activeCount >= (tenant.seats ?? 0)) {
        throw new ConflictException('Seat limit reached for this tenant');
      }
      // Approver limit enforcement when creating approvers
      if (userData.role === 'approver') {
        const approverCount = await this.userModel.countDocuments({ tenantId: userData.tenantId, role: 'approver', isActive: true });
        const limit = (tenant as any).approverLimit ?? Infinity;
        if (Number.isFinite(limit) && approverCount >= limit) {
          throw new ConflictException('Approver limit reached for this tenant');
        }
      }
    }
    // Check if user exists
    const existingUser = await this.findByEmail(userData.email);
    if (existingUser) {
      throw new ConflictException('Email already exists');
    }

    const user = new this.userModel({
      ...userData,
      tenantId: userData.tenantId,
      isActive: true,
      emailVerified: false,
      credentials: [],
    });

    await user.save();

    return {
      id: user._id.toString(),
      email: user.email,
      name: user.name,
      firstName: user.firstName,
      lastName: user.lastName,
      phone: user.phone,
      role: user.role,
      isActive: user.isActive,
    };
  }

  async update(id: string, userData: Partial<User>) {
    const user = await this.userModel.findById(id);
    if (!user) {
      throw new NotFoundException('User not found');
    }

    // Check email uniqueness if changing email
    if (userData.email && userData.email !== user.email) {
      const existingUser = await this.findByEmail(userData.email);
      if (existingUser) {
        throw new ConflictException('Email already exists');
      }
    }

    // If changing role to approver, enforce approver limit per tenant
    if (userData.role && userData.role !== user.role && userData.role === 'approver') {
      if (!user.tenantId) {
        throw new ForbiddenException('Approver role requires tenant');
      }
      const tenant = await this.tenantModel.findById(user.tenantId);
      if (!tenant) throw new NotFoundException('Tenant not found');
      const approverCount = await this.userModel.countDocuments({ tenantId: user.tenantId, role: 'approver', isActive: true });
      const limit = (tenant as any).approverLimit ?? Infinity;
      if (Number.isFinite(limit) && approverCount >= limit) {
        throw new ConflictException('Approver limit reached for this tenant');
      }
    }

    Object.assign(user, userData);
    await user.save();

    return {
      id: user._id.toString(),
      email: user.email,
      name: user.name,
      firstName: user.firstName,
      lastName: user.lastName,
      phone: user.phone,
      role: user.role,
      isActive: user.isActive,
      updatedAt: user.updatedAt,
    };
  }

  async remove(id: string) {
    const user = await this.userModel.findById(id);
    if (!user) {
      throw new NotFoundException('User not found');
    }

    // Soft delete - just deactivate
    user.isActive = false;
    await user.save();

    return { message: 'User deactivated successfully', id };
  }

  async hardDelete(id: string) {
    const result = await this.userModel.findByIdAndDelete(id);
    if (!result) {
      throw new NotFoundException('User not found');
    }
    return { message: 'User permanently deleted', id };
  }

  async getUserStats() {
    const total = await this.userModel.countDocuments();
    const active = await this.userModel.countDocuments({ isActive: true });
    const byTenant = await this.userModel.aggregate([
      { $match: { isActive: true, tenantId: { $ne: null } } },
      { $group: { _id: '$tenantId', count: { $sum: 1 } } },
    ]);
    const byRole = await this.userModel.aggregate([
      { $group: { _id: '$role', count: { $sum: 1 } } },
    ]);

    return {
      total,
      active,
      inactive: total - active,
      byTenant: byTenant.reduce((acc, curr) => { acc[curr._id] = curr.count; return acc; }, {}),
      byRole: byRole.reduce((acc, curr) => {
        acc[curr._id] = curr.count;
        return acc;
      }, {}),
    };
  }
}
