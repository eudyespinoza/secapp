import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { Document } from 'mongoose';

@Schema({ timestamps: true })
export class Tenant extends Document {
  @Prop({ required: true, unique: true })
  key: string; // e.g., acme

  @Prop({ required: true })
  name: string; // e.g., Acme Inc.

  @Prop({ type: [String], default: [] })
  domains: string[]; // whitelisted domains (optional)

  @Prop({ default: true })
  isActive: boolean;

  // Billing & Plan
  @Prop({ default: 'free' })
  planId: string; // e.g., free, pro, enterprise

  @Prop({ default: 5 })
  seats: number; // max active users

  // Max number of approvers allowed by plan (null or large number = unlimited)
  @Prop({ default: 2 })
  approverLimit: number;

  @Prop({ default: 'inactive' })
  status: string; // inactive|active|past_due|canceled|paused

  @Prop({ type: Object, default: {} })
  billing?: {
    provider?: 'stripe' | 'paddle' | 'manual';
    customerId?: string;
    subscriptionId?: string;
    currentPeriodEnd?: Date;
  };

  @Prop()
  createdAt: Date;

  @Prop()
  updatedAt: Date;
}

export const TenantSchema = SchemaFactory.createForClass(Tenant);

// Indexes
TenantSchema.index({ key: 1 }, { unique: true });
TenantSchema.index({ isActive: 1 });
