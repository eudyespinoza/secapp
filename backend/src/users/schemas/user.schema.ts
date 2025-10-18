import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { Document } from 'mongoose';

export interface WebAuthnCredential {
  credentialID: string;
  credentialPublicKey: string;
  counter: number;
  transports?: string[];
}

@Schema({ timestamps: true })
export class User extends Document {
  @Prop({ type: String, ref: 'Tenant', index: true, required: false })
  tenantId?: string;
  @Prop({ required: true, unique: true })
  email: string;

  @Prop()
  name: string;

  @Prop()
  firstName: string;

  @Prop()
  lastName: string;

  @Prop()
  phone: string;

  @Prop({
    default: 'requester',
    enum: ['superadmin', 'tenant_admin', 'requester', 'approver', 'auditor']
  })
  role: string;

  @Prop({ default: true })
  isActive: boolean;

  @Prop({ default: false })
  emailVerified: boolean;

  @Prop({
    type: [{
      credentialID: { type: String, required: true },
      credentialPublicKey: { type: String, required: true },
      counter: { type: Number, required: true },
      transports: { type: [String], default: [] }
    }],
    default: []
  })
  credentials: WebAuthnCredential[];

  @Prop()
  totpSecret: string;

  @Prop({ default: false })
  totpEnabled: boolean;

  @Prop()
  lastLogin: Date;

  @Prop()
  lastLoginAt: Date;

  @Prop()
  company: string;

  @Prop({ type: [String], default: [] })
  refreshTokens: string[];

  @Prop()
  currentChallenge: string;

  @Prop()
  createdAt: Date;

  @Prop()
  updatedAt: Date;
}

export const UserSchema = SchemaFactory.createForClass(User);

// Indexes
UserSchema.index({ email: 1 }, { unique: true });
UserSchema.index({ role: 1 });
UserSchema.index({ tenantId: 1, role: 1 });
UserSchema.index({ isActive: 1 });
