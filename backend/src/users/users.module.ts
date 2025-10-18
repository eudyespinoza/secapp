import { Module } from '@nestjs/common';
import { MongooseModule } from '@nestjs/mongoose';
import { UsersController } from './users.controller';
import { InvitesController } from './invites.controller';
import { UsersService } from './users.service';
import { InvitesService } from './invites.service';
import { User, UserSchema } from './schemas/user.schema';
import { Tenant, TenantSchema } from './schemas/tenant.schema';
import { Invite, InviteSchema } from './schemas/invite.schema';
import { AuthModule } from '../auth/auth.module';

@Module({
  imports: [
    MongooseModule.forFeature([
      { name: User.name, schema: UserSchema },
      { name: Tenant.name, schema: TenantSchema },
      { name: Invite.name, schema: InviteSchema },
    ]),
    AuthModule,
  ],
  controllers: [UsersController, InvitesController],
  providers: [UsersService, InvitesService],
  exports: [UsersService],
})
export class UsersModule {}
