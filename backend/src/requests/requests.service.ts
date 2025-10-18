import { Injectable, NotFoundException, BadRequestException, ForbiddenException } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { ApprovalRequest } from './schemas/request.schema';

@Injectable()
export class RequestsService {
  constructor(
    @InjectModel(ApprovalRequest.name) private requestModel: Model<ApprovalRequest>,
  ) {}

  async findAll(filters?: {
    status?: string;
    requesterId?: string;
    approverId?: string;
    priority?: string;
    page?: number;
    limit?: number;
    tenantId?: string;
  }) {
    const page = filters?.page || 1;
    const limit = filters?.limit || 10;
    const skip = (page - 1) * limit;

    const query: any = {};
    if (filters?.tenantId) {
      query.tenantId = filters.tenantId;
    }

    if (filters?.status) {
      query.status = filters.status;
    }

    if (filters?.requesterId) {
      query.requesterId = filters.requesterId;
    }

    if (filters?.approverId) {
      query.approverId = filters.approverId;
    }

    if (filters?.priority) {
      query.priority = filters.priority;
    }

    const [requests, total] = await Promise.all([
      this.requestModel
        .find(query)
        .sort({ createdAt: -1 })
        .skip(skip)
        .limit(limit)
        .exec(),
      this.requestModel.countDocuments(query),
    ]);

    return {
      data: requests.map(req => ({
        id: req._id.toString(),
        tenantId: req.tenantId,
        requesterId: req.requesterId,
        title: req.title,
        description: req.description,
        priority: req.priority,
        status: req.status,
        approverId: req.approverId,
        approverComment: req.approverComment,
        approvedAt: req.approvedAt,
        metadata: req.metadata,
        expiresAt: req.expiresAt,
        createdAt: req.createdAt,
        updatedAt: req.updatedAt,
      })),
      total,
      page,
      limit,
      totalPages: Math.ceil(total / limit),
    };
  }

  async findOne(id: string) {
    const request = await this.requestModel.findById(id).exec();

    if (!request) {
      throw new NotFoundException('Request not found');
    }

    return {
      id: request._id.toString(),
      requesterId: request.requesterId,
      title: request.title,
      description: request.description,
      priority: request.priority,
      status: request.status,
      approverId: request.approverId,
      approverComment: request.approverComment,
      approvedAt: request.approvedAt,
      metadata: request.metadata,
      expiresAt: request.expiresAt,
      createdAt: request.createdAt,
      updatedAt: request.updatedAt,
    };
  }

  async create(requestData: {
    requesterId: string;
    title: string;
    description: string;
    priority: string;
    metadata?: any;
    expiresAt?: Date;
    tenantId?: string;
  }) {
    // Validate priority
    const validPriorities = ['low', 'medium', 'high', 'critical'];
    if (!validPriorities.includes(requestData.priority)) {
      throw new BadRequestException('Invalid priority level');
    }

    const request = new this.requestModel({
      ...requestData,
      tenantId: requestData.tenantId,
      status: 'pending',
    });

    await request.save();

    return {
      id: request._id.toString(),
      requesterId: request.requesterId,
      title: request.title,
      description: request.description,
      priority: request.priority,
      status: request.status,
      metadata: request.metadata,
      createdAt: request.createdAt,
    };
  }

  async approve(id: string, userId: string, comment?: string) {
    const request = await this.requestModel.findById(id);

    if (!request) {
      throw new NotFoundException('Request not found');
    }

    if (request.status !== 'pending') {
      throw new BadRequestException(`Request is already ${request.status}`);
    }

    // Check if expired
    if (request.expiresAt && new Date() > request.expiresAt) {
      request.status = 'cancelled';
      await request.save();
      throw new BadRequestException('Request has expired');
    }

    request.status = 'approved';
    request.approverId = userId;
    request.approverComment = comment;
    request.approvedAt = new Date();

    await request.save();

    return {
      id: request._id.toString(),
      status: request.status,
      approverId: request.approverId,
      approvedAt: request.approvedAt,
      approverComment: request.approverComment,
    };
  }

  async reject(id: string, userId: string, reason: string) {
    const request = await this.requestModel.findById(id);

    if (!request) {
      throw new NotFoundException('Request not found');
    }

    if (request.status !== 'pending') {
      throw new BadRequestException(`Request is already ${request.status}`);
    }

    if (!reason) {
      throw new BadRequestException('Rejection reason is required');
    }

    request.status = 'rejected';
    request.approverId = userId;
    request.approverComment = reason;
    request.approvedAt = new Date();

    await request.save();

    return {
      id: request._id.toString(),
      status: request.status,
      approverId: request.approverId,
      approverComment: request.approverComment,
    };
  }

  async cancel(id: string, userId: string) {
    const request = await this.requestModel.findById(id);

    if (!request) {
      throw new NotFoundException('Request not found');
    }

    if (request.requesterId !== userId) {
      throw new ForbiddenException('Only the requester can cancel this request');
    }

    if (request.status !== 'pending') {
      throw new BadRequestException(`Cannot cancel ${request.status} request`);
    }

    request.status = 'cancelled';
    await request.save();

    return {
      id: request._id.toString(),
      status: request.status,
    };
  }

  async remove(id: string) {
    const result = await this.requestModel.findByIdAndDelete(id);
    if (!result) {
      throw new NotFoundException('Request not found');
    }
    return { message: 'Request deleted successfully', id };
  }

  async getStats(userId?: string) {
    const query: any = userId ? { requesterId: userId } : {};

    const [total, pending, approved, rejected, cancelled] = await Promise.all([
      this.requestModel.countDocuments(query),
      this.requestModel.countDocuments({ ...query, status: 'pending' }),
      this.requestModel.countDocuments({ ...query, status: 'approved' }),
      this.requestModel.countDocuments({ ...query, status: 'rejected' }),
      this.requestModel.countDocuments({ ...query, status: 'cancelled' }),
    ]);

    // Get priority breakdown
    const byPriority = await this.requestModel.aggregate([
      { $match: query },
      { $group: { _id: '$priority', count: { $sum: 1 } } },
    ]);

    // Get recent activity (last 7 days)
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

    const recentActivity = await this.requestModel.countDocuments({
      ...query,
      createdAt: { $gte: sevenDaysAgo },
    });

    return {
      total,
      pending,
      approved,
      rejected,
      cancelled,
      recentActivity,
      byPriority: byPriority.reduce((acc, curr) => {
        acc[curr._id] = curr.count;
        return acc;
      }, {}),
    };
  }

  async getRecentActivity(limit: number = 10) {
    const requests = await this.requestModel
      .find()
      .sort({ updatedAt: -1 })
      .limit(limit)
      .exec();

    return requests.map(req => ({
      id: req._id.toString(),
      title: req.title,
      status: req.status,
      priority: req.priority,
      requesterId: req.requesterId,
      updatedAt: req.updatedAt,
    }));
  }
}
