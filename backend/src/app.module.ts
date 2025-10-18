import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { MongooseModule } from '@nestjs/mongoose';
import { ThrottlerModule } from '@nestjs/throttler';
// import { CacheModule } from '@nestjs/cache-manager';
// import * as redisStore from 'cache-manager-redis-store';
// import { HealthModule } from './health/health.module';
import { AppController } from './app.controller';
import { AuthModule } from './auth/auth.module';
import { UsersModule } from './users/users.module';
import { RequestsModule } from './requests/requests.module';
import { SecurityModule } from './security/security.module';
import { CommonModule } from './common/common.module';
import { TenantsModule } from './tenants/tenants.module';
import { BillingModule } from './billing/billing.module';

@Module({
  controllers: [AppController],
  imports: [
    // Configuration
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: '../.env',
    }),

    // Database - MongoDB
    MongooseModule.forRootAsync({
      imports: [ConfigModule],
      useFactory: async (configService: ConfigService) => ({
        uri: configService.get<string>('MONGODB_URI'),
        useNewUrlParser: true,
        useUnifiedTopology: true,
        retryWrites: true,
        w: 'majority',
      }),
      inject: [ConfigService],
    }),

    // Cache - Redis (Temporarily disabled - missing dependencies)
    // CacheModule.registerAsync({
    //   isGlobal: true,
    //   imports: [ConfigModule],
    //   useFactory: async (configService: ConfigService) => ({
    //     store: redisStore,
    //     host: configService.get('REDIS_HOST'),
    //     port: configService.get('REDIS_PORT'),
    //     password: configService.get('REDIS_PASSWORD'),
    //     db: configService.get('REDIS_DB'),
    //     ttl: configService.get('REDIS_TTL'),
    //   }),
    //   inject: [ConfigService],
    // }),

    // Rate Limiting
    ThrottlerModule.forRootAsync({
      imports: [ConfigModule],
      useFactory: async (configService: ConfigService) => ([{
        ttl: parseInt(configService.get('RATE_LIMIT_WINDOW_MS') || '60000'),
        limit: parseInt(configService.get('RATE_LIMIT_MAX_REQUESTS') || '10'),
      }]),
      inject: [ConfigService],
    }),

    // Feature Modules
    CommonModule,
    // HealthModule, // Temporarily disabled - missing @nestjs/terminus
    AuthModule,
    UsersModule,
    RequestsModule,
    SecurityModule,
    TenantsModule,
    BillingModule,
  ],
})
export class AppModule {}
