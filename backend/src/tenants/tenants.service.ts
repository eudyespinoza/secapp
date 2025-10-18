import { Injectable, NotFoundException, ConflictException, ForbiddenException } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { Tenant } from '../users/schemas/tenant.schema';

@Injectable()
export class TenantsService {
  constructor(@InjectModel(Tenant.name) private tenantModel: Model<Tenant>) {}

  async list() {
    return this.tenantModel.find().sort({ createdAt: -1 }).exec();
  }

  async get(id: string) {
    const tenant = await this.tenantModel.findById(id).exec();
    if (!tenant) throw new NotFoundException('Tenant not found');
    return tenant;
  }

  async create(data: { key: string; name: string; domains?: string[] }) {
    const exists = await this.tenantModel.findOne({ key: data.key }).exec();
    if (exists) throw new ConflictException('Tenant key already exists');
    const tenant = new this.tenantModel({ ...data, isActive: true });
    await tenant.save();
    return tenant;
  }

  async update(id: string, data: Partial<Tenant>) {
    const tenant = await this.tenantModel.findById(id).exec();
    if (!tenant) throw new NotFoundException('Tenant not found');
    Object.assign(tenant, data);
    await tenant.save();
    return tenant;
  }

  async remove(id: string) {
    const tenant = await this.tenantModel.findById(id).exec();
    if (!tenant) throw new NotFoundException('Tenant not found');
    await tenant.deleteOne();
    return { message: 'Tenant deleted', id };
  }
}
