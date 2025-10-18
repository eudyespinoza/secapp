import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { AuditLog } from './schemas/audit-log.schema';

@Injectable()
export class SecurityService {
  constructor(
    @InjectModel(AuditLog.name) private auditLogModel: Model<AuditLog>,
  ) {}

  async logEvent(eventData: {
    userId: string;
    action: string;
    resource: string;
    ipAddress?: string;
    userAgent?: string;
    metadata?: any;
    severity?: string;
    suspicious?: boolean;
  }) {
    const log = new this.auditLogModel({
      ...eventData,
      severity: eventData.severity || 'info',
      suspicious: eventData.suspicious || false,
    });

    await log.save();

    return {
      id: log._id.toString(),
      logged: true,
      timestamp: log.createdAt,
    };
  }

  async getAuditLogs(filters?: {
    userId?: string;
    action?: string;
    resource?: string;
    severity?: string;
    suspicious?: boolean;
    startDate?: Date;
    endDate?: Date;
    page?: number;
    limit?: number;
  }) {
    const page = filters?.page || 1;
    const limit = filters?.limit || 50;
    const skip = (page - 1) * limit;

    const query: any = {};

    if (filters?.userId) {
      query.userId = filters.userId;
    }

    if (filters?.action) {
      query.action = { $regex: filters.action, $options: 'i' };
    }

    if (filters?.resource) {
      query.resource = { $regex: filters.resource, $options: 'i' };
    }

    if (filters?.severity) {
      query.severity = filters.severity;
    }

    if (filters?.suspicious !== undefined) {
      query.suspicious = filters.suspicious;
    }

    if (filters?.startDate || filters?.endDate) {
      query.createdAt = {};
      if (filters.startDate) {
        query.createdAt.$gte = filters.startDate;
      }
      if (filters.endDate) {
        query.createdAt.$lte = filters.endDate;
      }
    }

    const [logs, total] = await Promise.all([
      this.auditLogModel
        .find(query)
        .sort({ createdAt: -1 })
        .skip(skip)
        .limit(limit)
        .exec(),
      this.auditLogModel.countDocuments(query),
    ]);

    return {
      data: logs.map(log => ({
        id: log._id.toString(),
        userId: log.userId,
        action: log.action,
        resource: log.resource,
        ipAddress: log.ipAddress,
        userAgent: log.userAgent,
        metadata: log.metadata,
        severity: log.severity,
        suspicious: log.suspicious,
        createdAt: log.createdAt,
      })),
      total,
      page,
      limit,
      totalPages: Math.ceil(total / limit),
    };
  }

  async getSecurityEvents(filters?: {
    severity?: string;
    suspicious?: boolean;
    limit?: number;
  }) {
    const limit = filters?.limit || 100;
    const query: any = {};

    if (filters?.severity) {
      query.severity = { $in: ['error', 'critical', 'warning'] };
    }

    if (filters?.suspicious !== undefined) {
      query.suspicious = true;
    }

    const events = await this.auditLogModel
      .find(query)
      .sort({ createdAt: -1 })
      .limit(limit)
      .exec();

    return {
      data: events.map(event => ({
        id: event._id.toString(),
        userId: event.userId,
        action: event.action,
        resource: event.resource,
        severity: event.severity,
        suspicious: event.suspicious,
        ipAddress: event.ipAddress,
        createdAt: event.createdAt,
      })),
      total: events.length,
    };
  }

  async getSecurityStats() {
    const [
      total,
      suspicious,
      bySevert,
      recentCritical
    ] = await Promise.all([
      this.auditLogModel.countDocuments(),
      this.auditLogModel.countDocuments({ suspicious: true }),
      this.auditLogModel.aggregate([
        { $group: { _id: '$severity', count: { $sum: 1 } } },
      ]),
      this.auditLogModel.countDocuments({
        severity: 'critical',
        createdAt: { $gte: new Date(Date.now() - 24 * 60 * 60 * 1000) },
      }),
    ]);

    return {
      total,
      suspicious,
      recentCritical,
      bySeverity: bySevert.reduce((acc, curr) => {
        acc[curr._id] = curr.count;
        return acc;
      }, {}),
    };
  }

  async flagSuspicious(logId: string) {
    const log = await this.auditLogModel.findById(logId);
    if (!log) {
      throw new Error('Audit log not found');
    }

    log.suspicious = true;
    log.severity = 'critical';
    await log.save();

    return { message: 'Event flagged as suspicious', id: logId };
  }

  async getUserActivity(userId: string, limit: number = 20) {
    const logs = await this.auditLogModel
      .find({ userId })
      .sort({ createdAt: -1 })
      .limit(limit)
      .exec();

    return logs.map(log => ({
      id: log._id.toString(),
      action: log.action,
      resource: log.resource,
      ipAddress: log.ipAddress,
      severity: log.severity,
      createdAt: log.createdAt,
    }));
  }
}
