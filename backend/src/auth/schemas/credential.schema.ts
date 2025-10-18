import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { Document } from 'mongoose';

@Schema({ timestamps: true })
export class Credential extends Document {
  @Prop({ required: true })
  userId: string;

  @Prop({ required: true, unique: true })
  credentialId: string;

  @Prop({ required: true })
  publicKey: string;

  @Prop({ required: true })
  counter: number;

  @Prop({ required: true })
  deviceType: string;

  @Prop()
  transports: string[];

  @Prop()
  aaguid: string;

  @Prop({ default: true })
  isActive: boolean;

  @Prop()
  lastUsed: Date;

  @Prop()
  createdAt: Date;

  @Prop()
  updatedAt: Date;
}

export const CredentialSchema = SchemaFactory.createForClass(Credential);

// Indexes
CredentialSchema.index({ userId: 1 });
CredentialSchema.index({ credentialId: 1 }, { unique: true });
