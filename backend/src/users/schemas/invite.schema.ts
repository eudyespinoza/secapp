import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { Document } from 'mongoose';

export type InviteStatus = 'pending' | 'accepted' | 'revoked' | 'expired';

@Schema({ timestamps: true })
export class Invite extends Document {
  @Prop({ type: String, ref: 'Tenant', index: true, required: true })
  tenantId: string;

  @Prop({ required: true, index: true })
  email: string;

  @Prop({
    required: true,
    enum: ['requester', 'approver', 'auditor', 'tenant_admin'],
    default: 'requester',
  })
  role: string;

  @Prop({ required: true, unique: true, index: true })
  token: string;

  @Prop({ required: true })
  expiresAt: Date;

  @Prop({ default: 'pending' })
  status: InviteStatus;

  @Prop({ type: String })
  createdBy?: string; // userId who created the invite

  @Prop()
  acceptedAt?: Date;
}

export const InviteSchema = SchemaFactory.createForClass(Invite);

InviteSchema.index({ tenantId: 1, email: 1, status: 1 });
InviteSchema.index({ expiresAt: 1 });
