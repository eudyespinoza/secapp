import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { Document } from 'mongoose';

@Schema({ timestamps: true })
export class ApprovalRequest extends Document {
  @Prop({ type: String, ref: 'Tenant', index: true, required: false })
  tenantId?: string;
  @Prop({ required: true })
  requesterId: string;

  @Prop({ required: true })
  title: string;

  @Prop({ required: true })
  description: string;

  @Prop({ required: true, enum: ['low', 'medium', 'high', 'critical'] })
  priority: string;

  @Prop({ required: true, enum: ['pending', 'approved', 'rejected', 'cancelled'] })
  status: string;

  @Prop()
  approverId: string;

  @Prop()
  approverComment: string;

  @Prop()
  approvedAt: Date;

  @Prop({ type: Object })
  metadata: Record<string, any>;

  @Prop()
  expiresAt: Date;

  @Prop()
  createdAt: Date;

  @Prop()
  updatedAt: Date;
}

export const ApprovalRequestSchema = SchemaFactory.createForClass(ApprovalRequest);

// Indexes
ApprovalRequestSchema.index({ requesterId: 1 });
ApprovalRequestSchema.index({ approverId: 1 });
ApprovalRequestSchema.index({ status: 1 });
ApprovalRequestSchema.index({ tenantId: 1, status: 1 });
ApprovalRequestSchema.index({ createdAt: -1 });
